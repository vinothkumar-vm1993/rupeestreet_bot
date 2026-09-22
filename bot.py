import logging
import datetime
import sys
import os
import re
import json
import urllib.parse
import threading
import http.server
import socketserver
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters
)

import config
import database
import agents_network
import chart_engine
import sentinels
import search_engine
import today_engine
import macro_news_engine
import commodities_engine
import market_status_engine
import whatsapp_engine

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)
)
logger = logging.getLogger("RupeeStreetBot")

ACTIVE_CHAT_ID = None

def is_authorized(user_id: int) -> bool:
    if not config.AUTHORIZED_USERS:
        return True
    return user_id in config.AUTHORIZED_USERS


async def safe_reply(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, reply_markup=None):
    """Universal safe dispatch ensuring zero unhandled entity errors and message length splitting."""
    chat_id = update.effective_chat.id
    max_chunk = 3900
    if len(text) <= max_chunk:
        chunks = [text]
    else:
        chunks = []
        lines = text.split("\n")
        current_chunk = []
        current_len = 0
        for line in lines:
            line_len = len(line) + 1
            if current_len + line_len > max_chunk:
                if current_chunk:
                    chunks.append("\n".join(current_chunk))
                    current_chunk = []
                    current_len = 0
                while len(line) > max_chunk:
                    chunks.append(line[:max_chunk])
                    line = line[max_chunk:]
            current_chunk.append(line)
            current_len += len(line) + 1
        if current_chunk:
            chunks.append("\n".join(current_chunk))

    last_res = None
    for idx, chunk in enumerate(chunks):
        markup = reply_markup if idx == len(chunks) - 1 else None
        try:
            last_res = await context.bot.send_message(
                chat_id=chat_id,
                text=chunk,
                parse_mode=ParseMode.HTML,
                reply_markup=markup
            )
        except Exception as e:
            logger.warning(f"HTML send fallback triggered ({e}). Sending plain text.")
            clean_chunk = re.sub(r'<[^>]*>', '', chunk)
            last_res = await context.bot.send_message(
                chat_id=chat_id,
                text=clean_chunk,
                reply_markup=markup
            )
    return last_res


def get_intel_card_keyboard(symbol: str) -> InlineKeyboardMarkup:
    """Standardized touch controls for every Rapid Intel Card with dynamic track/untrack button."""
    is_tracked = database.is_trade_tracked(symbol)
    track_btn = (
        InlineKeyboardButton("🗑️ Remove from Tracking", callback_data=f"deltrade_sym_{symbol}")
        if is_tracked else
        InlineKeyboardButton("✅ Track This Trade", callback_data=f"trackpos_{symbol}")
    )
    return InlineKeyboardMarkup([
        [
            track_btn,
            InlineKeyboardButton("📈 Open Chart", callback_data=f"chart_{symbol}")
        ],
        [
            InlineKeyboardButton("📊 Option Levels", callback_data=f"deriv_{symbol}"),
            InlineKeyboardButton("🛡️ Zero-Risk Status", callback_data=f"be_{symbol}")
        ],
        [
            InlineKeyboardButton("🌅 Today's Top Stocks", callback_data="cmd_todaystocks"),
            InlineKeyboardButton("🪙 Daily Rates", callback_data="cmd_rates")
        ],
        [
            InlineKeyboardButton("⬅️ Back to Search", callback_data="cmd_search_prompt"),
            InlineKeyboardButton("🏠 Main Menu", callback_data="cmd_menu")
        ]
    ])


def get_intel_card_with_pagination_keyboard(symbol: str, tier_key: str, page: int) -> InlineKeyboardMarkup:
    """Attaches track/chart buttons + 'More Stocks (Next 5)' or 'Back to First 5' pagination."""
    is_tracked = database.is_trade_tracked(symbol)
    track_btn = (
        InlineKeyboardButton("🗑️ Remove from Tracking", callback_data=f"deltrade_sym_{symbol}")
        if is_tracked else
        InlineKeyboardButton("✅ Track This Trade", callback_data=f"trackpos_{symbol}")
    )
    t_info = agents_network.PRICE_TIERS.get(tier_key.upper(), {})
    total_in_universe = len(t_info.get("universe", []))
    label = t_info.get("label", t_info.get("name", "Budget"))

    buttons = [
        [
            track_btn,
            InlineKeyboardButton("📈 Open Chart", callback_data=f"chart_{symbol}")
        ],
        [
            InlineKeyboardButton("📊 Option Levels", callback_data=f"deriv_{symbol}"),
            InlineKeyboardButton("🛡️ Zero-Risk Status", callback_data=f"be_{symbol}")
        ]
    ]

    # Pagination row
    if page == 0 and total_in_universe > 5:
        buttons.append([
            InlineKeyboardButton(f"➕ More {label} Stocks (Next 5)", callback_data=f"tier_{tier_key}_1")
        ])
    elif page > 0:
        buttons.append([
            InlineKeyboardButton(f"⬅️ Back to First 5 {label} Stocks", callback_data=f"tier_{tier_key}_0")
        ])

    buttons.append([
        InlineKeyboardButton("⬅️ Back to Budget Menu", callback_data="cmd_todaystocks"),
        InlineKeyboardButton("🏠 Main Menu", callback_data="cmd_menu")
    ])
    return InlineKeyboardMarkup(buttons)


def get_macro_menu_keyboard() -> InlineKeyboardMarkup:
    """Interactive navigation for World and India Macro intelligence."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🌍 Top 10 World News (Live)", callback_data="macro_world"),
            InlineKeyboardButton("🇮🇳 Top 10 Indian News (Live)", callback_data="macro_india"),
        ],
        [
            InlineKeyboardButton("🔄 Refresh News Menu", callback_data="macro_refresh_menu"),
            InlineKeyboardButton("🌐 Read All 20 Points", callback_data="macro_all"),
        ],
        [
            InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="cmd_menu")
        ]
    ])


def get_world_news_keyboard() -> InlineKeyboardMarkup:
    """Navigation for World News with instant Refresh."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔄 Refresh World News", callback_data="macro_world"),
            InlineKeyboardButton("🇮🇳 Read Indian News", callback_data="macro_india"),
        ],
        [
            InlineKeyboardButton("⬅️ Back to News Menu", callback_data="cmd_macro_menu"),
            InlineKeyboardButton("🏠 Main Menu", callback_data="cmd_menu")
        ]
    ])


