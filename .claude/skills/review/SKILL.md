---
name: review
description: P13 scheduled review of the ALPHA trading system (weekly report; monthly keep/watch/review per sleeve; quarterly re-pick proposal). Runs Saturdays 09:00.
---
# ALPHA review

Rules: you may FIX CODE. You never change RULES (signals, parameters, sleeves, core, risk limits).
Anything rule-like goes to `reports/for_later.md` as a proposal for the human to approve.

1. `git pull`. Read CLAUDE.md, PROGRESS.md.
2. Weekly (every run):
   - `python3 -m pytest -q` — if a test fails, fix the code (not the rule), commit.
   - `python3 -m src.bot status` (keys are never printed).
   - Read `logs/runs.jsonl` for the last 7 days: halts, alerts, orders, fills, stops.
   - `python3 -m src.gap` — paper vs backtest gap by group.
   - Write `reports/weekly_YYYY-MM-DD.md`: equity, week return, DD from peak, positions, trades, halts,
     gap summary, kill-line distance for each sleeve and the core. Keep it short.
3. Monthly (first Saturday of the month): for each sleeve call `src.health.assess` and record
   keep / watch / review / out in the report. "out" from the kill line is applied automatically by
   `src.health.switch_off`; everything else is a proposal.
4. Quarterly (first Saturday of Jan/Apr/Jul/Oct): run the P6 re-pick on the latest 24 months
   (`src.p6_picking` logic for one quarter). If the pick differs, propose the swap with `python3 rotate.py OUT IN`
   output in the report and WAIT for approval. Never `--apply` yourself.
5. Send a 5-line Telegram summary with `src.notify.send`. Commit the report and push.
