import datetime
import zoneinfo
import logging
import requests
import database

logger = logging.getLogger("MarketStatusEngine")

# Official NSE / BSE Market Holidays (2025 - 2027)
NSE_HOLIDAYS = {
    # 2025
    "2025-01-26": "Republic Day",
    "2025-02-26": "Mahashivratri",
    "2025-03-14": "Holi",
    "2025-03-31": "Id-Ul-Fitr (Ramzan Id)",
    "2025-04-10": "Mahavir Jayanti",
    "2025-04-14": "Dr. Baba Saheb Ambedkar Jayanti",
    "2025-04-18": "Good Friday",
    "2025-05-01": "Maharashtra Day",
    "2025-06-07": "Bakri Id",
    "2025-08-15": "Independence Day",
    "2025-08-27": "Ganesh Chaturthi",
    "2025-10-02": "Mahatma Gandhi Jayanti",
    "2025-10-21": "Diwali Laxmi Pujan",
    "2025-10-22": "Diwali Balipratipada",
    "2025-11-05": "Guru Nanak Jayanti",
    "2025-12-25": "Christmas",
    # 2026
    "2026-01-26": "Republic Day",
    "2026-02-18": "Mahashivratri",
    "2026-03-03": "Holi",
    "2026-03-20": "Eid-ul-Fitr (Ramzan Id)",
    "2026-04-03": "Good Friday",
    "2026-04-14": "Dr. Ambedkar Jayanti",
    "2026-04-26": "Ram Navami",
    "2026-05-01": "Maharashtra Day",
    "2026-05-27": "Bakri Id (Id-Ul-Adha)",
    "2026-06-26": "Muharram",
    "2026-08-15": "Independence Day",
    "2026-08-26": "Milad-un-Nabi",
    "2026-10-02": "Mahatma Gandhi Jayanti",
    "2026-10-20": "Dussehra",
    "2026-11-08": "Diwali Laxmi Pujan (Muhurat Trading)",
    "2026-11-10": "Diwali Balipratipada",
    "2026-11-24": "Guru Nanak Jayanti",
    "2026-12-25": "Christmas"
}

def get_ist_now() -> datetime.datetime:
    """Returns the current real-time datetime in Indian Standard Time (Asia/Kolkata)."""
    return datetime.datetime.now(zoneinfo.ZoneInfo("Asia/Kolkata"))

def find_next_trading_day(dt: datetime.datetime) -> datetime.date:
    """Finds the next upcoming NSE trading day strictly after dt.date()."""
    cand = dt.date() + datetime.timedelta(days=1)
    while True:
        date_str = cand.strftime("%Y-%m-%d")
        if cand.weekday() < 5 and date_str not in NSE_HOLIDAYS:
            return cand
        cand += datetime.timedelta(days=1)

def format_delta(td: datetime.timedelta) -> str:
    """Converts a timedelta into a clean, human-friendly countdown."""
    total_seconds = max(0, int(td.total_seconds()))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    if hours > 0 and minutes > 0:
        return f"{hours} hr{'s' if hours > 1 else ''} {minutes} min{'s' if minutes > 1 else ''}"
    elif hours > 0:
        return f"{hours} hr{'s' if hours > 1 else ''}"
    else:
        return f"{max(1, minutes)} min{'s' if minutes != 1 else ''}"

def check_live_nifty_metric() -> tuple[float, float, float]:
    """Fetches real-time NIFTY 50 price, previous close, and intraday % change."""
    try:
        url = "https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI?range=1d&interval=5m"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=3)
        if r.status_code == 200:
            res = r.json().get("chart", {}).get("result")
            if res:
                meta = res[0]["meta"]
                cur_p = float(meta.get("regularMarketPrice") or 0.0)
                prev_c = float(meta.get("chartPreviousClose") or cur_p)
                if prev_c > 0 and cur_p > 0:
                    pct = round(((cur_p - prev_c) / prev_c) * 100, 2)
                    return cur_p, prev_c, pct
    except Exception as e:
        logger.debug(f"Nifty live check error: {e}")
    return 0.0, 0.0, 0.0

def has_recent_sentinel_crash(max_hours: int = 2) -> tuple[bool, str]:
    """Checks SQLite database for any recent flash-crash or circuit halt event."""
    try:
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT event_type, details, timestamp FROM sentinel_events "
            "WHERE event_type IN ('FLASH_CRASH', 'CIRCUIT_HALT') "
            "ORDER BY id DESC LIMIT 1"
        )
        row = cursor.fetchone()
        conn.close()
        if row:
            ev_type, details, ts_str = row
            return True, f"{ev_type}: {details}"
    except Exception as e:
        logger.debug(f"Sentinel db check error: {e}")
    return False, ""

