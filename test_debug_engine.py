#!/usr/bin/env python3
"""
Debug the geometric engine step by step
"""

import yfinance as yf
import pandas as pd
import numpy as np
from scipy.signal import argrelextrema

def debug_geometric_engine(ticker):
    """Debug version of the geometric engine"""
    
    print(f"🔍 DEBUGGING {ticker}")
    print("="*50)
    
    try:
        # 1. Fetch data
        df = yf.download(ticker, period="8y", interval="1mo", auto_adjust=True, progress=False)
        if df.empty or len(df) < 24:
            print("❌ Insufficient data")
            return None
        
        print(f"✅ Data: {len(df)} months")
        
        df = df.dropna()
        df['Price_Idx'] = np.arange(len(df))
        low_prices = df['Low'].values.flatten()
        
        # 2. Find touchbacks
        touchbacks = argrelextrema(low_prices, np.less, order=12)
        if len(touchbacks[0]) < 3:
            print(f"❌ Only {len(touchbacks[0])} touches, need 3+")
            return None
        
        print(f"✅ Touches: {len(touchbacks[0])}")
        
        # 3. Fit trendline
        num_touches = min(4, len(touchbacks[0]))
        x_anchors = df['Price_Idx'].iloc[touchbacks[0][-num_touches:]].values
        y_anchors = low_prices[touchbacks[0][-num_touches:]]
        slope, intercept = np.polyfit(x_anchors, y_anchors, 1)
        
        if slope <= 0:
            print(f"❌ Slope not ascending: {slope}")
            return None
        
        print(f"✅ Trendline: slope={slope:.4f}")
        
        # 4. Calculate wave
        last_touch_idx = touchbacks[0][-1]
        last_touch_price = low_prices[last_touch_idx]
        
        # Simple swing high calculation
        data_after_touch = df.iloc[last_touch_idx:]
        swing_high_after_touch = data_after_touch['High'].max().item()
        
        wave_base_origin = last_touch_price
        wave_peak_ceiling = swing_high_after_touch
        total_wave_range = wave_peak_ceiling - wave_base_origin
        
        if total_wave_range <= 0:
            print(f"❌ Invalid wave range: {total_wave_range}")
            return None
        
        print(f"✅ Wave: {wave_base_origin:.2f} → {wave_peak_ceiling:.2f} (range: {total_wave_range:.2f})")
        
        # 5. Project trendline
        current_bar_idx = df['Price_Idx'].iloc[-1]
        current_close = df['Close'].iloc[-1].item()
        expected_trendline_trigger = (slope * current_bar_idx) + intercept
        
        print(f"✅ Current: ₹{current_close:.2f}, Trendline: ₹{expected_trendline_trigger:.2f}")
        
        # 6. Check Fibonacci
        upcoming_line_fib_pct = ((wave_peak_ceiling - expected_trendline_trigger) / total_wave_range) * 100
        
        print(f"✅ Fibonacci level: {upcoming_line_fib_pct:.2f}%")
        
        if upcoming_line_fib_pct < 38.2:
            print(f"❌ Fibonacci too shallow: {upcoming_line_fib_pct:.2f}% < 38.2%")
            return None
        
        print(f"✅ Fibonacci acceptable: {upcoming_line_fib_pct:.2f}% >= 38.2%")
        
        # 7. Check distance
        pct_distance_to_line = ((current_close - expected_trendline_trigger) / expected_trendline_trigger) * 100
        
        print(f"✅ Distance: {pct_distance_to_line:.2f}%")
        
        touch_tolerance = 5.0
        if not (-touch_tolerance <= pct_distance_to_line <= touch_tolerance):
            print(f"❌ Outside tolerance: {pct_distance_to_line:.2f}% not in ±{touch_tolerance}%")
            return None
        
        print(f"✅ Within tolerance: {pct_distance_to_line:.2f}% in ±{touch_tolerance}%")
        
        print("🎯 SIGNAL SHOULD BE FOUND!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    debug_geometric_engine("ASIANPAINT.NS")