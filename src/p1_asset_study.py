"""P1: how each asset moves. Labels computed on the training window only."""
import pandas as pd
from .config import S, ROOT
from .data import load
from .signals import sma, rsi


def events(mask, gap):
    """Non-overlapping event days: at least `gap` days apart."""
    out, last = [], -10**9
    for i, v in enumerate(mask.values):
        if v and i - last >= gap:
            out.append(mask.index[i]); last = i
    return pd.DatetimeIndex(out)


def study():
    C = load("close")
    tr0, tr1 = S["train"]
    spy_r = C["SPY"].pct_change()
    rows = []
    for t in S["study"]:
        c = C[t]
        r = c.pct_change()
        fwd20 = c.shift(-20) / c - 1
        fwd5 = c.shift(-5) / c - 1
        up = c > sma(c, 200)
        hi50 = c >= c.rolling(50).max()
        win = lambda s: s.loc[tr0:tr1]
        # KEEPS GOING
        kg_ev = events(win(up & hi50), 20)
        kg_ev = kg_ev[kg_ev <= pd.Timestamp(tr1) - pd.Timedelta(days=28)]
        kg_ret, kg_base = fwd20.loc[kg_ev].mean(), win(fwd20).mean()
        keeps = len(kg_ev) >= 6 and kg_ret > kg_base
        # SNAPS BACK
        sb_ev = events(win(up & (rsi(c, 2) < 10)), 5)
        sb_ev = sb_ev[sb_ev <= pd.Timestamp(tr1) - pd.Timedelta(days=7)]
        sb_ret, sb_base = fwd5.loc[sb_ev].mean(), win(fwd5).mean()
        snaps = len(sb_ev) >= 12 and sb_ret > sb_base
        # HOLDS UP
        down = win((C['SPY'] < sma(C['SPY'], 200)).shift(1).fillna(False).astype(bool))  # SPY down regime
        on_down = win(r)[down].mean()
        cash_down = win(C["BIL"].pct_change())[down].mean()
        corr = win(r).corr(win(spy_r))
        holds = on_down > cash_down and corr < 0.5
        # WILD
        vol = win(r).std() * 252 ** 0.5
        wild = vol > 2 * win(spy_r).std() * 252 ** 0.5
        labels = [n for n, f in [("KEEPS GOING", keeps), ("SNAPS BACK", snaps),
                                 ("HOLDS UP", holds), ("WILD", wild)] if f]
        rows.append(dict(ticker=t, labels=", ".join(labels) or "—",
                         kg_events=len(kg_ev), kg_fwd20=kg_ret, kg_base20=kg_base,
                         sb_events=len(sb_ev), sb_fwd5=sb_ret, sb_base5=sb_base,
                         ret_on_spy_down=on_down, corr_spy=corr, vol=vol,
                         keeps=keeps, snaps=snaps, holds=holds, wild=wild))
    df = pd.DataFrame(rows)
    df.to_csv(ROOT / "results" / "asset_study.csv", index=False)
    corr = C[S["study"]].pct_change().loc[tr0:tr1].corr()
    corr.to_csv(ROOT / "results" / "correlation.csv")
    return df, corr


if __name__ == "__main__":
    df, corr = study()
    print(df[["ticker", "labels", "kg_events", "sb_events", "corr_spy", "vol"]].round(2).to_string(index=False))
    print(f"FINGERPRINT P1: keeps={df.keeps.sum()}, snaps={df.snaps.sum()}, holds={df.holds.sum()}, wild={df.wild.sum()}")
