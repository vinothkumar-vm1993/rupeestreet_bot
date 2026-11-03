import argparse
import numpy as np
import pandas as pd

class TechnicalEngine:
    @staticmethod
    def calculate_ema(series: pd.Series, span: int) -> pd.Series:
        return series.ewm(span=span, adjust=False).mean()

    @staticmethod
    def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / (loss + 1e-9)
        return 100 - (100 / (1 + rs))

    @staticmethod
    def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        tr1 = df['High'] - df['Low']
        tr2 = (df['High'] - df['Close'].shift(1)).abs()
        tr3 = (df['Low'] - df['Close'].shift(1)).abs()
        return pd.concat([tr1, tr2, tr3], axis=1).max(axis=1).rolling(window=period).mean()

class ForensicShield:
    @staticmethod
    def evaluate(debt_to_equity: float, opm: float, pledge: float, volume: int) -> bool:
        return debt_to_equity <= 1.2 and opm > 0.05 and pledge == 0.0 and volume >= 1_500_000

class PositionSizer:
    def __init__(self, max_risk: float = 500.0):
        self.max_risk = max_risk

    def calculate_levels(self, cmp: float, atr: float) -> dict:
        risk_dist = round(1.5 * atr, 2)
        qty = max(1, int(self.max_risk // risk_dist)) if risk_dist > 0 else 1
        return {
            "qty": qty,
            "sl": round(cmp - risk_dist, 2),
            "be_trigger": round(cmp + (1.2 * risk_dist), 2),
            "target_1": round(cmp + (2.0 * risk_dist), 2),
            "target_2": round(cmp + (3.5 * risk_dist), 2)
        }

def run_scan():
    tickers = {
        "₹100 Tier": ("BEL.NS", 125.0),
        "₹200 Tier": ("TATASTEEL.NS", 155.0),
        "₹500 Tier": ("TATAPOWER.NS", 420.0),
        "₹1000 Tier": ("ICICIBANK.NS", 1260.0),
        "₹5000+ Tier": ("TCS.NS", 4150.0)
    }
    sizer = PositionSizer(max_risk=500.0)
    print("\n--- Rupeestreet Bot: Indian Market Multi-Tier Scan ---\n")
    
    for tier, (symbol, cmp) in tickers.items():
        if not ForensicShield.evaluate(debt_to_equity=0.4, opm=0.18, pledge=0.0, volume=2_100_000):
            continue
        levels = sizer.calculate_levels(cmp=cmp, atr=cmp * 0.02)
        print(f"⚡ RAPID INTEL: ${symbol} ({tier})")
        print(f"• CMP: ₹{cmp:.2f} | Quantity: {levels['qty']} Shares (Max Risk: ₹500)")
        print(f"• Initial SL: ₹{levels['sl']} | Zero-Risk Shift at: ₹{levels['be_trigger']}")
        print(f"• Target 1: ₹{levels['target_1']} | Target 2: ₹{levels['target_2']}\n")

if __name__ == '__main__':
    run_scan()
