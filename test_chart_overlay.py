import os
import pandas as pd
import mplfinance as mpf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import datetime
import requests

sym = "BEL"
url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}.NS?range=3mo&interval=1d"
r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
res = r.json()["chart"]["result"][0]
timestamps = res.get("timestamp", [])
q = res["indicators"]["quote"][0]
dates = [datetime.datetime.fromtimestamp(ts) for ts in timestamps]
df = pd.DataFrame({
    "Open": q["open"], "High": q["high"], "Low": q["low"], "Close": q["close"], "Volume": q["volume"]
}, index=pd.DatetimeIndex(dates)).dropna()

df_slice = df.tail(45).copy()

# Add 20-EMA (Cyan) and 50-EMA (Orange)
ema20 = df["Close"].ewm(span=20, adjust=False).mean().tail(45)
ema50 = df["Close"].ewm(span=50, adjust=False).mean().tail(45)

ap = [
    mpf.make_addplot(ema20, color='#00e5ff', width=1.4),
    mpf.make_addplot(ema50, color='#ff9100', width=1.4)
]

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

# Horizontal lines
hlines_values = [398.5, 385.0, 404.0, 415.0, 428.0]
hlines_colors = ['#29b6f6', '#ff5252', '#ffb300', '#26a69a', '#00e676']
hlines_styles = ['-', '-', ':', '--', '--']
hlines_widths = [1.8, 1.8, 1.4, 1.8, 1.8]

hlines_dict = dict(hlines=hlines_values, colors=hlines_colors, linestyle=hlines_styles, linewidths=hlines_widths, alpha=0.9)

fig, axlist = mpf.plot(
    df_slice,
    type='candle',
    style=custom_style,
    addplot=ap,
    hlines=hlines_dict,
    volume=True,
    figsize=(11, 6.5),
    returnfig=True
)

fig.savefig("/home/vinoth/Project/rupeestreet_bot/charts/test_tradingview.png", dpi=120, facecolor='#0a0e17')
plt.close(fig)
print("Saved TradingView style chart:", os.path.getsize("/home/vinoth/Project/rupeestreet_bot/charts/test_tradingview.png"), "bytes")
