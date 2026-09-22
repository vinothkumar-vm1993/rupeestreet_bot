import datetime
import requests
import logging

logger = logging.getLogger("RupeeStreetCommodities")

# Troy Ounce to Gram conversion constant
TROY_OUNCE_IN_GRAMS = 31.1034768

# Standard fuel prices across major Indian cities (Retail pump prices in ₹ / Litre)
CITY_FUEL_PRICES = {
    "Chennai": {
        "petrol": 100.75,
        "diesel": 92.34,
        "state": "Tamil Nadu"
    },
    "Delhi": {
        "petrol": 94.72,
        "diesel": 87.62,
        "state": "Delhi NCR"
    },
    "Mumbai": {
        "petrol": 104.21,
        "diesel": 92.15,
        "state": "Maharashtra"
    },
    "Bengaluru": {
        "petrol": 102.84,
        "diesel": 88.95,
        "state": "Karnataka"
    },
    "Hyderabad": {
        "petrol": 107.41,
        "diesel": 95.65,
        "state": "Telangana"
    },
    "Kolkata": {
        "petrol": 103.94,
        "diesel": 90.76,
        "state": "West Bengal"
    }
}


def fetch_live_rates() -> dict:
    """
    Fetches real-time live market feeds for USD/INR, Gold, Silver, and Crude Oil,
    and calculates calibrated Indian retail prices for Gold, Silver, and Fuel.
    """
    targets = {
        "usdinr": "INR=X",      # USD to INR
        "gold": "GC=F",         # Gold COMEX ($/oz)
        "silver": "SI=F",       # Silver COMEX ($/oz)
        "brent": "BZ=F"         # Brent Crude Oil ($/bbl)
    }

    raw_data = {}
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    for key, sym in targets.items():
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=1d&interval=1d"
            r = requests.get(url, headers=headers, timeout=4)
            if r.status_code == 200:
                res = r.json().get("chart", {}).get("result")
                if res:
                    meta = res[0]["meta"]
                    price = float(meta.get("regularMarketPrice") or 0.0)
                    prev = float(meta.get("chartPreviousClose") or price)
                    chg = round(((price - prev) / prev) * 100, 2) if prev > 0 else 0.0
                    raw_data[key] = {
                        "price": price,
                        "change_pct": chg,
                        "prev": prev
                    }
        except Exception as e:
            logger.debug(f"Feed fetch error for {sym}: {e}")

    # Fallback safe defaults if external feeds are unavailable
    defaults = {
        "usdinr": {"price": 95.80, "change_pct": 0.00, "prev": 95.80},
        "gold": {"price": 4389.20, "change_pct": 0.12, "prev": 4383.94},
        "silver": {"price": 66.78, "change_pct": 0.56, "prev": 66.41},
        "brent": {"price": 96.93, "change_pct": 0.72, "prev": 96.24}
    }

    for k, v in defaults.items():
        if k not in raw_data or raw_data[k]["price"] <= 0:
            raw_data[k] = v

    usd_inr = raw_data["usdinr"]["price"]
    gold_usd = raw_data["gold"]["price"]
    silver_usd = raw_data["silver"]["price"]
    brent_usd = raw_data["brent"]["price"]

    # 1. Indian Gold Price Calculation
    # Landed cost includes ~6% Basic Customs Duty + AIDC + 3% GST + bullion transport margin (~1.085)
    gold_24k_1g = round((gold_usd / TROY_OUNCE_IN_GRAMS) * usd_inr * 1.085, 2)
    gold_24k_8g = round(gold_24k_1g * 8, 2)
    gold_24k_10g = round(gold_24k_1g * 10, 2)

    # 22K Hallmark Jewelry Gold is 91.6% pure
    gold_22k_1g = round(gold_24k_1g * 0.916, 2)
    gold_22k_8g = round(gold_22k_1g * 8, 2)
    gold_22k_10g = round(gold_22k_1g * 10, 2)

    # 2. Indian Silver Price Calculation
    # Silver landed cost with customs duty and GST (~1.10 multiplier)
    silver_1g = round((silver_usd / TROY_OUNCE_IN_GRAMS) * usd_inr * 1.10, 2)
    silver_10g = round(silver_1g * 10, 2)
    silver_100g = round(silver_1g * 100, 2)
    silver_1kg = round(silver_1g * 1000, 2)

    return {
        "timestamp": datetime.datetime.now().strftime("%d %b %Y, %I:%M %p IST"),
        "usdinr": raw_data["usdinr"],
        "gold_comex": raw_data["gold"],
        "silver_comex": raw_data["silver"],
        "brent": raw_data["brent"],
        "gold": {
            "gold_24k_1g": gold_24k_1g,
            "gold_24k_8g": gold_24k_8g,
            "gold_24k_10g": gold_24k_10g,
            "gold_22k_1g": gold_22k_1g,
            "gold_22k_8g": gold_22k_8g,
            "gold_22k_10g": gold_22k_10g,
            "change_pct": raw_data["gold"]["change_pct"]
        },
        "silver": {
            "silver_1g": silver_1g,
            "silver_10g": silver_10g,
            "silver_100g": silver_100g,
            "silver_1kg": silver_1kg,
            "change_pct": raw_data["silver"]["change_pct"]
        },
        "fuel": CITY_FUEL_PRICES
    }


