"""P4b: Claude's own 10 sleeve ideas through the same tests as P4.

All parameters are fixed up front (no tuning). Every choice is made on the training window;
the locked test is reported as a check only. Funnel: profitable (train) -> trades >= 8 ->
PF >= 1.3 -> neighbours (+/-1 step on 2 params) all profitable -> locked test profitable (check).
Signal on the close, trade at the next open, 8% stop, cost 0.05% per side (src.backtest.run_trades).
"""
import numpy as np
import pandas as pd
from .config import S, ROOT
from .data import load
from .signals import sma, rsi
from .backtest import run_trades, metrics, window, in_position, lookahead_guard
from .p4_sleeves import TRADABLE, MIN_TRADES, MIN_PF

TR, TE = S["train"], S["test"]
STOP = 0.08
SECTORS = ["XLK", "XLF", "XLE", "XLV", "XLI", "XLY", "XLP", "XLU", "XLB", "XLC", "XLRE"]
SAFE = ["TLT", "IEF", "SHY", "GLD"]


# ---------- extra indicators (local to P4b; src/signals.py untouched) ----------
def ibs(d):
    rng = (d.high - d.low).replace(0, np.nan)
    return (d.close - d.low) / rng


def busdays_left_in_month(idx):
    """Business days left until month end, from the calendar (known in advance, no look-ahead)."""
    me = (idx + pd.offsets.MonthEnd(0)).values.astype("datetime64[D]")
    return pd.Series(np.busday_count(idx.values.astype("datetime64[D]"), me), index=idx)


# ---------- the 10 ideas: entry(d, p, ctx) / exit(d, p, ctx) on one ticker's OHLCV frame ----------
def _up(d, p):
    return d.close > sma(d.close, p.get("trend", 200))


IDEAS = {
    # 1. Internal bar strength: close near the day's low in an uptrend
    "ibs": dict(p=dict(ibs_max=0.2, trend=200), steps=dict(ibs_max=0.05, trend=50), max_days=5,
                entry=lambda d, p, x: (ibs(d) < p["ibs_max"]) & _up(d, p),
                exit=lambda d, p, x: (ibs(d) > 0.7) | (d.close > d.high.shift(1))),
    # 2. N lower closes in a row in an uptrend
    "down3": dict(p=dict(n=3, trend=200), steps=dict(n=1, trend=50), max_days=10,
                  entry=lambda d, p, x: (d.close.diff() < 0).astype(int).rolling(p["n"]).sum().eq(p["n"]) & _up(d, p),
                  exit=lambda d, p, x: d.close > sma(d.close, 5)),
    # 3. Close below the lower Bollinger band in an uptrend
    "bb": dict(p=dict(n=20, k=2.0), steps=dict(n=5, k=0.25), max_days=10,
               entry=lambda d, p, x: (d.close < sma(d.close, p["n"]) - p["k"] * d.close.rolling(p["n"]).std()) & _up(d, {}),
               exit=lambda d, p, x: d.close > sma(d.close, p["n"])),
    # 4. 20-day-high breakout on heavy volume
    "volbreak": dict(p=dict(high_n=20, vmult=1.5), steps=dict(high_n=5, vmult=0.25), max_days=20,
                     entry=lambda d, p, x: (d.close >= d.close.rolling(p["high_n"]).max())
                     & (d.volume > p["vmult"] * d.volume.rolling(20).mean().shift(1)) & _up(d, {}),
                     exit=lambda d, p, x: d.close < d.close.rolling(10).min().shift(1)),
    # 5. Gap-down reversal: opens below yesterday's low, closes above its open
    "gapdown": dict(p=dict(gap=0.0025, trend=200), steps=dict(gap=0.0025, trend=50), max_days=5,
                    entry=lambda d, p, x: (d.open < d.low.shift(1) * (1 - p["gap"])) & (d.close > d.open) & _up(d, p),
                    exit=lambda d, p, x: d.close > d.high.shift(1)),
    # 6. Turn of the month: buy k business days before month end, hold `hold` days
    "tom": dict(p=dict(k=4, hold=6), steps=dict(k=1, hold=1), max_days=None,
                entry=lambda d, p, x: busdays_left_in_month(d.index).eq(p["k"]) & _up(d, {}),
                exit=lambda d, p, x: pd.Series(False, index=d.index)),
    # 7. Relative strength: hold the top sector ETF by lookback return, exit when it drops out of top `exit_rank`
    "rs": dict(p=dict(lookback=63, exit_rank=3), steps=dict(lookback=21, exit_rank=1), max_days=60, tickers=SECTORS,
               entry=lambda d, p, x: (x["rank"](p["lookback"]) == 1) & _up(d, {}),
               exit=lambda d, p, x: x["rank"](p["lookback"]) > p["exit_rank"]),
    # 8. Safe-asset dip: RSI on bonds/gold (no trend filter)
    "safedip": dict(p=dict(rsi_max=20, rsi_n=3), steps=dict(rsi_max=5, rsi_n=1), max_days=10, tickers=SAFE,
                    entry=lambda d, p, x: rsi(d.close, p["rsi_n"]) < p["rsi_max"],
                    exit=lambda d, p, x: rsi(d.close, p["rsi_n"]) > 50),
    # 9. NR7 inside day in an uptrend (volatility contraction)
    "nr7": dict(p=dict(n=7, trend=200), steps=dict(n=1, trend=50), max_days=5,
                entry=lambda d, p, x: ((d.high - d.low) <= (d.high - d.low).rolling(p["n"]).min())
                & (d.high < d.high.shift(1)) & (d.low > d.low.shift(1)) & _up(d, p),
                exit=lambda d, p, x: d.close < d.low.rolling(10).min().shift(1)),
    # 10. Bad week in an uptrend: Friday close down > drop over 5 days
    "badweek": dict(p=dict(drop=0.02, trend=200), steps=dict(drop=0.005, trend=50), max_days=5,
                    entry=lambda d, p, x: (d.index.to_series().dt.weekday.eq(4).values)
                    & (d.close / d.close.shift(5) - 1 < -p["drop"]) & _up(d, p),
                    exit=lambda d, p, x: d.close > sma(d.close, 5)),
}

