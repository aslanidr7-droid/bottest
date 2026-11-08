"""P5: core + sleeves together. Core stays 100% invested; each sleeve gets a 20% slot ON MARGIN
(explicit exception to 'no leverage', as in the video). Greedy add on training ret/DD, skip if corr > 0.6."""
import json
import pandas as pd
from .config import S, ROOT
from .data import load
from .signals import SLEEVE_DEFAULTS
from .backtest import metrics, window, in_position
from . import p4_sleeves as p4

TR, TE = S["train"], S["test"]
SLOT, MAX_CORR = 0.20, 0.6


def sleeve_streams(names):
    out = {}
    for n in names:
        t, fam = n.split()
        daily, tr = p4.run(fam, t, SLEEVE_DEFAULTS[fam])
        out[n] = (daily, in_position(tr, daily.index), tr)
    return out


def combine(core_ret, streams, chosen, slot=SLOT, rate=S["margin_rate"]):
    idx = core_ret.index
    ret = core_ret.copy()
    borrowed = pd.Series(0.0, index=idx)
    for n in chosen:
        d, pos, _ = streams[n]
        ret = ret + slot * d.reindex(idx).fillna(0)
        borrowed = borrowed + slot * pos.reindex(idx).fillna(0)
    ret = ret - borrowed * rate / 252
    return ret, borrowed


def greedy(core_ret, streams, win=TR):
    order = sorted(streams, key=lambda n: -metrics(window(streams[n][0], win))["ret_dd"])
    chosen, log = [], []
    best = metrics(window(core_ret, win))["ret_dd"]
    for n in order:
        corr = max([window(streams[n][0], win).corr(window(streams[c][0], win)) for c in chosen], default=0)
        if corr > MAX_CORR:
            log.append((n, "skip corr", corr)); continue
        r, _ = combine(core_ret, streams, chosen + [n])
        score = metrics(window(r, win))["ret_dd"]
        if score > best:
            chosen.append(n); best = score; log.append((n, "added", score))
        else:
            log.append((n, "no gain", score))
    return chosen, log


if __name__ == "__main__":
    import sys
    core = pd.read_parquet(ROOT / "results" / "core_returns.parquet")["ret"]
    if "--video" in sys.argv:  # use the video's final pick as-is (P5 result shown at 1:42:05)
        chosen, log = ["QQQ breakout", "XLK dip", "GLD dip"], [("video pick", "fixed", float("nan"))]
        streams = sleeve_streams(chosen)
    else:
        passed = json.load(open(ROOT / "config" / "sleeves_passed.json"))
        streams = sleeve_streams(passed)
        chosen, log = greedy(core, streams)
    for row in log:
        print(f"  {row[0]:<14} {row[1]:<9} {row[2]:.3f}")
    total, borrowed = combine(core, streams, chosen)
    O, C = load("open"), load("close")
    spy = (C["SPY"].pct_change()).loc[core.index]
    rows = []
    for name, r in [("Core QQQ/GLD", core), ("Whole account", total), ("SPY buy & hold", spy)]:
        tr, te = metrics(window(r, TR)), metrics(window(r, TE))
        rows.append(dict(backtest=name, train_ann=tr["annual"], train_dd=tr["max_dd"],
                         test_ann=te["annual"], test_dd=te["max_dd"], test_ret_dd=te["ret_dd"]))
    tab = pd.DataFrame(rows)
    print(tab.round(3).to_string(index=False))
    full = window(total, [TR[0], TE[1]]); spyf = window(spy, [TR[0], TE[1]])
    eq, eqs = S["capital"] * (1 + full).cumprod(), S["capital"] * (1 + spyf).cumprod()
    print(f"Full period: ${eq.iloc[-1]:,.0f} (max DD {metrics(full)['max_dd']:.1%}) vs SPY ${eqs.iloc[-1]:,.0f} "
          f"(max DD {metrics(spyf)['max_dd']:.1%}); max borrowing {borrowed.max():.1%}")
    tab.to_csv(ROOT / "results" / "portfolio.csv", index=False)
    pd.DataFrame({"account": total, "core": core, "borrowed": borrowed}).to_parquet(ROOT / "results" / "portfolio_returns.parquet")
    json.dump(dict(sleeves=chosen, slot=SLOT), open(ROOT / "config" / "sleeves.json", "w"), indent=2)
    w = tab.iloc[1]
    print(f"FINGERPRINT P5: sleeves={', '.join(chosen)}; account train={w.train_ann:.1%}/{w.train_dd:.1%}, "
          f"test={w.test_ann:.1%}/{w.test_dd:.1%} (check, not a fresh test)")
