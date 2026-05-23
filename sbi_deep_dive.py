#!/usr/bin/env python3
"""
Deep dive into SBI's pattern - why no trendline signals?
"""

import yfinance as yf
import pandas as pd
import numpy as np
from scipy.signal import argrelextrema
import matplotlib.pyplot as plt

def sbi_pattern_investigation():
    """Investigate SBI's price pattern in detail"""
    
    ticker = "SBIN.NS"
    
    print("🔍 SBI PATTERN INVESTIGATION")
    print("="*60)
    
    # Download data with different timeframes
    df_8y = yf.download(ticker, period="8y", interval="1mo", auto_adjust=True, progress=False)
    df_15y = yf.download(ticker, period="15y", interval="1mo", auto_adjust=True, progress=False)
    
    print(f"📊 DATA COMPARISON:")
    print(f"   8-year data: {len(df_8y)} months")
    print(f"   15-year data: {len(df_15y)} months")
    
    # Test different order parameters for bottom detection
    print(f"\n🔍 BOTTOM DETECTION WITH DIFFERENT PARAMETERS:")
    print("-" * 50)
    
    for period, df in [("8-year", df_8y), ("15-year", df_15y)]:
        if df.empty:
            continue
            
        df = df.dropna()
        df['Price_Idx'] = np.arange(len(df))
        low_prices = df['Low'].values.flatten()
        
        print(f"\n{period.upper()} ANALYSIS:")
        
        # Try different order parameters
        for order in [6, 9, 12, 15, 18]:
            touchbacks = argrelextrema(low_prices, np.less, order=order)
            print(f"   Order {order:2d}: {len(touchbacks[0])} major bottoms found")
            
            if len(touchbacks[0]) >= 3:
                print(f"            ✅ Sufficient for trendline (≥3)")
                
                # Show the touch points
                print(f"            Touch points:")
                for i, touch_idx in enumerate(touchbacks[0]):
                    touch_date = df.index[touch_idx]
                    touch_price = low_prices[touch_idx]
                    print(f"              {i+1}. {touch_date.strftime('%Y-%m')} at ₹{touch_price:.2f}")
                
                # Test trendline
                num_touches = min(4, len(touchbacks[0]))
                x_anchors = df['Price_Idx'].iloc[touchbacks[0][-num_touches:]].values
                y_anchors = low_prices[touchbacks[0][-num_touches:]]
                slope, intercept = np.polyfit(x_anchors, y_anchors, 1)
                
                print(f"            Trendline slope: {slope:.4f} ({'Ascending' if slope > 0 else 'Descending'})")
                
                if slope > 0:
                    # Calculate current position
                    current_bar_idx = df['Price_Idx'].iloc[-1]
                    current_close = df['Close'].iloc[-1].item()
                    projected_trendline = (slope * current_bar_idx) + intercept
                    distance_pct = ((current_close - projected_trendline) / projected_trendline) * 100
                    
                    print(f"            Current vs Trendline: {distance_pct:+.1f}%")
                    
                    if abs(distance_pct) <= 10.0:
                        print(f"            🎯 POTENTIAL SIGNAL (within ±10%)")
                break
    
    # Analyze SBI's unique characteristics
    print(f"\n📈 SBI PRICE BEHAVIOR ANALYSIS:")
    print("-" * 50)
    
    df = df_15y if not df_15y.empty else df_8y
    df = df.dropna()
    
    # Calculate volatility
    df['Returns'] = df['Close'].pct_change()
    volatility = df['Returns'].std() * np.sqrt(12) * 100  # Annualized
    
    print(f"   Current Price: ₹{df['Close'].iloc[-1].item():.2f}")
    print(f"   All-time High: ₹{df['High'].max().item():.2f}")
    print(f"   All-time Low: ₹{df['Low'].min().item():.2f}")
    print(f"   Price Range: {(df['High'].max().item() / df['Low'].min().item()):.1f}x")
    print(f"   Annualized Volatility: {volatility:.1f}%")
    
    # Check for major events/disruptions
    print(f"\n📅 MAJOR PRICE MOVEMENTS:")
    print("-" * 50)
    
    # Find biggest monthly moves
    df['Monthly_Change'] = df['Close'].pct_change() * 100
    biggest_moves = df.nlargest(5, 'Monthly_Change')[['Monthly_Change']].copy()
    biggest_drops = df.nsmallest(5, 'Monthly_Change')[['Monthly_Change']].copy()
    
    print("   Biggest Monthly Gains:")
    for date, row in biggest_moves.iterrows():
        print(f"      {date.strftime('%Y-%m')}: +{row['Monthly_Change'].item():.1f}%")
    
    print("   Biggest Monthly Drops:")
    for date, row in biggest_drops.iterrows():
        print(f"      {date.strftime('%Y-%m')}: {row['Monthly_Change'].item():.1f}%")
    
    # Banking sector specific analysis
    print(f"\n🏦 BANKING SECTOR INSIGHTS:")
    print("-" * 50)
    
    # Check if SBI follows different patterns than other stocks
    recent_high = df['High'].rolling(window=12).max().iloc[-1]
    recent_low = df['Low'].rolling(window=12).min().iloc[-1]
    current_price = df['Close'].iloc[-1].item()
    
    position_in_range = (current_price - recent_low) / (recent_high - recent_low) * 100
    
    print(f"   12-month High: ₹{recent_high:.2f}")
    print(f"   12-month Low: ₹{recent_low:.2f}")
    print(f"   Current Position: {position_in_range:.1f}% of 12-month range")
    
    # Check for consolidation patterns
    recent_data = df.tail(24)  # Last 2 years
    price_stability = recent_data['Close'].std() / recent_data['Close'].mean() * 100
    
    print(f"   Recent Price Stability: {price_stability:.1f}% (lower = more stable)")
    
    if price_stability < 20:
        print("   📊 SBI shows consolidation pattern (low volatility)")
    elif price_stability > 40:
        print("   📊 SBI shows high volatility pattern")
    else:
        print("   📊 SBI shows moderate volatility pattern")
    
    # Final assessment
    print(f"\n🎓 SBI PATTERN ASSESSMENT:")
    print("="*60)
    
    print("📚 WHAT I LEARNED ABOUT SBI:")
    print("1. Banking stocks have different technical behavior")
    print("2. Government policy impacts create irregular patterns")
    print("3. SBI may need different detection parameters")
    print("4. Large-cap banking stocks are less predictable with trendlines")
    print("5. Sector rotation affects banking stock patterns")
    
    print(f"\n💡 ALGORITHM IMPROVEMENTS NEEDED:")
    print("- Adjust order parameter for banking stocks (try 6-9 instead of 12)")
    print("- Consider sector-specific Fibonacci preferences")
    print("- Account for policy event disruptions")
    print("- Use different timeframes for different market caps")
    print("- Add sector classification to improve detection")
    
    print(f"\n🎯 TRADING IMPLICATIONS:")
    if position_in_range > 70:
        print("- SBI near recent highs - wait for pullback")
    elif position_in_range < 30:
        print("- SBI near recent lows - potential accumulation zone")
    else:
        print("- SBI in middle range - monitor for breakout/breakdown")

if __name__ == "__main__":
    sbi_pattern_investigation()