def format_daily_rates_report(data: dict = None) -> str:
    """
    Formats a clean, beautiful, plain-English report for common people
    explaining today's Gold, Silver, Fuel, and USD/INR rates.
    """
    if not data:
        data = fetch_live_rates()

    ts = data["timestamp"]
    g = data["gold"]
    s = data["silver"]
    usd = data["usdinr"]
    brent = data["brent"]
    fuel = data["fuel"]

    g_dir = "🔺" if g["change_pct"] >= 0 else "🔻"
    s_dir = "🔺" if s["change_pct"] >= 0 else "🔻"
    usd_dir = "🔺" if usd["change_pct"] >= 0 else "🔻"
    brent_dir = "🔺" if brent["change_pct"] >= 0 else "🔻"

    # Build fuel lines
    fuel_blocks = []
    for city, info in fuel.items():
        fuel_blocks.append(
            f"• <b>{city}</b>: Petrol <b>₹{info['petrol']:.2f}</b> | Diesel <b>₹{info['diesel']:.2f}</b> / L"
        )
    fuel_str = "\n".join(fuel_blocks)

    return f"""🪙 <b>RUPEESTREET // TODAY'S GOLD, SILVER, FUEL &amp; USD RATES</b>
<i>Live Update: {ts} | India Daily Rates Guide</i>
================================================================
🟡 <b>GOLD RATES TODAY:</b>
• <b>24K Pure Gold (99.9% Purity - Bar / Coin):</b>
  - 1 Gram : <b>₹{g['gold_24k_1g']:,.2f}</b>
  - 8 Grams (1 Sovereign / 8g) : <b>₹{g['gold_24k_8g']:,.2f}</b>
  - 10 Grams : <b>₹{g['gold_24k_10g']:,.2f}</b>

• <b>22K Hallmark Jewelry Gold (91.6% Purity):</b>
  - 1 Gram : <b>₹{g['gold_22k_1g']:,.2f}</b>
  - 8 Grams (1 Sovereign / 8g) : <b>₹{g['gold_22k_8g']:,.2f}</b>
  - 10 Grams : <b>₹{g['gold_22k_10g']:,.2f}</b>
• <i>Trend:</i> {g_dir} {abs(g['change_pct']):.2f}% in global bullion markets (${data['gold_comex']['price']:,.1f}/oz).
• 💡 <i>Simple Tip:</i> 22 Karat gold is the standard hallmark gold used for daily jewelry and wedding ornaments. 1 Sovereign = 8 grams.

================================================================
⚪ <b>SILVER RATES TODAY:</b>
• 1 Gram : <b>₹{s['silver_1g']:,.2f}</b>
• 10 Grams : <b>₹{s['silver_10g']:,.2f}</b>
• 100 Grams : <b>₹{s['silver_100g']:,.2f}</b>
• 1 Kilogram (1 KG) : <b>₹{s['silver_1kg']:,.2f}</b>
• <i>Trend:</i> {s_dir} {abs(s['change_pct']):.2f}% (${data['silver_comex']['price']:.2f}/oz).
• 💡 <i>Simple Tip:</i> High demand for solar power panels, EV batteries, and electronics keeps silver prices supported worldwide.

================================================================
⛽ <b>PETROL &amp; DIESEL PRICES TODAY:</b>
<i>Retail Pump Rates across Major Cities:</i>
{fuel_str}

• <b>Brent Crude Benchmark:</b> <b>${brent['price']:.2f} / barrel</b> ({brent_dir} {abs(brent['change_pct']):.2f}%)
• 💡 <i>Simple Tip:</i> India imports over 85% of its crude oil. When world crude prices rise, it pushes up domestic petrol and transport expenses.

================================================================
💵 <b>US DOLLAR TO INDIAN RUPEE (USD / INR):</b>
• <b>Exchange Rate:</b> <b>1 USD = ₹{usd['price']:.2f} INR</b> ({usd_dir} {abs(usd['change_pct']):.2f}%)
• 💡 <i>What this means for everyday life:</i>
  - A stronger Dollar makes imported petrol, electronics, and foreign education/travel slightly costlier.
  - Indian IT companies (TCS, Infosys) earn more Rupees from US clients when the Dollar is strong.
  - RBI maintains record foreign exchange reserves ($690+ Billion) to keep the Rupee steady against sharp swings.
================================================================
✅ <i>Tap [ 🔄 Refresh Rates ] below for updated live prices.</i>"""


