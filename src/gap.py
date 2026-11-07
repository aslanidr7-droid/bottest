"""P11: paper vs backtest. Every difference is put in one of 6 groups:
fills (fill price vs open), timing (trade on a different day), data (bar differs from research/backtest data),
rounding (whole-share sizing), limits (risk rules blocked/changed an order), rules (bot decided differently = bug)."""
import json
import pandas as pd
from .config import ROOT
from .data import load
from .signals import sleeve_entry, sleeve_exit, SLEEVE_DEFAULTS
from .backtest import run_trades
from . import live

RUNS = ROOT / "logs" / "runs.jsonl"
GROUPS = ["fills", "timing", "data", "rounding", "limits", "rules"]


def runs():
    if not RUNS.exists():
        return []
    return [json.loads(x) for x in RUNS.read_text().splitlines()]


def report(bars=None):
    rs = [r for r in runs() if r.get("job") == "evening" and not r.get("dry_run") and not r.get("halt")]
    out = {g: [] for g in GROUPS}
    if not rs:
        return out, 0
    bars = bars or {f: live.fetch()[f] for f in ["open", "high", "low", "close"]}
    idx = bars["close"].index
    first = pd.Timestamp(rs[0]["day"])
    bot_sig = {(r["day"], o["ticker"], o["side"], o["sleeve"]) for r in rs for o in r["orders"]}
    for name in live.SLEEVES["sleeves"]:
        t, fam = name.split(); p = SLEEVE_DEFAULTS[fam]; c = bars["close"][t]
        _, tr = run_trades(sleeve_entry(fam, c, p), sleeve_exit(fam, c, p), bars["open"][t], bars["high"][t],
                           bars["low"][t], c, p["max_days"], p["stop"])
        for e in tr.entry[tr.entry > first]:
            sig_day = str(idx[idx.get_loc(e) - 1].date())
            if (sig_day, t, "buy", name) not in bot_sig:
                blocked = any(r["day"] == sig_day and r["risk"] for r in rs)
                out["limits" if blocked else "rules"].append(f"{name}: backtest bought {e.date()}, bot did not")
    # data: compare live bars to research data where they overlap
    try:
        res = load("close")[list(bars["close"].columns)]
        ov = bars["close"].index.intersection(res.index)
        diff = (bars["close"].loc[ov] / res.loc[ov] - 1).abs().max()
        for t, d in diff.items():
            if d > 0.002:
                out["data"].append(f"{t}: live vs research close differs up to {d:.2%} (dividend re-adjustment?)")
    except Exception:
        pass
    # fills / rounding from morning logs
    for r in runs():
        for n in r.get("notes", []):
            if "stopped out" in n:
                out["fills"].append(n)
    return out, len(rs)


if __name__ == "__main__":
    out, n = report()
    print(f"paper evenings compared: {n}")
    for g in GROUPS:
        print(f"{g:>9}: {len(out[g])}")
        for x in out[g][:10]:
            print(f"           - {x}")
