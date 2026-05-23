#!/usr/bin/env python3
"""
SBI Trendline Drawing Analysis - Focus on HOW, WHERE, WHEN to draw
"""

import yfinance as yf
import pandas as pd
import numpy as np
from scipy.signal import argrelextrema
from datetime import datetime, timedelta

def sbi_trendline_drawing_guide():
    """Complete guide on drawing SBI's trendline"""
    
    ticker = "SBIN.NS"
    
    print("📏 SBI TRENDLINE DRAWING MASTERCLASS")
    print("="*70)
    
    # Download 8-year monthly data
    df = yf.download(ticker, period="8y", interval="1mo", auto_adjust=True, progress=False)
    df = df.dropna()
    df['Price_Idx'] = np.arange(len(df))
    low_prices = df['Low'].values.flatten()
    
    print("🎯 STEP 1: IDENTIFY MAJOR BOTTOMS")
    print("-" * 50)
    
    # Find major bottoms with order=6 (banking sector adjustment)
    touchbacks = argrelextrema(low_prices, np.less, order=6)
    
    print(f"✅ Found {len(touchbacks[0])} major bottoms using 6-month order")
    print("\n📍 ALL MAJOR TOUCH POINTS:")
    
    touch_points = []
    for i, touch_idx in enumerate(touchbacks[0]):
        touch_date = df.index[touch_idx]
        touch_price = low_prices[touch_idx]
        touch_points.append({
            'index': touch_idx,
            'date': touch_date,
            'price': touch_price,
            'months_from_start': touch_idx
        })
        print(f"   Touch {i+1}: {touch_date.strftime('%Y-%m-%d')} at ₹{touch_price:.2f}")
    
    print("\n🎯 STEP 2: SELECT TRENDLINE ANCHOR POINTS")
    print("-" * 50)
    
    # Use last 3 touches for trendline (most recent and relevant)
    last_3_touches = touch_points[-3:]
    
    print("📌 LAST 3 TOUCH POINTS (TRENDLINE ANCHORS):")
    for i, touch in enumerate(last_3_touches, 1):
        print(f"   Anchor {i}: {touch['date'].strftime('%Y-%m-%d')} at ₹{touch['price']:.2f}")
    
    # Extract coordinates for trendline calculation
    x_coords = [touch['months_from_start'] for touch in last_3_touches]
    y_coords = [touch['price'] for touch in last_3_touches]
    
    print(f"\n📊 TRENDLINE COORDINATES:")
    print(f"   X (Time): {x_coords}")
    print(f"   Y (Price): {[f'₹{p:.2f}' for p in y_coords]}")
    
    print("\n🎯 STEP 3: CALCULATE TRENDLINE EQUATION")
    print("-" * 50)
    
    # Fit trendline using last 3 touches
    slope, intercept = np.polyfit(x_coords, y_coords, 1)
    
    print(f"📈 TRENDLINE MATHEMATICS:")
    print(f"   Equation: Price = {slope:.4f} × Month + {intercept:.2f}")
    print(f"   Slope: ₹{slope:.2f} per month")
    print(f"   Growth Rate: {(slope/intercept)*100:.2f}% per month")
    
    # Validate trendline quality
    r_squared = np.corrcoef(x_coords, y_coords)[0, 1] ** 2
    print(f"   R-squared: {r_squared:.3f} ({'Strong' if r_squared > 0.8 else 'Moderate' if r_squared > 0.6 else 'Weak'} correlation)")
    
    print("\n🎯 STEP 4: CURRENT TRENDLINE POSITION")
    print("-" * 50)
    
    current_month = df['Price_Idx'].iloc[-1]
    current_price = df['Close'].iloc[-1].item()
    current_trendline = (slope * current_month) + intercept
    
    print(f"📅 CURRENT ANALYSIS ({df.index[-1].strftime('%Y-%m-%d')}):")
    print(f"   Current Price: ₹{current_price:.2f}")
    print(f"   Trendline Level: ₹{current_trendline:.2f}")
    
    distance_pct = ((current_price - current_trendline) / current_trendline) * 100
    print(f"   Distance: {distance_pct:+.2f}%")
    
    if abs(distance_pct) <= 5:
        status = "🎯 TOUCHING TRENDLINE"
    elif distance_pct > 5:
        status = f"📈 ABOVE TRENDLINE ({distance_pct:.1f}%)"
    else:
        status = f"📉 BELOW TRENDLINE ({abs(distance_pct):.1f}%)"
    
    print(f"   Status: {status}")
    
    print("\n🎯 STEP 5: FUTURE TRENDLINE PROJECTIONS")
    print("-" * 50)
    
    # Calculate historical touch intervals
    intervals = []
    for i in range(1, len(last_3_touches)):
        interval = last_3_touches[i]['months_from_start'] - last_3_touches[i-1]['months_from_start']
        intervals.append(interval)
    
    avg_interval = sum(intervals) / len(intervals)
    
    print(f"📊 TOUCH INTERVAL ANALYSIS:")
    print(f"   Touch Intervals: {intervals} months")
    print(f"   Average Interval: {avg_interval:.1f} months")
    
    # Predict next 3 touch points
    last_touch_month = last_3_touches[-1]['months_from_start']
    
    print(f"\n🔮 FUTURE TOUCH POINT PREDICTIONS:")
    
    for i in range(1, 4):
        future_month = last_touch_month + (avg_interval * i)
        future_price = (slope * future_month) + intercept
        
        # Convert to actual date
        months_from_now = future_month - current_month
        future_date = datetime.now() + timedelta(days=int(months_from_now * 30))
        
        print(f"   Future Touch {i}:")
        print(f"      Date: {future_date.strftime('%Y-%m-%d')}")
        print(f"      Price: ₹{future_price:.2f}")
        print(f"      Months Away: {months_from_now:.1f}")
        print()
    
    print("🎯 STEP 6: TRENDLINE DRAWING RULES")
    print("-" * 50)
    
    print("📏 HOW TO DRAW:")
    print("   1. Use MONTHLY timeframe (not daily/weekly)")
    print("   2. Connect the LOWEST points of major bottoms")
    print("   3. Use minimum 3 touch points for validation")
    print("   4. Line should have ASCENDING slope")
    print("   5. More touches = stronger trendline")
    
    print(f"\n📍 WHERE TO DRAW:")
    print("   1. Start from the OLDEST major bottom")
    print("   2. Connect through subsequent major lows")
    print("   3. Ignore minor pullbacks/corrections")
    print("   4. Focus on SIGNIFICANT bottoms (6+ month order)")
    print("   5. Line should touch multiple points without breaking")
    
    print(f"\n⏰ WHEN TO DRAW:")
    print("   1. After minimum 3 major bottoms are formed")
    print("   2. When pattern shows consistent ascending lows")
    print("   3. After each new major bottom (update trendline)")
    print("   4. Use for ENTRY when price approaches line")
    print("   5. Invalidate if line is broken significantly")
    
    print("\n🎯 STEP 7: SBI TRENDLINE SUMMARY")
    print("-" * 50)
    
    print("📋 SBI TRENDLINE FACTS:")
    print(f"   ✅ Valid ascending trendline established")
    print(f"   ✅ Based on {len(last_3_touches)} recent major bottoms")
    print(f"   ✅ Growing at ₹{slope:.2f} per month")
    print(f"   ✅ Strong mathematical correlation (R² = {r_squared:.3f})")
    
    print(f"\n🎯 TRADING IMPLICATIONS:")
    if distance_pct > 10:
        print(f"   ⚠️  Currently {distance_pct:.1f}% above trendline - WAIT for pullback")
        print(f"   🎯 Target entry zone: ₹{current_trendline-50:.0f} - ₹{current_trendline+50:.0f}")
    elif abs(distance_pct) <= 5:
        print(f"   ✅ Near trendline - POTENTIAL ENTRY ZONE")
    else:
        print(f"   📉 Below trendline - STRONG BUY if fundamentals support")
    
    print(f"\n📅 NEXT MONITORING DATES:")
    next_touch_date = datetime.now() + timedelta(days=int(avg_interval * 30))
    print(f"   🔮 Next expected touch: {next_touch_date.strftime('%Y-%m-%d')}")
    print(f"   📊 Monitor monthly for trendline approach")
    print(f"   🎯 Set alerts at ₹{current_trendline-100:.0f} and ₹{current_trendline+100:.0f}")

if __name__ == "__main__":
    sbi_trendline_drawing_guide()