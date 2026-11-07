"""P4: find the sleeves. DIP-BUY and BREAKOUT x every tradable ticker, through the funnel."""
import json
import pandas as pd
from .config import S, ROOT
from .data import load
from .signals import sleeve_entry, sleeve_exit, SLEEVE_DEFAULTS, neighbors
from .backtest import run_trades, metrics, window

TR, TE = S["train"], S["test"]
TRADABLE = [t for t in S["study"] if t not in S["no_trade"] + [S["cash"]]]
MIN_TRADES, MIN_PF = 8, 1.3
_D = None


def data():
    global _D
    if _D is None:
        _D = {f: load(f) for f in ["open", "high", "low", "close"]}
    return _D


def run(family, t, p):
    D = data()
    o, h, l, c = (D[f][t] for f in ["open", "high", "low", "close"])
    return run_trades(sleeve_entry(family, c, p), sleeve_exit(family, c, p), o, h, l, c,
                      max_days=p["max_days"], stop=p["stop"])


def stats(family, t, p, win):
    daily, tr = run(family, t, p)
    tw = tr[(tr.entry >= win[0]) & (tr.entry <= win[1])]
    return metrics(window(daily, win), tw), daily, tr


def funnel(tickers=TRADABLE, labels=None, train=TR, test=TE, log=True):
    if labels is None:
        labels = pd.read_csv(ROOT / "results" / "asset_study.csv").set_index("ticker")
    rows = []
    for t in tickers:
        for fam in ["dip", "breakout"]:
            p = SLEEVE_DEFAULTS[fam]
            m, _, _ = stats(fam, t, p, train)
            fits = bool(labels.loc[t, "snaps" if fam == "dip" else "keeps"])
            nb = [stats(fam, t, q, train)[0]["total"] for q in neighbors(fam, p)]
            mt = stats(fam, t, p, test)[0] if test else {}
            rec = dict(sleeve=f"{t} {fam}", ticker=t, family=fam, fits_label=fits,
                       profitable=m["total"] > 0, enough_trades=m["trades"] >= MIN_TRADES,
                       pf_ok=m["profit_factor"] >= MIN_PF, neighbours_ok=all(x > 0 for x in nb),
                       test_ok=(mt.get("total", 0) > 0) if test else None,
                       **{f"train_{k}": v for k, v in m.items()},
                       **{f"test_{k}": v for k, v in mt.items()})
            rows.append(rec)
    df = pd.DataFrame(rows)
    stages = ["fits_label", "profitable", "enough_trades", "pf_ok", "neighbours_ok"] + (["test_ok"] if test else [])
    alive = pd.Series(True, index=df.index)
    counts = [("candidates", len(df))]
    for s in stages:
        alive &= df[s].astype(bool)
        df[f"alive_{s}"] = alive
        counts.append((s, int(alive.sum())))
    df["passed"] = alive
    return df, counts


if __name__ == "__main__":
    df, counts = funnel()
    for s, n in counts:
        print(f"{s:>15}: {n}")
    keep = df[df.passed]
    cols = ["sleeve", "train_annual", "train_max_dd", "train_trades", "train_profit_factor",
            "test_annual", "test_trades", "test_profit_factor"]
    print(keep[cols].round(3).to_string(index=False))
    df.to_csv(ROOT / "results" / "sleeves_funnel.csv", index=False)
    log = df[["sleeve", "passed", "train_total", "train_trades", "train_profit_factor", "test_total"]].assign(step="P4")
    log.to_csv(ROOT / "results" / "ideas_log.csv", index=False)
    json.dump(keep.sleeve.tolist(), open(ROOT / "config" / "sleeves_passed.json", "w"), indent=2)
    print("FINGERPRINT P4: " + " -> ".join(str(n) for _, n in counts) + f"; passed={', '.join(keep.sleeve)}")
