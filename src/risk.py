"""P8b risk limits.
1. PAUSE file -> no new sleeves, no borrowing. Core and stops keep working. SELL_ALL file -> flatten.
2. Day loss > 3% -> no new sleeves today. Day loss > 5% -> bot writes PAUSE itself.
3. Drawdown deeper than the training worst -> stop borrowing (no new sleeves).
4. No order bigger than 105% of its target.
"""
import json
from .config import ROOT

STATE = ROOT / "state"
PAUSE, SELL_ALL = STATE / "PAUSE", STATE / "SELL_ALL"
DAY_SOFT, DAY_HARD, ORDER_CAP = 0.03, 0.05, 1.05


def train_worst_dd():
    import pandas as pd
    try:
        t = pd.read_csv(ROOT / "results" / "portfolio.csv").set_index("backtest")
        return float(t.loc["Whole account", "train_dd"])
    except Exception:
        return -0.30


def check(acct, state):
    """Return (allow_new_sleeves, reasons)."""
    reasons = []
    eq, last = acct["equity"], acct["last_equity"] or acct["equity"]
    day = eq / last - 1
    peak = max(state.get("peak_equity", eq), eq)
    state["peak_equity"] = peak
    dd = eq / peak - 1
    if PAUSE.exists():
        reasons.append("PAUSE file present")
    if day < -DAY_HARD:
        STATE.mkdir(exist_ok=True)
        PAUSE.write_text(json.dumps({"reason": f"day loss {day:.1%}"}))
        reasons.append(f"day loss {day:.1%} > {DAY_HARD:.0%}: PAUSE written")
    elif day < -DAY_SOFT:
        reasons.append(f"day loss {day:.1%} > {DAY_SOFT:.0%}: no new sleeves today")
    if dd < train_worst_dd():
        reasons.append(f"drawdown {dd:.1%} deeper than training worst: borrowing stopped")
    return (len(reasons) == 0), reasons


def cap_orders(orders, equity, prices, targets):
    """Drop any order whose value exceeds 105% of its target value."""
    ok, dropped = [], []
    for o in orders:
        tgt = targets.get(o["sleeve"], equity)
        if o["side"] == "buy" and o["qty"] * prices[o["ticker"]] > ORDER_CAP * tgt:
            dropped.append(o)
        else:
            ok.append(o)
    return ok, dropped


def pause(on=True):
    STATE.mkdir(exist_ok=True)
    if on:
        PAUSE.write_text(json.dumps({"reason": "manual"}))
    elif PAUSE.exists():
        PAUSE.unlink()
