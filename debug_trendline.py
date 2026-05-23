#!/usr/bin/env python3
"""
Debug version of trendline logic to see where filtering happens
"""

import yfinance as yf
import pandas as pd
import numpy as np
from scipy.signal import argrelextrema

def debug_trendline_logic(ticker):
    """Debug version with detailed logging"""
    
    print(f"\n🔍 DEBUGGING {ticker}")
    print("="*50)
    
    try:
        # 1. Fetch data
        print("1. Fetching 8-year monthly data...")
        df = yf.download(ticker, period="8y", interval="1mo", auto_adjust=True, progress=False)
        
        if df.empty:
            print("❌ No data downloaded")
            return
        
        print(f"✅ Downloaded {len(df)} months of data")
        
        if len(df) < 24:
            print("❌ Insufficient data (need 24+ months)")
            return
        
        # 2. Process data
        df = df.dropna()
        df['Price_Idx'] = np.arange(len(df))
        low_prices = df['Low'].values.flatten()
        
        print(f"✅ Processed data: {len(df)} valid months")
        
        # 3. Find touchbacks
        print("2. Finding major bottoms...")
        touchbacks = argrelextrema(low_prices, np.less, order=12)
        
        print(f"✅ Found {len(touchbacks[0])} major bottoms")
        
        if len(touchbacks[0]) < 3:
            print("❌ Need minimum 3 touches for trendline")
            return
        
        # 4. Fit trendline
        print("3. Fitting trendline...")
        num_touches = min(4, len(touchbacks[0]))
        x_anchors = df['Price_Idx'].iloc[touchbacks[0][-num_touches:]].values
        y_anchors = low_prices[touchbacks[0][-num_touches:]]
        slope, intercept = np.polyfit(x_anchors, y_anchors, 1)
        
        print(f"✅ Trendline: slope={slope:.4f}, intercept={intercept:.2f}")
        
        # 5. Check ascending
        if slope <= 0:
            print("❌ Trendline not ascending (slope <= 0)")
            return
        
        print("✅ Trendline is ascending")
        
        # 6. Get swing high
        last_touch_idx = touchbacks[0][-1]
        last_touch_price = float(low_prices[last_touch_idx])
        
        print(f"Debug: last_touch_idx={last_touch_idx}, last_touch_price={last_touch_price}")
        
        # Simple swing high calculation
        data_after_touch = df.iloc[last_touch_idx:]
        if len(data_after_touch) > 0:
            swing_high_after_touch = data_after_touch['High'].max()
            if hasattr(swing_high_after_touch, 'item'):
                swing_high_after_touch = swing_high_after_touch.item()
            else:
                swing_high_after_touch = float(swing_high_after_touch)
        else:
            swing_high_after_touch = df['High'].max()
            if hasattr(swing_high_after_touch, 'item'):
                swing_high_after_touch = swing_high_after_touch.item()
            else:
                swing_high_after_touch = float(swing_high_after_touch)
        
        print(f"✅ Last touch: ₹{last_touch_price:.2f}, Swing high: ₹{swing_high_after_touch:.2f}")
        
        # 7. Calculate Fibonacci
        wave_base_origin = float(last_touch_price)
        wave_peak_ceiling = swing_high_after_touch
        total_wave_range = wave_peak_ceiling - wave_base_origin
        
        if total_wave_range <= 0:
            print("❌ Invalid wave range (swing high <= last touch)")
            return
        
        print(f"✅ Wave range: ₹{total_wave_range:.2f}")
        
        # 8. Project trendline
        current_bar_idx = int(df['Price_Idx'].iloc[-1])
        current_close_raw = df['Close'].iloc[-1]
        if hasattr(current_close_raw, 'item'):
            current_close = current_close_raw.item()
        else:
            current_close = float(current_close_raw)
        expected_trendline_trigger = (slope * current_bar_idx) + intercept
        
        print(f"✅ Current price: ₹{current_close:.2f}, Trendline: ₹{expected_trendline_trigger:.2f}")
        
        # 9. Check Fibonacci zone
        upcoming_line_fib_pct = ((wave_peak_ceiling - expected_trendline_trigger) / total_wave_range) * 100
        
        print(f"✅ Fibonacci level: {upcoming_line_fib_pct:.2f}%")
        
        if upcoming_line_fib_pct < 38.2:
            print("❌ Fibonacci level too shallow (< 38.2%)")
            return
        
        print("✅ Fibonacci level acceptable (>= 38.2%)")
        
        # 10. Check distance to trendline
        pct_distance_to_line = ((current_close - expected_trendline_trigger) / expected_trendline_trigger) * 100
        
        print(f"✅ Distance to trendline: {pct_distance_to_line:.2f}%")
        
        touch_tolerance = 5.0
        if not (-touch_tolerance <= pct_distance_to_line <= touch_tolerance):
            print(f"❌ Not within ±{touch_tolerance}% of trendline")
            return
        
        print("✅ Within touch tolerance - SIGNAL FOUND!")
        
        # Show final result
        is_alert_active = abs(pct_distance_to_line) <= 1.0
        
        print(f"\n🎯 FINAL SIGNAL:")
        print(f"   Ticker: {ticker.replace('.NS', '')}")
        print(f"   Current: ₹{current_close:.2f}")
        print(f"   Trigger: ₹{expected_trendline_trigger:.2f}")
        print(f"   Distance: {abs(pct_distance_to_line):.2f}%")
        print(f"   Fib Level: {upcoming_line_fib_pct:.2f}%")
        print(f"   Alert: {is_alert_active}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    # Test a few stocks
    test_stocks = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS", 
                   "HINDUNILVR.NS", "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "KOTAKBANK.NS",
                   "LT.NS", "AXISBANK.NS", "ASIANPAINT.NS", "MARUTI.NS", "SUNPHARMA.NS",
                   "TITAN.NS", "BAJFINANCE.NS", "ULTRACEMCO.NS", "NESTLEIND.NS", "WIPRO.NS",
                   "ONGC.NS", "NTPC.NS", "POWERGRID.NS", "TATASTEEL.NS", "ADANIENT.NS"]
    
    for stock in test_stocks:
        debug_trendline_logic(stock)
        print("\n" + "="*70 + "\n")