_D = None


def data():
    global _D
    if _D is None:
        _D = {f: load(f) for f in ["open", "high", "low", "close", "volume"]}
    return _D


def frame(t, D=None):
    D = D or data()
    return pd.DataFrame({f: D[f][t] for f in ["open", "high", "low", "close", "volume"]})


def rank_fn(closes):
    """ctx['rank'](lookback) -> rank (1 = best) of each sector by lookback return, per day."""
    cache = {}

    def r(lb):
        if lb not in cache:
            cache[lb] = (closes[SECTORS] / closes[SECTORS].shift(lb) - 1).rank(axis=1, ascending=False)
        return cache[lb]
    return r


def ctx_for(t, closes):
    rf = rank_fn(closes)
    return {"rank": lambda lb: rf(lb)[t] if t in SECTORS else pd.Series(np.nan, index=closes.index)}


def run_idea(name, t, p):
    idea = IDEAS[name]
    d = frame(t)
    x = ctx_for(t, data()["close"])
    e = pd.Series(idea["entry"](d, p, x), index=d.index).fillna(False).astype(bool)
    ex = pd.Series(idea["exit"](d, p, x), index=d.index).fillna(False).astype(bool)
    md = idea["max_days"] or p["hold"]
    return run_trades(e, ex, d.open, d.high, d.low, d.close, max_days=md, stop=STOP)


def stats(name, t, p, win):
    daily, tr = run_idea(name, t, p)
    tw = tr[(tr.entry >= win[0]) & (tr.entry <= win[1])]
    return metrics(window(daily, win), tw), daily, tr


def neighbours(name):
    idea = IDEAS[name]
    out = []
    for k, step in idea["steps"].items():
        for sgn in (-1, 1):
            q = dict(idea["p"])
            q[k] = type(q[k])(q[k] + sgn * step)
            out.append(q)
    return out


def guard_all():
    """Every entry function must pass the look-ahead guard (on QQQ / XLK / GLD)."""
    for name, idea in IDEAS.items():
        t = (idea.get("tickers") or ["QQQ"])[0]
        d = frame(t)
        if name == "rs":
            cl = data()["close"]
            lookahead_guard(lambda w: (rank_fn(w)(63)[t] == 1) & (w[t] > sma(w[t], 200)), cl)
        else:
            lookahead_guard(lambda w, i=idea: pd.Series(i["entry"](w, i["p"], {}), index=w.index).astype(bool), d)
    return True