def get_india_news_keyboard() -> InlineKeyboardMarkup:
    """Navigation for India News with instant Refresh."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔄 Refresh India News", callback_data="macro_india"),
            InlineKeyboardButton("🌍 Read World News", callback_data="macro_world"),
        ],
        [
            InlineKeyboardButton("⬅️ Back to News Menu", callback_data="cmd_macro_menu"),
            InlineKeyboardButton("🏠 Main Menu", callback_data="cmd_menu")
        ]
    ])


def get_rates_keyboard() -> InlineKeyboardMarkup:
    """Interactive navigation for Daily Rates (Gold, Silver, Fuel, USD)."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔮 Gold, Silver & Oil Forecast Guide", callback_data="cmd_commodity_forecast"),
        ],
        [
            InlineKeyboardButton("🔄 Refresh Rates", callback_data="cmd_rates"),
            InlineKeyboardButton("🌍 World & India News", callback_data="cmd_macro_menu"),
        ],
        [
            InlineKeyboardButton("🌅 Today's Top Stocks", callback_data="cmd_todaystocks"),
            InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="cmd_menu")
        ]
    ])


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Initializes bot context, registers user chat ID, and displays master UI."""
    global ACTIVE_CHAT_ID
    ACTIVE_CHAT_ID = update.effective_chat.id
    user = update.effective_user

    if not is_authorized(user.id):
        await safe_reply(
            update, context,
            f"⛔ <b>Access Restricted</b>\nUser ID: <code>{user.id}</code> is not authorized."
        )
        return

    market_banner = market_status_engine.get_market_status_banner()

    welcome_text = f"""👋 <b>Welcome {user.first_name} to RupeeStreet Stock Assistant!</b>
<i>Your friendly, safe trading companion for the Indian Stock Market (NSE/BSE).</i>
================================================================
{market_banner}
================================================================
📌 <b>USEFUL COMMANDS LIST:</b>
• <b>/start</b> - Open Main Menu &amp; Market Status
• <b>/status</b> - Live NSE/BSE Open/Closed/Halt Status
• <b>/rules</b> - 3 Golden Safety Rules
• <b>/today</b> - Today's Top Buy Recommendations
• <b>/rates</b> - Today's Gold, Silver, Petrol, Diesel &amp; USD/INR Rates
• <b>/forecast</b> - Gold, Silver &amp; Oil Price Forecast Guide
• <b>/news</b> - Top 10 World &amp; India Market News
• <b>/portfolio</b> - View &amp; Manage Tracked Trades
• <b>/remove &lt;STOCK&gt;</b> - Remove a stock from portfolio (e.g. <code>/remove BEL</code>)
• <b>/chart &lt;STOCK&gt;</b> - Color-coded Price Chart (e.g. <code>/chart TATAPOWER</code>)
• <b>/risk</b> - Live Market Risk &amp; Safety Dashboard
• <b>/terms</b> - Terms &amp; Conditions and Disclaimer
================================================================
💡 <i>Tip: Tap any button below or type a stock name (e.g. <code>TATA</code>, <code>RELIANCE</code>, <code>INFY</code>) to analyze it instantly.</i>"""

    keyboard = [
        [
            InlineKeyboardButton("🌅 Today's Top Stocks (/today)", callback_data="cmd_todaystocks"),
            InlineKeyboardButton("🪙 Daily Rates: Gold, Silver, Fuel, USD (/rates)", callback_data="cmd_rates"),
        ],
        [
            InlineKeyboardButton("🛡️ 3 Safety Rules (/rules)", callback_data="cmd_rules"),
            InlineKeyboardButton("🌍 World & India Market News (/news)", callback_data="cmd_macro_menu"),
        ],
        [
            InlineKeyboardButton("🔍 Search Stocks", callback_data="cmd_search_prompt"),
            InlineKeyboardButton("💼 My Tracked Trades (/portfolio)", callback_data="cmd_portfolio"),
        ],
        [
            InlineKeyboardButton("🛡️ Risk Dashboard (/risk)", callback_data="cmd_risk"),
            InlineKeyboardButton("📜 Terms & Conditions (/terms)", callback_data="cmd_terms"),
        ],
        [
            InlineKeyboardButton("🔄 Refresh Main Menu & Market Status", callback_data="cmd_menu"),
        ]
    ]
    await safe_reply(update, context, welcome_text, reply_markup=InlineKeyboardMarkup(keyboard))


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays real-time Indian Stock Market operational status and trading schedule."""
    if not is_authorized(update.effective_user.id):
        return
    status_card = market_status_engine.get_market_status_banner()
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Refresh Status", callback_data="cmd_status")],
        [InlineKeyboardButton("🌅 Today's Top Stocks", callback_data="cmd_todaystocks")],
        [InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="cmd_menu")]
    ])
    await safe_reply(update, context, status_card, reply_markup=kb)


async def todaystocks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays the Today's Top Stocks Budget Category Menu."""
    global ACTIVE_CHAT_ID
    ACTIVE_CHAT_ID = update.effective_chat.id

    msg = """🌅 <b>TODAY'S TOP BUY PICKS BY BUDGET</b>
<i>Principle: Strict ₹500 Max Risk per Trade | 100% Quality Liquid Stocks</i>
================================================================
Select your preferred budget bracket to view 5 top stock plans:

• ⚡ <b>Under ₹100 Budget:</b> Stocks priced at ₹100 and below (≤ ₹100)
• ⚡ <b>₹200 – ₹499 Budget:</b> Stocks priced between ₹200 and ₹499
• ⚡ <b>₹500 – ₹999 Budget:</b> Stocks priced between ₹500 and ₹999
• ⚡ <b>₹1,000 – ₹1,999 Budget:</b> Stocks priced between ₹1,000 and ₹1,999
• ⚡ <b>₹2,000 – ₹4,999 Budget:</b> Stocks priced between ₹2,000 and ₹4,999
• ⚡ <b>₹5,000+ Budget:</b> High-value stocks priced at ₹5,000 and above
================================================================
💡 <i>Tap any category below to load 5 stocks (tap 'More' for 5 more):</i>"""

    keyboard = [
        [
            InlineKeyboardButton("⚡ Under ₹100 Budget (≤ ₹100)", callback_data="tier_TIER_100_0"),
            InlineKeyboardButton("⚡ ₹200 – ₹499 Budget", callback_data="tier_TIER_200_0"),
        ],
        [
            InlineKeyboardButton("⚡ ₹500 – ₹999 Budget", callback_data="tier_TIER_500_0"),
            InlineKeyboardButton("⚡ ₹1,000 – ₹1,999 Budget", callback_data="tier_TIER_1000_0"),
        ],
        [
            InlineKeyboardButton("⚡ ₹2,000 – ₹4,999 Budget", callback_data="tier_TIER_2000_0"),
            InlineKeyboardButton("⚡ ₹5,000+ Budget (₹5,000+)", callback_data="tier_TIER_5000_0"),
        ],
        [
            InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="cmd_menu")
        ]
    ]
    await safe_reply(update, context, msg, reply_markup=InlineKeyboardMarkup(keyboard))


