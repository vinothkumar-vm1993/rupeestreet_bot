"""
RupeeStreet WhatsApp Integration Engine
=======================================
Enables full two-way WhatsApp Bot capabilities:
- Native Meta WhatsApp Cloud API (Graph API) Webhook & Dispatch
- Twilio WhatsApp Sandbox / REST Webhook Fallback
- Automatic HTML to WhatsApp Markdown formatting
- Numbered menu shortcuts (1: Today, 2: Rates, 3: Status, 4: Forecast, 5: Rules)
- Full 15-agent quantitative stock screening & ₹500 risk protection over WhatsApp
"""

import os
import re
import json
import logging
import urllib.request
import urllib.parse
import urllib.error

import agents_network
import search_engine
import today_engine
import commodities_engine
import market_status_engine
import macro_news_engine

logger = logging.getLogger("RupeeStreetWhatsApp")

# Configuration from Environment Variables
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN", "")
WHATSAPP_PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "")
WHATSAPP_VERIFY_TOKEN = os.environ.get("WHATSAPP_VERIFY_TOKEN", "rupeestreet_verify_2026")

# Twilio Support (Optional)
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER", "")


def html_to_whatsapp(text: str) -> str:
    """Converts HTML-formatted strings into clean WhatsApp Markdown."""
    if not text:
        return ""
    text = text.replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")
    text = re.sub(r'<\/?(b|strong)>', '*', text)
    text = re.sub(r'<\/?(i|em)>', '_', text)
    text = re.sub(r'<\/?(code|pre)>', '```', text)
    text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"')
    text = re.sub(r'<[^>]+>', '', text)
    return text.strip()


def get_whatsapp_menu_text() -> str:
    """Returns clean, numbered menu for easy WhatsApp typing."""
    market_banner = html_to_whatsapp(market_status_engine.get_market_status_banner())
    return f"""👋 *Welcome to RupeeStreet WhatsApp Assistant!*
_Your disciplined stock market & capital protection co-pilot (NSE/BSE)._

{market_banner}

📌 *REPLY WITH ANY NUMBER OR KEYWORD:*
*1* or *today*  - 🌅 Today's Top Buy Recommendations
*2* or *rates*  - 🪙 Live Gold, Silver, Petrol, Diesel & USD
*3* or *status* - 🕒 Live Market Open/Closed Status
*4* or *forecast*- 🔮 Gold, Silver & Oil Forecast Guide
*5* or *rules*  - 🛡️ 3 Golden Safety Rules (Max ₹500 Risk)
*6* or *news*   - 🌍 Top 10 World & India Market News
*7* or *risk*   - 🛡️ Live Market Volatility Dashboard

🔍 *OR TYPE ANY STOCK NAME:*
Send any company name like *Tata*, *Reliance*, *BEL*, or *ITC* to get instant quantitative buy/sell targets!"""


def get_whatsapp_rules_text() -> str:
    """Returns the 3 Golden Rules formatted for WhatsApp."""
    return """🛡️ *THE 3 GOLDEN SAFETY RULES OF RUPEESTREET*
================================================================
_Protect your capital first, profits will follow naturally!_

1️⃣ *STRICT ₹500 MAX RISK PER TRADE:*
No matter which stock you buy, your maximum loss is strictly capped at ₹500. You never blow up your account.

2️⃣ *OBEY THE CALCULATED QUANTITY:*
The bot calculates the exact mathematical shares:
*Quantity = ₹500 ÷ (Buy Price - Stop Loss)*
Never buy extra shares out of greed.

3️⃣ *NEVER PUT ALL MONEY IN ONE STOCK:*
Always spread your capital across 2 to 4 different stocks to stay completely safe!"""


