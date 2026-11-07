"""P2: the backtester must pass fake-data checks before anything real is tested."""
import numpy as np
import pandas as pd
import pytest
from src.backtest import run_trades, lookahead_guard, LookAheadError


def fake_market(n=3000, seed=1, planted=None):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2000-01-03", periods=n)
    night = rng.normal(0, 0.004, n)
    day = rng.normal(0, 0.008, n)
    marks = pd.Series(rng.random(n) < 0.05, index=idx)
    if planted:
        day = day + np.r_[0, marks.values[:-1]] * planted  # +x% on the day after a mark (open->close)
    o, c = np.empty(n), np.empty(n)
    px = 100.0
    for i in range(n):
        o[i] = px * (1 + night[i])
        c[i] = o[i] * (1 + day[i])
        px = c[i]
    o, c = pd.Series(o, idx), pd.Series(c, idx)
    h, l = pd.concat([o, c], axis=1).max(axis=1) * 1.001, pd.concat([o, c], axis=1).min(axis=1) * 0.999
    return o, h, l, c, marks


def one_day(marks, o, h, l, c):
    never = pd.Series(False, index=c.index)
    return run_trades(marks, never, o, h, l, c, max_days=1, stop=0.99)


def test_planted_edge():
    o, h, l, c, marks = fake_market(planted=0.01)
    _, tr = one_day(marks, o, h, l, c)
    avg = tr.ret.mean()
    print(f"planted edge avg trade = {avg:.2%}")
    assert 0.006 <= avg <= 0.012


def test_pure_noise():
    o, h, l, c, marks = fake_market()
    _, tr = one_day(marks, o, h, l, c)
    avg = tr.ret.mean()
    print(f"noise avg trade = {avg:.2%}")
    assert -0.004 <= avg <= 0.002


def test_cheating_signal_is_stopped():
    o, h, l, c, _ = fake_market()
    cheat = lambda d: (d.shift(-1) > d)  # looks at tomorrow's close
    with pytest.raises(LookAheadError):
        lookahead_guard(cheat, c)


def test_real_signal_passes_guard():
    from src.signals import sleeve_entry, SLEEVE_DEFAULTS
    o, h, l, c, _ = fake_market()
    assert lookahead_guard(lambda d: sleeve_entry("dip", d, SLEEVE_DEFAULTS["dip"]), c)
    assert lookahead_guard(lambda d: sleeve_entry("breakout", d, SLEEVE_DEFAULTS["breakout"]), c)
