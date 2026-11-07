"""P3: find the core. Engine + safe chosen on training; neighbours; locked test run once."""
import json
import pandas as pd
from .config import S, ROOT
from .data import load
from .signals import above, core_targets
from .backtest import run_weights, metrics, window

TR, TE = S["train"], S["test"]


def pick():
    C = load("close")
    rows = []
    for t in S["engine"]:
        r = C[t].pct_change()
        up = above(C[t]).shift(1)
        ru, rd = window(r[up == True], TR).mean() * 252, window(r[up == False], TR).mean() * 252  # noqa
        rows.append(dict(ticker=t, up_ann=ru, down_ann=rd, spread=ru - rd))
    eng = pd.DataFrame(rows).sort_values("spread", ascending=False)
    engine = eng.iloc[0].ticker
    down = above(C[engine]).shift(1) == False  # noqa
    er = C[engine].pct_change()
    srows = []
    for t in S["safe"]:
        r = C[t].pct_change()
        srows.append(dict(ticker=t, on_engine_down_ann=window(r[down], TR).mean() * 252,
                          corr=window(r, TR).corr(window(er, TR))))
    safe_t = pd.DataFrame(srows)
    ok = safe_t[safe_t["corr"] < 0.5].sort_values("on_engine_down_ann", ascending=False)
    return engine, ok.iloc[0].ticker, eng, safe_t


def test_core(engine, safe, variants):
    O, C = load("open"), load("close")
    out = []
    for name, kw in variants:
        w = core_targets(C, engine, safe, **kw)
        ret, sw = run_weights(w, O, C)
        rec = dict(variant=name)
        for lab, win in [("train", TR), ("test", TE)]:
            m = metrics(window(ret, win))
            rec.update({f"{lab}_{k}": v for k, v in m.items()})
        rec["switches"] = sw
        out.append((rec, ret))
    return out


if __name__ == "__main__":
    engine, safe, eng, safe_t = pick()
    print(eng.round(3).to_string(index=False)); print(safe_t.round(3).to_string(index=False))
    variants = [("SMA200", dict(n=200)), ("SMA100", dict(n=100)), ("SMA150", dict(n=150)),
                ("SMA250", dict(n=250)), ("EMA200", dict(n=200, kind="ema")), ("50/200 cross", dict(kind="cross"))]
    res = test_core(engine, safe, variants)
    df = pd.DataFrame([r for r, _ in res])
    # neighbours judged on training only; locked test columns shown for SMA200 (run once)
    print(df[["variant", "train_annual", "train_max_dd", "train_ret_dd", "switches"]].round(3).to_string(index=False))
    main = df.iloc[0]
    print(f"LOCKED TEST (once): annual={main.test_annual:.1%}, max_dd={main.test_max_dd:.1%}, ret/dd={main.test_ret_dd:.2f}")
    df.to_csv(ROOT / "results" / "core.csv", index=False)
    res[0][1].to_frame("ret").to_parquet(ROOT / "results" / "core_returns.parquet")
    json.dump(dict(engine=engine, safe=safe, n=200, kind="sma"), open(ROOT / "config" / "core.json", "w"), indent=2)
    print(f"FINGERPRINT P3: engine={engine} spread={eng.iloc[0].spread:+.1%}, safe={safe}, "
          f"train={main.train_annual:.1%}/{main.train_max_dd:.1%}, test={main.test_annual:.1%}/{main.test_max_dd:.1%}, "
          f"neighbours_profitable={(df.train_annual > 0).sum()}/{len(df)}")
