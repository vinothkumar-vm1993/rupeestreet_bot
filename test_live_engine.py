import requests
import numpy as np
import math

def analyze_symbol(symbol: str):
    sym = symbol.upper().strip().replace(".NS", "").replace(".BO", "")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    # Try fetching data from Yahoo chart API
    data = None
    for ticker in [f"{sym}.NS", f"{sym}.BO", sym]:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=1y&interval=1d"
        try:
            r = requests.get(url, headers=headers, timeout=6)
            if r.status_code == 200:
                res = r.json().get("chart", {}).get("result")
                if res:
                    meta = res[0]["meta"]
                    quotes = res[0]["indicators"]["quote"][0]
                    closes = [c for c in quotes.get("close", []) if c is not None]
                    highs = [h for h in quotes.get("high", []) if h is not None]
                    lows = [l for l in quotes.get("low", []) if l is not None]
                    volumes = [v for v in quotes.get("volume", []) if v is not None]
                    if len(closes) >= 20:
                        data = {
                            "symbol": sym,
                            "ticker": ticker,
                            "price": meta.get("regularMarketPrice") or closes[-1],
                            "prev_close": meta.get("chartPreviousClose") or closes[-2],
                            "currency": meta.get("currency", "INR"),
                            "exchange": meta.get("exchangeName", "NSE"),
                            "fiftyTwoWeekHigh": meta.get("fiftyTwoWeekHigh") or max(highs),
                            "fiftyTwoWeekLow": meta.get("fiftyTwoWeekLow") or min(lows),
                            "closes": closes,
                            "highs": highs,
                            "lows": lows,
                            "volumes": volumes,
                        }
                        break
        except Exception:
            pass
            
    if not data:
        return None
        
    closes = np.array(data["closes"])
    highs = np.array(data["highs"][-len(closes):])
    lows = np.array(data["lows"][-len(closes):])
    vols = np.array(data["volumes"][-len(closes):])
    price = float(data["price"])
    
    # EMAs
    def calc_ema(arr, span):
        alpha = 2.0 / (span + 1.0)
        ema = [arr[0]]
        for val in arr[1:]:
            ema.append(alpha * val + (1 - alpha) * ema[-1])
        return ema[-1]

    ema_20 = calc_ema(closes, 20) if len(closes) >= 20 else price
    ema_50 = calc_ema(closes, 50) if len(closes) >= 50 else price
    ema_200 = calc_ema(closes, 200) if len(closes) >= 200 else price
    
    # RSI (14)
    diffs = np.diff(closes)
    gains = np.where(diffs > 0, diffs, 0.0)
    losses = np.where(diffs < 0, -diffs, 0.0)
    if len(gains) >= 14:
        avg_gain = np.mean(gains[-14:])
        avg_loss = np.mean(losses[-14:])
        if avg_loss == 0:
            rsi_14 = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi_14 = round(100.0 - (100.0 / (1.0 + rs)), 1)
    else:
        rsi_14 = 50.0

    # ATR (14)
    tr_list = []
    for i in range(1, min(len(closes), 15)):
        tr = max(highs[-i] - lows[-i], abs(highs[-i] - closes[-i-1]), abs(lows[-i] - closes[-i-1]))
        tr_list.append(tr)
    atr = round(float(np.mean(tr_list)), 2) if tr_list else round(price * 0.015, 2)
    
    # Volatility & Max Drawdown
    log_ret = np.diff(np.log(closes))
    ann_vol = round(float(np.std(log_ret) * math.sqrt(252) * 100), 1)
    peak = np.maximum.accumulate(closes)
    drawdowns = (closes - peak) / peak
    max_dd = round(float(np.min(drawdowns) * 100), 1)
    
    return {
        "sym": sym,
        "price": price,
        "ema_20": round(ema_20, 2),
        "ema_50": round(ema_50, 2),
        "ema_200": round(ema_200, 2),
        "rsi_14": rsi_14,
        "atr": atr,
        "ann_vol": ann_vol,
        "max_dd": max_dd,
        "52w_high": round(data["fiftyTwoWeekHigh"], 2),
        "52w_low": round(data["fiftyTwoWeekLow"], 2)
    }

res = analyze_symbol("INFY")
print("Live Analysis for INFY:", res)
res2 = analyze_symbol("TATAPOWER")
print("Live Analysis for TATAPOWER:", res2)