def process_whatsapp_user_query(incoming_text: str) -> list[str]:
    """Processes incoming text and returns list of messages to send back."""
    query = incoming_text.strip().lower()
    if not query:
        return [get_whatsapp_menu_text()]

    # Numbered & Keyword Shortcuts
    if query in ("hi", "hello", "start", "help", "menu", "0"):
        return [get_whatsapp_menu_text()]

    elif query in ("1", "today", "todaystocks", "stocks", "buy"):
        rep = today_engine.get_today_morning_recommendations()
        return [html_to_whatsapp(rep)]

    elif query in ("2", "rates", "gold", "silver", "fuel", "petrol", "diesel", "usd"):
        data = commodities_engine.fetch_live_rates()
        rep = commodities_engine.format_daily_rates_report(data)
        return [html_to_whatsapp(rep)]

    elif query in ("3", "status", "market", "timing", "open", "close"):
        banner = market_status_engine.get_market_status_banner()
        return [html_to_whatsapp(banner)]

    elif query in ("4", "forecast", "commodity", "oil"):
        parts = commodities_engine.get_commodity_macro_forecast_parts()
        return [html_to_whatsapp(parts[0]), html_to_whatsapp(parts[1])]

    elif query in ("5", "rules", "safety", "rule"):
        return [get_whatsapp_rules_text()]

    elif query in ("6", "news", "macro", "world", "india"):
        data = macro_news_engine.fetch_macro_indicators()
        news = macro_news_engine.fetch_live_news_headlines()
        w_rep = html_to_whatsapp(macro_news_engine.get_world_top_10_intel(data, news))
        i_rep = html_to_whatsapp(macro_news_engine.get_india_top_10_intel(data, news))
        return [w_rep, i_rep]

    elif query in ("7", "risk", "vix"):
        dashboard = macro_news_engine.get_live_risk_dashboard()
        return [html_to_whatsapp(dashboard)]

    # Otherwise: Search as a stock ticker or company name using search_engine
    match_type, matched_entity, payload = search_engine.resolve_input_with_fuzzy(query)
    if match_type == "EXACT":
        analysis = agents_network.InstitutionalNetwork.run_15_agents(matched_entity)
        if analysis.get("success"):
            card = agents_network.format_rapid_intel_card(analysis)
            return [html_to_whatsapp(card)]
        return [f"⚠️ Unable to analyze *{matched_entity}* right now. Please retry in a few seconds."]

    elif match_type in ("GROUP_MATCH", "TYPO_SUGGESTION") and payload:
        lines = [
            f"🏢 *{matched_entity.upper()} EQUITIES FOUND:*",
            "Reply with any stock code below to analyze:\n"
        ]
        for item in payload[:5]:
            lines.append(f"• *{item['symbol']}* ({item['name']})")
        return ["\n".join(lines)]

    else:
        return [
            f"❌ *Stock Not Found:* '{incoming_text.upper()}'\n\n"
            f"💡 *Try typing:*\n"
            f"• Stock code: *BEL*, *TATAPOWER*, *INFY*, *SBIN*, *ITC*\n"
            f"• Group name: *Tata*, *HDFC*, *Jio*, *Adani*\n\n"
            f"Reply *menu* to see all options."
        ]


def send_meta_whatsapp_message(to_phone: str, text: str) -> bool:
    """Dispatches message via official Meta WhatsApp Cloud Graph API."""
    if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
        logger.warning("Meta WhatsApp credentials not configured. Message logged locally.")
        return False

    url = f"https://graph.facebook.com/v21.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_phone,
        "type": "text",
        "text": {
            "preview_url": False,
            "body": text
        }
    }
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {WHATSAPP_TOKEN}",
                "Content-Type": "application/json"
            }
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status in (200, 201)
    except Exception as e:
        logger.error(f"Error dispatching Meta WhatsApp message to {to_phone}: {e}")
        return False


def send_whatsapp_reply(to_phone: str, messages: list[str]) -> bool:
    """Universal dispatcher sending response messages to WhatsApp user."""
    success = True
    for msg in messages:
        # Respect WhatsApp 4096 character limit
        chunks = [msg[i:i+4000] for i in range(0, len(msg), 4000)]
        for chunk in chunks:
            ok = send_meta_whatsapp_message(to_phone, chunk)
            if not ok:
                success = False
    return success


def handle_meta_webhook_event(data: dict):
    """Parses Meta WhatsApp Cloud API incoming JSON payload."""
    try:
        entry = data.get("entry", [])
        if not entry:
            return
        changes = entry[0].get("changes", [])
        if not changes:
            return
        val = changes[0].get("value", {})
        messages = val.get("messages", [])
        if not messages:
            return

        msg_obj = messages[0]
        sender = msg_obj.get("from")
        msg_type = msg_obj.get("type")

        if msg_type == "text":
            user_text = msg_obj.get("text", {}).get("body", "")
        elif msg_type == "interactive":
            interactive = msg_obj.get("interactive", {})
            user_text = (
                interactive.get("button_reply", {}).get("id") or
                interactive.get("list_reply", {}).get("id") or
                interactive.get("button_reply", {}).get("title") or ""
            )
        else:
            user_text = "menu"

        if sender and user_text:
            replies = process_whatsapp_user_query(user_text)
            send_whatsapp_reply(sender, replies)
    except Exception as e:
        logger.error(f"Error processing Meta webhook event: {e}")