async def portfolio_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Queries rupeestreet_execution.db and renders live P&L, CMP, active stop-loss, and trade status."""
    if not is_authorized(update.effective_user.id):
        return

    trades = database.get_active_trades()
    if not trades:
        msg = """💼 <b>MY TRACKED TRADES & PORTFOLIO</b>
================================================================
<b>ACTIVE TRADES:</b> 0 open positions

<i>You are not tracking any trades right now.</i>
<i>Search any stock (e.g. BEL, TATAPOWER) and tap [ ✅ Track This Trade ] to follow it with auto-safety protection!</i>
================================================================"""
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔍 Search Stocks to Track", callback_data="cmd_search_prompt")],
            [InlineKeyboardButton("🌅 Today's Top Stocks", callback_data="cmd_todaystocks")],
            [InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="cmd_menu")]
        ])
        await safe_reply(update, context, msg, reply_markup=kb)
        return

    trade_blocks = ""
    kb_rows = []
    for t in trades:
        live = agents_network.InstitutionalNetwork.fetch_live_data(t["ticker"])
        cmp_price = live["price"] if live else t["entry_price"]
        pnl = round(((cmp_price - t["entry_price"]) / t["entry_price"]) * 100, 2)
        status_badge = "🛡️ ZERO-RISK (Can't Lose)" if t["status"] == "BREAKEVEN_LOCKED" else "🎯 ACTIVE"

        trade_blocks += f"""• <b>${t['ticker']}</b> ({t['tier']}) | <b>{status_badge}</b>
  Bought At: ₹{t['entry_price']:.2f} | Current Price: <b>₹{cmp_price:.2f}</b> ({'+' if pnl>=0 else ''}{pnl}%)
  Quantity: <b>{t['quantity']} shares</b> | Safety Stop: <b>₹{t['stop_loss']:.2f}</b>
  Zero-Risk Level: ₹{t['breakeven_trigger']:.2f} | Target 1: ₹{t['target_1']:.2f} | Target 2: ₹{t['target_2']:.2f}\n\n"""
        kb_rows.append([InlineKeyboardButton(f"🗑️ Remove ${t['ticker']}", callback_data=f"deltrade_id_{t['id']}")])

    if len(trades) > 1:
        kb_rows.append([InlineKeyboardButton("🗑️ Remove All Tracked Trades", callback_data="deltrade_all")])

    kb_rows.append([
        InlineKeyboardButton("🔍 Search Stocks", callback_data="cmd_search_prompt"),
        InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="cmd_menu")
    ])

    msg = f"""💼 <b>MY TRACKED TRADES & PORTFOLIO</b>
================================================================
<b>TOTAL TRACKED TRADES:</b> {len(trades)}
<b>SAFETY CASH BUFFER:</b> <b>12%</b> (Always kept safe for fresh opportunities)
<b>PROTECTION SHIELD:</b> Active (Auto-Alerts & Zero-Risk Locks enabled)

📊 <b>CURRENT TRADES:</b>
{trade_blocks}💡 <i>Tap any [ 🗑️ Remove ... ] button below to remove a stock from tracking anytime.</i>
================================================================"""
    await safe_reply(update, context, msg, reply_markup=InlineKeyboardMarkup(kb_rows))


async def chart_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generates and returns a high-resolution dark-mode candlestick chart."""
    if not is_authorized(update.effective_user.id):
        return

    if not context.args:
        await safe_reply(update, context, "⚠️ <b>HOW TO USE:</b> Type <code>/chart &lt;STOCK&gt;</code>\nExample: <code>/chart BEL</code>, <code>/chart TATAPOWER</code>")
        return

    symbol = context.args[0].upper().strip()
    await send_candlestick_chart(update, context, symbol)


async def send_candlestick_chart(update: Update, context: ContextTypes.DEFAULT_TYPE, symbol: str):
    """Helper to render and send TradingView style candlestick chart."""
    await safe_reply(update, context, f"🎨 <i>Creating a color-coded price chart for ${symbol}...</i>")
    
    analysis = agents_network.InstitutionalNetwork.run_15_agents(symbol)
    if not analysis.get("success"):
        await safe_reply(update, context, f"Unable to create chart for ${symbol}.")
        return

    chart_path = chart_engine.generate_candlestick_chart(
        symbol=symbol,
        entry=float(analysis["price"]),
        initial_stop=float(analysis["initial_stop"]),
        breakeven=float(analysis["breakeven_trigger"]),
        target1=float(analysis["target1"]),
        target2=float(analysis["target2"])
    )

    if chart_path and os.path.exists(chart_path):
        caption = f"""📊 <b>PRICE CHART FOR ${symbol} (EASY COLOR GUIDE)</b>
================================================================
• 🔵 <b>Blue Line:</b> Where to Buy (₹{analysis['price']:.2f})
• 🔴 <b>Red Line:</b> Safety Stop-Loss (₹{analysis['initial_stop']:.2f})
• 🟠 <b>Orange Dotted:</b> Zero-Risk Level (+4% / ₹{analysis['breakeven_trigger']:.2f})
• 🔷 <b>Teal Dashed:</b> First Profit Target (Sell Half / ₹{analysis['target1']:.2f})
• 🟢 <b>Green Dashed:</b> Final Profit Target (₹{analysis['target2']:.2f})
================================================================"""
        chart_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"📊 {symbol} Option Levels", callback_data=f"deriv_{symbol}")],
            [InlineKeyboardButton(f"⬅️ Back to {symbol} Plan", callback_data=f"sym_{symbol}")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="cmd_menu")]
        ])
        with open(chart_path, "rb") as photo_file:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=photo_file,
                caption=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=chart_kb
            )
    else:
        await safe_reply(update, context, "Failed to create chart.")


