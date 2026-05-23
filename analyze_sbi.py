#!/usr/bin/env python3
"""
Deep analysis of SBI using trendline logic
"""

from editable_trigger_engine import EditableTriggerEngine
import yfinance as yf
import pandas as pd
import numpy as np
from scipy.signal import argrelextrema
from datetime import datetime, timedelta

def analyze_sbi_deep():
    """Comprehensive SBI analysis using trendline methodology"""
    
    ticker = "SBIN.NS"
    
    print("🏦 SBI (STATE BANK OF INDIA) - TRENDLINE ANALYSIS")
    print("="*80)
    
    # 1. Download and examine data
    print("📊 DATA ANALYSIS:")
    print("-" * 40)
    
    df = yf.download(ticker, period="8y", interval="1mo", auto_adjust=True, progress=False)
    
    if df.empty:
        print("❌ No data available")
        return
    
    print(f"✅ Data Range: {df.index[0].strftime('%Y-%m-%d')} to {df.index[-1].strftime('%Y-%m-%d')}")
    print(f"✅ Total Months: {len(df)}")
    print(f"✅ Current Price: ₹{df['Close'].iloc[-1].item():.2f}")
    print(f"✅ 8-Year Range: ₹{df['Low'].min().item():.2f} - ₹{df['High'].max().item():.2f}")
    
    # 2. Trendline Analysis
    print(f"\n🔍 TRENDLINE DETECTION:")
    print("-" * 40)
    
    df = df.dropna()
    df['Price_Idx'] = np.arange(len(df))
    low_prices = df['Low'].values.flatten()
    
    # Find major bottoms
    touchbacks = argrelextrema(low_prices, np.less, order=12)
    
    print(f"✅ Major Bottoms Found: {len(touchbacks[0])}")
    
    if len(touchbacks[0]) >= 3:
        print("✅ Sufficient touches for trendline analysis")
        
        # Show touch points
        print(f"\n📍 MAJOR TOUCH POINTS:")
        for i, touch_idx in enumerate(touchbacks[0]):
            touch_date = df.index[touch_idx]
            touch_price = low_prices[touch_idx]
            print(f"   Touch {i+1}: {touch_date.strftime('%Y-%m-%d')} at ₹{touch_price:.2f}")
        
        # Fit trendline using last 3-4 touches
        num_touches = min(4, len(touchbacks[0]))
        x_anchors = df['Price_Idx'].iloc[touchbacks[0][-num_touches:]].values
        y_anchors = low_prices[touchbacks[0][-num_touches:]]
        slope, intercept = np.polyfit(x_anchors, y_anchors, 1)
        
        print(f"\n📈 TRENDLINE MATHEMATICS:")
        print(f"   Slope: {slope:.4f} (₹{slope:.2f} per month)")
        print(f"   Intercept: {intercept:.2f}")
        print(f"   Direction: {'✅ Ascending' if slope > 0 else '❌ Descending'}")
        
        if slope > 0:
            # Calculate current trendline projection
            current_bar_idx = df['Price_Idx'].iloc[-1]
            current_close = df['Close'].iloc[-1].item()
            projected_trendline = (slope * current_bar_idx) + intercept
            
            print(f"\n🎯 CURRENT SITUATION:")
            print(f"   Current Price: ₹{current_close:.2f}")
            print(f"   Trendline Level: ₹{projected_trendline:.2f}")
            
            distance_pct = ((current_close - projected_trendline) / projected_trendline) * 100
            print(f"   Distance: {distance_pct:+.2f}%")
            
            if abs(distance_pct) <= 5.0:
                print(f"   Status: ✅ NEAR TRENDLINE (within ±5%)")
            elif distance_pct > 5.0:
                print(f"   Status: 📈 ABOVE TRENDLINE ({distance_pct:.1f}% above)")
            else:
                print(f"   Status: 📉 BELOW TRENDLINE ({abs(distance_pct):.1f}% below)")
            
            # Wave and Fibonacci Analysis
            print(f"\n🌊 WAVE & FIBONACCI ANALYSIS:")
            print("-" * 40)
            
            last_touch_idx = touchbacks[0][-1]
            last_touch_price = low_prices[last_touch_idx]
            
            # Find swing high after last touch
            data_after_touch = df.iloc[last_touch_idx:]
            swing_high = data_after_touch['High'].max().item()
            
            wave_range = swing_high - last_touch_price
            
            print(f"   Last Touch: ₹{last_touch_price:.2f}")
            print(f"   Swing High: ₹{swing_high:.2f}")
            print(f"   Wave Range: ₹{wave_range:.2f}")
            
            # Calculate Fibonacci levels
            fib_levels = {
                "23.6%": swing_high - (wave_range * 0.236),
                "38.2%": swing_high - (wave_range * 0.382),
                "50.0%": swing_high - (wave_range * 0.500),
                "61.8%": swing_high - (wave_range * 0.618),
                "78.6%": swing_high - (wave_range * 0.786),
                "100.0%": last_touch_price
            }
            
            print(f"\n📊 FIBONACCI RETRACEMENT LEVELS:")
            for level, price in fib_levels.items():
                distance_to_current = abs(current_close - price)
                pct_from_current = (distance_to_current / current_close) * 100
                
                # Check if current price is near this level
                if pct_from_current <= 2.0:
                    status = "🎯 CURRENT ZONE"
                elif current_close > price:
                    status = "⬆️ ABOVE"
                else:
                    status = "⬇️ BELOW"
                
                print(f"   {level:>6s}: ₹{price:>7.2f} | {status}")
            
            # Trendline vs Fibonacci confluence
            print(f"\n🎯 TRENDLINE-FIBONACCI CONFLUENCE:")
            print("-" * 40)
            
            closest_fib = None
            min_distance = float('inf')
            
            for level, fib_price in fib_levels.items():
                distance = abs(projected_trendline - fib_price)
                distance_pct = (distance / fib_price) * 100
                
                if distance_pct < min_distance:
                    min_distance = distance_pct
                    closest_fib = level
            
            print(f"   Trendline Level: ₹{projected_trendline:.2f}")
            print(f"   Closest Fib Level: {closest_fib} (₹{fib_levels[closest_fib]:.2f})")
            print(f"   Confluence Distance: {min_distance:.2f}%")
            
            if min_distance <= 1.0:
                confluence_quality = "🏆 PERFECT CONFLUENCE"
            elif min_distance <= 2.0:
                confluence_quality = "✅ GOOD CONFLUENCE"
            elif min_distance <= 5.0:
                confluence_quality = "⚠️ MODERATE CONFLUENCE"
            else:
                confluence_quality = "❌ WEAK CONFLUENCE"
            
            print(f"   Quality: {confluence_quality}")
            
            # Future Prediction
            print(f"\n🔮 FUTURE TRENDLINE PROJECTIONS:")
            print("-" * 40)
            
            # Calculate touch intervals
            if len(touchbacks[0]) >= 3:
                intervals = []
                for i in range(1, len(touchbacks[0])):
                    interval = touchbacks[0][i] - touchbacks[0][i-1]
                    intervals.append(interval)
                
                avg_interval = sum(intervals) / len(intervals)
                
                print(f"   Historical Touch Intervals: {intervals}")
                print(f"   Average Interval: {avg_interval:.1f} months")
                
                # Predict next touch
                last_touch_idx = touchbacks[0][-1]
                predicted_next_idx = last_touch_idx + avg_interval
                predicted_price = (slope * predicted_next_idx) + intercept
                
                months_ahead = predicted_next_idx - current_bar_idx
                predicted_date = datetime.now() + timedelta(days=int(months_ahead * 30))
                
                print(f"\n   📅 NEXT PREDICTED TOUCH:")
                print(f"      Date: {predicted_date.strftime('%Y-%m-%d')}")
                print(f"      Price: ₹{predicted_price:.2f}")
                print(f"      Months Away: {months_ahead:.1f}")
        
        else:
            print("❌ Trendline is descending - not suitable for our strategy")
    
    else:
        print(f"❌ Insufficient touches ({len(touchbacks[0])}) - need minimum 3")
    
    # 3. Test with our algorithm
    print(f"\n🤖 ALGORITHM TEST:")
    print("-" * 40)
    
    engine = EditableTriggerEngine(touch_tolerance=8.0)  # Wider tolerance for analysis
    result = engine.process_ticker_geometry(ticker)
    
    if result:
        current = result['currentSignal']
        print(f"✅ ALGORITHM SIGNAL DETECTED:")
        print(f"   Current Price: ₹{current['currentPrice']}")
        print(f"   Trigger Price: ₹{current['triggerPrice']}")
        print(f"   Distance: {current['distanceRemaining']}%")
        print(f"   Confluence Score: {current['confluenceScore']}/10")
        print(f"   Fibonacci Level: {current['fibLevelMatch']}")
        print(f"   Pattern Zone: {current['patternZone']}")
        print(f"   Alert Active: {'Yes' if current['notificationTrigger'] else 'No'}")
        
        if 'futureSignal' in result and result['futureSignal']['isActive']:
            future = result['futureSignal']
            print(f"\n🔮 FUTURE PREDICTION:")
            print(f"   Next Touch: {future['nextTouchDate']}")
            print(f"   Predicted Price: ₹{future['predictedPrice']}")
            print(f"   Confidence: {future['confidenceScore']}%")
    else:
        print("❌ No algorithm signal detected")
        print("   Possible reasons:")
        print("   - Insufficient historical touches")
        print("   - Not within tolerance range")
        print("   - Fibonacci level too shallow")
        print("   - Trendline not ascending")
    
    # 4. Learning Summary
    print(f"\n🎓 LEARNING INSIGHTS:")
    print("="*80)
    
    if len(touchbacks[0]) >= 3 and slope > 0:
        print("✅ SBI shows a valid ascending trendline pattern")
        print(f"✅ Trendline grows at ₹{slope:.2f} per month")
        print(f"✅ Current price is {distance_pct:+.1f}% from trendline")
        
        if abs(distance_pct) <= 5.0:
            print("🎯 SBI is currently in the trendline interaction zone")
            print("📈 This could be a potential entry area if other conditions align")
        
        if min_distance <= 2.0:
            print(f"🎯 Good Fibonacci confluence with {closest_fib} level")
        
        print(f"📅 Next trendline touch expected around {predicted_date.strftime('%Y-%m')}")
        
    else:
        print("❌ SBI doesn't meet our trendline criteria currently")
        print("📚 This teaches us that not all stocks have tradeable trendline patterns")
    
    print(f"\n💡 KEY TAKEAWAYS:")
    print("- Banking stocks often have longer cycles (18+ months)")
    print("- Government policy impacts can disrupt technical patterns")
    print("- Large cap stocks may have different Fibonacci preferences")
    print("- Always validate algorithm results with manual chart analysis")

if __name__ == "__main__":
    analyze_sbi_deep()