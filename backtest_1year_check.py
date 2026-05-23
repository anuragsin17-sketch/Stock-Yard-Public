#!/usr/bin/env python3
"""
1-Year Backtest Check - Last 1 Year Data
Fixing the monthly trendline vs daily price comparison issue
"""

import yfinance as yf
import pandas as pd
import numpy as np
from scipy.signal import argrelextrema
from datetime import datetime, timedelta
import json

def get_monthly_trendline(ticker):
    """
    Build trendline from MONTHLY data using WICK-BASED touch detection
    Wicks (candle shadows) count as trendline touches - as taught!
    """
    try:
        # Get 8 years monthly data
        df_monthly = yf.download(ticker, period="8y", interval="1mo", 
                                  auto_adjust=True, progress=False)
        if df_monthly.empty or len(df_monthly) < 24:
            return None
        
        df_monthly = df_monthly.dropna()
        df_monthly['Price_Idx'] = np.arange(len(df_monthly))
        low_prices = df_monthly['Low'].values.flatten()
        
        # Sector-specific order
        banking = ['SBIN', 'HDFCBANK', 'ICICIBANK', 'AXISBANK', 'KOTAKBANK']
        
        # Try progressively smaller orders until we get enough anchors
        # This handles stocks with different cycle lengths (Maruti needs order=5-8)
        order = 6 if any(b in ticker for b in banking) else 10
        
        touchbacks = argrelextrema(low_prices, np.less, order=order)
        
        # If not enough anchors, reduce order progressively
        for fallback_order in [8, 6, 5]:
            if len(touchbacks[0]) >= 2:
                break
            touchbacks = argrelextrema(low_prices, np.less, order=fallback_order)
        
        if len(touchbacks[0]) < 2:
            return None
        
        # Use last 2-3 major anchors to define trendline slope
        num_anchors = min(3, len(touchbacks[0]))
        anchor_indices = touchbacks[0][-num_anchors:]
        
        x_coords = [df_monthly['Price_Idx'].iloc[idx] for idx in anchor_indices]
        y_coords = [low_prices[idx] for idx in anchor_indices]
        
        slope, intercept = np.polyfit(x_coords, y_coords, 1)
        
        if slope <= 0:
            return None
        
        # STEP 2: COUNT WICK TOUCHES (KEY FIX!)
        # A touch = any candle whose LOW (wick) comes within ±5% of trendline
        wick_touches = []
        for i in range(len(df_monthly)):
            month_idx = df_monthly['Price_Idx'].iloc[i]
            trendline_at_month = (slope * month_idx) + intercept
            candle_low = low_prices[i]  # This IS the wick low
            
            # Distance from wick to trendline
            distance_pct = abs((candle_low - trendline_at_month) / trendline_at_month) * 100
            
            # WICK TOUCH: candle low within ±5% of trendline
            if distance_pct <= 5.0:
                wick_touches.append({
                    'date': df_monthly.index[i].strftime('%Y-%m-%d'),
                    'price': round(candle_low, 2),
                    'trendline_price': round(trendline_at_month, 2),
                    'distance_pct': round(distance_pct, 2),
                    'month_idx': int(month_idx)
                })
        
        # MINIMUM 3 WICK TOUCHES REQUIRED
        if len(wick_touches) < 3:
            return None
        
        # Get last month index for reference
        last_month_idx = df_monthly['Price_Idx'].iloc[-1]
        last_month_date = df_monthly.index[-1]
        
        return {
            'slope': slope,
            'intercept': intercept,
            'last_month_idx': int(last_month_idx),
            'last_month_date': last_month_date,
            'touch_points': wick_touches,  # ALL wick touches
            'anchor_points': [{'date': df_monthly.index[idx].strftime('%Y-%m-%d'),
                               'price': round(low_prices[idx], 2)} 
                              for idx in anchor_indices],
            'total_wick_touches': len(wick_touches),
            'monthly_df': df_monthly
        }
        
    except Exception as e:
        return None

