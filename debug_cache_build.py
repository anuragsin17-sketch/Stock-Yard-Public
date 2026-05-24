#!/usr/bin/env python3
import yfinance as yf
import numpy as np
from scipy.signal import argrelextrema

# Simulate exactly what trendline_cache.py does
def get_sector_order(ticker):
    banking = ['SBIN', 'HDFCBANK', 'ICICIBANK', 'AXISBANK', 'KOTAKBANK',
               'INDUSINDBK', 'FEDERALBNK', 'BANDHANBNK', 'RBLBANK', 'IDFCFIRSTB']
    return 6 if any(b in ticker.upper() for b in banking) else 10

def build_trendline(ticker):
    def from_df(df, timeframe):
        print(f"  from_df called: timeframe={timeframe}, len={len(df)}")
        if df.empty or len(df) < 18:
            print(f"  FAIL: empty or short")
            return None
        df = df.dropna()
        df['Price_Idx'] = np.arange(len(df))
        low_prices = df['Low'].values.flatten()
        print(f"  low_prices type: {type(low_prices)}, shape: {low_prices.shape}")

        order = get_sector_order(ticker)
        if timeframe == 'weekly':
            order = max(3, order // 2)

        touchbacks = argrelextrema(low_prices, np.less, order=order)
        print(f"  touchbacks: {len(touchbacks[0])}")
        for fallback in [8, 6, 5, 4, 3]:
            if len(touchbacks[0]) >= 2:
                break
            touchbacks = argrelextrema(low_prices, np.less, order=fallback)

        if len(touchbacks[0]) < 2:
            print(f"  FAIL: no anchors")
            return None

        num = min(3, len(touchbacks[0]))
        anchors = touchbacks[0][-num:]
        x = [int(df['Price_Idx'].iloc[i]) for i in anchors]
        y = [float(low_prices[i]) for i in anchors]
        slope, intercept = np.polyfit(x, y, 1)
        print(f"  slope={slope:.4f}")

        if slope <= 0:
            print(f"  FAIL: descending")
            return None

        wicks = 0
        for i in range(len(df)):
            midx = int(df['Price_Idx'].iloc[i])
            tl = (slope * midx) + intercept
            dist = abs((float(low_prices[i]) - tl) / tl) * 100
            if dist <= 8.0:
                wicks += 1

        print(f"  wicks={wicks}")
        if wicks < 3:
            print(f"  FAIL: insufficient wicks")
            return None

        print(f"  SUCCESS!")
        return {'slope': slope, 'wicks': wicks, 'timeframe': timeframe}

    try:
        print(f"\nTesting {ticker}...")
        df_monthly = yf.download(ticker, period="8y", interval="1mo", auto_adjust=True, progress=False)
        result = from_df(df_monthly, 'monthly')
        if result:
            return result
        df_weekly = yf.download(ticker, period="5y", interval="1wk", auto_adjust=True, progress=False)
        return from_df(df_weekly, 'weekly')
    except Exception as e:
        print(f"  EXCEPTION: {e}")
        return None

r = build_trendline('RELIANCE.NS')
print(f"\nFinal: {r}")
