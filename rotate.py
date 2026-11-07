"""P12: swap a sleeve for one from the bench. Rules: corr <= 0.6 with the remaining sleeves and the
whole-account training return/DD must not get worse. Every change goes to results/changes.csv.
Rule changes go idea -> proof -> paper -> switch on; this never edits live code.

Usage: python rotate.py OUT_SLEEVE [IN_SLEEVE] [--apply]
"""
import json
import sys
import pandas as pd
from src.config import ROOT, S
from src.backtest import metrics, window
from src.p5_portfolio import sleeve_streams, combine, MAX_CORR

TR = S["train"]


def bench():
    df = pd.read_csv(ROOT / "results" / "sleeves_funnel.csv")
    return df[df.alive_neighbours_ok].sleeve.tolist()


def evaluate(current, out, cand):
    core = pd.read_parquet(ROOT / "results" / "core_returns.parquet")["ret"]
    rest = [s for s in current if s != out]
    streams = sleeve_streams(set(rest + [cand, out]))
    corr = max([window(streams[cand][0], TR).corr(window(streams[r][0], TR)) for r in rest], default=0)
    before = metrics(window(combine(core, streams, current)[0], TR))["ret_dd"]
    after = metrics(window(combine(core, streams, rest + [cand])[0], TR))["ret_dd"]
    return corr, before, after


if __name__ == "__main__":
    cfg = json.load(open(ROOT / "config" / "sleeves.json"))
    out = " ".join(sys.argv[1:3]) if len(sys.argv) > 2 else None
    if not out:
        print(__doc__); sys.exit(1)
    apply = "--apply" in sys.argv
    args = [a for a in sys.argv[3:] if a != "--apply"]
    cands = [" ".join(args[:2])] if args else [b for b in bench() if b not in cfg["sleeves"]]
    best = None
    for c in cands:
        corr, before, after = evaluate(cfg["sleeves"], out, c)
        ok = corr <= MAX_CORR and after >= before
        print(f"{c:<16} corr {corr:.2f}  ret/dd {before:.3f} -> {after:.3f}  {'OK' if ok else 'no'}")
        if ok and (best is None or after > best[1]):
            best = (c, after)
    if best and apply:
        cfg["sleeves"] = [s for s in cfg["sleeves"] if s != out] + [best[0]]
        json.dump(cfg, open(ROOT / "config" / "sleeves.json", "w"), indent=2)
        with open(ROOT / "results" / "changes.csv", "a") as f:
            f.write(f"{pd.Timestamp.now().date()},{out},swapped,{best[0]}\n")
        print("applied:", out, "->", best[0])
