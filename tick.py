"""P9: the tick. Run every 30 minutes (or by the cloud scheduled task). Decides which job is due.

- evening: trading day, after 19:00 New York, not yet run today
- morning: trading day, after 09:35 New York, not yet run today
- missed run: after 23:30 New York on a trading day and the evening job has not run -> alert
Safe to call any number of times.
"""
import sys
from datetime import datetime, time
from zoneinfo import ZoneInfo
from src import bot, notify
from src.broker import Alpaca

NY = ZoneInfo("America/New_York")


def is_trading_day(b, d):
    from alpaca.trading.requests import GetCalendarRequest
    cal = b.c.get_calendar(GetCalendarRequest(start=d, end=d))
    return bool(cal) and cal[0].date == d


def main():
    now = datetime.now(NY)
    try:
        b = Alpaca()
    except Exception as e:
        notify.send(f"ALPHA tick: cannot reach broker ({type(e).__name__})"); return 2
    if not is_trading_day(b, now.date()):
        print("not a trading day"); return 0
    st = bot.load_state()
    today = str(now.date())
    ran = []
    if now.time() >= time(9, 35) and st.get("last_morning") != today:
        bot.morning(b, now=now); ran.append("morning")
    if now.time() >= time(19, 0) and st.get("last_evening") != today:
        r = bot.evening(b, now=now); ran.append("evening")
        if r.get("halt"):
            return 2
    elif now.time() >= time(23, 30) and st.get("last_evening") != today:
        notify.send(f"ALPHA: missed run — evening job has not run for {today}")
    print("ran:", ran or "nothing due")
    return 0


if __name__ == "__main__":
    sys.exit(main())
