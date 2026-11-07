"""Download and freeze research data (data/prices.parquet). The live bot never writes here."""
import pandas as pd
import yfinance as yf
from .config import S, ROOT

PRICES = ROOT / "data" / "prices.parquet"


def download():
    end = (pd.Timestamp(S["data_end"]) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    df = yf.download(S["study"] + ["^VIX"], start=S["data_start"], end=end,
                     auto_adjust=True, progress=False, group_by="ticker", threads=True)
    rows = []
    for t in S["study"] + ["^VIX"]:
        d = df[t].dropna(how="all").copy()
        d["ticker"] = t
        rows.append(d.reset_index().rename(columns=str.lower))
    out = pd.concat(rows)[["date", "ticker", "open", "high", "low", "close", "volume"]]
    out.to_parquet(PRICES, index=False)
    return out


def load(field="close", tickers=None, trading_days_of="SPY"):
    """Wide frame (date x ticker). Rows aligned to SPY trading days (BTC trades 7 days)."""
    p = pd.read_parquet(PRICES)
    w = p.pivot(index="date", columns="ticker", values=field)
    w.index = pd.to_datetime(w.index)
    w = w.loc[w[trading_days_of].notna()]
    if tickers:
        w = w[tickers]
    return w.ffill()


if __name__ == "__main__":
    d = download()
    g = d.groupby("ticker")["date"].agg(["min", "max", "count"])
    print(g.to_string())
    print(f"FINGERPRINT D: tickers={d.ticker.nunique()}, rows={len(d)}, last={d.date.max().date()}")
