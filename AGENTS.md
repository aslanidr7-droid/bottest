# ALPHA Trading System — House rules

Read `PLAN.md` (the step list) and `PROGRESS.md` (what is done, what is next) before doing anything.
After each step: update PROGRESS.md, print the step's FINGERPRINT line, commit.

## My settings
- Bar size: daily. Data: Yahoo Finance (yfinance), 2020-07-01 → 2026-10-23, split/dividend adjusted.
- Training window: 2022-01-03 → 2024-12-31. Locked test: 2025-01-02 → 2026-10-23.
- Study tickers: SPY QQQ IWM DIA XLK XLF XLE XLV XLI XLY XLP XLU XLB XLC XLRE TLT IEF SHY BIL GLD SLV USO DBC BTC-USD
- Engine candidates: SPY QQQ IWM DIA. Safe candidates: BIL SHY IEF TLT GLD. Cash ticker: BIL.
- BTC-USD is studied only, never traded.
- Cost: 0.05% on every buy and every sell. Starting capital: $100,000.
- All settings live in `config/settings.yaml`; code reads them from there.

## Data
- Research data `data/prices.parquet` is frozen at the end date. The live bot never writes to it.

## Windows
- Every choice and every tweak is made on the training window only.
- The locked test is run once. Nothing is changed after looking at it.

## Backtests
- Signal on the close, trade at the next day's open. Long only, no leverage (P5 adds margin explicitly and says so).
- Nothing is tested until the backtester has passed the fake-data checks (P2).
- Every test reports: total return, annual return, max drawdown, return/drawdown, trades, win rate,
  profit factor, average trade, exposure. Main score: return / drawdown.
- `src/signals.py` is the single source of signal code; backtest and bot both import it.

## Other rules
- Never change a rule because of recent results.
- Scheduled reviews may fix code. They never change rules.
- Log every idea tested, including failures, in `results/ideas_log.csv`.
- Never open, print or log `.env` or any secret. Check that keys exist without showing them.
