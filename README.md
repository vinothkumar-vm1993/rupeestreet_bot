# Rupeestreet Bot 📈

[[https://img.shields.io/badge/License-MIT-blue.svg]](LICENSE)
[[https://img.shields.io/badge/python-3.10%2B-blue]](https://www.python.org/)
[[https://img.shields.io/badge/market-NSE%20%7C%20BSE-orange]](https://www.nseindia.com/)
[[https://img.shields.io/badge/interface-Telegram%20Bot-blue]](https://core.telegram.org/bots)
[[https://img.shields.io/badge/broker-DhanHQ%20API-green]](https://dhanhq.co/)

**Rupeestreet Bot** is an open-source, institutional-grade market intelligence system, technical stock analysis engine, and automated execution bot built specifically for Indian financial markets (**NSE & BSE**). Deployed natively via a Telegram interface and integrated directly with broker execution APIs (such as DhanHQ and Angel One SmartAPI), Rupeestreet Bot enforces a strict **Capital Preservation Above All Else** directive through deterministic risk management, dynamic position sizing, and zero-loss breakeven automation.

## Core Architectural Pillars

1. **Capital Preservation Protocol**: Dynamic ATR-based stop-loss mechanics and automated breakeven transitions ensure capital protection before profit chasing.
2. **5-Tier Price Segmentation**: Equities are classified into 5 distinct capital tiers (₹100, ₹200, ₹500, ₹1,000, and ₹5,000+ brackets) with liquidity and forensic safety checks.
3. **Forensic & Penny Stock Shield**: Eliminates operator-driven and distressed stocks by validating promoter pledging (0.0%), operating profit margin (OPM > 5%), debt-to-equity (≤ 1.2), and minimum daily volume (≥ 1.5M shares).
4. **Quantitative Position Sizing**: Automatically calculates position quantity based on a fixed risk budget and the instrument's volatility profile (1.5 × ATR-14).
5. **Zero-Loss Breakeven Automation**: Shifts stop-loss orders to entry price once a trade hits +4.0% unrealized profit or Target 1 (1:2 R:R), locking in zero downside risk.
6. **Telemetry & Dark-Theme Charting**: Generates high-resolution TradingView-style candlestick charts plotting trade geometry (entry, stop-loss, breakeven, and targets) via mplfinance.

## System Architecture

```text
rupeestreet_bot/
├── config/
│   ├── settings.py            # Environment configurations & risk limits
│   └── universe.py            # NSE/BSE tier universes & stock filters
├── core/
│   ├── data_engine.py         # Real-time tick & historical data ingestion
│   ├── forensic_shield.py     # Balance sheet & debt/pledge filtration
│   └── technical_engine.py    # 20/50/200 EMA, RSI, and ATR models
├── execution/
│   ├── broker_dhan.py         # DhanHQ API connector & GTT order routing
│   ├── position_sizer.py      # Mathematical ATR-based sizing
│   └── state_machine.py       # SQLite state engine (active_trades table)
├── telegram/
│   ├── bot.py                 # Command router & webhook listener
│   ├── handlers.py            # /start, /todaystocks, /portfolio, /chart
│   └── intel_cards.py         # Standardized Rapid Intel Card formatters
├── visualization/
│   └── chart_engine.py        # Dark-mode candlestick generator (mplfinance)
├── tests/
│   ├── test_indicators.py     # Mathematical verification for technicals
│   └── test_risk_engine.py    # Unit tests for position sizing and stops
├── .env.example
├── LICENSE
├── requirements.txt
└── main.py
```

## Quantitative Position Sizing & Risk Model

Instead of allocating arbitrary capital amounts, Rupeestreet Bot computes share allocation dynamically using trailing volatility:

- **Risk Distance (₹)** = 1.5 × ATR_14
- **Calculated Quantity** = max(1, floor(Predefined Account Risk / Risk Distance))
- **Initial Stop-Loss**: CMP − Risk Distance
- **Breakeven Shift Trigger**: CMP + (1.2 × Risk Distance) ≈ +4.0%
- **Target 1 (50% Profit Harvest)**: CMP + (2.0 × Risk Distance) (1:2.0 Risk-to-Reward)
- **Target 2 (Runner)**: CMP + (3.5 × Risk Distance) (1:3.5 Risk-to-Reward)

## Telegram Command Matrix

| Command | Action | Output / Behavior |
| :--- | :--- | :--- |
| `/start` | Initializes user session | Registers Telegram chat ID and starts background monitoring daemons. |
| `/todaystocks` | On-demand multi-tier scan | Runs analysis across all 5 price tiers and delivers Rapid Intel Cards. |
| `/portfolio` | Live P&L and active orders | Fetches active positions from SQLite database with real-time CMP and trailing stops. |
| `/chart <TICKER>` | Technical chart generation | Renders high-res dark-theme candlestick chart with entry, SL, and target levels. |
| `/macro` | Macroeconomic telemetry | Displays current Brent Crude, USD/INR, 10Y Indian Bond Yield, and FII/DII net flows. |
| `/risk` | Risk management rules | Displays active risk limits, portfolio concentration caps, and drawdown thresholds. |

## Getting Started

### Prerequisites

- Python 3.10 or higher
- Telegram Bot Token (from @BotFather)
- Broker API credentials (such as DhanHQ API)

### Installation

1. Clone the repository:
```bash
git clone [https://github.com/vinothkumar-vm1993/rupeestreet_bot.git](https://github.com/vinothkumar-vm1993/rupeestreet_bot.git)
cd rupeestreet_bot
```

2. Create and activate a Python virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install required packages:
```bash
pip install -r requirements.txt
```

4. Configure your `.env` file:
```bash
cp .env.example .env
```

Populate `.env` with your API keys and risk thresholds:
```env
TELEGRAM_BOT_TOKEN="your_telegram_bot_token"
DHAN_CLIENT_ID="your_dhan_client_id"
DHAN_ACCESS_TOKEN="your_dhan_access_token"
MAX_ACCOUNT_RISK_PER_TRADE=500
PORTFOLIO_EQUITY_CAP_PERCENT=10.0
```

## Running the Bot

Start the Telegram Bot & Background Sentinels:
```bash
python main.py
```

Run an Automated Pre-Market Scan:
```bash
python main.py --scan-premarket
```

Run Test Suite:
```bash
pytest tests/ -v
```

## Contributing

Contributions, bug reports, and pull requests are welcome:

1. Fork the repository.
2. Create your feature branch (`git checkout -b feature/NewIndicator`).
3. Commit your changes (`git commit -m 'feat: add supertrend volatility indicator'`).
4. Push to your branch (`git push origin feature/NewIndicator`).
5. Open a Pull Request.

## License

Distributed under the MIT License. See `LICENSE` for details.
