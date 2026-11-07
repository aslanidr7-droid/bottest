"""Broker layer. Only this file changes if the broker changes. Alpaca (paper) + a simulated broker for tests."""
import os


def keys_present():
    """Check keys exist without showing them."""
    return {k: bool(os.environ.get(k)) for k in ["ALPACA_API_KEY", "ALPACA_SECRET_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"]}


def load_env():
    try:
        from dotenv import load_dotenv
        from .config import ROOT
        load_dotenv(ROOT / ".env", override=False)
    except Exception:
        pass


class Alpaca:
    def __init__(self):
        load_env()
        from alpaca.trading.client import TradingClient
        paper = os.environ.get("ALPACA_PAPER", "true").lower() != "false"
        if not paper:
            raise RuntimeError("Real-money trading is locked. Set up paper first.")
        self.c = TradingClient(os.environ["ALPACA_API_KEY"], os.environ["ALPACA_SECRET_KEY"], paper=True)

    def clock(self):
        return self.c.get_clock()

    def calendar_next_open(self):
        return self.clock().next_open

    def account(self):
        a = self.c.get_account()
        return dict(equity=float(a.equity), last_equity=float(a.last_equity), cash=float(a.cash),
                    buying_power=float(a.buying_power), status=str(a.status))

    def positions(self):
        return {p.symbol: int(float(p.qty)) for p in self.c.get_all_positions()}

    def order_by_cid(self, cid):
        try:
            o = self.c.get_order_by_client_id(cid)
            return dict(status=str(o.status.value), filled_qty=int(float(o.filled_qty or 0)),
                        filled_avg_price=float(o.filled_avg_price or 0), id=str(o.id))
        except Exception:
            return None

    def order_by_id(self, oid):
        o = self.c.get_order_by_id(oid)
        return dict(status=str(o.status.value), filled_qty=int(float(o.filled_qty or 0)),
                    filled_avg_price=float(o.filled_avg_price or 0), id=str(o.id))

    def submit_opg(self, ticker, side, qty, cid):
        from alpaca.trading.requests import MarketOrderRequest
        from alpaca.trading.enums import OrderSide, TimeInForce
        o = self.c.submit_order(MarketOrderRequest(symbol=ticker, qty=int(qty), client_order_id=cid,
                                                   side=OrderSide.BUY if side == "buy" else OrderSide.SELL,
                                                   time_in_force=TimeInForce.OPG))
        return str(o.id)

    def submit_stop(self, ticker, qty, stop_price, cid):
        from alpaca.trading.requests import StopOrderRequest
        from alpaca.trading.enums import OrderSide, TimeInForce
        o = self.c.submit_order(StopOrderRequest(symbol=ticker, qty=int(qty), side=OrderSide.SELL,
                                                 stop_price=round(stop_price, 2), client_order_id=cid,
                                                 time_in_force=TimeInForce.GTC))
        return str(o.id)

    def cancel(self, oid):
        try:
            self.c.cancel_order_by_id(oid)
        except Exception:
            pass

    def close_all(self):
        self.c.cancel_orders()
        self.c.close_all_positions(cancel_orders=True)


class SimBroker:
    """In-memory broker for tests and dry runs."""

    def __init__(self, equity=100000.0, positions=None):
        self.eq, self.pos, self.orders, self.sent = equity, dict(positions or {}), {}, []

    def account(self):
        return dict(equity=self.eq, last_equity=self.eq, cash=self.eq, buying_power=2 * self.eq, status="ACTIVE")

    def positions(self):
        return {k: v for k, v in self.pos.items() if v}

    def order_by_cid(self, cid):
        return self.orders.get(cid)

    def order_by_id(self, oid):
        return next(o for o in self.orders.values() if o["id"] == oid)

    def submit_opg(self, ticker, side, qty, cid):
        if cid in self.orders:
            raise RuntimeError("duplicate client_order_id")
        self.orders[cid] = dict(status="new", filled_qty=0, filled_avg_price=0, id=cid, ticker=ticker, side=side, qty=qty)
        self.sent.append(cid)
        return cid

    def submit_stop(self, ticker, qty, stop_price, cid):
        return self.submit_opg(ticker, "sell", qty, cid)

    def fill_all(self, prices):
        for o in self.orders.values():
            if o["status"] == "new" and not o["id"].endswith("-stop"):
                o.update(status="filled", filled_qty=o["qty"], filled_avg_price=prices[o["ticker"]])
                self.pos[o["ticker"]] = self.pos.get(o["ticker"], 0) + (o["qty"] if o["side"] == "buy" else -o["qty"])

    def cancel(self, oid):
        for o in self.orders.values():
            if o["id"] == oid and o["status"] == "new":
                o["status"] = "canceled"

    def close_all(self):
        self.pos = {}