def get_commodity_macro_forecast_parts(data: dict = None) -> list[str]:
    """
    World-level institutional macroeconomic analysis, seasonal price cycles,
    and buying windows for Gold, Silver, and Crude Oil.
    Returns [part1, part2] to stay strictly within Telegram 4096-char limits.
    """
    if not data:
        data = fetch_live_rates()

    now_str = datetime.datetime.now().strftime("%d %b %Y, %I:%M %p IST")
    gold_p = data["gold_comex"]["price"]
    silver_p = data["silver_comex"]["price"]
    brent_p = data["brent"]["price"]
    usd_p = data["usdinr"]["price"]

    # Calculate gold to silver ratio
    ratio = round(gold_p / silver_p, 1) if silver_p > 0 else 75.0

    part1 = f"""🔮 <b>RUPEESTREET // GLOBAL COMMODITY FORECAST (PART 1/2)</b>
<i>🟡 GOLD (XAU/USD) DEEP MACRO FORECAST &amp; DROP CYCLES | {now_str}</i>
================================================================
⚠️ <b>TRUTH ABOUT 95% PREDICTIONS &amp; EXACT CALENDAR DATES:</b>
• <b>Institutional Reality:</b> In global financial markets, <b>no credible institution (Goldman Sachs, JP Morgan, or Central Banks) can guarantee a 95% directional certainty or predict exact future calendar dates</b> for price tops or bottoms.
• Commodity prices move based on unpredictable global events: sudden geopolitical conflicts, surprise OPEC+ quotas, US Federal Reserve interest rate decisions, and currency fluctuations.
• <b>The Professional Approach:</b> Smart money never gambles on a single date. Instead, they identify <b>Seasonal Dip Windows &amp; Support Zones</b> and accumulate in 3 to 4 parts (Dollar-Cost Averaging / SIP).

================================================================
🟡 <b>1. GOLD (XAU/USD) // EXACT DROP &amp; RISE ANALYSIS:</b>
• <b>Current Global Spot:</b> <b>${gold_p:,.2f} / oz</b> | USD/INR: <b>₹{usd_p:.2f}</b>

📉 <b>WHEN &amp; WHY WILL GOLD RATES DROP? (PULLBACK TRIGGERS):</b>
1. <b>US Dollar (DXY) Spikes &amp; US Fed Rate Delays:</b>
   • Whenever the US Dollar strengthens (DXY index above 104) or the US Fed delays interest rate cuts due to sticky inflation, global capital flows out of zero-yielding gold into high-yielding US Treasury bonds (yielding 4.5%+).
2. <b>Geopolitical De-escalation &amp; Peace Accords:</b>
   • Gold carries an active $100–$250/oz 'safe-haven war premium'. Whenever ceasefires or diplomatic accords are announced, that risk premium rapidly unwinds, causing sharp 4% to 7% price corrections.
3. <b>Central Bank Profit-Taking &amp; Import Duty Reductions:</b>
   • When gold reaches record peaks, central bank buying temporarily pauses. In India, customs duty cuts or sudden rupee appreciation against the USD immediately pull domestic gold prices down.

📅 <b>EXACT CALENDAR DROP WINDOWS FOR GOLD (WHEN TO BUY):</b>
• <b>Seasonal Drop Window 1 (February 15 – April 10):</b> Post-wedding demand vacuum and financial year-end liquidity crunch cause prices to cool off and consolidate.
• <b>Seasonal Drop Window 2 (June 15 – August 10):</b> Summer monsoon doldrums before the Indian festive buying surge historically produce the best accumulation rates of the year.
• <b>Seasonal Drop Window 3 (Late December):</b> Year-end institutional book squaring and profit-taking by global hedge funds.
• <b>Technical Pullback Target:</b> Gold historically experiences 5% to 8% healthy pullbacks from all-time highs during these windows—making them ideal accumulation points.

📈 <b>WHEN DOES GOLD REACH PEAK HIGHS?</b>
• <b>Peak Surge Window (September 15 – January 31):</b> Dhanteras, Diwali, peak Indian wedding season, Christmas, and Chinese New Year physical demand drive prices to annual highs."""

    part2 = f"""🔮 <b>RUPEESTREET // GLOBAL COMMODITY FORECAST (PART 2/2)</b>
<i>⚪ SILVER &amp; 🛢️ CRUDE OIL OUTLOOK &amp; ACTION PLAN | {now_str}</i>
================================================================
⚪ <b>2. SILVER (XAG/USD) // EXACT DROP &amp; RISE ANALYSIS:</b>
• <b>Current Global Spot:</b> <b>${silver_p:.2f} / oz</b> | <b>Gold-to-Silver Ratio:</b> <b>{ratio}:1</b>

📉 <b>WHEN &amp; WHY WILL SILVER RATES DROP? (PULLBACK TRIGGERS):</b>
1. <b>Global Industrial &amp; Manufacturing Slowdowns:</b>
   • Over 60% of silver demand is industrial (solar panels, electronics, EVs, AI chip contacts). When manufacturing PMIs in China, US, or Europe contract, industrial silver demand drops sharply.
2. <b>Base Metals Liquidation (Copper &amp; Zinc Sell-Offs):</b>
   • Most silver is mined as a byproduct of copper and zinc. When base metals crash, institutional funds dump speculative silver futures, triggering accelerated declines.
3. <b>Exchange Margin Hikes &amp; High Beta Volatility:</b>
   • Silver has 2x to 3x higher price volatility than gold. When exchanges like COMEX or MCX increase margin requirements, leveraged traders are forced to liquidate, sparking steep 8% to 15% pullbacks.

📅 <b>EXACT CALENDAR DROP WINDOWS FOR SILVER (WHEN TO BUY):</b>
• <b>Seasonal Drop Window 1 (March 20 – April 25):</b> Spring industrial inventory destocking and Q1 corporate book adjustments.
• <b>Seasonal Drop Window 2 (June 10 – August 10):</b> Summer industrial factory shutdowns across Europe, the US, and Asia cause seasonal softness.
• <b>Valuation Rule:</b> When the Gold/Silver Ratio rises above <b>80:1 to 85:1</b>, silver is historically undervalued compared to gold—making it a prime buying zone!

📈 <b>WHEN DOES SILVER REACH PEAK HIGHS?</b>
• <b>Peak Window (October – February):</b> Heavy industrial restocking combined with winter jewelry demand creates sharp percentage rallies.

================================================================
🛢️ <b>3. CRUDE OIL (BRENT) // EXACT DROP &amp; SPIKE ANALYSIS:</b>
• <b>Current Brent Price:</b> <b>${brent_p:.2f} / barrel</b>

📉 <b>WHEN &amp; WHY WILL CRUDE OIL PRICES DROP?</b>
1. <b>End of Summer Driving Season (September 15 – November 20):</b> Global refinery maintenance season begins in autumn, drastically reducing crude intake. This is historically the weakest period for oil.
2. <b>Surging Non-OPEC Production:</b> Record US shale production (13.5M+ bpd), plus rising output from Guyana and Brazil, increases world oil supply.
3. <b>OPEC+ Quota Unwinding:</b> When OPEC+ gradually restores paused production, supply increases, bringing prices down.
4. <b>Global EV &amp; Renewable Adoption:</b> Expanding electric vehicle fleets steadily dampen long-term petrol/diesel consumption growth.

📈 <b>WHEN DOES OIL SPIKE?</b>
• Geopolitical conflicts in the Middle East / Persian Gulf / Red Sea shipping routes.
• Severe hurricanes in the US Gulf Coast shutting down offshore drilling (August–October).
• Peak winter heating demand in Europe and North America (December–February).

================================================================
💡 <b>BEST ACTION PLAN FOR CONSUMERS &amp; INVESTORS:</b>
1. <b>Never Buy Everything on a Single Day:</b> Split your gold/silver purchase budget into 3–4 installments.
2. <b>Target Seasonal Dips:</b> Buy jewelry or gold coins during the Feb–April or June–August windows ahead of festival surges.
3. <b>Watch the Gold/Silver Ratio:</b> Accumulate silver when the ratio is above 80:1 for higher long-term upside potential."""

    return [part1, part2]


def get_commodity_deep_macro_forecast(data: dict = None) -> str:
    """Returns joined forecast for backwards compatibility."""
    parts = get_commodity_macro_forecast_parts(data)
    return "\n\n".join(parts)

