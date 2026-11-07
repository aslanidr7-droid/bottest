"""P12: when a sleeve comes out.
1. Kill line: live drawdown > 2x the worst tested drawdown -> sleeve switched off automatically
   (core: 1.5x -> alert only).
2. Quarterly re-pick does not choose it -> Claude proposes a change, you approve.
3. After 3 months, trade frequency < 0.5x or > 2x the tested rate -> review.
One bad week is never a reason. States: keep / watch / review / out.
"""
import json
import pandas as pd
from .config import ROOT
from . import live
from .p4_sleeves import stats
from .signals import SLEEVE_DEFAULTS
from .config import S

HEALTH = ROOT / "state" / "health.json"
OFF = ROOT / "state" / "sleeves_off.json"


def tested(name):
    t, fam = name.split()
    m, _, _ = stats(fam, t, SLEEVE_DEFAULTS[fam], [S["train"][0], S["test"][1]])
    return m


def live_trades(name):
    rows = []
    for r in map(json.loads, (ROOT / "logs" / "runs.jsonl").read_text().splitlines()) if (ROOT / "logs" / "runs.jsonl").exists() else []:
        for o in r.get("orders", []):
            if o["sleeve"] == name:
                rows.append(dict(day=r["day"], side=o["side"], value=o["value"]))
    return pd.DataFrame(rows)


def assess(name, live_dd, months_live, picked_last_quarter=True):
    m = tested(name)
    worst = m["max_dd"]
    if live_dd < 2 * worst:
        return "out", f"kill line: live DD {live_dd:.1%} < 2x tested worst {worst:.1%}"
    if not picked_last_quarter:
        return "review", "not picked by quarterly re-pick -> propose swap"
    if months_live >= 3:
        lt = live_trades(name)
        n = (lt.side == "buy").sum() if len(lt) else 0
        rate_live = n / months_live
        rate_test = m["trades"] / (len(pd.bdate_range(S["train"][0], S["test"][1])) / 21)
        if rate_live < 0.5 * rate_test or rate_live > 2 * rate_test:
            return "review", f"trade rate {rate_live:.2f}/mo vs tested {rate_test:.2f}/mo"
    if live_dd < worst:
        return "watch", f"live DD {live_dd:.1%} past tested worst {worst:.1%}"
    return "keep", "within tested behaviour"


def core_alert(live_dd, tested_dd):
    return live_dd < 1.5 * tested_dd


def switch_off(name, reason):
    off = json.loads(OFF.read_text()) if OFF.exists() else {}
    off[name] = reason
    OFF.parent.mkdir(exist_ok=True)
    OFF.write_text(json.dumps(off, indent=2))
    with open(ROOT / "results" / "changes.csv", "a") as f:
        f.write(f"{pd.Timestamp.now().date()},{name},out,{reason}\n")
