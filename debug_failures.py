#!/usr/bin/env python3
"""Debug why trendlines fail for certain stocks"""

import yfinance as yf
import pandas as pd
import numpy as np
from scipy.signal import argrelextrema
from collections import Counter

# Load Nifty 500
nifty_df = pd.read_csv('ind_nifty500list.csv')
tickers = [s + '.NS' for s in nifty_df['Symbol'].tolist()]

# Test first 50 failed ones
failure_reasons = Counter()
sample_failures = []

print("🔍 DIAGNOSING TRENDLINE FAILURES...")
print("-" * 50)

for ticker in tickers[:100]:
    try:
        df = yf.download(ticker, period="8y", interval="1mo",
                         auto_adjust=True, progress=False)
        
        if df.empty:
            failure_reasons['Empty data'] += 1
            sample_failures.append((ticker, 'Empty data'))
            continue
            
        if len(df) < 24:
            failure_reasons[f'Insufficient data ({len(df)} months)'] += 1
            sample_failures.append((ticker, f'Only {len(df)} months'))
            continue

        df = df.dropna()
        df['Price_Idx'] = np.arange(len(df))
        low_prices = df['Low'].values.flatten()

        # Try all orders
        found_anchors = False
        for order in [10, 8, 6, 5]:
            touchbacks = argrelextrema(low_prices, np.less, order=order)
            if len(touchbacks[0]) >= 2:
                found_anchors = True
                break

        if not found_anchors:
            failure_reasons['No anchors found'] += 1
            sample_failures.append((ticker, 'No anchors'))
            continue

        # Fit trendline
        num = min(3, len(touchbacks[0]))
        anchor_indices = touchbacks[0][-num:]
        x = [int(df['Price_Idx'].iloc[i]) for i in anchor_indices]
        y = [float(low_prices[i]) for i in anchor_indices]
        slope, intercept = np.polyfit(x, y, 1)

        if slope <= 0:
            failure_reasons['Descending trendline'] += 1
            sample_failures.append((ticker, f'Slope={slope:.4f}'))
            continue

        # Count wick touches with 8% tolerance
        wick_count = 0
        for i in range(len(df)):
            midx = int(df['Price_Idx'].iloc[i])
            tl = (slope * midx) + intercept
            dist = abs((float(low_prices[i]) - tl) / tl) * 100
            if dist <= 8.0:  # Fixed: 8% not 5%
                wick_count += 1

        if wick_count < 3:
            failure_reasons[f'Insufficient wick touches ({wick_count})'] += 1
            sample_failures.append((ticker, f'Only {wick_count} wick touches'))
            continue

        # SUCCESS
        failure_reasons['SUCCESS'] += 1

    except Exception as e:
        failure_reasons[f'Exception: {str(e)[:50]}'] += 1
        sample_failures.append((ticker, str(e)[:50]))

print("\n📊 FAILURE REASONS:")
for reason, count in failure_reasons.most_common():
    print(f"   {reason}: {count}")

print(f"\n📋 SAMPLE FAILURES:")
for ticker, reason in sample_failures[:20]:
    if reason != 'SUCCESS':
        print(f"   {ticker.replace('.NS',''):15} → {reason}")
