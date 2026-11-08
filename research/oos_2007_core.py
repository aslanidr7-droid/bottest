import sys; sys.path.insert(0, "/home/user/bottest")
import pandas as pd, yfinance as yf
from src import p5b_filters as f
from src.signals import core_targets, sma
from src.backtest import run_weights, metrics, window
SEC = ["XLK","XLF","XLE","XLV","XLI","XLY","XLP","XLU","XLB"]
T = ["QQQ","GLD","BIL","SPY","^VIX"] + SEC
df = yf.download(T, start="2005-06-01", end="2022-01-01", auto_adjust=True, progress=False, group_by="ticker")
O = pd.DataFrame({t: df[t]["Open"] for t in T}); C = pd.DataFrame({t: df[t]["Close"] for t in T})
keep = C["SPY"].notna(); O, C = O[keep].ffill(), C[keep].ffill()
C["BIL"] = C["BIL"].bfill(); O["BIL"] = O["BIL"].bfill()
vix = C["^VIX"]; breadth = pd.concat([C[t] > sma(C[t], 50) for t in SEC], axis=1).mean(axis=1)
v = C["SPY"].pct_change().rolling(20).std(); wild = v > v.rolling(252).median()
W = ["2007-01-03", "2021-12-31"]
for k in ["base", "vix_breadth", "calm_wild", "vix_dial"]:
    r, sw = run_weights(f.core_weights(k, O, C, vix, breadth, wild), O, C)
    m = metrics(window(r, W)); print(f"core {k:<12} ann {m['annual']:.1%} dd {m['max_dd']:.1%} ret/dd {m['ret_dd']:.2f} switches {sw}")
for n in [150, 175]:
    w = core_targets(C, "QQQ", "GLD", n=n); r, sw = run_weights(w, O, C)
    m = metrics(window(r, W)); print(f"core SMA{n:<9} ann {m['annual']:.1%} dd {m['max_dd']:.1%} ret/dd {m['ret_dd']:.2f}")
