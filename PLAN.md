# ALPHA Trading Sistemi — İlerleme Planı

Kaynak: "How To Actually Build an AI Trading Bot With Claude" (AI Pathways) videosunun raporu.
Amaç: videoda yapılan her adımı (P0 → P13) aynı sırayla, aynı ayarlarla kopyalamak.
Durum takibi: `PROGRESS.md` (her adım bitince güncellenir; bağlam kopsa bile buradan devam edilir).

## Ayarlar (P0 "My settings")
- Bar: günlük. Veri: yfinance, 2020-07-01 → 2026-10-23, split/temettü düzeltmeli.
- Training: 2022-01-03 → 2024-12-31. Locked test: 2025-01-02 → 2026-10-23 (tek sefer).
- Study tickers (24): SPY QQQ IWM DIA XLK XLF XLE XLV XLI XLY XLP XLU XLB XLC XLRE TLT IEF SHY BIL GLD SLV USO DBC BTC-USD
- Engine: SPY QQQ IWM DIA · Safe: BIL SHY IEF TLT GLD · Cash: BIL · BTC sadece incelenir.
- Maliyet %0,05 / taraf. Sermaye $100.000. Sinyal kapanışta, işlem ertesi açılışta.
- Ana ölçüt: getiri / max drawdown.

## Adımlar

| # | Adım | Çıktı | Kontrol (FINGERPRINT) |
|---|---|---|---|
| P0 | Setup: klasörler, CLAUDE.md/AGENTS.md, .env.example, git, dashboard | iskelet | `folders=10, git=yes` |
| D | Veri indir ve dondur | `data/prices.parquet` | 24 ticker, tarih aralığı |
| P1 | Asset study: KEEPS GOING / SNAPS BACK / HOLDS UP etiketleri, korelasyon | `results/asset_study.csv`, dashboard bölümü | etiket sayıları |
| P2 | Backtester doğrulama: planted edge, noise, cheating, look-ahead | `src/backtest.py`, `tests/` | `planted≈0.8%, noise≈0, cheating=stopped` |
| P3 | Core: engine + safe seçimi, 200 SMA kuralı, komşular, locked test | `results/core.csv` | engine, safe, train/test ret & DD |
| P4 | Sleeve hunisi: DIP-BUY/BREAKOUT × ticker, 44 → … | `results/sleeves_funnel.csv` | huni sayıları |
| P4b/4c | Opsiyonel: Claude fikirleri / screener (videoda çalıştırılmadı) | — | atlandı (videoyla aynı) |
| P5 | Core + sleeve birleşimi, %20 slot, marjin %6,5, greedy, korelasyon ≤0,6 | `results/portfolio.csv` | tüm hesap tablosu |
| P5b | Opsiyonel VIX/breadth filtresi | — | opsiyonel |
| P6 | Seçim yönteminin walk-forward testi (çeyreklik, 24a seçim / 12a kontrol) | `results/picking_test.csv` | 11 çeyrek sonucu |
| P7 | AI katmanı (FOMC kararı, maskeli replay) | `src/ai_layer.py` | videoda çalıştırılmadı; kod hazır, çalıştırma opsiyonel |
| P8 | Bot: Alpaca paper, 11 adımlı akşam döngüsü, sabah stop, dry-run, testler | `src/bot.py`, `src/signals.py` | `paper=yes, N test pass` |
| P8b | Risk limitleri: PAUSE, %5 günlük, DD > train worst → borç dur | `src/risk.py` | testler |
| P9 | Zamanlama + Telegram (hata, akşam/sabah özeti, missed run) | `tick.py`, scheduled task | test mesajı |
| P10 | Fed kontrolü (hafta içi 17:00) | scheduled task | — |
| P11 | Paper vs backtest gap raporu (6 grup) | `src/gap.py` | testler |
| P12 | Sleeve çıkarma: kill line 2×, çeyreklik, işlem sıklığı; bench + rotate.py | `src/health.py`, `rotate.py` | testler |
| P13 | Cumartesi 09:00 Claude incelemesi (haftalık/aylık/çeyreklik) | scheduled task | ilk rapor |

## Bulutta çalışma (PC kapalıyken)
- Kod GitHub'da (`aslanidr7-droid/bottest`, dal `alpha-system`) tutulur; her adım sonunda commit + push.
- Videodaki "OS zamanlayıcısı 30 dk'da bir tick.py" yerine: Claude bulut **scheduled task**
  (her fire yeni oturum, repoyu çeker, `python tick.py` çalıştırır, bot state'ini repoya commit eder).
- Anahtarlar `.env`'e değil, ortamın network secret'larına (Alpaca, Telegram) girilir; kod asla yazdırmaz.

## Bilinen sapmalar (videoya göre)
- Videodaki eleştiri noktaları (locked test seçimde kullanılmış, kaldıraç) videoyla aynı şekilde kopyalanır,
  ama raporlarda açıkça işaretlenir.