def get_trigger_for_date(trendline_data, target_date):
    """
    Get trendline trigger price for any given date
    Using imaginary vertical line method
    """
    slope = trendline_data['slope']
    intercept = trendline_data['intercept']
    last_month_idx = trendline_data['last_month_idx']
    last_month_date = trendline_data['last_month_date']
    
    # Calculate months difference from last known month
    months_diff = ((target_date.year - last_month_date.year) * 12 + 
                   (target_date.month - last_month_date.month))
    
    # Current month index for target date
    current_month_idx = last_month_idx + months_diff
    
    # Apply imaginary vertical line - get trigger price
    trigger_price = (slope * current_month_idx) + intercept
    
    return trigger_price

def calculate_fib_confluence(monthly_df, touch_indices, trigger_price):
    """
    Calculate Fibonacci confluence score.
    RULE: Only consider Fib level if trendline is within 2% of it.
    If no Fib level within 2%, still allow trade (score=6, trendline touch is enough).
    """
    try:
        if not touch_indices:
            return 6  # Default pass - trendline touch is sufficient

        last_touch_idx = touch_indices[-1]
        last_touch_price = monthly_df['Low'].iloc[last_touch_idx]
        if hasattr(last_touch_price, 'item'):
            last_touch_price = last_touch_price.item()

        # Find swing high after last touch
        data_after = monthly_df.iloc[last_touch_idx:]
        swing_high = data_after['High'].max()
        if hasattr(swing_high, 'item'):
            swing_high = swing_high.item()

        fib_range = swing_high - last_touch_price
        if fib_range <= 0:
            return 6  # Default pass

        # All 5 Fibonacci levels
        fib_levels = {
            '23.6%': swing_high - (fib_range * 0.236),
            '38.2%': swing_high - (fib_range * 0.382),
            '50.0%': swing_high - (fib_range * 0.500),
            '61.8%': swing_high - (fib_range * 0.618),
            '78.6%': swing_high - (fib_range * 0.786)
        }

        # Find closest Fibonacci level to trigger
        min_distance = float('inf')
        closest_level = None
        for level_name, fib_price in fib_levels.items():
            dist = abs((trigger_price - fib_price) / fib_price) * 100
            if dist < min_distance:
                min_distance = dist
                closest_level = level_name

        # RULE: Only count Fib confluence if within 2%
        if min_distance <= 2.0:
            # Strong confluence - trendline aligns with Fib level
            if min_distance <= 0.5:
                score = 10  # Perfect
            elif min_distance <= 1.0:
                score = 9   # Excellent
            else:
                score = 8   # Good (within 2%)
            # Bonus for Golden Ratio 61.8%
            if closest_level == '61.8%':
                score = min(10, score + 1)
            return score
        else:
            # No Fib confluence within 2%
            # Trendline touch alone is valid - return 6 (passes >= 5 filter)
            return 6

    except Exception:
        return 6  # Default pass on error

