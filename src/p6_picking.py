"""P6: test the PICKING, not the picks. Each quarter, sleeves are re-selected using only data
available before that quarter (24 months selection, last 12 months as control), then held one quarter."""
import pandas as pd
from .config import ROOT
from .backtest import metrics
from .p1_asset_study import study
from . import p4_sleeves as p4
from .p5_portfolio import sleeve_streams, combine, greedy

if __name__ == "__main__":
    core = pd.read_parquet(ROOT / "results" / "core_returns.parquet")["ret"]
    starts = pd.date_range("2024-01-01", "2026-07-01", freq="QS")
    pieces_sys, pieces_core, rows = [], [], []
    for q0 in starts:
        q1 = q0 + pd.offsets.QuarterEnd(0)
        sel = [str((q0 - pd.DateOffset(months=24)).date()), str((q0 - pd.Timedelta(days=1)).date())]
        ctl = [str((q0 - pd.DateOffset(months=12)).date()), sel[1]]
        labels, _ = study(sel, save=False)
        df, _ = p4.funnel(labels=labels, train=sel, test=ctl)
        passed = df[df.passed].sleeve.tolist()
        streams = sleeve_streams(passed)
        chosen, _ = greedy(core.loc[:sel[1]], streams, win=sel) if passed else ([], [])
        total, _ = combine(core, streams, chosen)
        rs, rc = total.loc[q0:q1], core.loc[q0:q1]
        pieces_sys.append(rs); pieces_core.append(rc)
        rows.append(dict(quarter=f"{q0.year}Q{q0.quarter}", picked=", ".join(chosen) or "none",
                         system=(1 + rs).prod() - 1, core=(1 + rc).prod() - 1))
        print(f"{rows[-1]['quarter']}: {rows[-1]['picked']:<40} sys {rows[-1]['system']:+.1%}  core {rows[-1]['core']:+.1%}")
    s, c = metrics(pd.concat(pieces_sys)), metrics(pd.concat(pieces_core))
    pd.DataFrame(rows).to_csv(ROOT / "results" / "picking_test.csv", index=False)
    beat = sum(r["system"] > r["core"] for r in rows)
    print(f"Walk-forward system: annual {s['annual']:.1%}, DD {s['max_dd']:.1%}, ret/dd {s['ret_dd']:.2f} | "
          f"core alone: annual {c['annual']:.1%}, DD {c['max_dd']:.1%}, ret/dd {c['ret_dd']:.2f}")
    print(f"FINGERPRINT P6: quarters={len(rows)}, beat_core={beat}/{len(rows)}, "
          f"sys_ret_dd={s['ret_dd']:.2f}, core_ret_dd={c['ret_dd']:.2f}")