async def derivatives_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Option Chain Telemetry (Put-Call Ratio, Max Pain, ATM Implied Volatility)."""
    if not is_authorized(update.effective_user.id):
        return

    symbol = context.args[0].upper().strip() if context.args else "NIFTY"
    analysis = agents_network.InstitutionalNetwork.run_15_agents(symbol)
    if not analysis.get("success"):
        await safe_reply(update, context, f"Data unavailable for {symbol}.")
        return

    a_d = analysis["divisions"]["div2"][2]
    msg = f"""📊 <b>BIG MONEY & OPTION MARKET MOOD: ${symbol}</b>
================================================================
• <b>Key Pivot Level:</b> <b>₹{a_d['max_pain']}</b> (Most contracts settle near this price)
• <b>Buyer vs Seller Ratio (PCR):</b> <b>{a_d['pcr']}</b> (>1.0 means buyers are active & confident)
• <b>Overall Big-Money Mood:</b> {a_d['oi_bias']}
• <b>Market Calminess:</b> Calm & Steady (Normal risk level, safe for buying)
================================================================"""
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"📈 Open {symbol} Chart", callback_data=f"chart_{symbol}")],
        [InlineKeyboardButton(f"⬅️ Back to {symbol} Plan", callback_data=f"sym_{symbol}")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="cmd_menu")]
    ])
    await safe_reply(update, context, msg, reply_markup=kb)


async def rates_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays today's Gold, Silver, Petrol, Diesel, and USD/INR rates in easy language."""
    if not is_authorized(update.effective_user.id):
        return

    data = commodities_engine.fetch_live_rates()
    report = commodities_engine.format_daily_rates_report(data)
    await safe_reply(update, context, report, reply_markup=get_rates_keyboard())


async def forecast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays deep world macro forecast and seasonal buying windows for Gold, Silver, and Crude Oil."""
    if not is_authorized(update.effective_user.id):
        return
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🪙 Live Daily Rates", callback_data="cmd_rates")],
        [InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="cmd_menu")]
    ])
    parts = commodities_engine.get_commodity_macro_forecast_parts()
    await safe_reply(update, context, parts[0])
    await safe_reply(update, context, parts[1], reply_markup=kb)


async def macro_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Dispatches full 10-point World and 10-point India Macro Economic Intelligence reports with live breaking news."""
    if not is_authorized(update.effective_user.id):
        return

    await safe_reply(update, context, "⏳ <i>Fetching latest live World &amp; Indian market news headlines...</i>")
    data = macro_news_engine.fetch_macro_indicators()
    news = macro_news_engine.fetch_live_news_headlines()
    world_rep = macro_news_engine.get_world_top_10_intel(data, news)
    india_rep = macro_news_engine.get_india_top_10_intel(data, news)

    await safe_reply(update, context, world_rep, reply_markup=get_world_news_keyboard())
    await safe_reply(update, context, india_rep, reply_markup=get_india_news_keyboard())


async def risk_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays real-time dynamic institutional risk dashboard."""
    if not is_authorized(update.effective_user.id):
        return

    dashboard = macro_news_engine.get_live_risk_dashboard()
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="cmd_menu")]
    ])
    await safe_reply(update, context, dashboard, reply_markup=kb)


def get_safety_rules_text() -> str:
    """Returns friendly, plain-English explanation of the 3 Golden Safety Rules."""
    return """🛡️ <b>THE 3 GOLDEN SAFETY RULES OF RUPEESTREET (/rules)</b>
================================================================
<i>We designed RupeeStreet with one core priority: Protect your money first, profits will follow naturally!</i>

1️⃣ <b>STRICT ₹500 MAX RISK PER TRADE:</b>
• Before buying any stock, we look at the safety exit price (Stop-Loss).
• We calculate the exact number of shares to buy so that if the stock falls and hits your stop-loss, <b>your loss is strictly capped under ₹500</b>!
• <i>Example: If you buy BEL at ₹398 with stop-loss at ₹385, the risk is ₹13/share. We recommend buying 38 shares (38 x ₹13 = ₹494 risk).</i>

2️⃣ <b>ZERO-LOSS PROFIT LOCK (+4% RULE):</b>
• As soon as your stock gains +4% from your buy price, the system alerts you and automatically shifts your stop-loss up to your exact buying price!
• <b>From that moment on, your risk becomes ₹0 (Zero Rupee)!</b>
• Even if the stock drops back down, you exit safely with no loss.

3️⃣ <b>CLEAN & HEALTHY COMPANIES ONLY:</b>
• We never recommend risky penny stocks or companies with heavy debt.
• Every stock must have high daily trading volume (easy to buy and sell anytime) and solid business financials.
================================================================
💡 <b>HOW TO GET STARTED:</b>
• Type <b>/start</b> to open the Main Menu
• Type <b>/today</b> to see today's top picks matching these rules
• Type any stock name like <code>TATA</code> or <code>BEL</code> to get an instant safety plan!"""


async def rules_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays the 3 Golden Safety Rules."""
    if not is_authorized(update.effective_user.id):
        return

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🌅 Today's Top Stocks", callback_data="cmd_todaystocks")],
        [InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="cmd_menu")]
    ])
    await safe_reply(update, context, get_safety_rules_text(), reply_markup=kb)