def get_market_status(simulated_now: datetime.datetime = None) -> dict:
    """
    Computes real-time Indian Stock Market (NSE/BSE) operational status.
    Returns:
      - status: 'OPEN', 'CLOSED', 'PRE_OPEN', 'POST_MARKET', 'EMERGENCY_HALT'
      - is_open: bool
      - html: Complete formatted Telegram HTML message card
      - now_str: Current readable IST timestamp
    """
    now = simulated_now or get_ist_now()
    cur_date_str = now.strftime("%Y-%m-%d")
    now_time = now.time()
    readable_now = now.strftime("%A, %d %b %Y | %I:%M:%S %p IST")

    is_weekend = now.weekday() >= 5  # 5=Sat, 6=Sun
    holiday_name = NSE_HOLIDAYS.get(cur_date_str)
    is_holiday = bool(holiday_name)

    # Market Timing Boundaries (IST)
    t_pre_open_start = datetime.time(9, 0)
    t_market_open = datetime.time(9, 15)
    t_market_close = datetime.time(15, 30)
    t_post_market_end = datetime.time(16, 0)

    # 1. EMERGENCY HALT / CIRCUIT BREAKER / CRASH CHECK
    cur_nifty, prev_nifty, nifty_drop = check_live_nifty_metric()
    recent_crash, crash_details = has_recent_sentinel_crash(max_hours=2)
    is_circuit_breaker = (cur_nifty > 0 and nifty_drop <= -10.0)
    is_severe_flash_crash = (cur_nifty > 0 and nifty_drop <= -1.50)

    if (not is_weekend) and (not is_holiday) and (t_market_open <= now_time < t_market_close) and (is_circuit_breaker or is_severe_flash_crash or recent_crash):
        severity_title = "SEBI CIRCUIT BREAKER HALT (10% DROP)" if is_circuit_breaker else "MARKET FLASH-CRASH VOLATILITY ALERT"
        nifty_line = f"📉 <b>NIFTY 50 Index:</b> <b>{cur_nifty:,.2f}</b> ({nifty_drop:+.2f}%)\n" if cur_nifty > 0 else ""
        detail_line = f"⚠️ <b>Event Details:</b> {crash_details}\n" if crash_details else ""

        html_block = f"""🚨 <b>MARKET STATUS: EMERGENCY HALT / CRASH ALERT!</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📅 <b>Live Date &amp; Time:</b> {readable_now}
⚠️ <b>Emergency Event:</b> {severity_title}
{nifty_line}{detail_line}🛑 <b>Trading Action:</b> Market halted or severe risk active!
🛡️ <b>RupeeStreet Protection:</b> Automated capital safety engaged. Do NOT enter new trades!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
        return {
            "status": "EMERGENCY_HALT",
            "is_open": False,
            "html": html_block,
            "now_str": readable_now
        }

    # 2. WEEKEND CLOSURE
    if is_weekend:
        next_day = find_next_trading_day(now)
        next_open_dt = datetime.datetime.combine(next_day, t_market_open, tzinfo=now.tzinfo)
        time_left = format_delta(next_open_dt - now)
        next_open_str = f"{next_day.strftime('%A, %d %b %Y')} at 09:15 AM IST (in {time_left})"

        html_block = f"""🔴 <b>MARKET STATUS: CLOSED (WEEKEND)</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📅 <b>Live Date &amp; Time:</b> {readable_now}
