"""One-page HTML dashboard: asset labels, correlation, core, sleeve funnel, portfolio, picking test, bot status."""
import base64, io, json
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from .config import ROOT, S


def img(fig):
    b = io.BytesIO(); fig.savefig(b, format="png", dpi=110, bbox_inches="tight"); plt.close(fig)
    return f'<img src="data:image/png;base64,{base64.b64encode(b.getvalue()).decode()}">'


def table(df, pct=()):
    d = df.copy()
    for c in d.columns:
        if c in pct or any(k in c for k in ("annual", "_dd", "ret", "total", "fwd", "base", "system", "core")) and d[c].dtype.kind == "f":
            d[c] = d[c].map(lambda v: f"{v:.1%}" if pd.notna(v) else "")
    return d.to_html(index=False, border=0, float_format=lambda v: f"{v:.2f}")


def build():
    R = ROOT / "results"
    parts = ["<h1>ALPHA Trading System</h1>", f"<p>Train {S['train'][0]} → {S['train'][1]} · Locked test {S['test'][0]} → {S['test'][1]} · cost {S['cost']:.2%}/side</p>"]
    a = pd.read_csv(R / "asset_study.csv")
    parts += ["<h2>P1 · How each asset moves</h2>", table(a[["ticker", "labels", "kg_events", "sb_events", "corr_spy", "vol"]], pct=("vol",))]
    corr = pd.read_csv(R / "correlation.csv", index_col=0)
    fig, ax = plt.subplots(figsize=(9, 7)); im = ax.imshow(corr, cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(range(len(corr))); ax.set_xticklabels(corr.columns, rotation=90, fontsize=7)
    ax.set_yticks(range(len(corr))); ax.set_yticklabels(corr.index, fontsize=7); fig.colorbar(im)
    parts.append(img(fig))
    parts += ["<h2>P3 · Core</h2>", table(pd.read_csv(R / "core.csv")[["variant", "train_annual", "train_max_dd", "train_ret_dd", "switches"]])]
    f = pd.read_csv(R / "sleeves_funnel.csv")
    stages = ["fits_label", "profitable", "enough_trades", "pf_ok", "neighbours_ok", "test_ok"]
    fun = pd.DataFrame({"stage": ["candidates"] + stages, "left": [len(f)] + [int(f[f"alive_{s}"].sum()) for s in stages]})
    parts += ["<h2>P4 · Sleeve funnel</h2>", fun.to_html(index=False, border=0),
              table(f[f.passed][["sleeve", "train_annual", "train_max_dd", "train_trades", "train_profit_factor", "test_annual", "test_trades"]])]
    parts += ["<h2>P5 · Core + sleeves</h2>", "<p><b>Locked test here is a check, not a fresh test:</b> the funnel already used it.</p>",
              table(pd.read_csv(R / "portfolio.csv"))]
    pr = pd.read_parquet(R / "portfolio_returns.parquet").loc[S["train"][0]:S["test"][1]]
    from .data import load
    spy = load("close")["SPY"].pct_change().reindex(pr.index).fillna(0)
    fig, ax = plt.subplots(figsize=(10, 4))
    for col, lab in [("account", "Whole account"), ("core", "Core QQQ/GLD")]:
        ax.plot(S["capital"] * (1 + pr[col]).cumprod(), label=lab)
    ax.plot(S["capital"] * (1 + spy).cumprod(), label="SPY", alpha=.7)
    ax.axvline(pd.Timestamp(S["test"][0]), color="k", ls="--", lw=1); ax.legend(); ax.set_yscale("log")
    parts.append(img(fig))
    parts += ["<h2>P6 · Test the picking (walk-forward)</h2>", table(pd.read_csv(R / "picking_test.csv"))]
    st = ROOT / "state" / "state.json"
    parts += ["<h2>Bot</h2>", f"<pre>{st.read_text() if st.exists() else 'not started'}</pre>"]
    css = "body{font:14px system-ui;max-width:1100px;margin:auto;padding:16px}table{border-collapse:collapse;margin:8px 0}td,th{padding:3px 8px;border-bottom:1px solid #ddd;text-align:right}img{max-width:100%}"
    (ROOT / "dashboard" / "index.html").write_text(f"<html><head><meta charset='utf-8'><title>ALPHA dashboard</title><style>{css}</style></head><body>{''.join(parts)}</body></html>")


if __name__ == "__main__":
    build(); print("dashboard/index.html written")
