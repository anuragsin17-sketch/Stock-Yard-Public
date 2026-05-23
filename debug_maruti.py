import yfinance as yf
import numpy as np
from scipy.signal import argrelextrema

df = yf.download('MARUTI.NS', period='8y', interval='1mo', auto_adjust=True, progress=False)
df = df.dropna()
df['Price_Idx'] = np.arange(len(df))
low_prices = df['Low'].values.flatten()

print(f"Total months: {len(df)}")

# Try different orders
for order in [5, 6, 8, 10, 12]:
    touchbacks = argrelextrema(low_prices, np.less, order=order)
    print(f"\nOrder={order}: Found {len(touchbacks[0])} major bottoms")
    for idx in touchbacks[0]:
        print(f"  {df.index[idx].strftime('%Y-%m')} @ Rs{low_prices[idx]:.0f}")

# Use order=5 to get more bottoms
touchbacks = argrelextrema(low_prices, np.less, order=5)
if len(touchbacks[0]) >= 2:
    num = min(3, len(touchbacks[0]))
    x = [df['Price_Idx'].iloc[i] for i in touchbacks[0][-num:]]
    y = [low_prices[i] for i in touchbacks[0][-num:]]
    slope, intercept = np.polyfit(x, y, 1)
    print(f"\nSlope: {slope:.2f}, Ascending: {slope > 0}")
    
    # Count wick touches
    touches = []
    for i in range(len(df)):
        midx = df['Price_Idx'].iloc[i]
        tl = (slope * midx) + intercept
        dist = abs((low_prices[i] - tl) / tl) * 100
        if dist <= 5.0:
            touches.append((df.index[i].strftime('%Y-%m'), low_prices[i], dist))
    
    print(f"Total wick touches (order=5): {len(touches)}")
    for t in touches:
        print(f"  {t[0]} @ Rs{t[1]:.0f} (dist: {t[2]:.1f}%)")
