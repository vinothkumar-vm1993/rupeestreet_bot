# 📈 RUPEESTREET // MASTER OPERATIONS TERMINAL
### *Institutional-Grade Quantitative Intelligence & Capital Preservation for Indian Financial Markets*

![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-blue.svg?style=flat-square)
![Telegram API](https://img.shields.io/badge/Telegram%20Bot%20API-v22%2B-2CA5E0.svg?style=flat-square&logo=telegram)
![Risk Engine](https://img.shields.io/badge/Max%20Risk%20Invariant-%E2%82%B9500%20Cap-brightgreen.svg?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)
![Status](https://img.shields.io/badge/Status-Production%20Ready-success.svg?style=flat-square)

**RupeeStreet** is a disciplined, institutional-grade trading terminal built directly inside Telegram for the Indian Stock Market (NSE/BSE). Designed with a strict **"Capital Preservation First, Profits Second"** philosophy, it replaces emotional retail trading with rigorous mathematical position sizing, automated risk sentinels, budget-tiered screening, and real-time global macroeconomic intelligence.

---

## 🏛️ Core Architectural Pillars

### 1. 🛡️ Mathematical Risk & Capital Shield
* **Strict ₹500 Maximum Loss Invariant**: No matter the share price (₹50 or ₹5,000), every trade's maximum potential loss is mathematically capped at ₹500.
* **Dynamic Position Sizing (Agent M)**: Calculates exact share quantity dynamically using 14-period Average True Range (ATR):
  $$\text{Shares to Buy} = \frac{₹500}{\text{Entry Price} - \text{Stop-Loss Price}}$$
* **Zero-Loss Breakeven Engine (Agent N)**: Once a tracked trade achieves a +2% to +4% gain, Agent N automatically advises advancing the stop-loss to entry price, eliminating financial risk entirely.
* **Flash-Crash Sentinel (Agent O)**: Runs background surveillance every 180 seconds across all active positions to alert on sudden adverse price movements.

### 2. 🎯 Budget-Tiered Stock Discovery
* Categorizes top institutional opportunities into distinct price brackets:
  * **Under ₹100 Tier**: Accessible micro-caps & PSU turnarounds.
  * **₹200 – ₹499 Tier**: High-volume momentum mid-caps.
  * **₹500 – ₹999 Tier**: Quality sectoral compounders.
  * **₹1,000 – ₹1,999 Tier**: Nifty 50 and large-cap leaders.
  * **₹2,000 – ₹4,999 Tier**: Blue-chip institutional staples.
  * **₹5,000+ Tier**: Heavyweight corporate leaders.
* Smart pagination (**5 stocks per page**) with one-touch navigation and typo-tolerant fuzzy symbol resolution (e.g., searching `hfc` resolves to `HDFCBANK`).

### 3. 🌍 Global & Domestic Macro Intelligence
* **Live Daily Rates**: Real-time spot prices for COMEX Gold, Silver, Brent Crude Oil, Retail Fuel (Petrol & Diesel), and USD/INR exchange rates.
* **Institutional Commodity Forecast Engine**: Deep cyclical analysis providing multi-decade seasonal dip accumulation windows and macroeconomic drop triggers for Gold, Silver, and Crude Oil.
* **Top 10 Macro Intel**: 10-point World Economic Intelligence and 10-point Indian Domestic Dashboard integrated with live breaking headlines.
* **Live Market Status**: Real-time NSE/BSE operational status banner with Indian Standard Time (IST) schedule tracking and circuit-breaker crash monitoring.

### 4. 📊 Technical Charting & Derivatives
* **On-Demand Candlestick Charts**: Generated with volume bars, EMA-20, EMA-50, and 14-period RSI technical indicators.
* **Derivatives Strike Analysis**: Real-time Put-Call Ratio (PCR), Max Pain levels, and heavy Call/Put Open Interest (OI) support and resistance barriers.

---

## ⌨️ Command Reference Matrix

| Command | Shortcut / Aliases | Description |
| :--- | :--- | :--- |
| `/start` | `/help` | Launch the master touch-control dashboard and view live market status. |
| `/status` | `/market` | Display real-time NSE/BSE operational status, trading hours, and halts. |
| `/rules` | `/safety` | Review the 3 Golden Rules of Capital Preservation. |
| `/today` | `/todaystocks` | Scan today's top algorithmic buy candidates across all price tiers. |
| `/rates` | `/gold`, `/fuel`, `/usd` | Display live spot rates for Gold, Silver, Petrol, Diesel, and USD/INR. |
| `/forecast` | `/commodity` | View deep macroeconomic price cycles and seasonal dip buying windows. |
| `/news` | `/macro`, `/world` | Dispatch Top 10 Global and Top 10 Indian market economic briefings. |
| `/portfolio` | — | Inspect open tracked trades, breakeven milestones, and stop levels. |
| `/remove <SYM>`| `/untrack` | Remove a stock from active background tracking (e.g., `/remove BEL`). |
| `/chart <SYM>` | — | Generate a technical candlestick chart (e.g., `/chart TATAPOWER`). |
| `/derivatives`| `/deriv` | Inspect options strikes, PCR ratios, and institutional open interest. |
| `/risk` | — | Real-time market risk, volatility gauge, and circuit-breaker telemetry. |
| `/terms` | `/disclaimer` | View official operational guidelines and regulatory disclaimers. |

---

## 🚀 Quickstart & Local Setup

### 1. Prerequisites
* Python 3.11, 3.12, 3.13, or 3.14
* Git

### 2. Installation
```bash
# Clone repository
git clone https://github.com/vinothkumar-vm1993/rupeestreet_bot.git
cd rupeestreet_bot

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install production dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration
Copy `.env.example` to `.env` and insert your Telegram Bot Token:
```bash
cp .env.example .env
```
Edit `.env`:
```env
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
AUTHORIZED_USERS=your_telegram_user_id   # Optional: Leave empty for open access
LOG_LEVEL=INFO
```

### 4. Run the Bot
```bash
python bot.py
```

---

## ☁️ 24/7 Cloud Deployment (Render.com)

RupeeStreet is pre-configured for zero-downtime, continuous cloud hosting:

1. **Link Repository**: Connect your GitHub repository to [Render.com](https://render.com).
2. **Select Web Service**: Create a new Web Service pointing to `rupeestreet_bot`.
3. **Build & Start Commands**:
   * **Runtime**: `Python 3`
   * **Build Command**: `pip install -r requirements.txt`
   * **Start Command**: `python bot.py`
4. **Environment Variables**:
   * Add `TELEGRAM_BOT_TOKEN` with your bot's token.
5. **Continuous Uptime**:
   * RupeeStreet features an integrated, lightweight HTTP health server listening on `$PORT`.
   * Add your free service URL (`https://<app-name>.onrender.com`) to [UptimeRobot](https://uptimerobot.com) with a 5-minute ping interval to prevent idle sleep.

---

## 🔒 Security & Privacy Architecture
* **Non-Custodial Design**: RupeeStreet has **zero connection** to your broker account (Zerodha, Groww, AngelOne). It cannot execute financial transactions or access user funds.
* **Isolated Environment**: Sensitive tokens and SQLite state databases are strictly isolated via `.gitignore`.
* **Zero Credential Sharing**: Users retain 100% manual order-entry control in their respective brokerage applications.

---

## 📜 Regulatory Notice & Disclaimer
*RupeeStreet is an automated quantitative research and mathematical execution-guidance terminal designed for educational and capital discipline purposes. It does not provide SEBI-registered portfolio management or guaranteed investment returns. Financial markets involve inherent volatility; always conduct your own research and strictly respect stop-loss limits.*

---

**Crafted with discipline for Indian retail traders.**
