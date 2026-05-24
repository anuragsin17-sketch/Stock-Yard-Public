#!/usr/bin/env python3
"""
Quick scan - count valid trendlines across all 500 Nifty stocks
Shows monthly vs weekly fallback breakdown
"""

import yfinance as yf
import pandas as pd
import numpy as np
from scipy.signal import argrelextrema
from datetime import datetime
from collections import Counter

def get_sector_order(ticker):
    banking = ['SBIN', 'HDFCBANK', 'ICICIBANK', 'AXISBANK', 'KOTAKBANK',
               'INDUSINDBK', 'FEDERALBNK', 'BANDHANBNK', 'RBLBANK', 'IDFCFIRSTB']
    return 6 if any(b in ticker.upper() for b in banking) else 10

def build_trendline_from_df(df, ticker, timeframe):
    if df.empty or len(df) < 18:
        return None, 'insufficient_data'
    df = df.dropna()
    df['Price_Idx'] = np.arange(len(df))
    low_prices = df['Low'].values.flatten()

    order = get_sector_order(ticker)
    if timeframe == 'weekly':
        order = max(3, order // 2)

    touchbacks = argrelextrema(low_prices, np.less, order=order)
    for fallback in [8, 6, 5, 4, 3]:
        if len(touchbacks[0]) >= 2:
            break
        touchbacks = argrelextrema(low_prices, np.less, order=fallback)

    if len(touchbacks[0]) < 2:
        return None, 'no_anchors'

    num = min(3, len(touchbacks[0]))
    anchor_indices = touchbacks[0][-num:]
    x = [int(df['Price_Idx'].iloc[i]) for i in anchor_indices]
    y = [float(low_prices[i]) for i in anchor_indices]
    slope, intercept = np.polyfit(x, y, 1)

    if slope <= 0:
        return None, 'descending'

    wick_touches = 0
    for i in range(len(df)):
        midx = int(df['Price_Idx'].iloc[i])
        tl = (slope * midx) + intercept
        dist = abs((float(low_prices[i]) - tl) / tl) * 100
        if dist <= 8.0:
            wick_touches += 1

    if wick_touches < 3:
        return None, f'only_{wick_touches}_touches'

    return {
        'slope': slope,
        'intercept': intercept,
        'last_month_idx': int(df['Price_Idx'].iloc[-1]),
        'last_month_date': df.index[-1],
        'wick_touch_count': wick_touches,
        'timeframe': timeframe
    }, 'success'

def scan_all_500():
    print("🎯 NIFTY 500 TRENDLINE COUNT SCAN")
    print("="*60)
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    nifty_df = pd.read_csv('ind_nifty500list.csv')
    tickers = [s + '.NS' for s in nifty_df['Symbol'].tolist()]
    print(f"📊 Total stocks: {len(tickers)}")

    results = {
        'monthly_success': [],
        'weekly_success': [],
        'failed': [],
        'failure_reasons': Counter()
    }

    print(f"\n🔄 Scanning...")
    print("-"*60)

    for i, ticker in enumerate(tickers, 1):
        try:
            # PRIMARY: Monthly 8 years
            df_monthly = yf.download(ticker, period="8y", interval="1mo",
                                      auto_adjust=True, progress=False)
            tl, reason = build_trendline_from_df(df_monthly, ticker, 'monthly')

            if tl:
                results['monthly_success'].append(ticker)
            else:
                # FALLBACK: Weekly 5 years
                df_weekly = yf.download(ticker, period="5y", interval="1wk",
                                         auto_adjust=True, progress=False)
                tl_w, reason_w = build_trendline_from_df(df_weekly, ticker, 'weekly')

                if tl_w:
                    results['weekly_success'].append(ticker)
                else:
                    results['failed'].append((ticker, reason, reason_w))
                    results['failure_reasons'][reason] += 1

        except Exception as e:
            results['failed'].append((ticker, 'exception', str(e)[:30]))
            results['failure_reasons']['exception'] += 1

        if i % 50 == 0:
            total_valid = len(results['monthly_success']) + len(results['weekly_success'])
            print(f"   {i:3d}/500 | Monthly: {len(results['monthly_success'])} | Weekly: {len(results['weekly_success'])} | Failed: {len(results['failed'])} | Total Valid: {total_valid}")

    # Final results
    total_valid = len(results['monthly_success']) + len(results['weekly_success'])
    total_failed = len(results['failed'])

    print(f"\n{'='*60}")
    print(f"🏆 FINAL RESULTS")
    print(f"{'='*60}")
    print(f"✅ Monthly trendlines (8yr): {len(results['monthly_success'])}")
    print(f"✅ Weekly trendlines (5yr):  {len(results['weekly_success'])}")
    print(f"📊 TOTAL VALID:              {total_valid}/{len(tickers)} ({total_valid/len(tickers)*100:.1f}%)")
    print(f"❌ Failed:                   {total_failed}")

    print(f"\n📋 FAILURE REASONS:")
    for reason, count in results['failure_reasons'].most_common():
        print(f"   {reason:30}: {count}")

    print(f"\n✅ WEEKLY FALLBACK STOCKS (sample):")
    for t in results['weekly_success'][:20]:
        print(f"   {t.replace('.NS','')}")

    if len(results['weekly_success']) > 20:
        print(f"   ... and {len(results['weekly_success'])-20} more")

if __name__ == "__main__":
    scan_all_500()
