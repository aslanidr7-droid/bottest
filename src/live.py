"""Pure decision logic for the live bot. Same signal code as the backtest (src/signals.py).
No broker calls here: decide() takes market data + bot state, returns intended orders."""
import json
import math
import pandas as pd
import yfinance as yf
from .config import ROOT, S
from .signals import core_targets, sleeve_entry, sleeve_exit, SLEEVE_DEFAULTS

CORE = json.load(open(ROOT / "config" / "core.json"))
SLEEVES = json.load(open(ROOT / "config" / "sleeves.json"))
LIVE = ROOT / "data" / "live"


def tickers():
    t = {CORE["engine"], CORE["safe"], S["cash"], "SPY"}
    t |= {s.split()[0] for s in SLEEVES["sleeves"]}
    return sorted(t)


class DataError(Exception):
    pass


def fetch(days=500, tries=3):
    """Fresh daily bars for the live bot (separate from frozen research data).
    Downloads one ticker at a time (no threads -> no yfinance cache lock), retries, and raises
    DataError if any ticker is still missing so the bot halts with a clear reason."""
    import time
    LIVE.mkdir(parents=True, exist_ok=True)
    try:
        yf.set_tz_cache_location(str(LIVE / "yf_cache"))
    except Exception:
        pass
    frames, missing = {}, []
    for t in tickers():
        d = None
        for k in range(tries):
            try:
                d = yf.download(t, period=f"{days}d", auto_adjust=True, progress=False, threads=False,
                                multi_level_index=False)
            except Exception:
                d = None
            if d is not None and len(d.dropna()) >= 250:
                break
            time.sleep(2 * (k + 1))
        if d is None or len(d.dropna()) < 250:
            missing.append(t)
        else:
            frames[t] = d
    if missing:
        raise DataError(f"no data for {', '.join(missing)} after {tries} tries")
    out = {f: pd.DataFrame({t: frames[t][f.capitalize()] for t in tickers()}) for f in ["open", "high", "low", "close"]}
    pd.concat(out, axis=1).to_parquet(LIVE / "bars.parquet")
    return {k: v.dropna(how="all") for k, v in out.items()}


def check_bars(bars, today):
    """Every ticker must have a bar for today; otherwise halt."""
    last = bars["close"].loc[:pd.Timestamp(today)].iloc[-1]
    bad = [t for t, v in last.items() if pd.isna(v)]
    if bad:
        raise DataError(f"missing today's bar for {', '.join(bad)}")


def cut(bars, as_of):
    return {k: v.loc[:pd.Timestamp(as_of)] for k, v in bars.items()}


def core_pick(closes, override=None):
    w = core_targets(closes, CORE["engine"], CORE["safe"], CORE["n"], CORE["kind"]).iloc[-1]
    rule = w.idxmax() if w.notna().all() else None
    if override:
        rule = {"engine": CORE["engine"], "safe": CORE["safe"], "cash": S["cash"]}.get(override["action"], rule)
    return rule


def decide(bars, state, equity, today, allow_new_sleeves=True, override=None):
    """Return list of intended orders [{ticker, side, qty, sleeve}] for the next open, and new state."""
    C = bars["close"]
    px = C.iloc[-1]
    orders = []
    st = json.loads(json.dumps(state))  # copy
    # ----- core -----
    want = core_pick(C, override)
    held = st.get("core", {})
    if want and held.get("ticker") != want:
        if held.get("qty", 0) > 0:
            orders.append(dict(ticker=held["ticker"], side="sell", qty=held["qty"], sleeve="core"))
        qty = math.floor(equity * 1.0 / px[want])
        orders.append(dict(ticker=want, side="buy", qty=qty, sleeve="core"))
        st["core_pending"] = dict(ticker=want, qty=qty)
    # ----- sleeves -----
    sl = st.setdefault("sleeves", {})
    off_file = ROOT / "state" / "sleeves_off.json"
    off = json.loads(off_file.read_text()) if off_file.exists() else {}
    for name in SLEEVES["sleeves"]:
        t, fam = name.split()
        p = SLEEVE_DEFAULTS[fam]
        s = sl.setdefault(name, {"qty": 0})
        c = C[t].dropna()
        if s.get("qty", 0) > 0:
            s["days"] = s.get("days", 0) + 1
            if bool(sleeve_exit(fam, c, p).iloc[-1]) or s["days"] >= p["max_days"]:
                orders.append(dict(ticker=t, side="sell", qty=s["qty"], sleeve=name))
        elif s.get("last_exit") == str(today.date()):
            continue  # no same-day re-entry (matches backtest)
        elif name in off:
            continue  # switched off by the kill line
        elif allow_new_sleeves and bool(sleeve_entry(fam, c, p).iloc[-1]):
            qty = math.floor(equity * SLEEVES["slot"] / px[t])
            if qty > 0:
                orders.append(dict(ticker=t, side="buy", qty=qty, sleeve=name))
    return orders, st


def client_order_id(day, o):
    return f"{day}-{o['ticker']}-{o['side']}-{o['sleeve'].replace(' ', '_')}"
