# PROGRESS — read this first when resuming

Branch: `alpha-system` in `aslanidr7-droid/bottest`. Old PPO bot project (Botprojesi/, metriler.py) deleted on this branch.
Environment: cloud env `alpha-trading` (Yahoo, Alpaca paper, Telegram, federalreserve.gov allowed).
Run any step: `python3 -m src.<module>` from repo root. Tests: `python3 -m pytest -q`.

| Step | Status | FINGERPRINT | Video |
|---|---|---|---|
| P0 setup | done | folders=10, git=yes | same |
| D data | done | tickers=25 (24+VIX), rows=40396, last=2026-10-23 | — |
| P1 asset study | done | keeps=11, snaps=16, holds=4, wild=1 (SPY/IWM/DIA snaps; QQQ both) | same pattern |
| P2 backtester | done | planted=0.79%, noise=-0.21%, cheating=stopped, real=pass | 0.8 / -0.1 / stopped / pass |
| P3 core | done | QQQ spread +23.8%, GLD; train 13.7%/-28.4%; test 25.3%/-11.3% | +23.4, GLD, 13.5/-28.4, 24.8/-11.2 |
| P4 sleeves | next | | 44→25→20→18→14→11→7 |

## Notes / decisions
- HOLDS UP uses "SPY below its 200-day average" as down days (daily negative days gave 0 holders).
- BREAKOUT exit rule is not given in the video: exit when close < prior 10-day low, or 20 days, stop -8%.
- GitHub push from this session was refused (Claude GitHub App not linked) → commits are local until fixed.
