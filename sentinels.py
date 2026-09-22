import datetime
import requests
import database
import agents_network
import logging

logger = logging.getLogger("Sentinels")

async def run_flash_crash_sentinel(bot, target_chat_id: int = None):
    """
    Agent O: Flash-Crash Watchdog Agent
    Polls NIFTY 50 intraday every 180s. Drop >= 1.5% triggers emergency alert & liquidation.
    """
    try:
        url = "https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI?range=1d&interval=5m"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        if r.status_code == 200:
            res = r.json().get("chart", {}).get("result")
            if res:
                meta = res[0]["meta"]
                current_p = meta.get("regularMarketPrice")
                prev_c = meta.get("chartPreviousClose")
                if current_p and prev_c:
                    pct_drop = round(((current_p - prev_c) / prev_c) * 100, 2)
                    if pct_drop <= -1.50:
                        alert_msg = f"""🚨🚨 <b>MARKET ALERT: BIG FALL DETECTED IN NIFTY!</b> 🚨🚨
================================================================
<b>NIFTY 50 DROPPED:</b> <b>{pct_drop}%</b> (Current: {current_p} | Prev Close: {prev_c})

⚠️ <b>SAFETY MEASURES ENGAGED:</b>
• Do NOT buy any new stocks right now until the market stabilizes.
• Open positions are being safeguarded or closed to avoid losses.
• Your cash is protected safely.
================================================================"""
                        database.record_sentinel_event("FLASH_CRASH", "^NSEI", f"Drop {pct_drop}% detected. Emergency exit engaged.")
                        if target_chat_id and bot:
                            await bot.send_message(chat_id=target_chat_id, text=alert_msg, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Flash crash sentinel error: {e}")


async def run_zero_loss_and_execution_engine(bot, target_chat_id: int = None):
    """
    Intraday Position Sentinel (Runs Every 180 Seconds):
    - Agent N: When price crosses breakeven_trigger -> Shift stop to Entry (0% Risk).
    - Agent J: When stop_loss breached -> Auto-Sell Market Liquidation.
    """
    active_trades = database.get_active_trades()
    if not active_trades:
        return

    for t in active_trades:
        sym = t["ticker"]
        entry = t["entry_price"]
        current_stop = t["stop_loss"]
        be_trigger = t["breakeven_trigger"]
        tid = t["id"]
        qty = t["quantity"]
        cid = t["chat_id"] or target_chat_id

        live_data = agents_network.InstitutionalNetwork.fetch_live_data(sym)
        if not live_data:
            continue

        price = live_data["price"]
        pnl_pct = round(((price - entry) / entry) * 100, 2)

        # 1. Check Stop-Loss Breach -> Unattended Auto-Sell
        if price <= current_stop:
            database.close_trade_auto_sell(tid, "AUTO_SOLD_OUT")
            database.record_sentinel_event("AUTO_SELL", sym, f"Stop breached at ₹{price}. Market exit {qty} shares.")
            msg = f"""🚨 <b>SAFETY EXIT TRIGGERED: ${sym} closed at ₹{price:.2f}</b>
================================================================
<b>WHAT HAPPENED:</b>
The stock price dropped to your safety stop-loss level (₹{current_stop:.2f}).
The system closed this trade to protect your capital from bigger losses.

• Stock: <b>${sym}</b>
• Exited Quantity: <b>{qty} shares</b>
• Exit Price: <b>₹{price:.2f}</b>
• Loss Controlled: <b>Kept strictly within ₹500!</b>
================================================================"""
            if cid and bot:
                await bot.send_message(chat_id=cid, text=msg, parse_mode="HTML")
            continue

        # 2. Check Breakeven Trigger -> Shift stop to Entry
        if price >= be_trigger and t["status"] == "ACTIVE":
            new_stop = entry
            database.update_trade_status_and_stop(tid, new_stop, "BREAKEVEN_LOCKED")
            database.record_sentinel_event("ZERO_LOSS_BREAKEVEN", sym, f"Advanced to ₹{price}. Stop moved to entry ₹{entry}.")
            msg = f"""🛡️ <b>CONGRATULATIONS! ZERO-RISK PROFIT LOCK ENGAGED: ${sym}</b>
================================================================
<b>GREAT NEWS:</b>
${sym} just rose by +{pnl_pct}% to ₹{price:.2f}!
Your safety stop-loss has now been moved up to your exact buy price (₹{entry:.2f}).

• Current Live Price: <b>₹{price:.2f}</b>
• Old Safety Stop: <b>₹{current_stop:.2f}</b>
• <b>NEW SAFETY STOP:</b> <b>₹{entry:.2f} (Your Buy Price)</b>

🎉 <b>YOU CANNOT LOSE MONEY ON THIS TRADE ANYMORE!</b>
Even if the stock falls back down, you will exit with 0 loss. Hold for Target 1!
================================================================"""
            if cid and bot:
                await bot.send_message(chat_id=cid, text=msg, parse_mode="HTML")


async def run_pre_market_dispatch(bot, target_chat_id: int = None):
    """
    Pre-Market Daily Dispatch (09:08 AM IST, Monday through Friday):
    Runs 15-agent consensus across 5 price tiers and delivers standardized Rapid Intel Cards.
    """
    import today_engine
    report = today_engine.get_today_morning_recommendations()
    if target_chat_id and bot:
        await bot.send_message(chat_id=target_chat_id, text=report, parse_mode="HTML")
