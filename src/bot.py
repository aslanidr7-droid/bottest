"""P8: the bot. Evening loop (after 19:00 New York) and morning check (after 09:35).

Evening, 11 steps: lock -> calendar -> reconcile -> data -> regime -> signals -> AI call -> weights -> risk -> orders -> log
Morning: confirm fills, place broker-side stop orders for new sleeve buys, morning summary.

Usage: python -m src.bot evening [--dry-run] [--as-of YYYY-MM-DD]
       python -m src.bot morning | status | pause | resume | sell-all
"""
import argparse
import json
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd
from .config import ROOT
from . import live, risk, notify
from .ai_layer import active_override
from .signals import SLEEVE_DEFAULTS

NY = ZoneInfo("America/New_York")
STATE_DIR = ROOT / "state"
STATE = STATE_DIR / "state.json"
LOCK = STATE_DIR / "lock"
RUNS = ROOT / "logs" / "runs.jsonl"


class Halt(Exception):
    pass


def load_state():
    return json.loads(STATE.read_text()) if STATE.exists() else {"core": {}, "sleeves": {}, "pending": []}


def save_state(st):
    STATE_DIR.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(st, indent=2, default=str))


def log_run(rec):
    RUNS.parent.mkdir(exist_ok=True)
    with open(RUNS, "a") as f:
        f.write(json.dumps(rec, default=str) + "\n")


# ---------- sync fills / stops ----------
def sync(broker, st, today):
    keep, notes = [], []
    for p in st.get("pending", []):
        q = broker.order_by_cid(p["cid"])
        if q is None or q["status"] in ("new", "accepted", "pending_new", "held"):
            keep.append(p); continue
        if q["status"] != "filled":
            notes.append(f"order {p['cid']} {q['status']}"); continue
        qty, px = q["filled_qty"], q["filled_avg_price"]
        if p["sleeve"] == "core":
            if p["side"] == "sell":
                st["core"] = {}
            else:
                st["core"] = {"ticker": p["ticker"], "qty": qty}
        else:
            s = st["sleeves"].setdefault(p["sleeve"], {"qty": 0})
            if p["side"] == "buy":
                s.update(qty=qty, entry_price=px, entry_date=today, days=0, stop_id=None)
            else:
                s.update(qty=0, last_exit=today, stop_id=None)
    st["pending"] = keep
    for name, s in st.get("sleeves", {}).items():
        if s.get("qty", 0) > 0 and s.get("stop_id"):
            q = broker.order_by_id(s["stop_id"])
            if q and q["status"] == "filled":
                notes.append(f"{name} stopped out at {q['filled_avg_price']:.2f}")
                s.update(qty=0, last_exit=today, stop_id=None)
    st.pop("core_pending", None)
    return notes


def expected_positions(st):
    exp = {}
    if st.get("core", {}).get("qty"):
        exp[st["core"]["ticker"]] = exp.get(st["core"]["ticker"], 0) + st["core"]["qty"]
    for name, s in st.get("sleeves", {}).items():
        if s.get("qty"):
            t = name.split()[0]
            exp[t] = exp.get(t, 0) + s["qty"]
    return exp


def reconcile(broker, st):
    have, exp = broker.positions(), expected_positions(st)
    bad = {t: (have.get(t, 0), exp.get(t, 0)) for t in set(have) | set(exp) if have.get(t, 0) != exp.get(t, 0)}
    if bad:
        raise Halt(f"reconcile mismatch (broker, bot): {bad}")


