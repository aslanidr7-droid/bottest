"""Single source of signal code. Backtest and live bot both import this file.

Every function only looks at data up to and including the bar it labels
(checked by backtest.lookahead_guard).
"""
import numpy as np
import pandas as pd


# ---------- indicators ----------
def sma(s, n):
    return s.rolling(n, min_periods=n).mean()


def ema(s, n):
    return s.ewm(span=n, adjust=False, min_periods=n).mean()


def rsi(s, n=2):
    d = s.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    rs = up / dn.replace(0, np.nan)
    out = 100 - 100 / (1 + rs)
    return out.where(dn != 0, 100.0)


# ---------- regime / core ----------
def above(close, n=200, kind="sma"):
    ma = sma(close, n) if kind == "sma" else ema(close, n)
    return (close > ma).where(ma.notna())


def cross(close, fast=50, slow=200):
    a, b = sma(close, fast), sma(close, slow)
    return (a > b).where(b.notna())


def core_targets(closes, engine="QQQ", safe="GLD", n=200, kind="sma"):
    """Target weights decided on each close: engine if above its MA, else safe."""
    up = cross(closes[engine]) if kind == "cross" else above(closes[engine], n, kind)
    w = pd.DataFrame(0.0, index=closes.index, columns=[engine, safe])
    w.loc[up == True, engine] = 1.0  # noqa: E712
    w.loc[up == False, safe] = 1.0  # noqa: E712
    w[up.isna()] = np.nan
    return w


# ---------- sleeves ----------
SLEEVE_DEFAULTS = {
    "dip": dict(rsi_n=2, rsi_max=10, trend=200, exit_ma=5, max_days=10, stop=0.08),
    "breakout": dict(high_n=50, trend=200, exit_low=10, max_days=20, stop=0.08),
}


def sleeve_entry(family, close, p):
    """Boolean entry setup on the close (enter at next open)."""
    if family == "dip":
        return (rsi(close, p["rsi_n"]) < p["rsi_max"]) & (close > sma(close, p["trend"]))
    if family == "breakout":
        hi = close.rolling(p["high_n"], min_periods=p["high_n"]).max()
        return (close >= hi) & (close > sma(close, p["trend"]))
    raise ValueError(family)


def sleeve_exit(family, close, p):
    """Boolean exit condition on the close (exit at next open). Day count / stop handled by the engine."""
    if family == "dip":
        return close > sma(close, p["exit_ma"])
    if family == "breakout":
        lo = close.rolling(p["exit_low"], min_periods=p["exit_low"]).min().shift(1)
        return close < lo
    raise ValueError(family)


def neighbors(family, p):
    """Parameter neighbours used for the plateau check."""
    out = []
    if family == "dip":
        for k, vals in [("rsi_max", [5, 15]), ("trend", [150, 250]), ("exit_ma", [3, 7])]:
            out += [{**p, k: v} for v in vals]
    else:
        for k, vals in [("high_n", [40, 60]), ("trend", [150, 250]), ("exit_low", [7, 15])]:
            out += [{**p, k: v} for v in vals]
    return out
