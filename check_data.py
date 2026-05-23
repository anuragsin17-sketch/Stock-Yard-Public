#!/usr/bin/env python3
"""
Check current data for ASIANPAINT
"""

import yfinance as yf
import pandas as pd
import numpy as np
from scipy.signal import argrelextrema

def check_asianpaint_data():
    """Check what's happening with ASIANPAINT data"""
    
    ticker = "ASIANPAINT.NS"
    print(f"Checking {ticker}...")
    
    # Download data
    df = yf.download(ticker, period="8y", interval="1mo", auto_adjust=True, progress=False)
    
    if df.empty:
        print("❌ No data downloaded")
        return
    
    print(f"✅ Downloaded {len(df)} months of data")
    print(f"Latest price: ₹{df['Close'].iloc[-1].item():.2f}")
    print(f"Date range: {df.index[0].strftime('%Y-%m-%d')} to {df.index[-1].strftime('%Y-%m-%d')}")
    
    # Check for bottoms
    df = df.dropna()
    df['Price_Idx'] = np.arange(len(df))
    low_prices = df['Low'].values.flatten()
    
    touchbacks = argrelextrema(low_prices, np.less, order=12)
    print(f"Found {len(touchbacks[0])} major bottoms")
    
    if len(touchbacks[0]) >= 3:
        print("✅ Sufficient touches for trendline")
        
        # Fit trendline
        num_touches = min(4, len(touchbacks[0]))
        x_anchors = df['Price_Idx'].iloc[touchbacks[0][-num_touches:]].values
        y_anchors = low_prices[touchbacks[0][-num_touches:]]
        slope, intercept = np.polyfit(x_anchors, y_anchors, 1)
        
        print(f"Trendline: slope={slope:.4f}, intercept={intercept:.2f}")
        
        if slope > 0:
            print("✅ Ascending trendline")
            
            # Project to current
            current_bar_idx = df['Price_Idx'].iloc[-1]
            current_close = df['Close'].iloc[-1].item()
            expected_trendline_trigger = (slope * current_bar_idx) + intercept
            
            print(f"Current price: ₹{current_close:.2f}")
            print(f"Trendline price: ₹{expected_trendline_trigger:.2f}")
            
            pct_distance = ((current_close - expected_trendline_trigger) / expected_trendline_trigger) * 100
            print(f"Distance: {pct_distance:.2f}%")
            
            if abs(pct_distance) <= 5.0:
                print("✅ Within ±5% tolerance - SHOULD BE A SIGNAL!")
            else:
                print("❌ Outside ±5% tolerance")
        else:
            print("❌ Not ascending")
    else:
        print("❌ Insufficient touches")

if __name__ == "__main__":
    check_asianpaint_data()