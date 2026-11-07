"""Backtester. Signal on the close, trade at the next open, cost on every buy and sell."""
import numpy as np
import pandas as pd
from .config import S

COST = S["cost"]


class LookAheadError(Exception):
    pass


# ---------- metrics ----------
def max_dd(eq):
    return float((eq / eq.cummax() - 1).min())


def metrics(ret, trades=None):
    ret = ret.dropna()
    eq = (1 + ret).cumprod()
    yrs = len(ret) / 252
    total = float(eq.iloc[-1] - 1) if len(eq) else 0.0
    ann = float(eq.iloc[-1] ** (1 / yrs) - 1) if yrs > 0 and eq.iloc[-1] > 0 else -1.0
    dd = max_dd(eq) if len(eq) else 0.0
    m = dict(total=total, annual=ann, max_dd=dd, ret_dd=ann / abs(dd) if dd < 0 else np.nan)
    if trades is not None:
        t = trades["ret"] if len(trades) else pd.Series(dtype=float)
        wins, losses = t[t > 0].sum(), -t[t < 0].sum()
        m.update(trades=len(t), win_rate=float((t > 0).mean()) if len(t) else np.nan,
                 profit_factor=float(wins / losses) if losses > 0 else (np.inf if wins > 0 else np.nan),
                 avg_trade=float(t.mean()) if len(t) else np.nan,
                 exposure=float(trades["days"].sum() / max(len(ret), 1)) if len(t) else 0.0)
    return m


# ---------- weight engine (core) ----------
def run_weights(targets, opens, closes, cost=COST):
    """targets: weights decided on close of day t, held from open t+1.
    Daily return = old weights overnight (close->open) + new weights intraday (open->close) - cost*turnover."""
    tg = targets.reindex(closes.index).shift(1)  # effective at today's open
    cols = tg.columns
    o, c = opens[cols], closes[cols]
    overnight = o / c.shift(1) - 1
    intraday = c / o - 1
    held = tg.shift(1).fillna(0.0)
    new = tg.fillna(0.0)
    turnover = (new - held).abs().sum(axis=1)
    ret = (held * overnight.fillna(0)).sum(axis=1) + (new * intraday.fillna(0)).sum(axis=1) - cost * turnover
    ret = ret[tg.notna().any(axis=1)]
    switches = int(((new - held).abs().sum(axis=1) > 1e-9).sum())
    return ret, switches


# ---------- trade engine (sleeves) ----------
def run_trades(entry, exit_, o, h, l, c, max_days=10, stop=0.08, cost=COST):
    """Single-ticker, one position at a time. Returns (daily slot returns, trades frame).
    Entry: setup on close t -> buy open t+1. Exit: exit condition on close or max_days -> sell next open.
    Stop: resting stop at entry*(1-stop); fills at stop, or at the open if it gaps below."""
    idx = c.index
    e, x = entry.reindex(idx).fillna(False).values, exit_.reindex(idx).fillna(False).values
    O, H, L, C = o.values, h.values, l.values, c.values
    daily = np.zeros(len(idx))
    trades = []
    pos, entry_px, days, i0, prev_mark, pend_buy, pend_sell = False, 0, 0, 0, 0, False, False
    for i in range(len(idx)):
        if pend_sell and pos:  # sell at open
            px = O[i]
            daily[i] += px / prev_mark - 1 - cost
            trades.append((idx[i0], idx[i], px / entry_px - 1 - 2 * cost, days))
            pos, pend_sell = False, False
            continue  # no same-day re-entry
        if pend_buy and not pos:
            entry_px, pos, days, i0, pend_buy = O[i], True, 0, i, False
            prev_mark = entry_px * (1 + cost)  # pay cost on entry
            daily[i] -= 0  # cost folded into mark
        if pos:
            days += 1
            sp = entry_px * (1 - stop)
            if L[i] <= sp:  # stop hit intraday
                px = min(O[i], sp) if i != i0 else sp
                daily[i] += px * (1 - cost) / prev_mark - 1
                trades.append((idx[i0], idx[i], px / entry_px - 1 - 2 * cost, days))
                pos = False
                continue
            daily[i] += C[i] / prev_mark - 1
            prev_mark = C[i]
            if x[i] or days >= max_days:
                pend_sell = True
        elif e[i] and not np.isnan(C[i]):
            pend_buy = True
    tr = pd.DataFrame(trades, columns=["entry", "exit", "ret", "days"])
    return pd.Series(daily, index=idx), tr


def in_position(trades, index):
    """Daily 0/1 exposure from a trades frame."""
    s = pd.Series(0.0, index=index)
    for _, t in trades.iterrows():
        s.loc[t.entry:t.exit] = 1.0
    return s


# ---------- look-ahead guard ----------
def lookahead_guard(signal_fn, data, n=30, seed=0):
    """Recompute the signal with data cut at n random days; must equal the full-history value."""
    full = signal_fn(data)
    rng = np.random.default_rng(seed)
    valid = full.dropna().index
    days = rng.choice(valid[len(valid) // 10: -1], size=min(n, len(valid) - 1), replace=False)
    for d in days:
        cut = data.loc[:d]
        v = signal_fn(cut).loc[d]
        f = full.loc[d]
        same = (pd.isna(v) and pd.isna(f)) or v == f or (
            isinstance(v, float) and isinstance(f, float) and abs(v - f) < 1e-9)
        if not same:
            raise LookAheadError(f"signal on {pd.Timestamp(d).date()} changes when future data is removed")
    return True


def window(s, w):
    return s.loc[w[0]:w[1]]