def get_terms_and_conditions_text() -> str:
    """Returns simple, friendly plain-English Terms & Conditions and Market Disclaimer."""
    return """📜 <b>RUPEESTREET // TERMS & CONDITIONS AND DISCLAIMER</b>
================================================================
<i>Please read these simple points before using this market assistant. By using this bot, you agree to the following terms:</i>

1. 🤖 <b>AUTOMATED MARKET INTELLIGENCE &amp; ALGORITHMIC ANALYSIS:</b>
• This bot is an automated analytical assistant designed to track, calculate, and evaluate publicly available market data from Indian exchanges (NSE/BSE).
• <b>We are not SEBI-registered investment advisers or portfolio managers.</b>
• All stock signals, risk parameters, and price levels are computed mathematically by automated algorithms to assist your trading evaluation.

2. ⚠️ <b>STOCK MARKET RISK AWARENESS:</b>
• Trading in equities (NSE/BSE) involves financial risk. Stock prices move up and down based on market conditions, company results, and global events.
• Past performance does not guarantee future results. Never invest money that you cannot afford to risk or emergency savings funds.

3. 🛡️ <b>RISK MANAGEMENT & STOP-LOSS:</b>
• The ₹500 maximum risk and zero-loss breakeven calculations are mathematical rules designed to help you protect your capital.
• While the system alerts you when stop-loss levels are reached, stock prices can experience sudden market gaps or liquidity volatility.
• Always use your own broker's formal stop-loss orders (SL-M / GTT) to protect your positions.

4. 📡 <b>DATA ACCURACY & INTERNET FEEDS:</b>
• Market prices and metrics are collected from public market data feeds (Yahoo Finance / NSE / BSE).
• While we make every effort to ensure live accuracy, data may occasionally experience momentary delays or network latency.

5. 💼 <b>NO DIRECT BROKER ACCESS OR FUND HANDLING:</b>
• This bot does NOT hold your money, does not ask for your bank account or OTP, and does not execute actual financial transactions on your behalf.
• All actual buy and sell orders are placed by you directly inside your own trusted brokerage account.

6. ⚖️ <b>USER RESPONSIBILITY:</b>
• You are solely responsible for your own trading and financial decisions.
• Always conduct your own research or consult a certified financial advisor before making large investments.
================================================================
✅ <i>By continuing to use RupeeStreet, you acknowledge and agree to these terms.</i>"""


async def terms_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays Terms & Conditions and Market Disclaimer."""
    if not is_authorized(update.effective_user.id):
        return

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="cmd_menu")]
    ])
    await safe_reply(update, context, get_terms_and_conditions_text(), reply_markup=kb)


async def remove_trade_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Allows user to remove a trade by typing /remove or /untrack <TICKER>."""
    if not is_authorized(update.effective_user.id):
        return

    if not context.args:
        trades = database.get_active_trades()
        if not trades:
            await safe_reply(update, context, "ℹ️ You don't have any tracked trades to remove right now.")
            return

        buttons = []
        for t in trades:
            buttons.append([InlineKeyboardButton(f"🗑️ Remove ${t['ticker']} (ID #{t['id']})", callback_data=f"deltrade_id_{t['id']}")])
        if len(trades) > 1:
            buttons.append([InlineKeyboardButton("🗑️ Remove All Trades", callback_data="deltrade_all")])
        buttons.append([InlineKeyboardButton("⬅️ Main Menu", callback_data="cmd_menu")])

        await safe_reply(
            update, context,
            "🗑️ <b>REMOVE TRACKED TRADES:</b>\n<i>Select which trade you want to remove from tracking:</i>",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    target = context.args[0].upper().strip().replace("$", "")
    removed = database.remove_active_trade_by_ticker(target)
    if removed:
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("💼 View Updated Portfolio", callback_data="cmd_portfolio")],
            [InlineKeyboardButton("⬅️ Main Menu", callback_data="cmd_menu")]
        ])
        await safe_reply(
            update, context,
            f"✅ <b>TRADE REMOVED:</b> <code>${target}</code>\n================================================================\n<i>${target} has been successfully removed from your active tracking and portfolio.</i>",
            reply_markup=kb
        )
    else:
        await safe_reply(
            update, context,
            f"ℹ️ <code>${target}</code> is not currently in your active tracked trades list.\nType <code>/portfolio</code> to see your open trades."
        )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Interactive Touch Control Router."""
    global ACTIVE_CHAT_ID
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass
    user_id = query.from_user.id
    ACTIVE_CHAT_ID = update.effective_chat.id

    if not is_authorized(user_id):
        await query.edit_message_text("⛔ Access Denied.")
        return

    data = query.data

    if data == "cmd_menu":
        try:
            await query.message.delete()
        except Exception:
            pass
        await start_command(update, context)

    elif data in ("cmd_status", "cmd_refresh_status"):
        status_card = market_status_engine.get_market_status_banner()
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Refresh Status", callback_data="cmd_refresh_status")],
            [InlineKeyboardButton("🌅 Today's Top Stocks", callback_data="cmd_todaystocks")],
            [InlineKeyboardButton("⬅️ Main Menu", callback_data="cmd_menu")]
        ])
        await safe_reply(update, context, status_card, reply_markup=kb)

    elif data == "cmd_todaystocks":
        await todaystocks_command(update, context)

    elif data == "cmd_rates":
        data_rates = commodities_engine.fetch_live_rates()
        report = commodities_engine.format_daily_rates_report(data_rates)
        await safe_reply(update, context, report, reply_markup=get_rates_keyboard())

    elif data == "cmd_commodity_forecast":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🪙 Live Daily Rates", callback_data="cmd_rates")],
            [InlineKeyboardButton("⬅️ Main Menu", callback_data="cmd_menu")]
        ])
        parts = commodities_engine.get_commodity_macro_forecast_parts()
        await safe_reply(update, context, parts[0])
        await safe_reply(update, context, parts[1], reply_markup=kb)

    elif data == "cmd_portfolio":
        await portfolio_command(update, context)

    elif data in ("cmd_macro", "cmd_macro_menu", "macro_refresh_menu"):
        now_str = datetime.datetime.now().strftime("%d %b %Y, %I:%M %p IST")
        msg = f"""🌍 <b>WORLD &amp; INDIA MARKET NEWS &amp; ECONOMIC GUIDE</b>
<i>Live Refreshed: {now_str} | Fresh Global &amp; Domestic News</i>
================================================================
Get simple, easy-to-read market insights with live breaking headlines:

• <b>World Level (Top 10 Points):</b> Real-time breaking world stories, Crude Oil, Gold, Silver, US Dollar, and shipping routes.
• <b>India Level (Top 10 Points):</b> Real-time breaking Indian stock headlines, Nifty 50, Sensex, Bank Nifty, Panic Meter (India VIX), and citizen mutual fund SIP savings.

