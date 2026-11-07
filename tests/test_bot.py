"""P8 tests: bot == backtest over the last 60 days, no double orders, AI decisions, risk limits, reconcile."""
from datetime import datetime
import pandas as pd
import pytest
from src import bot, risk, live, ai_layer, notify
from src.broker import SimBroker
from src.data import load
from src.signals import SLEEVE_DEFAULTS
from src.backtest import run_trades
from src.signals import sleeve_entry, sleeve_exit, core_targets


@pytest.fixture(autouse=True)
def tmp_state(tmp_path, monkeypatch):
    monkeypatch.setattr(bot, "STATE_DIR", tmp_path)
    monkeypatch.setattr(bot, "STATE", tmp_path / "state.json")
    monkeypatch.setattr(bot, "LOCK", tmp_path / "lock")
    monkeypatch.setattr(bot, "RUNS", tmp_path / "runs.jsonl")
    monkeypatch.setattr(risk, "STATE", tmp_path)
    monkeypatch.setattr(risk, "PAUSE", tmp_path / "PAUSE")
    monkeypatch.setattr(risk, "SELL_ALL", tmp_path / "SELL_ALL")
    monkeypatch.setattr(ai_layer, "DECISIONS", tmp_path / "decisions.jsonl")
    monkeypatch.setattr(notify, "send", lambda t: None)
    monkeypatch.setattr(bot.notify, "send", lambda t: None)
    yield tmp_path


class StopSim(SimBroker):
    def __init__(self, *a, **k):
        super().__init__(*a, **k); self.stops = {}

    def submit_stop(self, ticker, qty, stop_price, cid):
        self.orders[cid] = dict(status="new", filled_qty=0, filled_avg_price=0, id=cid, ticker=ticker, side="sell", qty=qty)
        self.stops[cid] = stop_price
        return cid

    def cancel(self, oid):
        super().cancel(oid); self.stops.pop(oid, None)

    def check_stops(self, lows, opens):
        for cid, sp in list(self.stops.items()):
            o = self.orders[cid]
            if o["status"] == "new" and lows[o["ticker"]] <= sp:
                o.update(status="filled", filled_qty=o["qty"], filled_avg_price=min(opens[o["ticker"]], sp))
                self.pos[o["ticker"]] -= o["qty"]; del self.stops[cid]


def research_bars():
    return {f: load(f) for f in ["open", "high", "low", "close"]}


def simulate(days):
    bars = research_bars()
    b = StopSim()
    for d in days:
        o, l = bars["open"].loc[d], bars["low"].loc[d]
        b.fill_all(o)
        bot.morning(b, now=datetime(d.year, d.month, d.day, 9, 40))
        b.check_stops(l, o)
        r = bot.evening(b, bars=bars, as_of=d, now=datetime(d.year, d.month, d.day, 19, 15))
        assert not r.get("halt"), r
    return b, bars


def test_bot_matches_backtest_last_60_days():
    bars = research_bars()
    idx = bars["close"].index
    days = idx[-180:]
    b, _ = simulate(days)
    window = idx[-60:]
    for name in live.SLEEVES["sleeves"]:
        t, fam = name.split()
        p = SLEEVE_DEFAULTS[fam]
        c = bars["close"][t]
        _, tr = run_trades(sleeve_entry(fam, c, p), sleeve_exit(fam, c, p), bars["open"][t], bars["high"][t],
                           bars["low"][t], c, max_days=p["max_days"], stop=p["stop"])
        bt = sorted(str(x.date()) for x in tr.entry if x >= days[1] and x >= window[0])
        bot_buys = sorted(str(pd.Timestamp(cid[:10]) + pd.offsets.BDay(0)) for cid in b.sent
                          if f"buy-{name.replace(' ', '_')}" in cid)
        # bot cid date = signal day; backtest entry = next trading day
        nxt = {str(idx[i].date()): str(idx[i + 1].date()) for i in range(len(idx) - 1)}
        bot_entries = sorted(nxt[cid[:10]] for cid in b.sent if f"buy-{name.replace(' ', '_')}" in cid
                             and cid[:10] in nxt and nxt[cid[:10]] >= str(window[0].date()))
        assert bot_entries == bt, (name, bot_entries, bt)
    w = core_targets(bars["close"], live.CORE["engine"], live.CORE["safe"]).loc[window]
    st = bot.load_state()
    assert st["core"]["ticker"] == w.iloc[-1].idxmax() or st.get("pending")


def test_no_double_orders():
    bars = research_bars()
    d = bars["close"].index[-1]
    b = SimBroker()
    r1 = bot.evening(b, bars=bars, as_of=d)
    n = len(b.sent)
    st = bot.load_state(); st.pop("last_evening"); st["pending"] = []; bot.save_state(st)
    bot.evening(b, bars=bars, as_of=d)
    assert len(b.sent) == n and n > 0, r1
    with pytest.raises(RuntimeError):
        b.submit_opg("QQQ", "buy", 1, b.sent[0])


def test_ai_decision_menu_seal_and_override():
    from datetime import date
    sd = date.today().strftime("%Y%m%d")
    with pytest.raises(ValueError):
        ai_layer.record(sd, "buy everything", 5, "x")
    rec = ai_layer.record(sd, "cash", 5, "test")
    assert ai_layer.verify(rec)
    with pytest.raises(ValueError):
        ai_layer.record(sd, "safe", 5, "second decision for same statement")
    days = list(pd.bdate_range(date.today(), periods=10))
    assert ai_layer.active_override(days[1], days)["action"] == "cash"
    assert ai_layer.active_override(days[7], days) is None


def test_pause_blocks_new_sleeves_and_day_loss_writes_pause():
    risk.pause(True)
    ok, why = risk.check(dict(equity=100000, last_equity=100000), {})
    assert not ok and "PAUSE" in why[0]
    risk.pause(False)
    ok, why = risk.check(dict(equity=94000, last_equity=100000), {})
    assert not ok and risk.PAUSE.exists()


def test_order_cap():
    o = [dict(ticker="QQQ", side="buy", qty=1000, sleeve="core")]
    ok, dropped = risk.cap_orders(o, 100000, {"QQQ": 600.0}, {"core": 100000})
    assert not ok and dropped


def test_reconcile_mismatch_halts():
    bars = research_bars()
    b = SimBroker(positions={"QQQ": 5})
    r = bot.evening(b, bars=bars, as_of=bars["close"].index[-1])
    assert "reconcile" in r["halt"]


def test_stale_data_halts():
    bars = research_bars()
    r = bot.evening(SimBroker(), bars=bars, as_of=bars["close"].index[-1] + pd.Timedelta(days=3))
    assert "last bar" in r["halt"]
