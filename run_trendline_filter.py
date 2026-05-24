#!/usr/bin/env python3
"""
Run all 500 stocks through trendline filter
Show current signals: CRITICAL (±1%), WATCHLIST (±2%), APPROACHING (2-10%)
"""

import yfinance as yf
import pandas as pd
import numpy as np
from scipy.signal import argrelextrema
from datetime import datetime
import json
import os

def get_sector_order(ticker):
    banking = ['SBIN', 'HDFCBANK', 'ICICIBANK', 'AXISBANK', 'KOTAKBANK',
               'INDUSINDBK', 'FEDERALBNK', 'BANDHANBNK', 'RBLBANK', 'IDFCFIRSTB']
    return 6 if any(b in ticker.upper() for b in banking) else 10

def build_trendline(ticker):
    """Monthly 8yr PRIMARY, Weekly 5yr FALLBACK"""
    def from_df(df, timeframe):
        if df.empty or len(df) < 18:
            return None
        df = df.dropna()
        df['Price_Idx'] = np.arange(len(df))
        low_prices = df['Low'].values.flatten()

        order = get_sector_order(ticker)
        if timeframe == 'weekly':
            order = max(3, order // 2)

        touchbacks = argrelextrema(low_prices, np.less, order=order)
        for fb in [8, 6, 5, 4, 3]:
            if len(touchbacks[0]) >= 2:
                break
            touchbacks = argrelextrema(low_prices, np.less, order=fb)

        if len(touchbacks[0]) < 2:
            return None

        num = min(3, len(touchbacks[0]))
        anchors = touchbacks[0][-num:]
        x = [int(df['Price_Idx'].iloc[i]) for i in anchors]
        y = [float(low_prices[i]) for i in anchors]
        slope, intercept = np.polyfit(x, y, 1)

        if slope <= 0:
            return None

        wicks = sum(1 for i in range(len(df))
                    if abs((float(low_prices[i]) - ((slope * int(df['Price_Idx'].iloc[i])) + intercept)) /
                           ((slope * int(df['Price_Idx'].iloc[i])) + intercept) * 100) <= 8.0)

        if wicks < 3:
            return None

        # Fibonacci
        last_idx = int(anchors[-1])
        last_price = float(low_prices[last_idx])
        swing_high = float(df.iloc[last_idx:]['High'].max())
        fib_range = swing_high - last_price

        fib_levels = {}
        if fib_range > 0:
            fib_levels = {
                '23.6%': round(swing_high - fib_range * 0.236, 2),
                '38.2%': round(swing_high - fib_range * 0.382, 2),
                '50.0%': round(swing_high - fib_range * 0.500, 2),
                '61.8%': round(swing_high - fib_range * 0.618, 2),
                '78.6%': round(swing_high - fib_range * 0.786, 2)
            }

        return {
            'slope': slope, 'intercept': intercept,
            'last_month_idx': int(df['Price_Idx'].iloc[-1]),
            'last_month_date': df.index[-1],
            'wick_count': wicks, 'timeframe': timeframe,
            'fib_levels': fib_levels
        }

    try:
        df_m = yf.download(ticker, period="8y", interval="1mo", auto_adjust=True, progress=False)
        tl = from_df(df_m, 'monthly')
        if tl:
            return tl
        df_w = yf.download(ticker, period="5y", interval="1wk", auto_adjust=True, progress=False)
        return from_df(df_w, 'weekly')
    except Exception:
        return None

def get_trigger(tl, date):
    last_date = tl['last_month_date']
    if isinstance(last_date, str):
        last_date = datetime.strptime(last_date[:10], '%Y-%m-%d')
    months_diff = ((date.year - last_date.year) * 12 +
                   (date.month - last_date.month))
    return (tl['slope'] * (tl['last_month_idx'] + months_diff)) + tl['intercept']

def get_fib_score(tl, trigger):
    try:
        fib_levels = tl.get('fib_levels', {})
        if not fib_levels:
            return 6, 'No Fib'
        dists = {k: abs((trigger - v) / v * 100) for k, v in fib_levels.items()}
        closest = min(dists, key=dists.get)
        min_dist = dists[closest]
        if min_dist <= 2.0:
            score = 10 if min_dist <= 0.5 else 9 if min_dist <= 1.0 else 8
            if closest == '61.8%':
                score = min(10, score + 1)
            return score, f"{closest} ({min_dist:.1f}%)"
        return 6, f"No Fib within 2% (nearest {closest} {min_dist:.1f}%)"
    except Exception:
        return 6, 'Fib error'

def run_filter():
    print("🎯 NIFTY 500 TRENDLINE FILTER - LIVE SIGNALS")
    print("="*70)
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    # Step 1: Load from cache (NO rebuilding!)
    print(f"\n📂 Loading trendlines from cache...")
    if not os.path.exists('trendline_cache.json'):
        print("❌ Cache not found! Run trendline_cache.py first to build it.")
        return

    with open('trendline_cache.json', 'r') as f:
        cache = json.load(f)

    trendlines = cache['trendlines']
    print(f"✅ Loaded {len(trendlines)} trendlines from cache (built: {cache['built_at']})")

    # Step 2: Get current prices (batch) - ONLY current prices, no trendline rebuild!
    print(f"\n📥 Fetching ONLY current prices (fast)...")
    current_prices = {}
    ticker_list = [t if t.endswith('.NS') else t + '.NS' for t in trendlines.keys()]

    for i in range(0, len(ticker_list), 100):
        batch = ticker_list[i:i+100]
        try:
            data = yf.download(batch, period="2d", interval="1d",
                               auto_adjust=True, progress=False, group_by='ticker')
            for t in batch:
                try:
                    if len(batch) == 1:
                        p = float(data['Close'].iloc[-1])
                    else:
                        p = float(data[t]['Close'].iloc[-1])
                    if p > 0:
                        current_prices[t] = p
                except Exception:
                    pass
        except Exception:
            pass
        print(f"   Batch {i//100+1} done | Prices: {len(current_prices)}")

    # Step 3: Apply trendline filter
    print(f"\n🔍 Applying trendline filter...")
    today = datetime.now()

    critical = []   # ±1%
    watchlist = []  # ±2%
    approaching = [] # 2-10%

    for ticker, tl in trendlines.items():
        # Cache stores ticker without .NS, prices fetched with .NS
        ticker_ns = ticker if ticker.endswith('.NS') else ticker + '.NS'
        if ticker_ns not in current_prices and ticker not in current_prices:
            continue
        current_price = current_prices.get(ticker_ns) or current_prices.get(ticker)
            trigger = get_trigger(tl, today)
            if trigger <= 0:
                continue

            dist_pct = ((current_price - trigger) / trigger) * 100
            fib_score, fib_note = get_fib_score(tl, trigger)
            stop_loss = round(trigger * 0.92, 2)
            target = round(trigger * 1.20, 2)
            name = ticker.replace('.NS', '')

            signal = {
                'ticker': name,
                'current_price': round(current_price, 2),
                'trigger_price': round(trigger, 2),
                'distance_pct': round(dist_pct, 2),
                'fib_score': fib_score,
                'fib_note': fib_note,
                'wick_touches': tl['wick_count'],
                'timeframe': tl['timeframe'],
                'stop_loss': stop_loss,
                'target': target
            }

            if abs(dist_pct) <= 1.0:
                critical.append(signal)
            elif abs(dist_pct) <= 2.0:
                watchlist.append(signal)
            elif abs(dist_pct) <= 10.0:
                approaching.append(signal)

        except Exception:
            continue

    # Sort by distance
    critical.sort(key=lambda x: abs(x['distance_pct']))
    watchlist.sort(key=lambda x: abs(x['distance_pct']))
    approaching.sort(key=lambda x: abs(x['distance_pct']))

    # Display results
    print(f"\n{'='*70}")
    print(f"🏆 TRENDLINE FILTER RESULTS")
    print(f"{'='*70}")
    print(f"📊 Stocks scanned: {len(trendlines)}")
    print(f"💰 Prices fetched: {len(current_prices)}")
    print(f"\n🎯 CRITICAL ENTRY (±1%):    {len(critical)}")
    print(f"👀 WATCHLIST (±2%):         {len(watchlist)}")
    print(f"📈 APPROACHING (2-10%):     {len(approaching)}")
    print(f"📊 TOTAL OPPORTUNITIES:     {len(critical)+len(watchlist)+len(approaching)}")

    if critical:
        print(f"\n🎯 CRITICAL ENTRY SIGNALS (±1%) - BUY NOW:")
        print(f"   {'Stock':12} {'Price':8} {'Trigger':8} {'Dist':6} {'Fib':5} {'Wicks':5} {'TF':7} {'Stop':8} {'Target':8}")
        print(f"   {'-'*70}")
        for s in critical:
            print(f"   {s['ticker']:12} ₹{s['current_price']:7.2f} ₹{s['trigger_price']:7.2f} {s['distance_pct']:+5.1f}% {s['fib_score']:3}/10 {s['wick_touches']:4}  {s['timeframe']:7} ₹{s['stop_loss']:7.2f} ₹{s['target']:7.2f}")

    if watchlist:
        print(f"\n👀 WATCHLIST (±2%) - NEAR ENTRY:")
        print(f"   {'Stock':12} {'Price':8} {'Trigger':8} {'Dist':6} {'Fib':5} {'Wicks':5} {'TF':7}")
        print(f"   {'-'*55}")
        for s in watchlist:
            print(f"   {s['ticker']:12} ₹{s['current_price']:7.2f} ₹{s['trigger_price']:7.2f} {s['distance_pct']:+5.1f}% {s['fib_score']:3}/10 {s['wick_touches']:4}  {s['timeframe']:7}")

    if approaching:
        print(f"\n📈 APPROACHING TRENDLINE (2-10%) - MONITOR:")
        print(f"   {'Stock':12} {'Price':8} {'Trigger':8} {'Dist':6} {'Fib':5} {'Wicks':5} {'TF':7}")
        print(f"   {'-'*55}")
        for s in approaching[:30]:  # Top 30
            print(f"   {s['ticker']:12} ₹{s['current_price']:7.2f} ₹{s['trigger_price']:7.2f} {s['distance_pct']:+5.1f}% {s['fib_score']:3}/10 {s['wick_touches']:4}  {s['timeframe']:7}")
        if len(approaching) > 30:
            print(f"   ... and {len(approaching)-30} more")

    # Save to JSON
    output = {
        'scan_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'total_scanned': len(trendlines),
        'critical_count': len(critical),
        'watchlist_count': len(watchlist),
        'approaching_count': len(approaching),
        'critical_signals': critical,
        'watchlist_signals': watchlist,
        'approaching_signals': approaching[:50]
    }
    with open('trendline_screen.json', 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\n💾 Results saved to trendline_screen.json")

if __name__ == "__main__":
    run_filter()