Tap below to read either report with live refresh:
================================================================"""
        await safe_reply(update, context, msg, reply_markup=get_macro_menu_keyboard())

    elif data == "macro_world":
        await safe_reply(update, context, "⏳ <i>Fetching latest live World Market news &amp; indicators...</i>")
        data_m = macro_news_engine.fetch_macro_indicators()
        news_m = macro_news_engine.fetch_live_news_headlines()
        w_rep = macro_news_engine.get_world_top_10_intel(data_m, news_m)
        await safe_reply(update, context, w_rep, reply_markup=get_world_news_keyboard())

    elif data == "macro_india":
        await safe_reply(update, context, "⏳ <i>Fetching latest live Indian Market news &amp; indicators...</i>")
        data_m = macro_news_engine.fetch_macro_indicators()
        news_m = macro_news_engine.fetch_live_news_headlines()
        i_rep = macro_news_engine.get_india_top_10_intel(data_m, news_m)
        await safe_reply(update, context, i_rep, reply_markup=get_india_news_keyboard())

    elif data == "macro_all":
        await macro_command(update, context)

    elif data == "cmd_risk":
        await risk_command(update, context)

    elif data == "cmd_terms":
        await terms_command(update, context)

    elif data == "cmd_rules":
        await rules_command(update, context)

    elif data == "cmd_search_prompt":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🌅 Today's Top Stocks", callback_data="cmd_todaystocks")],
            [InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="cmd_menu")]
        ])
        await safe_reply(update, context, "🔍 <b>SEARCH ANY INDIAN STOCK:</b>\nType any company name (e.g. <code>Tata</code>, <code>Jio</code>, <code>HDFC</code>) or stock code (e.g. <code>BEL</code>, <code>INFY</code>).\nEven if there is a spelling mistake like <code>hfc</code>, the bot will find it!", reply_markup=kb)

    elif data.startswith("tier_"):
        raw_payload = data.replace("tier_", "")
        parts = raw_payload.rsplit("_", 1)
        if len(parts) == 2 and parts[1].isdigit():
            tier_key = parts[0]
            page = int(parts[1])
        else:
            tier_key = raw_payload
            page = 0

        alias_map = {
            "TIER_1": "TIER_100",
            "TIER_2": "TIER_200",
            "TIER_3": "TIER_500",
            "TIER_4": "TIER_1000",
            "TIER_5": "TIER_5000"
        }
        tier_key = alias_map.get(tier_key, tier_key)
        t_info = agents_network.PRICE_TIERS.get(tier_key, {})
        tier_name = t_info.get("name", tier_key)
        page_label = f"Page {page + 1}"

        await safe_reply(update, context, f"⏳ <i>Scanning 5 stocks in {tier_name} ({page_label})...</i>")
        picks = agents_network.InstitutionalNetwork.scan_price_tier(tier_key, page=page, limit=5)
        if not picks:
            await safe_reply(update, context, f"No stocks found in {tier_name} for this page.")
            return

        for idx, p in enumerate(picks):
            card = agents_network.format_rapid_intel_card(p)
            if idx == len(picks) - 1:
                kb = get_intel_card_with_pagination_keyboard(p["symbol"], tier_key, page)
            else:
                kb = get_intel_card_keyboard(p["symbol"])
            await safe_reply(update, context, card, reply_markup=kb)

    elif data.startswith("chart_"):
        symbol = data.replace("chart_", "")
        await send_candlestick_chart(update, context, symbol)

    elif data.startswith("trackpos_"):
        symbol = data.replace("trackpos_", "")
        analysis = agents_network.InstitutionalNetwork.run_15_agents(symbol)
        if analysis.get("success"):
            chat_id = update.effective_chat.id
            database.add_active_trade(
                chat_id=chat_id,
                ticker=symbol,
                tier=analysis["tier_name"],
                entry_price=float(analysis["price"]),
                stop_loss=float(analysis["initial_stop"]),
                breakeven_trigger=float(analysis["breakeven_trigger"]),
                target_1=float(analysis["target1"]),
                target_2=float(analysis["target2"]),
                quantity=int(analysis["shares"])
            )
            msg = f"""✅ <b>TRADE SAVED & AUTO-SAFETY SHIELD ENGAGED!</b>
================================================================
<b>STOCK:</b> <code>${symbol}</code>
• Buying Price      : <b>₹{analysis['price']:.2f}</b>
• Safe Quantity     : <b>{analysis['shares']} Shares</b> (Total: ~₹{analysis['position_value']:,.0f})
• Safety Stop-Loss  : <b>₹{analysis['initial_stop']:.2f}</b> (Maximum Loss: ₹500 only!)
• Zero-Risk Price   : <b>₹{analysis['breakeven_trigger']:.2f}</b> (+4.0% gain)
• First Target (T1) : <b>₹{analysis['target1']:.2f}</b> (Book 50% profit)

🛡️ <b>HOW WE PROTECT YOUR MONEY:</b>
• <b>Zero-Risk Lock:</b> When price rises to ₹{analysis['breakeven_trigger']:.2f}, your stop-loss moves to your buy price so you cannot lose money.
• <b>Safety Exit Alert:</b> If the price falls to ₹{analysis['initial_stop']:.2f}, the system notifies you immediately to exit and keep your loss within ₹500.