⏰ <b>Normal Trading Hours:</b> 09:15 AM – 03:30 PM IST (Mon – Fri)
⏳ <b>Next Market Opens:</b> <b>{next_open_str}</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
        return {
            "status": "CLOSED",
            "is_open": False,
            "html": html_block,
            "now_str": readable_now
        }

    # 3. NSE TRADING HOLIDAY CLOSURE
    if is_holiday:
        next_day = find_next_trading_day(now)
        next_open_dt = datetime.datetime.combine(next_day, t_market_open, tzinfo=now.tzinfo)
        time_left = format_delta(next_open_dt - now)
        next_open_str = f"{next_day.strftime('%A, %d %b %Y')} at 09:15 AM IST (in {time_left})"

        html_block = f"""🔴 <b>MARKET STATUS: CLOSED (NSE HOLIDAY)</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📅 <b>Live Date &amp; Time:</b> {readable_now}
🏖️ <b>Holiday Observed:</b> <b>{holiday_name}</b>
⏰ <b>Normal Trading Hours:</b> 09:15 AM – 03:30 PM IST (Mon – Fri)
⏳ <b>Next Market Opens:</b> <b>{next_open_str}</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
        return {
            "status": "CLOSED",
            "is_open": False,
            "html": html_block,
            "now_str": readable_now
        }

    # 4. WEEKDAY MORNING BEFORE PRE-OPEN (Midnight to 09:00 AM IST)
    if now_time < t_pre_open_start:
        open_dt = datetime.datetime.combine(now.date(), t_market_open, tzinfo=now.tzinfo)
        time_left = format_delta(open_dt - now)
        html_block = f"""🔴 <b>MARKET STATUS: CLOSED</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📅 <b>Live Date &amp; Time:</b> {readable_now}
⏰ <b>Normal Trading Hours:</b> 09:15 AM – 03:30 PM IST (Mon – Fri)
⏳ <b>Next Market Opens:</b> <b>Today at 09:15 AM IST</b> (in {time_left})
━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
        return {
            "status": "CLOSED",
            "is_open": False,
            "html": html_block,
            "now_str": readable_now
        }

    # 5. WEEKDAY PRE-OPEN SESSION (09:00 AM to 09:15 AM IST)
    if t_pre_open_start <= now_time < t_market_open:
        open_dt = datetime.datetime.combine(now.date(), t_market_open, tzinfo=now.tzinfo)
        time_left = format_delta(open_dt - now)
        html_block = f"""🟡 <b>MARKET STATUS: PRE-OPEN SESSION</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📅 <b>Live Date &amp; Time:</b> {readable_now}
⏰ <b>Pre-Market Window:</b> 09:00 AM – 09:15 AM IST (Order Discovery)
⏳ <b>Live Trading Starts:</b> <b>Today at 09:15 AM IST</b> (in {time_left})
━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
        return {
            "status": "PRE_OPEN",
            "is_open": False,
            "html": html_block,
            "now_str": readable_now
        }

    # 6. WEEKDAY REGULAR TRADING SESSION (09:15 AM to 03:30 PM IST)
    if t_market_open <= now_time < t_market_close:
        close_dt = datetime.datetime.combine(now.date(), t_market_close, tzinfo=now.tzinfo)
        time_left = format_delta(close_dt - now)
        nifty_snippet = f" | NIFTY 50: {cur_nifty:,.2f} ({nifty_drop:+.2f}%)" if cur_nifty > 0 else ""

        html_block = f"""🟢 <b>MARKET STATUS: LIVE (OPEN)</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📅 <b>Live Date &amp; Time:</b> {readable_now}
⏰ <b>Session:</b> Regular NSE/BSE Cash Market{nifty_snippet}
⏱️ <b>Market Closes Today:</b> <b>At 03:30 PM IST</b> (in {time_left})
━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
        return {
            "status": "OPEN",
            "is_open": True,
            "html": html_block,
            "now_str": readable_now
        }

    # 7. WEEKDAY POST-MARKET / EVENING (After 03:30 PM IST)
    next_day = find_next_trading_day(now)
    next_open_dt = datetime.datetime.combine(next_day, t_market_open, tzinfo=now.tzinfo)
    time_left = format_delta(next_open_dt - now)
    day_label = "Tomorrow" if next_day == (now.date() + datetime.timedelta(days=1)) else next_day.strftime("%A, %d %b")

    html_block = f"""🔴 <b>MARKET STATUS: CLOSED (POST-MARKET)</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📅 <b>Live Date &amp; Time:</b> {readable_now}
⏰ <b>Normal Trading Hours:</b> 09:15 AM – 03:30 PM IST (Mon – Fri)
⏳ <b>Next Market Opens:</b> <b>{day_label} at 09:15 AM IST</b> (in {time_left})
━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
    return {
        "status": "CLOSED",
        "is_open": False,
        "html": html_block,
        "now_str": readable_now
    }

def get_market_status_banner(simulated_now: datetime.datetime = None) -> str:
    """Returns just the HTML banner block for embedding into menus."""
    status_data = get_market_status(simulated_now)
    return status_data["html"]
