#!/usr/bin/env python3
"""
TITAN Trendline Analysis - Applying Learned Pattern Recognition
Using the methodology learned from SBI analysis
"""

import yfinance as yf
import pandas as pd
import numpy as np
from scipy.signal import argrelextrema
from datetime import datetime, timedelta

def titan_trendline_masterclass():
    """Complete TITAN trendline analysis using learned methodology"""
    
    ticker = "TITAN.NS"
    
    print("💎 TITAN TRENDLINE ANALYSIS - APPLYING LEARNED PATTERNS")
    print("="*80)
    
    # Download 8-year monthly data (as learned from SBI)
    df = yf.download(ticker, period="8y", interval="1mo", auto_adjust=True, progress=False)
    df = df.dropna()
    df['Price_Idx'] = np.arange(len(df))
    low_prices = df['Low'].values.flatten()
    
    print("🎯 STEP 1: SECTOR CLASSIFICATION & PARAMETER SELECTION")
    print("-" * 60)
    
    # TITAN is consumer goods, not banking - use standard order=12
    print("📊 SECTOR: Consumer Goods (Jewelry)")
    print("⚙️  PARAMETERS: Using order=12 (standard, not banking order=6)")
    print("📅 TIMEFRAME: Monthly (macro trend focus)")
    
    # Find major bottoms with standard order=12
    touchbacks = argrelextrema(low_prices, np.less, order=12)
    
    print(f"✅ Found {len(touchbacks[0])} major bottoms using 12-month order")
    
    print("\n🎯 STEP 2: IDENTIFY ALL MAJOR TOUCH POINTS")
    print("-" * 60)
    
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
    
    if len(touch_points) < 3:
        print("❌ INSUFFICIENT TOUCH POINTS - Need minimum 3 for valid trendline")
        return
    
    print("\n🎯 STEP 3: SELECT TRENDLINE ANCHOR POINTS (LAST 3)")
    print("-" * 60)
    
    # Use last 3 touches for most relevant trendline
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
    
    print("\n🎯 STEP 4: CALCULATE TRENDLINE EQUATION")
    print("-" * 60)
    
    # Fit trendline using last 3 touches
    slope, intercept = np.polyfit(x_coords, y_coords, 1)
    
    print(f"📈 TRENDLINE MATHEMATICS:")
    print(f"   Equation: Price = {slope:.4f} × Month + {intercept:.2f}")
    print(f"   Slope: ₹{slope:.2f} per month")
    print(f"   Growth Rate: {(slope/intercept)*100:.2f}% per month")
    
    # Validate trendline quality
    r_squared = np.corrcoef(x_coords, y_coords)[0, 1] ** 2
    print(f"   R-squared: {r_squared:.3f} ({'Strong' if r_squared > 0.8 else 'Moderate' if r_squared > 0.6 else 'Weak'} correlation)")
    
    # Check if trendline is ascending (positive slope)
    if slope > 0:
        print(f"   ✅ ASCENDING TRENDLINE (Valid for support)")
    else:
        print(f"   ❌ DESCENDING TRENDLINE (Not suitable for long entries)")
        return
    
    print("\n🎯 STEP 5: CURRENT POSITION ANALYSIS")
    print("-" * 60)
    
    current_month = df['Price_Idx'].iloc[-1]
    current_price = df['Close'].iloc[-1].item()
    current_trendline = (slope * current_month) + intercept
    
    print(f"📅 CURRENT ANALYSIS ({df.index[-1].strftime('%Y-%m-%d')}):")
    print(f"   Current Price: ₹{current_price:.2f}")
    print(f"   Trendline Level: ₹{current_trendline:.2f}")
    
    distance_pct = ((current_price - current_trendline) / current_trendline) * 100
    print(f"   Distance: {distance_pct:+.2f}%")
    
    # Apply learned tolerance levels (±5% from SBI learning)
    if abs(distance_pct) <= 5:
        status = "🎯 TOUCHING TRENDLINE (ENTRY ZONE)"
        signal = "BUY"
    elif distance_pct > 5 and distance_pct <= 15:
        status = f"📈 ABOVE TRENDLINE ({distance_pct:.1f}%) - WAIT"
        signal = "WAIT"
    elif distance_pct > 15:
        status = f"🚀 OVEREXTENDED ({distance_pct:.1f}%) - AVOID"
        signal = "AVOID"
    else:
        status = f"📉 BELOW TRENDLINE ({abs(distance_pct):.1f}%) - STRONG BUY"
        signal = "STRONG BUY"
    
    print(f"   Status: {status}")
    print(f"   Signal: {signal}")
    
    print("\n🎯 STEP 6: FIBONACCI CONFLUENCE ANALYSIS")
    print("-" * 60)
    
    # Find the swing high after last trendline touch for Fibonacci analysis
    last_touch_idx = last_3_touches[-1]['index']
    
    # Look for swing high after last touch
    high_prices_after_touch = df['High'].iloc[last_touch_idx:].values
    if len(high_prices_after_touch) > 0:
        swing_high = np.max(high_prices_after_touch)
        swing_low = last_3_touches[-1]['price']
        
        # Calculate Fibonacci levels
        fib_range = swing_high - swing_low
        fib_levels = {
            '23.6%': swing_high - (fib_range * 0.236),
            '38.2%': swing_high - (fib_range * 0.382),
            '50.0%': swing_high - (fib_range * 0.500),
            '61.8%': swing_high - (fib_range * 0.618),
            '78.6%': swing_high - (fib_range * 0.786)
        }
        
        print(f"📊 FIBONACCI RETRACEMENT LEVELS:")
        print(f"   Swing High: ₹{swing_high:.2f}")
        print(f"   Swing Low: ₹{swing_low:.2f}")
        print(f"   Range: ₹{fib_range:.2f}")
        print()
        
        # Check trendline confluence with Fibonacci levels
        best_fib_match = None
        min_distance = float('inf')
        
        for level_name, level_price in fib_levels.items():
            distance_to_fib = abs(current_trendline - level_price)
            distance_pct_fib = (distance_to_fib / level_price) * 100
            
            print(f"   {level_name}: ₹{level_price:.2f} (Distance: {distance_pct_fib:.1f}%)")
            
            if distance_pct_fib < min_distance:
                min_distance = distance_pct_fib
                best_fib_match = (level_name, level_price, distance_pct_fib)
        
        print(f"\n🎯 FIBONACCI CONFLUENCE:")
        if best_fib_match and best_fib_match[2] <= 5:
            print(f"   ✅ STRONG CONFLUENCE with {best_fib_match[0]} level")
            print(f"   📍 Trendline ₹{current_trendline:.2f} ≈ Fib {best_fib_match[0]} ₹{best_fib_match[1]:.2f}")
            print(f"   🎯 GOLDEN ENTRY ZONE CONFIRMED")
            confluence_score = 10 - int(best_fib_match[2])  # Higher score for closer match
        else:
            print(f"   ⚠️  WEAK CONFLUENCE - Closest: {best_fib_match[0]} ({best_fib_match[2]:.1f}% away)")
            confluence_score = max(1, 5 - int(best_fib_match[2]/2))
        
        print(f"   📊 Confluence Score: {confluence_score}/10")
    
    print("\n🎯 STEP 7: FUTURE TOUCH PREDICTIONS")
    print("-" * 60)
    
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
    
    print("🎯 STEP 8: RISK MANAGEMENT PARAMETERS")
    print("-" * 60)
    
    entry_price = current_trendline
    stop_loss = entry_price * 0.92  # 8% below entry (learned from requirements)
    target_1 = entry_price * 1.20   # 20% above entry
    target_2 = entry_price * 1.35   # 35% above entry (extended target)
    
    print(f"💰 TRADING PARAMETERS:")
    print(f"   Entry Zone: ₹{entry_price-50:.0f} - ₹{entry_price+50:.0f}")
    print(f"   Stop Loss: ₹{stop_loss:.2f} (-8%)")
    print(f"   Target 1: ₹{target_1:.2f} (+20%)")
    print(f"   Target 2: ₹{target_2:.2f} (+35%)")
    print(f"   Risk:Reward = 1:2.5 (Conservative)")
    
    print("\n🎯 STEP 9: FINAL ASSESSMENT & RECOMMENDATION")
    print("-" * 60)
    
    print("📋 TITAN TRENDLINE SCORECARD:")
    
    # Scoring system
    scores = []
    
    # Trendline strength
    if r_squared > 0.8:
        trendline_score = 10
        print(f"   ✅ Trendline Strength: EXCELLENT (R² = {r_squared:.3f}) - 10/10")
    elif r_squared > 0.6:
        trendline_score = 7
        print(f"   ✅ Trendline Strength: GOOD (R² = {r_squared:.3f}) - 7/10")
    else:
        trendline_score = 4
        print(f"   ⚠️  Trendline Strength: WEAK (R² = {r_squared:.3f}) - 4/10")
    scores.append(trendline_score)
    
    # Distance score
    if abs(distance_pct) <= 5:
        distance_score = 10
        print(f"   ✅ Distance to Trendline: PERFECT ({distance_pct:+.1f}%) - 10/10")
    elif abs(distance_pct) <= 10:
        distance_score = 7
        print(f"   ✅ Distance to Trendline: GOOD ({distance_pct:+.1f}%) - 7/10")
    else:
        distance_score = 3
        print(f"   ❌ Distance to Trendline: POOR ({distance_pct:+.1f}%) - 3/10")
    scores.append(distance_score)
    
    # Add confluence score
    scores.append(confluence_score)
    print(f"   📊 Fibonacci Confluence: {confluence_score}/10")
    
    # Touch count score
    touch_count_score = min(10, len(touch_points) * 2)
    scores.append(touch_count_score)
    print(f"   📍 Touch Point Count: {len(touch_points)} touches - {touch_count_score}/10")
    
    # Calculate final score
    final_score = sum(scores) / len(scores)
    
    print(f"\n🏆 FINAL SCORE: {final_score:.1f}/10")
    
    if final_score >= 8:
        recommendation = "🎯 STRONG BUY - High probability setup"
    elif final_score >= 6:
        recommendation = "✅ BUY - Good setup with caution"
    elif final_score >= 4:
        recommendation = "⚠️  HOLD - Wait for better setup"
    else:
        recommendation = "❌ AVOID - Poor setup quality"
    
    print(f"📈 RECOMMENDATION: {recommendation}")
    
    print(f"\n🎯 NEXT ACTIONS:")
    if signal == "BUY" or signal == "STRONG BUY":
        print(f"   1. Set buy alert at ₹{entry_price-30:.0f}")
        print(f"   2. Prepare position size (₹50,000 standard)")
        print(f"   3. Set stop loss at ₹{stop_loss:.0f}")
        print(f"   4. Monitor for Fibonacci confluence confirmation")
    else:
        print(f"   1. Add to watchlist")
        print(f"   2. Wait for pullback to ₹{entry_price:.0f} zone")
        print(f"   3. Monitor monthly for trendline approach")
        print(f"   4. Re-evaluate when price reaches entry zone")

if __name__ == "__main__":
    titan_trendline_masterclass()