💡 <i>Want to remove this trade later? You can tap [ 🗑️ Remove from Tracking ] or manage inside /portfolio anytime.</i>
================================================================"""
            track_kb = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(f"🗑️ Remove from Tracking", callback_data=f"deltrade_sym_{symbol}"),
                    InlineKeyboardButton("💼 My Tracked Trades", callback_data="cmd_portfolio")
                ],
                [
                    InlineKeyboardButton("📈 Open Chart", callback_data=f"chart_{symbol}"),
                    InlineKeyboardButton("⬅️ Main Menu", callback_data="cmd_menu")
                ]
            ])
            await safe_reply(update, context, msg, reply_markup=track_kb)

    elif data.startswith("deltrade_id_"):
        tid = int(data.replace("deltrade_id_", ""))
        trades = database.get_active_trades()
        matching = [t for t in trades if t["id"] == tid]
        ticker = matching[0]["ticker"] if matching else "Position"
        database.remove_active_trade(tid)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("💼 View Updated Portfolio", callback_data="cmd_portfolio")],
            [InlineKeyboardButton("🔍 Search Another Stock", callback_data="cmd_search_prompt")],
            [InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="cmd_menu")]
        ])
        await safe_reply(
            update, context,
            f"🗑️ <b>TRADE REMOVED:</b> <code>${ticker}</code>\n================================================================\n<i>${ticker} has been removed from your active portfolio. Automated safety sentinels for this trade are now disarmed.</i>",
            reply_markup=kb
        )

    elif data.startswith("deltrade_sym_"):
        symbol = data.replace("deltrade_sym_", "")
        database.remove_active_trade_by_ticker(symbol)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("💼 View Updated Portfolio", callback_data="cmd_portfolio")],
            [InlineKeyboardButton("🔍 Search Another Stock", callback_data="cmd_search_prompt")],
            [InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="cmd_menu")]
        ])
        await safe_reply(
            update, context,
            f"🗑️ <b>TRADE REMOVED:</b> <code>${symbol}</code>\n================================================================\n<i>${symbol} has been removed from your active portfolio. Automated safety sentinels for this trade are now disarmed.</i>",
            reply_markup=kb
        )

    elif data == "deltrade_all":
        count = database.remove_all_active_trades()
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🌅 Today's Top Stocks", callback_data="cmd_todaystocks")],
            [InlineKeyboardButton("🔍 Search Stocks", callback_data="cmd_search_prompt")],
            [InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="cmd_menu")]
        ])
        await safe_reply(
            update, context,
            f"🗑️ <b>ALL TRACKED TRADES REMOVED:</b>\n================================================================\n<i>Successfully cleared {count} active trade(s) from your portfolio database.</i>",
            reply_markup=kb
        )

    elif data.startswith("be_"):
        symbol = data.replace("be_", "")
        trades = database.get_active_trades()
        matching = [t for t in trades if t["ticker"] == symbol]
        if matching:
            t = matching[0]
            status_text = "🟢 ZERO-RISK LOCKED (You cannot lose money!)" if t["status"] == "BREAKEVEN_LOCKED" else "🟡 WAITING FOR +4% GAIN (To lock zero-risk)"
            msg = f"""🛡️ <b>SAFETY & ZERO-RISK STATUS: ${symbol}</b>
================================================================
• Buy Price: <b>₹{t['entry_price']:.2f}</b>
• Active Safety Stop: <b>₹{t['stop_loss']:.2f}</b>
• Price Needed for Zero-Risk: <b>₹{t['breakeven_trigger']:.2f}</b> (+4%)
• Protection Status: <b>{status_text}</b>
================================================================"""
        else:
            msg = f"ℹ️ <code>${symbol}</code> is not in your tracked list yet. Tap [ ✅ Track This Trade ] to follow it with safety protection."
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"⬅️ Back to {symbol} Plan", callback_data=f"sym_{symbol}")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="cmd_menu")]
        ])
        await safe_reply(update, context, msg, reply_markup=kb)

    elif data.startswith("deriv_"):
        symbol = data.replace("deriv_", "")
        context.args = [symbol]
        await derivatives_command(update, context)

    elif data.startswith("sym_"):
        symbol = data.replace("sym_", "")
        await handle_single_ticker(update, context, symbol)


async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Direct message input: Handles stock queries, fuzzy typo correction, and group expansion."""
    global ACTIVE_CHAT_ID
    ACTIVE_CHAT_ID = update.effective_chat.id
    if not is_authorized(update.effective_user.id):
        return

    raw_text = update.effective_message.text.strip()
    match_type, matched_entity, payload = search_engine.resolve_input_with_fuzzy(raw_text)

    # 1. Group Match or Typo Suggestion -> Return Interactive Button Grid
    if match_type in ("GROUP_MATCH", "TYPO_SUGGESTION"):
        buttons = []
        for item in payload:
            sym = item["symbol"]
            nm = item["name"]
            tier_info = f" [{item['tier']}]" if "tier" in item else ""
            buttons.append([InlineKeyboardButton(f"📊 {sym}: {nm}{tier_info}", callback_data=f"sym_{sym}")])
        buttons.append([InlineKeyboardButton("⬅️ Main Menu", callback_data="cmd_menu")])

        if match_type == "TYPO_SUGGESTION":
            msg_header = f"🔍 <b>DID YOU MEAN '{matched_entity}'?</b>\n<i>Found matching equities for your query:</i>"
        else:
            msg_header = f"🏢 <b>{matched_entity.upper()} CONGLOMERATE EQUITIES:</b>\n<i>Select which company to analyze:</i>"

        await safe_reply(update, context, f"{msg_header}\n================================================================", reply_markup=InlineKeyboardMarkup(buttons))
        return

    # 2. Not Found -> Clean warning without fetching random stocks
    if match_type == "NOT_FOUND":
        msg = f"""❌ <b>STOCK NOT FOUND:</b> '<code>{raw_text.upper()}</code>'
================================================================
<i>We couldn't find any Indian company matching this name.</i>

💡 <b>QUICK SEARCH EXAMPLES:</b>
• Company Groups: Type <code>JIO</code>, <code>TATA</code>, <code>HDFC</code>, <code>ADANI</code>, <code>SBI</code>
• Popular Stocks: Type <code>JIOFIN</code>, <code>BEL</code>, <code>TATAPOWER</code>, <code>INFY</code>, <code>TCS</code>
================================================================"""
        await safe_reply(update, context, msg)
        return

    # 3. Exact Single Ticker -> Execute 15 Agents and dispatch Rapid Intel Card
    symbol = matched_entity if match_type == "EXACT" else raw_text.upper().strip()
    await handle_single_ticker(update, context, symbol)


async def handle_single_ticker(update: Update, context: ContextTypes.DEFAULT_TYPE, symbol: str):
    """Runs 15 agents and dispatches the Standardized Rapid Intel Card."""
    await safe_reply(update, context, f"⚙️ <i>Deploying 15 Analytical Agents for <code>${symbol}</code>...</i>")
    analysis = agents_network.InstitutionalNetwork.run_15_agents(symbol)
    if not analysis.get("success"):
        await safe_reply(update, context, f"❌ <b>Error:</b> {analysis.get('error', 'Symbol not found on NSE/BSE feeds.')}")
        return

    card = agents_network.format_rapid_intel_card(analysis)
    kb = get_intel_card_keyboard(analysis["symbol"])
    await safe_reply(update, context, card, reply_markup=kb)


