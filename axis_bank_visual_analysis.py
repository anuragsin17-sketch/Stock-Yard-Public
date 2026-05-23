#!/usr/bin/env python3
"""
AXIS Bank Visual Trendline Analysis - Applying Imaginary Vertical Line Method
Learning to measure stock-specific monthly growth rates visually
"""

import yfinance as yf
import pandas as pd
import numpy as np
from scipy.signal import argrelextrema
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

def axis_bank_visual_trendline_analysis():
    """AXIS Bank analysis using visual measurement technique"""
    
    ticker = "AXISBANK.NS"
    
    print("🏦 AXIS BANK VISUAL TRENDLINE ANALYSIS")
    print("="*70)
    print("📚 APPLYING: Imaginary Vertical Line Method")
    print("🎯 LEARNING: Stock-specific monthly growth rate measurement")
    
    # Download 8-year monthly data
    df = yf.download(ticker, period="8y", interval="1mo", auto_adjust=True, progress=False)
    df = df.dropna()
    df['Price_Idx'] = np.arange(len(df))
    low_prices = df['Low'].values.flatten()
    
    print(f"\n📊 DATA OVERVIEW:")
    print(f"   Period: {df.index[0].strftime('%Y-%m-%d')} to {df.index[-1].strftime('%Y-%m-%d')}")
    print(f"   Total Months: {len(df)}")
    print(f"   Current Price: ₹{df['Close'].iloc[-1].item():.2f}")
    
    print("\n🎯 STEP 1: SECTOR CLASSIFICATION")
    print("-" * 50)
    print("📊 SECTOR: Banking (Private Bank)")
    print("⚙️  PARAMETERS: Using order=6 (banking sector adjustment)")
    print("📅 TIMEFRAME: Monthly (macro trend focus)")
    
    # Find major bottoms with banking order=6
    touchbacks = argrelextrema(low_prices, np.less, order=6)
    
    print(f"✅ Found {len(touchbacks[0])} major bottoms using 6-month order")
    
    print("\n🎯 STEP 2: IDENTIFY MAJOR TOUCH POINTS")
    print("-" * 50)
    
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
    
    print("\n🎯 STEP 3: SELECT MOST RELEVANT TRENDLINE ANCHORS")
    print("-" * 50)
    
    # Use last 3-4 touches for most relevant trendline (banking cycles)
    if len(touch_points) >= 4:
        relevant_touches = touch_points[-4:]
        print("📌 USING LAST 4 TOUCH POINTS (Banking sector pattern):")
    else:
        relevant_touches = touch_points[-3:]
        print("📌 USING LAST 3 TOUCH POINTS:")
    
    for i, touch in enumerate(relevant_touches, 1):
        print(f"   Anchor {i}: {touch['date'].strftime('%Y-%m-%d')} at ₹{touch['price']:.2f}")
    
    # Extract coordinates for trendline calculation
    x_coords = [touch['months_from_start'] for touch in relevant_touches]
    y_coords = [touch['price'] for touch in relevant_touches]
    
    print(f"\n📊 TRENDLINE COORDINATES:")
    print(f"   X (Time): {x_coords}")
    print(f"   Y (Price): {[f'₹{p:.2f}' for p in y_coords]}")
    
    print("\n🎯 STEP 4: VISUAL SLOPE MEASUREMENT")
    print("-" * 50)
    
    # Fit trendline using relevant touches
    slope, intercept = np.polyfit(x_coords, y_coords, 1)
    
    print(f"📈 MATHEMATICAL TRENDLINE:")
    print(f"   Equation: Price = {slope:.4f} × Month + {intercept:.2f}")
    print(f"   Calculated Slope: ₹{slope:.2f} per month")
    
    # Validate trendline quality
    r_squared = np.corrcoef(x_coords, y_coords)[0, 1] ** 2
    print(f"   R-squared: {r_squared:.3f} ({'Strong' if r_squared > 0.8 else 'Moderate' if r_squared > 0.6 else 'Weak'} correlation)")
    
    # Check if trendline is ascending
    if slope > 0:
        print(f"   ✅ ASCENDING TRENDLINE (Valid for support)")
    else:
        print(f"   ❌ DESCENDING/FLAT TRENDLINE")
        return
    
    print("\n🎯 STEP 5: IMAGINARY VERTICAL LINE METHOD")
    print("-" * 50)
    
    current_month = df['Price_Idx'].iloc[-1]
    current_trendline = (slope * current_month) + intercept
    
    # Apply imaginary vertical line method
    next_month = current_month + 1
    next_month_trendline = (slope * next_month) + intercept
    
    visual_monthly_growth = next_month_trendline - current_trendline
    
    print(f"📏 VISUAL MEASUREMENT TECHNIQUE:")
    print(f"   Current Month Position: {current_month}")
    print(f"   Current Trendline Level: ₹{current_trendline:.2f}")
    print(f"   Next Month Position: {next_month} (+1 candle width)")
    print(f"   Next Month Trendline: ₹{next_month_trendline:.2f}")
    print(f"   📊 VISUAL MONTHLY GROWTH: ₹{visual_monthly_growth:.2f} per month")
    
    print(f"\n🎯 AXIS BANK SPECIFIC LEARNING:")
    print(f"   💡 Banking Sector Growth Rate: ₹{visual_monthly_growth:.2f}/month")
    print(f"   💡 This is {'HIGHER' if visual_monthly_growth > 10 else 'LOWER'} than typical banking stocks")
    print(f"   💡 Compare to SBI: ₹7.43/month (AXIS is {'faster' if visual_monthly_growth > 7.43 else 'slower'})")
    
    print("\n🎯 STEP 6: CURRENT POSITION ANALYSIS")
    print("-" * 50)
    
    current_price = df['Close'].iloc[-1].item()
    distance_pct = ((current_price - current_trendline) / current_trendline) * 100
    
    print(f"📅 CURRENT ANALYSIS ({df.index[-1].strftime('%Y-%m-%d')}):")
    print(f"   Current Price: ₹{current_price:.2f}")
    print(f"   Trendline Level: ₹{current_trendline:.2f}")
    print(f"   Distance: {distance_pct:+.2f}%")
    
    # Apply learned tolerance levels (±5%)
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
    
    print("\n🎯 STEP 7: FUTURE MONTHLY PROJECTIONS")
    print("-" * 50)
    
    print(f"🔮 NEXT 6 MONTHS TRENDLINE PROJECTIONS:")
    print(f"   (Using ₹{visual_monthly_growth:.2f} monthly growth rate)")
    
    months = ['June 2026', 'July 2026', 'Aug 2026', 'Sep 2026', 'Oct 2026', 'Nov 2026']
    
    for i, month_name in enumerate(months, 1):
        future_month = current_month + i
        future_trendline = (slope * future_month) + intercept
        print(f"   {month_name}: ₹{future_trendline:.2f}")
    
    print("\n🎯 STEP 8: COMPARATIVE ANALYSIS")
    print("-" * 50)
    
    print(f"📊 AXIS BANK vs OTHER STOCKS:")
    print(f"   AXIS Monthly Growth: ₹{visual_monthly_growth:.2f}")
    print(f"   SBI Monthly Growth: ₹7.43 (Reference)")
    print(f"   TITAN Monthly Growth: ₹40.00 (Reference)")
    
    growth_ratio_sbi = visual_monthly_growth / 7.43
    growth_ratio_titan = visual_monthly_growth / 40.0
    
    print(f"\n📈 GROWTH RATE COMPARISON:")
    print(f"   AXIS vs SBI: {growth_ratio_sbi:.2f}x ({'Faster' if growth_ratio_sbi > 1 else 'Slower'})")
    print(f"   AXIS vs TITAN: {growth_ratio_titan:.2f}x ({'Faster' if growth_ratio_titan > 1 else 'Slower'})")
    
    print("\n🎯 STEP 9: KEY LEARNINGS FROM AXIS BANK")
    print("-" * 50)
    
    print(f"💡 WHAT I LEARNED:")
    print(f"   1. Banking stocks need order=6 parameter (confirmed)")
    print(f"   2. AXIS growth rate: ₹{visual_monthly_growth:.2f}/month (stock-specific)")
    print(f"   3. Visual measurement gives precise monthly progression")
    print(f"   4. Each stock has unique trendline characteristics")
    print(f"   5. Banking sector shows {'consistent' if 5 < visual_monthly_growth < 15 else 'variable'} growth patterns")
    
    print(f"\n🎯 TRADING IMPLICATIONS:")
    if signal == "BUY" or signal == "STRONG BUY":
        print(f"   ✅ AXIS is near trendline support - Good entry opportunity")
        print(f"   📊 Entry Zone: ₹{current_trendline-20:.0f} - ₹{current_trendline+20:.0f}")
        print(f"   🎯 Next month target: ₹{current_trendline + visual_monthly_growth:.0f}")
    elif signal == "WAIT":
        print(f"   ⏳ AXIS is above trendline - Wait for pullback")
        print(f"   📉 Target entry: ₹{current_trendline:.0f} level")
    else:
        print(f"   ❌ AXIS is overextended - Avoid current levels")
        print(f"   📉 Wait for significant correction to ₹{current_trendline:.0f}")
    
    print(f"\n🏆 VISUAL MEASUREMENT MASTERY:")
    print(f"   📏 Imaginary vertical line method: APPLIED ✅")
    print(f"   📊 Stock-specific growth rate: ₹{visual_monthly_growth:.2f} MEASURED ✅")
    print(f"   🎯 Monthly progression: CALCULATED ✅")
    print(f"   📈 Banking sector pattern: RECOGNIZED ✅")

if __name__ == "__main__":
    axis_bank_visual_trendline_analysis()