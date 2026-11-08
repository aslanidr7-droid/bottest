import sys; sys.path.insert(0, "/home/user/bottest")
import pandas as pd, yfinance as yf
from src import p4b_ideas as b, p4_sleeves as p4
from src.signals import core_targets, SLEEVE_DEFAULTS
from src.backtest import run_weights, metrics, window
T = ["QQQ","GLD","BIL","USO","XLE","XLK","SPY"]
df = yf.download(T, start="2005-06-01", end="2022-01-01", auto_adjust=True, progress=False, group_by="ticker")
D = {f: pd.DataFrame({t: df[t][f.capitalize()] for t in T}) for f in ["open","high","low","close","volume"]}
D = {k: v.loc[v["SPY"].notna()].ffill() for k, v in D.items()}
b._D = D; p4._D = {k: D[k] for k in ["open","high","low","close"]}
W = ["2007-01-03","2021-12-31"]
core, _ = run_weights(core_targets(D["close"], "QQQ", "GLD").fillna(0).where(core_targets(D["close"],"QQQ","GLD").notna()), D["open"], D["close"])
core = window(core, W)
streams = {}
for n in ["USO gapdown","XLE gapdown","XLK badweek"]:
    t, idea = n.split(); daily, tr = b.run_idea(idea, t, b.IDEAS[idea]["p"]); streams[n] = (daily, tr)
daily, tr = p4.run("dip", "QQQ", SLEEVE_DEFAULTS["dip"]); streams["QQQ dip"] = (daily, tr)
print("standalone 2007-2021 (slot equity):")
for n, (d, tr) in streams.items():
    m = metrics(window(d, W), tr[(tr.entry >= W[0]) & (tr.entry <= W[1])])
    print(f"  {n:<12} ann {m['annual']:+.1%} dd {m['max_dd']:.1%} trades {m['trades']} pf {m['profit_factor']:.2f} win {m['win_rate']:.0%}")
def acct(names):
    r = core.copy(); bor = 0
    for n in names:
        d, tr = streams[n]; pos = pd.Series(0.0, index=d.index)
        for _, x in tr.iterrows(): pos.loc[x.entry:x.exit] = 1
        r = r + 0.2 * d.reindex(r.index).fillna(0); bor = bor + 0.2 * pos.reindex(r.index).fillna(0)
    return r - bor * 0.065 / 252
for lab, names in [("core only", []), ("core + QQQ dip", ["QQQ dip"]), ("core + QQQ dip + 3 new", ["QQQ dip","USO gapdown","XLE gapdown","XLK badweek"])]:
    m = metrics(acct(names)); print(f"{lab:<26} ann {m['annual']:.1%} dd {m['max_dd']:.1%} ret/dd {m['ret_dd']:.2f}")
