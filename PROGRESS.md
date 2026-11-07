# PROGRESS — read this first when resuming

Branch: `alpha-system` in `aslanidr7-droid/bottest`. Old PPO bot project (Botprojesi/, metriler.py) deleted on this branch.
Cloud environment: `alpha-trading` (Yahoo, Alpaca paper, Telegram, federalreserve.gov allowed).
Run any step: `python3 -m src.<module>` from repo root. Tests: `python3 -m pytest -q` (12 pass).

| Step | Status | Result (ours) | Video |
|---|---|---|---|
| P0 setup | done | folders=10, git=yes, CLAUDE.md/AGENTS.md, settings.yaml | same |
| D data | done | 24 tickers + ^VIX, 2020-07-01 → 2026-10-23, frozen `data/prices.parquet` | — |
| P1 asset study | done | keeps=11, snaps=16, holds=4, wild=1; SPY/IWM/DIA snaps, QQQ both | same pattern |
| P2 backtester | done | planted 0.79%, noise −0.21%, cheating stopped, real pass | 0.8 / −0.1 / stopped / pass |
| P3 core | done | QQQ +23.8 / GLD; train 13.7% / −28.4%; test 25.3% / −11.3%; 6/6 neighbours | +23.4, GLD, 13.5/−28.4, 24.8/−11.2 |
| P4 sleeves | done | 44→24→18→18→13→9→6: QQQ dip, QQQ breakout, XLK dip, XLY dip, XLC breakout, SHY breakout | 44→25→20→18→14→11→7 |
| P5 portfolio | done | XLC breakout + QQQ dip; account train 15.9%/−29.4%, test 25.2%/−12.7%; $233,032 vs SPY $170,476; max borrow 40% | 28.7/−13.1, $244,092 vs $169,912, borrow 60.5% |
| P6 picking test | done | 11 quarters, beat core 6/11, ret/DD 2.19 vs core 2.11 | — |
| P7 AI layer | code done | `src/ai_layer.py`: menu, seal, redaction, 1 decision/statement, ≤5 bdays | not run in video either |
| P8 bot | code done, tested in sim | `src/bot.py` 11-step evening, morning stops, dry-run, as-of | paper=yes, 17 tests |
| P8b risk | done | PAUSE, SELL_ALL, 3%/5% day loss, DD>train worst, 105% cap | same |
| P9 schedule + Telegram | code done | `tick.py`, `src/notify.py`; NEEDS keys + scheduled tasks | — |
| P10 Fed check | code done | scheduled task to create (weekdays 17:00 NY) | — |
| P11 gap | code done | `src/gap.py` (6 groups) — needs paper history | — |
| P12 sleeve exit | code done | `src/health.py` kill line, `rotate.py` bench swap | — |
| P13 reviews | skill done | `.claude/skills/review/SKILL.md` — scheduled task Sat 09:00 NY | — |
| Dashboard | done | `python3 -m src.dashboard` → dashboard/index.html | — |

## BLOCKERS (user action)
1. ~~GitHub push~~ — fixed, branch alpha-system is on GitHub.
2. ~~Env vars~~ — set 2026-11-07. Paper check: account ACTIVE, equity $104,343.47, no positions; dry-run 2026-11-06 → buy 280 GLD (core=GLD). Telegram send not yet tested; getUpdates empty (message the bot once).

## NEXT (after blockers)
1. `python3 -m src.bot status` → paper account visible. `python3 -m src.bot evening --dry-run` → expect ~1 core buy (QQQ or GLD).
2. Telegram test: `python3 -c "from src import notify; notify.send('ALPHA test')"`; chat id via `notify.find_chat_id()`.
3. Create scheduled tasks (fresh session each fire, repo alpha-system branch):
   - evening  CRON_TZ=America/New_York 17 19 * * 1-5 → pull, `python3 tick.py`, commit state/ logs/, push
   - morning  CRON_TZ=America/New_York 41 9 * * 1-5 → same
   - missed   CRON_TZ=America/New_York 33 23 * * 1-5 → same (tick sends missed-run alert)
   - fed      CRON_TZ=America/New_York 3 17 * * 1-5 → check new FOMC statement, decide via ai_layer.record
   - review   CRON_TZ=America/New_York 2 9 * * 6 → run review skill
4. First live paper week → `python3 -m src.gap`.

## Notes / decisions
- HOLDS UP uses "SPY below its 200-day average" as down days (daily negative days gave 0 holders).
- BREAKOUT exit rule is not given in the video: exit when close < prior 10-day low, or 20 days, stop −8%.
- Neighbour sets are my definition; XLK/XLF breakout and GLD dip failed neighbours here. Not tuned to match the video.
- Flagged weaknesses copied from the video on purpose: locked test used in the funnel (P5 "test" is a check), margin leverage.
- P6: re-picking sometimes chooses up to 9 sleeves (180% borrowing). Live config uses the P5 pick (2 sleeves, max 40%).

## Scheduled tasks (created 2026-11-07, fresh cloud session each fire, env alpha-trading)
- evening  trig_01Ch3p3j85Qh4MZpRLHtarUc  Mon-Fri 19:17 NY
- morning  trig_01JBmbWMErqsN2NW8vbhSS7v  Mon-Fri 09:41 NY
- missed   trig_01MVWyrKjsh2bsCLq1HZ8DSm  Mon-Fri 23:33 NY
- fed      trig_01EBHPBXYxbLycSzUQLRfkQi  Mon-Fri 17:03 NY
- review   trig_017VM3KLi9KBuUSQNmKSRw41  Sat 09:02 NY
Each run stops with a report if Alpaca keys are missing.