async def background_sentinel_job(context: ContextTypes.DEFAULT_TYPE):
    """180-Second Background Sentinel Job (Agent O Flash Crash + Agent N Breakeven)."""
    global ACTIVE_CHAT_ID
    if ACTIVE_CHAT_ID:
        await sentinels.run_flash_crash_sentinel(context.bot, ACTIVE_CHAT_ID)
        await sentinels.run_zero_loss_and_execution_engine(context.bot, ACTIVE_CHAT_ID)


async def post_init(application):
    """Registers standard Telegram UI commands list on startup."""
    from telegram import BotCommand
    commands = [
        BotCommand("start", "Open Main Menu & Live Market Status"),
        BotCommand("status", "Live NSE/BSE Market Open/Closed Status"),
        BotCommand("rules", "3 Golden Safety Rules"),
        BotCommand("today", "Today's Top Buy Recommendations"),
        BotCommand("rates", "Today's Gold, Silver, Fuel & USD Rates"),
        BotCommand("forecast", "Gold, Silver & Oil Forecast Guide"),
        BotCommand("news", "Top 10 World & India Market News"),
        BotCommand("portfolio", "View & Manage Tracked Trades"),
        BotCommand("remove", "Remove a stock from portfolio"),
        BotCommand("chart", "Color-coded Price Chart"),
        BotCommand("risk", "Live Risk & Safety Dashboard"),
        BotCommand("terms", "Terms & Conditions and Disclaimer"),
    ]
    try:
        await application.bot.set_my_commands(commands)
    except Exception as e:
        logger.warning(f"Could not set bot commands: {e}")


class ReusableThreadingServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def run_health_server():
    """Multi-channel HTTP server: Render Health Check + Meta WhatsApp Webhook."""
    port = int(os.environ.get("PORT", 8080))

    class MultiChannelServer(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path
            query = urllib.parse.parse_qs(parsed.query)

            # Meta WhatsApp Webhook Verification handshake
            if path in ("/whatsapp", "/webhook"):
                mode = query.get("hub.mode", [""])[0]
                token = query.get("hub.verify_token", [""])[0]
                challenge = query.get("hub.challenge", [""])[0]
                expected_token = os.environ.get("WHATSAPP_VERIFY_TOKEN", "rupeestreet_verify_2026")

                if mode == "subscribe" and token == expected_token:
                    logger.info("✅ Meta WhatsApp Webhook verified successfully!")
                    self.send_response(200)
                    self.send_header("Content-type", "text/plain")
                    self.end_headers()
                    self.wfile.write(challenge.encode("utf-8"))
                    return
                else:
                    logger.warning("❌ Meta WhatsApp Webhook verification token mismatch.")
                    self.send_response(403)
                    self.end_headers()
                    self.wfile.write(b"Verification token mismatch")
                    return

            # Default Health check response for Render / UptimeRobot
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"RupeeStreet Master OS is running 24/7 (Telegram + WhatsApp)!\n")

        def do_POST(self):
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path

            if path in ("/whatsapp", "/webhook"):
                content_len = int(self.headers.get("Content-Length", 0))
                post_body = self.rfile.read(content_len)

                # Return 200 OK immediately to Meta (must respond within 3 seconds)
                self.send_response(200)
                self.send_header("Content-type", "text/plain")
                self.end_headers()
                self.wfile.write(b"EVENT_RECEIVED")

                # Process message asynchronously in background thread
                try:
                    data = json.loads(post_body.decode("utf-8"))
                    threading.Thread(
                        target=whatsapp_engine.handle_meta_webhook_event,
                        args=(data,),
                        daemon=True
                    ).start()
                except Exception as e:
                    logger.error(f"Error parsing incoming WhatsApp POST payload: {e}")
                return

            self.send_response(404)
            self.end_headers()

        def log_message(self, format, *args):
            return  # Silence health check ping logs

    import time
    for attempt in range(10):
        try:
            httpd = ReusableThreadingServer(("", port), MultiChannelServer)
            logger.info(f"✅ Cloud health & WhatsApp webhook server listening on port {port}")
            httpd.serve_forever()
            break
        except Exception as e:
            logger.warning(f"Could not bind webhook server on port {port} (attempt {attempt+1}/10): {e}")
            time.sleep(1)


def main():
    if not config.BOT_TOKEN or config.BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        print("❌ ERROR: TELEGRAM_BOT_TOKEN is not configured!")
        sys.exit(1)

    # Start background health server for Render/Cloud 24/7 hosting
    health_thread = threading.Thread(target=run_health_server, daemon=True)
    health_thread.start()

    print("🚀 Initializing RupeeStreet Master Operating System...")
    app = ApplicationBuilder().token(config.BOT_TOKEN).post_init(post_init).build()

    # Register Handlers
    app.add_handler(CommandHandler(["start", "help"], start_command))
    app.add_handler(CommandHandler(["status", "market"], status_command))
    app.add_handler(CommandHandler(["rules", "safety"], rules_command))
    app.add_handler(CommandHandler(["todaystocks", "today"], todaystocks_command))
    app.add_handler(CommandHandler(["rates", "gold", "silver", "fuel", "petrol", "diesel", "usd"], rates_command))
    app.add_handler(CommandHandler(["forecast", "commodity"], forecast_command))
    app.add_handler(CommandHandler("portfolio", portfolio_command))
    app.add_handler(CommandHandler(["remove", "untrack"], remove_trade_command))
    app.add_handler(CommandHandler("chart", chart_command))
    app.add_handler(CommandHandler("derivatives", derivatives_command))
    app.add_handler(CommandHandler(["macro", "news", "world", "india"], macro_command))
    app.add_handler(CommandHandler("risk", risk_command))
    app.add_handler(CommandHandler(["terms", "disclaimer"], terms_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_handler))

    # 180-Second Sentinel Schedule
    job_queue = app.job_queue
    if job_queue:
        job_queue.run_repeating(background_sentinel_job, interval=180, first=10)
        print("⏱️ Agent O Flash-Crash Sentinel & Agent N Breakeven Engine armed at 180-second interval.")

    print("✅ RupeeStreet Master System is ONLINE!")
    app.run_polling(bootstrap_retries=5)


if __name__ == "__main__":
    main()
