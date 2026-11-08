"""P5b + sizing ideas from the video that we had skipped. All fixed up front, judged on TRAINING only.

Core variants:
  base        QQQ > SMA200 -> QQQ else GLD
  vix_breadth P5b: VIX closes above its 1-year median (cross up) while breadth > 50% -> core in cash 5 days
              (breadth proxy: share of the 11 sector ETFs above their 50-day average)
  calm_wild   'Calm vs wild': SPY 20-day vol above its 1-year median -> engine at half size (rest in cash)
  vix_dial    Bonus 'dial': VIX < 20 full, 20-30 half, > 30 zero (rest in cash) while holding the engine
Sleeves:
  video_set   the video's final sleeves (QQQ breakout, XLK dip, GLD dip) instead of our greedy pick
  sleeves_cw  calm/wild applied to sleeve slots (wild -> half slot)
"""
import json
import pandas as pd
from .config import S, ROOT
from .data import load
from .signals import core_targets, sma
from .backtest import run_weights, metrics, window
from .p5_portfolio import sleeve_streams, combine

TR, TE, FULL = S["train"], S["test"], [S["train"][0], S["test"][1]]
SECTORS = ["XLK", "XLF", "XLE", "XLV", "XLI", "XLY", "XLP", "XLU", "XLB", "XLC", "XLRE"]
CASH = S["cash"]


def inputs():
    O, C = load("open"), load("close")
    vix = C["^VIX"]
    breadth = pd.concat([C[t] > sma(C[t], 50) for t in SECTORS], axis=1).mean(axis=1)
    spy_vol = C["SPY"].pct_change().rolling(20).std()
    wild = spy_vol > spy_vol.rolling(252).median()
    return O, C, vix, breadth, wild


def core_weights(kind, O, C, vix, breadth, wild, engine="QQQ", safe="GLD"):
    w = core_targets(C, engine, safe).reindex(columns=[engine, safe, CASH]).fillna(0.0)
    w[core_targets(C, engine, safe).isna().any(axis=1)] = float("nan")
    if kind == "vix_breadth":
        med = vix.rolling(252).median()
        trig = (vix > med) & (vix.shift(1) <= med.shift(1)) & (breadth > 0.5)
        out = trig.astype(int).rolling(5, min_periods=1).max().astype(bool)  # trigger day + next 4 closes
        w.loc[out, [engine, safe]] = 0.0
        w.loc[out, CASH] = 1.0
    elif kind == "calm_wild":
        cut = wild & (w[engine] > 0)
        w.loc[cut, engine] = 0.5
        w.loc[cut, CASH] = 0.5
    elif kind == "vix_dial":
        size = pd.Series(1.0, index=w.index).where(vix < 20, 0.5).where(vix <= 30, 0.0)
        hold = w[engine] > 0
        w.loc[hold, engine] = size[hold]
        w.loc[hold, CASH] = 1 - size[hold]
    return w


def row(name, r, borrowed=None):
    rec = dict(variant=name)
    for lab, win in [("train", TR), ("test", TE), ("full", FULL)]:
        m = metrics(window(r, win))
        rec.update({f"{lab}_ann": m["annual"], f"{lab}_dd": m["max_dd"], f"{lab}_ret_dd": m["ret_dd"]})
    rec["final_$"] = S["capital"] * (1 + window(r, FULL)).prod()
    if borrowed is not None:
        rec["max_borrow"] = borrowed.max()
    return rec


def sleeves_sized(core, streams, chosen, wild, slot=0.20):
    """combine() with the slot halved on wild days (decided on yesterday's close)."""
    idx = core.index
    size = (slot * (1 - 0.5 * wild.shift(1).reindex(idx).fillna(False).astype(float)))
    ret, borrowed = core.copy(), pd.Series(0.0, index=idx)
    for n in chosen:
        d, pos, _ = streams[n]
        ret += size * d.reindex(idx).fillna(0)
        borrowed += size * pos.reindex(idx).fillna(0)
    return ret - borrowed * S["margin_rate"] / 252, borrowed


if __name__ == "__main__":
    O, C, vix, breadth, wild = inputs()
    rows, cores = [], {}
    for k in ["base", "vix_breadth", "calm_wild", "vix_dial"]:
        r, sw = run_weights(core_weights(k, O, C, vix, breadth, wild), O, C)
        cores[k] = r
        rows.append({**row(f"core {k}", r), "switches": sw})
    live = json.load(open(ROOT / "config" / "sleeves.json"))["sleeves"]
    video = ["QQQ breakout", "XLK dip", "GLD dip"]
    streams = sleeve_streams(set(live + video))
    for k in ["base", "calm_wild", "vix_dial"]:
        r, b = combine(cores[k], streams, live)
        rows.append(row(f"account {k} + our sleeves", r, b))
        r, b = combine(cores[k], streams, video)
        rows.append(row(f"account {k} + video sleeves", r, b))
        r, b = sleeves_sized(cores[k], streams, live, wild)
        rows.append(row(f"account {k} + our sleeves calm/wild", r, b))
    df = pd.DataFrame(rows)
    df.to_csv(ROOT / "results" / "p5b_filters.csv", index=False)
    pd.set_option("display.width", 200)
    cols = ["variant", "train_ann", "train_dd", "train_ret_dd", "test_ann", "test_dd", "test_ret_dd", "full_ann", "full_dd", "final_$"]
    print(df[cols].round(3).to_string(index=False))
    log = df[["variant", "train_ret_dd", "test_ret_dd"]].assign(step="P5b")
    log.to_csv(ROOT / "results" / "ideas_log.csv", mode="a", header=False, index=False)
    best = df.sort_values("train_ret_dd", ascending=False).iloc[0]
    print(f"FINGERPRINT P5b: best on TRAIN = {best.variant} (train ret/dd {best.train_ret_dd:.2f}, test {best.test_ret_dd:.2f})")
