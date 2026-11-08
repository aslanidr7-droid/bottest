"""Extra robustness checks (video Proof section): cost stress, Monte Carlo, another period, delay.
Read-only with respect to rules/config. Writes results/robustness.md and results/robustness.csv."""
import json
import numpy as np
import pandas as pd
import yfinance as yf
from .config import S, ROOT
from .data import load
from .signals import core_targets, sleeve_entry, sleeve_exit, SLEEVE_DEFAULTS
from .backtest import run_weights, run_trades, metrics, window, in_position

TR, TE = S["train"], S["test"]
FULL = [TR[0], TE[1]]
CORE = json.load(open(ROOT / "config" / "core.json"))
SLV = json.load(open(ROOT / "config" / "sleeves.json"))
rows, md = [], []


def rec(check, variant, r, wins=(("train", TR), ("test", TE), ("full", FULL))):
    for lab, w in wins:
        m = metrics(window(r, w))
        rows.append(dict(check=check, variant=variant, window=lab, annual=m["annual"], max_dd=m["max_dd"], ret_dd=m["ret_dd"]))


def account(cost, rate, O, H, L, C, core_ret):
    ret = core_ret.copy()
    borrowed = pd.Series(0.0, index=ret.index)
    trades = []
    for n in SLV["sleeves"]:
        t, fam = n.split(); p = SLEEVE_DEFAULTS[fam]
        d, tr = run_trades(sleeve_entry(fam, C[t], p), sleeve_exit(fam, C[t], p), O[t], H[t], L[t], C[t],
                           p["max_days"], p["stop"], cost=cost)
        ret = ret + SLV["slot"] * d.reindex(ret.index).fillna(0)
        borrowed = borrowed + SLV["slot"] * in_position(tr, d.index).reindex(ret.index).fillna(0)
        trades.append(tr.assign(sleeve=n))
    return ret - borrowed * rate / 252, pd.concat(trades)


def main():
    O, H, L, C = (load(f) for f in ["open", "high", "low", "close"])
    w = core_targets(C, CORE["engine"], CORE["safe"], CORE["n"], CORE["kind"])
    # 1 cost stress
    md.append("## 1. Cost stress\n")
    for cost in [0.0005, 0.001, 0.002]:
        core_ret, _ = run_weights(w, O, C, cost=cost)
        rec("cost", f"core cost {cost:.2%}", core_ret)
        for rate in [0.065, 0.08]:
            acc, _ = account(cost, rate, O, H, L, C, core_ret)
            rec("cost", f"account cost {cost:.2%} margin {rate:.1%}", acc)
    base_core, _ = run_weights(w, O, C)
    base_acc, trades = account(S["cost"], S["margin_rate"], O, H, L, C, base_core)
    # 2a trade-order Monte Carlo (sleeves, as % of slot then scaled to account)
    rng = np.random.default_rng(42)
    tr = trades[(trades.entry >= TR[0])]["ret"].values * SLV["slot"]
    dds = []
    for _ in range(1000):
        eq = np.cumprod(1 + rng.permutation(tr))
        dds.append((eq / np.maximum.accumulate(eq) - 1).min())
    real_eq = np.cumprod(1 + tr); real_dd = (real_eq / np.maximum.accumulate(real_eq) - 1).min()
    mc_a = dict(n_trades=len(tr), real_dd=real_dd, p5=np.percentile(dds, 5), p50=np.percentile(dds, 50))
    # 2b block bootstrap of daily account returns
    r = window(base_acc, FULL).values
    n, B = len(r), 20
    anns, mdd = [], []
    for _ in range(2000):
        starts = rng.integers(0, n - B, size=n // B + 1)
        path = np.concatenate([r[s:s + B] for s in starts])[:n]
        eq = np.cumprod(1 + path)
        anns.append(eq[-1] ** (252 / n) - 1)
        mdd.append((eq / np.maximum.accumulate(eq) - 1).min())
    anns, mdd = np.array(anns), np.array(mdd)
    mc_b = dict(ann_p5=np.percentile(anns, 5), ann_p50=np.percentile(anns, 50), ann_p95=np.percentile(anns, 95),
                dd_p5=np.percentile(mdd, 5), dd_p50=np.percentile(mdd, 50), dd_p95=np.percentile(mdd, 95),
                p_dd_worse_30=float((mdd < -0.30).mean()), p_ann_below_0=float((anns < 0).mean()))
    for k, v in {**{f"trades_{k}": v for k, v in mc_a.items()}, **mc_b}.items():
        rows.append(dict(check="montecarlo", variant=k, window="full", annual=v))
    # 3 another period 2007-2021
    raw = yf.download(["QQQ", "SPY", "GLD", "IEF"], start="2006-01-01", end="2022-01-01", auto_adjust=True,
                      progress=False, group_by="ticker", threads=False)
    o2 = pd.DataFrame({t: raw[t]["Open"] for t in ["QQQ", "SPY", "GLD", "IEF"]}).dropna()
    c2 = pd.DataFrame({t: raw[t]["Close"] for t in ["QQQ", "SPY", "GLD", "IEF"]}).dropna()
    old = [("2007-01-01", "2021-12-31")]
    oldw = (("2007-2021", old[0]), ("2007-2013", ("2007-01-01", "2013-12-31")), ("2014-2021", ("2014-01-01", "2021-12-31")))
    for eng, safe in [("QQQ", "GLD"), ("SPY", "IEF"), ("SPY", "GLD"), ("QQQ", "IEF")]:
        rr, sw = run_weights(core_targets(c2, eng, safe), o2, c2)
        rec("old_period", f"{eng}>SMA200 else {safe}", rr, oldw)
    for t in ["QQQ", "SPY"]:
        rec("old_period", f"{t} buy&hold", c2[t].pct_change(), oldw)
    # 4 delay test (trade open t+2)
    d_ret, _ = run_weights(w.shift(1), O, C)
    rec("delay", "core +1 day delay", d_ret)
    rec("delay", "core baseline", base_core)
    # 5 core parameter sensitivity, full grid
    for n_ in [100, 125, 150, 175, 200, 225, 250]:
        rr, _ = run_weights(core_targets(C, CORE["engine"], CORE["safe"], n_), O, C)
        rec("sensitivity", f"SMA{n_}", rr)
    df = pd.DataFrame(rows)
    df.to_csv(ROOT / "results" / "robustness.csv", index=False)
    piv = df[df.check != "montecarlo"].pivot_table(index=["check", "variant"], columns="window",
                                                   values=["annual", "max_dd", "ret_dd"], sort=False)
    with open(ROOT / "results" / "robustness.md", "w") as f:
        f.write("# Robustness checks\n\n```\n" + piv.round(3).to_string() + "\n```\n\n")
        f.write(f"## Monte Carlo\nSleeve trade-order reshuffle: {mc_a}\n\nBlock bootstrap (20d, 2000 paths): {mc_b}\n")
    print(piv.round(3).to_string()); print(mc_a); print(mc_b)


if __name__ == "__main__":
    main()
