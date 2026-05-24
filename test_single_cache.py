#!/usr/bin/env python3
"""Test single stock trendline build to find the bug"""
import yfinance as yf
import numpy as np
from scipy.signal import argrelextrema

ticker = 'RELIANCE.NS'

def from_df(df, timeframe):
    print(f"  Testing {timeframe}: {len(df)} rows")
    if df.empty or len(df) < 18:
        print(f"  FAIL: insufficient data")
        return None
    df = df.dropna()
    df['Price_Idx'] = np.arange(len(df))
    low_prices = df['Low'].values.flatten()
    print(f"  Low prices shape: {low_prices.shape}, sample: {low_prices[:3]}")

    order = 10
    touchbacks = argrelextrema(low_prices, np.less, order=order)
    print(f"  Touchbacks with order={order}: {len(touchbacks[0])}")

    for fallback in [8, 6, 5, 4, 3]:
        if len(touchbacks[0]) >= 2:
            break
        touchbacks = argrelextrema(low_prices, np.less, order=fallback)
        print(f"  Touchbacks with order={fallback}: {len(touchbacks[0])}")

    if len(touchbacks[0]) < 2:
        print(f"  FAIL: no anchors")
        return None

    num = min(3, len(touchbacks[0]))
    anchors = touchbacks[0][-num:]
    x = [int(df['Price_Idx'].iloc[i]) for i in anchors]
    y = [float(low_prices[i]) for i in anchors]
    slope, intercept = np.polyfit(x, y, 1)
    print(f"  Slope: {slope:.4f}, Ascending: {slope > 0}")

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

    print(f"  Wick touches: {wicks}")
    if wicks < 3:
        print(f"  FAIL: insufficient wick touches")
        return None

    print(f"  SUCCESS!")
    return {'slope': slope, 'intercept': intercept, 'wicks': wicks}

print(f"Testing {ticker}...")
df_m = yf.download(ticker, period="8y", interval="1mo", auto_adjust=True, progress=False)
result = from_df(df_m, 'monthly')
if not result:
    df_w = yf.download(ticker, period="5y", interval="1wk", auto_adjust=True, progress=False)
    result = from_df(df_w, 'weekly')

print(f"\nFinal result: {result}")
