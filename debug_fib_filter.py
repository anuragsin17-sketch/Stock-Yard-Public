#!/usr/bin/env python3
"""
Debug why Fibonacci confluence is blocking trades
"""
import yfinance as yf
import numpy as np
from scipy.signal import argrelextrema
from datetime import datetime, timedelta
import pandas as pd

def get_monthly_trendline(ticker):
    df_monthly = yf.download(ticker, period="8y", interval="1mo", 
                              auto_adjust=True, progress=False)
    if df_monthly.empty or len(df_monthly) < 24:
        return None
    df_monthly = df_monthly.dropna()
    df_monthly['Price_Idx'] = np.arange(len(df_monthly))
    low_prices = df_monthly['Low'].values.flatten()
    
    banking = ['SBIN', 'HDFCBANK', 'ICICIBANK', 'AXISBANK', 'KOTAKBANK']
    order = 6 if any(b in ticker for b in banking) else 10
    touchbacks = argrelextrema(low_prices, np.less, order=order)
    for fallback_order in [8, 6, 5]:
        if len(touchbacks[0]) >= 2:
            break
        touchbacks = argrelextrema(low_prices, np.less, order=fallback_order)
    if len(touchbacks[0]) < 2:
        return None
    
    num = min(3, len(touchbacks[0]))
    anchor_indices = touchbacks[0][-num:]
    x = [df_monthly['Price_Idx'].iloc[i] for i in anchor_indices]
    y = [low_prices[i] for i in anchor_indices]
    slope, intercept = np.polyfit(x, y, 1)
    if slope <= 0:
        return None
    
    return {'slope': slope, 'intercept': intercept,
            'last_month_idx': int(df_monthly['Price_Idx'].iloc[-1]),
            'last_month_date': df_monthly.index[-1],
            'monthly_df': df_monthly,
            'anchor_indices': anchor_indices}

def get_trigger_for_date(tl, target_date):
    slope = tl['slope']
    intercept = tl['intercept']
    last_month_idx = tl['last_month_idx']
    last_month_date = tl['last_month_date']
    months_diff = ((target_date.year - last_month_date.year) * 12 + 
                   (target_date.month - last_month_date.month))
    current_month_idx = last_month_idx + months_diff
    return (slope * current_month_idx) + intercept

def analyze_fib_confluence(ticker, tl):
    """Show exactly what Fibonacci confluence looks like for a stock"""
    monthly_df = tl['monthly_df']
    anchor_indices = tl['anchor_indices']
    
    # Get current trigger
    current_date = datetime.now()
    trigger = get_trigger_for_date(tl, current_date)
    
    # Get current price
    current_price = monthly_df['Close'].iloc[-1]
    if hasattr(current_price, 'item'):
        current_price = current_price.item()
    
    distance_pct = ((current_price - trigger) / trigger) * 100
    
    print(f"\n{'='*60}")
    print(f"📊 {ticker.replace('.NS','')}")
    print(f"   Current Price: Rs{current_price:.2f}")
    print(f"   Trendline Trigger: Rs{trigger:.2f}")
    print(f"   Distance: {distance_pct:+.1f}%")
    
    # Fibonacci calculation
    last_touch_idx = anchor_indices[-1]
    last_touch_price = monthly_df['Low'].iloc[last_touch_idx]
    if hasattr(last_touch_price, 'item'):
        last_touch_price = last_touch_price.item()
    
    data_after = monthly_df.iloc[last_touch_idx:]
    swing_high = data_after['High'].max()
    if hasattr(swing_high, 'item'):
        swing_high = swing_high.item()
    
    fib_range = swing_high - last_touch_price
    
    print(f"\n   📐 FIBONACCI GRID:")
    print(f"   Base (last touch): Rs{last_touch_price:.2f}")
    print(f"   Peak (swing high): Rs{swing_high:.2f}")
    print(f"   Range: Rs{fib_range:.2f}")
    
    fib_levels = {
        '23.6%': swing_high - (fib_range * 0.236),
        '38.2%': swing_high - (fib_range * 0.382),
        '50.0%': swing_high - (fib_range * 0.500),
        '61.8%': swing_high - (fib_range * 0.618),
        '78.6%': swing_high - (fib_range * 0.786)
    }
    
    min_dist = float('inf')
    closest = None
    for level, price in fib_levels.items():
        dist = abs((trigger - price) / price) * 100
        marker = " ← TRENDLINE HERE" if dist < 5 else ""
        print(f"   {level}: Rs{price:.2f} (dist from trendline: {dist:.1f}%){marker}")
        if dist < min_dist:
            min_dist = dist
            closest = level
    
    # Score
    if min_dist <= 1.0: score = 10
    elif min_dist <= 2.0: score = 8
    elif min_dist <= 3.0: score = 7
    elif min_dist <= 5.0: score = 5
    else: score = 2
    
    print(f"\n   🎯 Closest Fib: {closest} ({min_dist:.1f}% away)")
    print(f"   📊 Confluence Score: {score}/10")
    
    if score >= 7:
        print(f"   ✅ PASSES filter (score >= 7)")
    else:
        print(f"   ❌ BLOCKED by filter (score < 7) - THIS IS WHY NO TRADE!")

# Test key stocks
tickers = ['MARUTI.NS', 'RELIANCE.NS', 'AXISBANK.NS', 'LT.NS', 
           'BAJFINANCE.NS', 'HCLTECH.NS', 'SBIN.NS', 'KOTAKBANK.NS']

print("🔍 FIBONACCI CONFLUENCE ANALYSIS - WHY TRADES ARE BLOCKED")
print("="*60)

for ticker in tickers:
    tl = get_monthly_trendline(ticker)
    if tl:
        analyze_fib_confluence(ticker, tl)
    else:
        print(f"\n❌ {ticker}: No valid trendline")