def funnel():
    labels = pd.read_csv(ROOT / "results" / "asset_study.csv").set_index("ticker")["labels"]
    rows = []
    for name, idea in IDEAS.items():
        for t in idea.get("tickers") or TRADABLE:
            m, _, _ = stats(name, t, idea["p"], TR)
            nb = [stats(name, t, q, TR)[0]["total"] for q in neighbours(name)]
            mt, _, _ = stats(name, t, idea["p"], TE)
            rows.append(dict(sleeve=f"{t} {name}", ticker=t, idea=name, label=labels.get(t, ""),
                             profitable=m["total"] > 0, enough_trades=m["trades"] >= MIN_TRADES,
                             pf_ok=(m["profit_factor"] or 0) >= MIN_PF, neighbours_ok=all(v > 0 for v in nb),
                             test_ok=mt["total"] > 0,
                             **{f"train_{k}": v for k, v in m.items()}, **{f"test_{k}": v for k, v in mt.items()}))
    df = pd.DataFrame(rows)
    stages = ["profitable", "enough_trades", "pf_ok", "neighbours_ok", "test_ok"]
    alive = pd.Series(True, index=df.index)
    counts = [("candidates", len(df))]
    for s in stages:
        alive &= df[s].astype(bool)
        df[f"alive_{s}"] = alive
        counts.append((s, int(alive.sum())))
    df["passed"] = alive
    return df, counts


def add_to_live(df):
    """Does each survivor improve TRAINING whole-account ret/DD of the current live portfolio?"""
    import json
    from .p5_portfolio import sleeve_streams, combine, MAX_CORR
    core = pd.read_parquet(ROOT / "results" / "core_returns.parquet")["ret"]
    live = json.load(open(ROOT / "config" / "sleeves.json"))["sleeves"]
    streams = sleeve_streams(live)
    for _, r in df[df.passed].iterrows():
        daily, tr = run_idea(r.idea, r.ticker, IDEAS[r.idea]["p"])
        streams[r.sleeve] = (daily, in_position(tr, daily.index), tr)
    score = lambda chosen, w: metrics(window(combine(core, streams, chosen)[0], w))["ret_dd"]
    base_tr, base_te = score(live, TR), score(live, TE)
    rows = []
    for s in df[df.passed].sleeve:
        corr = max(window(streams[s][0], TR).corr(window(streams[c][0], TR)) for c in live)
        rows.append(dict(sleeve=s, corr=corr, train_before=base_tr, train_after=score(live + [s], TR),
                         test_before=base_te, test_after=score(live + [s], TE)))
    add = pd.DataFrame(rows)
    if len(add):
        add["improves_train"] = (add.train_after > add.train_before) & (add["corr"] <= MAX_CORR)
    # greedy set on training, same rule as P5
    chosen, best = list(live), base_tr
    for s in (add.sort_values("train_after", ascending=False).sleeve if len(add) else []):
        corr = max(window(streams[s][0], TR).corr(window(streams[c][0], TR)) for c in chosen)
        if corr <= MAX_CORR and score(chosen + [s], TR) > best:
            chosen.append(s); best = score(chosen, TR)
    combo = dict(sleeves=chosen, train=best, test=score(chosen, TE),
                 train_m=metrics(window(combine(core, streams, chosen)[0], TR)),
                 test_m=metrics(window(combine(core, streams, chosen)[0], TE)),
                 base_train_m=metrics(window(combine(core, streams, live)[0], TR)),
                 base_test_m=metrics(window(combine(core, streams, live)[0], TE)),
                 max_borrow=combine(core, streams, chosen)[1].max())
    return add, combo


if __name__ == "__main__":
    print("look-ahead guard:", guard_all())
    df, counts = funnel()
    for s, n in counts:
        print(f"{s:>15}: {n}")
    df.to_csv(ROOT / "results" / "p4b_funnel.csv", index=False)
    log = df[["sleeve", "passed", "train_total", "train_trades", "train_profit_factor", "test_total"]].assign(step="P4b")
    log.to_csv(ROOT / "results" / "ideas_log.csv", mode="a", header=False, index=False)
    keep = df[df.passed]
    cols = ["sleeve", "label", "train_annual", "train_max_dd", "train_trades", "train_profit_factor",
            "test_annual", "test_trades", "test_profit_factor"]
    print(keep[cols].round(3).to_string(index=False))
    add, combo = add_to_live(df)
    print(add.round(3).to_string(index=False))
    print("greedy (train):", combo["sleeves"])
    for k in ["base_train_m", "train_m", "base_test_m", "test_m"]:
        m = combo[k]
        print(f"  {k:<13} annual {m['annual']:.1%}  dd {m['max_dd']:.1%}  ret/dd {m['ret_dd']:.2f}")
    print(f"  max borrowing {combo['max_borrow']:.0%}")
    print("FINGERPRINT P4b: " + " -> ".join(str(n) for _, n in counts) + f"; passed={', '.join(keep.sleeve)}")