# ---------- evening ----------
def evening(broker, bars=None, as_of=None, dry_run=False, now=None):
    now = now or datetime.now(NY)
    today = pd.Timestamp(as_of or now.date())
    tstr = str(today.date())
    st = load_state()
    rec = dict(job="evening", day=tstr, dry_run=dry_run, at=str(now))
    # 1 lock
    if LOCK.exists() and time.time() - LOCK.stat().st_mtime < 3600 and not dry_run:
        raise Halt("another run holds the lock")
    STATE_DIR.mkdir(exist_ok=True)
    LOCK.write_text(str(now))
    try:
        # 2 calendar
        if st.get("last_evening") == tstr and not dry_run:
            return {"skipped": "already ran today"}
        # 3 reconcile
        notes = sync(broker, st, tstr)
        reconcile(broker, st)
        # 4 data
        bars = bars or live.fetch()
        bars = live.cut(bars, today)
        last = bars["close"].index[-1]
        if last.normalize() != today.normalize():
            raise Halt(f"last bar is {last.date()}, not today {tstr} (holiday or stale data)")
        # 5-7 regime, signals, AI call
        override = active_override(today, list(bars["close"].index))
        acct = broker.account()
        allow, reasons = risk.check(acct, st)
        if risk.SELL_ALL.exists():
            if not dry_run:
                broker.close_all(); risk.SELL_ALL.unlink()
                st.update(core={}, sleeves={}, pending=[])
                risk.pause(True)
            rec.update(action="SELL ALL"); notify.send("SELL ALL executed; bot paused.")
            return rec
        orders, st2 = live.decide(bars, st, acct["equity"], today, allow_new_sleeves=allow, override=override)
        # 8 weights -> 9 risk caps
        prices = bars["close"].iloc[-1]
        targets = {"core": acct["equity"]}
        targets.update({n: acct["equity"] * live.SLEEVES["slot"] for n in live.SLEEVES["sleeves"]})
        orders, dropped = risk.cap_orders(orders, acct["equity"], prices, targets)
        # 10 orders
        sent = []
        for o in orders:
            cid = live.client_order_id(tstr, o)
            if broker.order_by_cid(cid) is not None:
                continue  # never send the same order twice
            if o["sleeve"] != "core" and o["side"] == "sell":
                sid = st2["sleeves"][o["sleeve"]].get("stop_id")
                if sid and not dry_run:
                    broker.cancel(sid)  # cancel the stop before selling
            if not dry_run:
                broker.submit_opg(o["ticker"], o["side"], o["qty"], cid)
                st2.setdefault("pending", []).append({**o, "cid": cid})
            sent.append({**o, "cid": cid, "value": round(o["qty"] * float(prices[o["ticker"]]), 2)})
        # 11 log
        st2["last_evening"] = tstr
        rec.update(equity=acct["equity"], core=live.core_pick(bars["close"], override), override=override,
                   risk=reasons, orders=sent, dropped=dropped, notes=notes)
        if not dry_run:
            save_state(st2)
            log_run(rec)
            notify.send(evening_summary(rec))
        return rec
    except Halt as e:
        rec.update(halt=str(e))
        if not dry_run:
            log_run(rec); notify.send(f"ALPHA bot HALTED: {e}")
        return rec
    finally:
        if LOCK.exists():
            LOCK.unlink()


def evening_summary(r):
    lines = [f"ALPHA evening {r['day']}: equity ${r['equity']:,.0f}, core={r['core']}"]
    if r.get("override"):
        lines.append(f"AI override: {r['override']['action']} {r['override']['days']}d")
    lines += [f"  {o['side']} {o['qty']} {o['ticker']} ({o['sleeve']}) ~${o['value']:,.0f}" for o in r["orders"]] or ["  no orders"]
    lines += [f"  risk: {x}" for x in r["risk"]] + [f"  note: {x}" for x in r["notes"]]
    return "\n".join(lines)


# ---------- morning ----------
def morning(broker, now=None):
    now = now or datetime.now(NY)
    tstr = str(now.date())
    st = load_state()
    notes = sync(broker, st, tstr)
    placed = []
    for name, s in st.get("sleeves", {}).items():
        if s.get("qty", 0) > 0 and not s.get("stop_id"):
            fam = name.split()[1]
            stop_px = s["entry_price"] * (1 - SLEEVE_DEFAULTS[fam]["stop"])
            s["stop_id"] = broker.submit_stop(name.split()[0], s["qty"], stop_px, f"{tstr}-{name.replace(' ', '_')}-stop")
            placed.append(f"{name} stop {stop_px:.2f}")
    st["last_morning"] = tstr
    save_state(st)
    acct = broker.account()
    rec = dict(job="morning", day=tstr, equity=acct["equity"], positions=broker.positions(), stops=placed, notes=notes)
    log_run(rec)
    notify.send(f"ALPHA morning {tstr}: equity ${acct['equity']:,.0f}, positions {rec['positions']}"
                + "".join(f"\n  {x}" for x in placed + notes))
    return rec


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("job", choices=["evening", "morning", "status", "pause", "resume", "sell-all"])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--as-of")
    a = ap.parse_args(argv)
    if a.job == "pause":
        risk.pause(True); print("paused"); return
    if a.job == "resume":
        risk.pause(False); print("resumed"); return
    if a.job == "sell-all":
        risk.STATE.mkdir(exist_ok=True); risk.SELL_ALL.write_text("1"); print("sell-all queued for next evening run"); return
    from .broker import Alpaca, keys_present
    print("keys:", keys_present())
    b = Alpaca()
    if a.job == "status":
        print(json.dumps(dict(account=b.account(), positions=b.positions(), state=load_state()), indent=2, default=str)); return
    r = evening(b, as_of=a.as_of, dry_run=a.dry_run) if a.job == "evening" else morning(b)
    print(json.dumps(r, indent=2, default=str))
    if r.get("halt"):
        sys.exit(2)


if __name__ == "__main__":
    main()
