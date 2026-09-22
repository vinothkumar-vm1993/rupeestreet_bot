import os
import pandas as pd
import mplfinance as mpf
import matplotlib
matplotlib.use("Agg")  # Headless backend
import matplotlib.pyplot as plt
import datetime
import requests

CHARTS_DIR = os.path.join(os.path.dirname(__file__), "charts")
os.makedirs(CHARTS_DIR, exist_ok=True)

def generate_candlestick_chart(symbol: str, entry: float, initial_stop: float, breakeven: float, target1: float, target2: float) -> str:
    """
    Generates a dark-theme TradingView-style layout (nightclouds palette with #131722 base background):
    - Technical Overlays: 20 EMA (Cyan #00e5ff), 50 EMA (Orange #ff9100), Volume bars
    - Horizontal Geometry Lines:
      * Entry Level: Solid Blue Line (#29b6f6)
      * Initial Hard Stop-Loss: Solid Red Line (#ff5252)
      * Zero-Risk Breakeven Trigger: Dotted Amber Line (#ffb300)
      * Target 1: Dashed Teal Line (#26a69a)
      * Target 2: Dashed Bright Green Line (#00e676)
    """
    sym = symbol.upper().strip().replace(".NS", "").replace(".BO", "")
    headers = {"User-Agent": "Mozilla/5.0"}
    
    quotes = None
    for ticker in [f"{sym}.NS", f"{sym}.BO", sym]:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=4mo&interval=1d"
        try:
            r = requests.get(url, headers=headers, timeout=6)
            if r.status_code == 200:
                res = r.json().get("chart", {}).get("result")
                if res:
                    timestamps = res[0].get("timestamp", [])
                    q = res[0]["indicators"]["quote"][0]
                    if len(timestamps) >= 20:
                        dates = [datetime.datetime.fromtimestamp(ts) for ts in timestamps]
                        df = pd.DataFrame({
                            "Open": q["open"],
                            "High": q["high"],
                            "Low": q["low"],
                            "Close": q["close"],
                            "Volume": q["volume"]
                        }, index=pd.DatetimeIndex(dates))
                        df = df.dropna()
                        quotes = df
                        break
        except Exception:
            continue
            
    if quotes is None or len(quotes) < 20:
        return None

    # Calculate 20 and 50 EMA on full history, then take last 45 bars
    df_full = quotes.copy()
    df_slice = df_full.tail(45).copy()
    ema20_slice = df_full["Close"].ewm(span=20, adjust=False).mean().tail(45)
    ema50_slice = df_full["Close"].ewm(span=50, adjust=False).mean().tail(45)

    # Overlays
    ap = [
        mpf.make_addplot(ema20_slice, color='#00e5ff', width=1.4),  # 20 EMA (Cyan)
        mpf.make_addplot(ema50_slice, color='#ff9100', width=1.4)   # 50 EMA (Orange)
    ]

    # TradingView Dark Style
    mc = mpf.make_marketcolors(up='#00e676', down='#ff1744', inherit=True)
    custom_style = mpf.make_mpf_style(
        base_mpf_style='nightclouds',
        marketcolors=mc,
        gridcolor='#2d3748',
        gridstyle='--',
        facecolor='#131722',
        edgecolor='#1a202c',
        figcolor='#0a0e17'
    )

    # Horizontal Lines configuration
    # Blue: Entry, Red: Initial Stop, Amber: Breakeven, Teal: Target 1, Green: Target 2
    hlines_values = [entry, initial_stop, breakeven, target1, target2]
    hlines_colors = ['#29b6f6', '#ff5252', '#ffb300', '#26a69a', '#00e676']
    hlines_styles = ['-', '-', ':', '--', '--']
    hlines_widths = [1.8, 1.8, 1.4, 1.8, 1.8]

    hlines_dict = dict(
        hlines=hlines_values,
        colors=hlines_colors,
        linestyle=hlines_styles,
        linewidths=hlines_widths,
        alpha=0.9
    )

    output_path = os.path.join(CHARTS_DIR, f"chart_{sym}.png")
    title_text = f"\nRUPEESTREET // {sym} [Cyan: 20-EMA | Orange: 50-EMA | Blue: Entry | Red: Stop | Amber: BE | Teal: T1 | Green: T2]"

    fig, axlist = mpf.plot(
        df_slice,
        type='candle',
        style=custom_style,
        addplot=ap,
        title=title_text,
        ylabel='Price (INR)',
        volume=True,
        ylabel_lower='Volume',
        hlines=hlines_dict,
        figsize=(11, 6.5),
        tight_layout=True,
        returnfig=True
    )

    fig.savefig(output_path, dpi=120, facecolor='#0a0e17')
    plt.close(fig)
    return output_path