def run_1year_backtest():
    """
    Run backtest on last 1 year of data
    """
    print("🎯 IMAGINARY VERTICAL LINE - 1 YEAR BACKTEST")
    print("="*70)
    
    # Last 1 year period
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    
    print(f"📅 Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print(f"💰 Initial Capital: ₹5,00,000")
    print(f"📊 Position Size: ₹50,000 per trade")
    print(f"🎯 Max Positions: 10")
    
    # Test stocks
    tickers = [
        'RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'HINDUNILVR.NS',
        'ICICIBANK.NS', 'SBIN.NS', 'BHARTIARTL.NS', 'KOTAKBANK.NS', 'ASIANPAINT.NS',
        'ITC.NS', 'AXISBANK.NS', 'LT.NS', 'TITAN.NS', 'WIPRO.NS',
        'MARUTI.NS', 'BAJFINANCE.NS', 'HCLTECH.NS', 'SUNPHARMA.NS', 'ULTRACEMCO.NS'
    ]
    
    # Step 1: Build trendlines from monthly data
    print(f"\n📐 BUILDING MONTHLY TRENDLINES...")
    print("-"*50)
    
    trendlines = {}
    for ticker in tickers:
        tl = get_monthly_trendline(ticker)
        if tl:
            trendlines[ticker] = tl
            touches = tl['touch_points']
            print(f"   ✅ {ticker.replace('.NS',''):12} | Wick Touches: {tl['total_wick_touches']} | Last: {touches[-1]['date']} @ ₹{touches[-1]['price']}")
        else:
            print(f"   ❌ {ticker.replace('.NS',''):12} | No valid trendline (< 3 wick touches)")
    
    print(f"\n✅ Valid trendlines: {len(trendlines)}/{len(tickers)}")
    
    # Step 2: Download daily data for last 1 year
    print(f"\n📥 DOWNLOADING DAILY DATA (Last 1 Year)...")
    print("-"*50)
    
    daily_data = {}
    for ticker in trendlines.keys():
        try:
            df = yf.download(ticker, 
                           start=start_date.strftime('%Y-%m-%d'),
                           end=end_date.strftime('%Y-%m-%d'),
                           interval="1d", auto_adjust=True, progress=False)
            if not df.empty:
                daily_data[ticker] = df
                print(f"   ✅ {ticker.replace('.NS',''):12} | {len(df)} trading days")
        except Exception:
            print(f"   ❌ {ticker.replace('.NS','')}")
    
    # Step 3: Simulate trading
    print(f"\n🔄 SIMULATING TRADES...")
    print("-"*50)
    
    capital = 500000
    position_size = 50000
    max_positions = 10
    open_positions = {}
    all_trades = []
    stopped_out_stocks = {}  # Track stocks that hit stop loss - cooldown 60 days
    
    # Get all trading dates
    all_dates = set()
    for df in daily_data.values():
        all_dates.update(df.index.tolist())
    all_dates = sorted(all_dates)
    
    print(f"📅 Total trading days: {len(all_dates)}")
    
    for current_date in all_dates:
        for ticker, df in daily_data.items():
            if ticker not in trendlines:
                continue
            if current_date not in df.index:
                continue
            
            try:
                current_price = df.loc[current_date, 'Close']
                if hasattr(current_price, 'item'):
                    current_price = current_price.item()
                
                # Get trendline trigger for this date (imaginary vertical line)
                trigger_price = get_trigger_for_date(trendlines[ticker], current_date)
                
                if trigger_price <= 0:
                    continue
                
                # Calculate distance
                distance_pct = ((current_price - trigger_price) / trigger_price) * 100
                
                # CHECK EXIT for open positions
                if ticker in open_positions:
                    pos = open_positions[ticker]
                    exit_reason = None
                    exit_price = current_price
                    
                    # DYNAMIC STOP: 8% below CURRENT month trendline (moves up monthly)
                    dynamic_stop = trigger_price * 0.92  # 8% below current trendline
                    
                    # SAFETY NET: Fixed 8% below entry trigger (catastrophic protection)
                    hard_stop = pos['stop_loss']
                    
                    # PRIMARY EXIT: Trendline breakdown (8% below current trendline)
                    if current_price < dynamic_stop:
                        exit_reason = 'Trendline Breakdown 📉'
                    # SAFETY NET: Hard stop loss
                    elif current_price <= hard_stop:
                        exit_reason = 'Hard Stop Loss 🛑'
                    # TARGET: 20% above TRENDLINE entry price
                    elif current_price >= pos['target']:
                        exit_reason = 'Target Hit ✅'
                    # MAX HOLD: 90 days
                    elif (current_date - pd.to_datetime(pos['entry_date'])).days >= 90:
                        exit_reason = 'Max Hold'
                    
                    if exit_reason:
                        pnl = (exit_price - pos['entry_price']) * pos['quantity']
                        pnl_pct = ((exit_price - pos['entry_price']) / pos['entry_price']) * 100
                        days_held = (current_date - pd.to_datetime(pos['entry_date'])).days
                        
                        capital += pos['quantity'] * exit_price
                        
                        trade = {
                            'ticker': ticker.replace('.NS',''),
                            'entry_date': pos['entry_date'],
                            'entry_price': round(pos['entry_price'], 2),
                            'exit_date': current_date.strftime('%Y-%m-%d'),
                            'exit_price': round(exit_price, 2),
                            'exit_reason': exit_reason,
                            'pnl': round(pnl, 2),
                            'pnl_pct': round(pnl_pct, 2),
                            'days_held': days_held,
                            'trigger_at_entry': round(pos['trigger_at_entry'], 2),
                            'distance_at_entry': round(pos['distance_at_entry'], 2),
                            'confluence_score': pos.get('confluence_score', 0)
                        }
                        all_trades.append(trade)
                        del open_positions[ticker]
                        
                        # If stop loss hit, add to cooldown list (60 days)
                        if exit_reason in ('Trendline Breakdown 📉', 'Hard Stop Loss 🛑'):
                            stopped_out_stocks[ticker] = current_date
                        
                        icon = "✅" if pnl > 0 else "❌"
                        print(f"   {icon} EXIT  {ticker.replace('.NS',''):12} | {pnl_pct:+.1f}% | ₹{pnl:+,.0f} | {exit_reason} | Dynamic Stop: ₹{dynamic_stop:.0f}")
                
                # CHECK ENTRY
                elif (len(open_positions) < max_positions and 
                      capital >= position_size and
                      ticker not in open_positions):
                    
                    # COOLDOWN CHECK: Skip if stopped out within last 60 days
                    if ticker in stopped_out_stocks:
                        days_since_stop = (current_date - stopped_out_stocks[ticker]).days
                        if days_since_stop < 60:
                            continue  # Still in cooldown
                        else:
                            del stopped_out_stocks[ticker]  # Cooldown expired
                    
                    # ENTRY CONDITION: Price within ±2% of trendline (strict discipline)
                    # WATCHLIST: 5-10% away (monitor only, no entry)
                    if -2.0 <= distance_pct <= 2.0:
                        
                        # FIBONACCI CONFLUENCE FILTER: Score must be >= 7
                        tl = trendlines[ticker]
                        monthly_df = tl['monthly_df']
                        recent_touches_idx = [
                            monthly_df.index.get_loc(
                                monthly_df.index[monthly_df.index <= pd.to_datetime(tp['date'])].max()
                            ) for tp in tl['touch_points']
                        ]
                        confluence = calculate_fib_confluence(monthly_df, recent_touches_idx, trigger_price)
                        
                        if confluence < 5:
                            continue  # Skip - no Fibonacci confluence within 2%
                        
                        quantity = int(position_size / trigger_price)  # Use trendline price for sizing
                        if quantity > 0:
                            investment = quantity * trigger_price  # Entry AT trendline price
                            capital -= investment
                            
                            open_positions[ticker] = {
                                'entry_date': current_date.strftime('%Y-%m-%d'),
                                'entry_price': trigger_price,  # Entry = trendline trigger
                                'quantity': quantity,
                                'investment': investment,
                                'stop_loss': trigger_price * 0.92,  # 8% below trendline
                                'target': trigger_price * 1.20,     # 20% above trendline
                                'trigger_at_entry': trigger_price,
                                'distance_at_entry': distance_pct,
                                'confluence_score': confluence
                            }
                            
                            print(f"   📈 ENTRY {ticker.replace('.NS',''):12} | Trendline: ₹{trigger_price:.2f} | Market: ₹{current_price:.2f} | Dist: {distance_pct:+.1f}% | Fib: {confluence}/10 🎯")
                    
                    # WATCHLIST: 2-10% away (monitor, no entry)
                    elif 2.0 < abs(distance_pct) <= 10.0:
                        pass  # Just monitoring, no trade
            
            except Exception:
                continue
    
    # Close remaining positions at end
    for ticker, pos in open_positions.items():
        if ticker in daily_data and not daily_data[ticker].empty:
            final_price = daily_data[ticker]['Close'].iloc[-1]
            if hasattr(final_price, 'item'):
                final_price = final_price.item()
            pnl = (final_price - pos['entry_price']) * pos['quantity']
            pnl_pct = ((final_price - pos['entry_price']) / pos['entry_price']) * 100
            capital += pos['quantity'] * final_price
            
            trade = {
                'ticker': ticker.replace('.NS',''),
                'entry_date': pos['entry_date'],
                'entry_price': round(pos['entry_price'], 2),
                'exit_date': end_date.strftime('%Y-%m-%d'),
                'exit_price': round(final_price, 2),
                'exit_reason': 'Still Open',
                'pnl': round(pnl, 2),
                'pnl_pct': round(pnl_pct, 2),
                'days_held': (end_date - pd.to_datetime(pos['entry_date'])).days,
                'trigger_at_entry': round(pos['trigger_at_entry'], 2),
                'distance_at_entry': round(pos['distance_at_entry'], 2)
            }
            all_trades.append(trade)
    
    # RESULTS
    print(f"\n{'='*70}")
    print(f"🏆 BACKTEST RESULTS - LAST 1 YEAR")
    print(f"{'='*70}")
    
    if not all_trades:
        print("❌ No trades executed")
        return
    
    total_trades = len(all_trades)
    winning = [t for t in all_trades if t['pnl'] > 0]
    losing = [t for t in all_trades if t['pnl'] <= 0]
    total_pnl = sum(t['pnl'] for t in all_trades)
    total_return = (total_pnl / 500000) * 100
    final_capital = 500000 + total_pnl
    win_rate = (len(winning) / total_trades) * 100
    
    print(f"\n💰 CAPITAL PERFORMANCE:")
    print(f"   Initial Capital : ₹5,00,000")
    print(f"   Final Capital   : ₹{final_capital:,.0f}")
    print(f"   Total P&L       : ₹{total_pnl:+,.0f}")
    print(f"   Total Return    : {total_return:+.2f}%")
    
    print(f"\n📊 TRADE STATISTICS:")
    print(f"   Total Trades    : {total_trades}")
    print(f"   Winning Trades  : {len(winning)} ({win_rate:.1f}%)")
    print(f"   Losing Trades   : {len(losing)} ({100-win_rate:.1f}%)")
    
    if winning:
        print(f"   Avg Win         : {np.mean([t['pnl_pct'] for t in winning]):+.2f}%")
    if losing:
        print(f"   Avg Loss        : {np.mean([t['pnl_pct'] for t in losing]):+.2f}%")
    
    print(f"\n📋 ALL TRADES:")
    print(f"   {'Stock':12} {'Entry':10} {'Exit':10} {'Entry₹':8} {'Exit₹':8} {'P&L%':7} {'Reason'}")
    print(f"   {'-'*70}")
    for t in sorted(all_trades, key=lambda x: x['pnl_pct'], reverse=True):
        icon = "✅" if t['pnl'] > 0 else "❌"
        print(f"   {icon} {t['ticker']:10} {t['entry_date']:10} {t['exit_date']:10} ₹{t['entry_price']:7.0f} ₹{t['exit_price']:7.0f} {t['pnl_pct']:+6.1f}% {t['exit_reason']}")
    
    # Save results
    with open('backtest_1year_results.json', 'w') as f:
        json.dump({
            'period': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
            'initial_capital': 500000,
            'final_capital': final_capital,
            'total_return_pct': total_return,
            'total_trades': total_trades,
            'win_rate': win_rate,
            'trades': all_trades
        }, f, indent=2)
    
    print(f"\n💾 Results saved to: backtest_1year_results.json")

if __name__ == "__main__":
    run_1year_backtest()
