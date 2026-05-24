#!/usr/bin/env python3
"""
Full Nifty 500 Backtest - Last 1 Year
Using all learned improvements:
- Wick-based touch detection
- ±2% entry discipline
- Entry AT trendline price
- Dynamic stop loss (8% below current trendline)
- Fibonacci within 2% only
- Minimum 3 wick touches
"""

import yfinance as yf
import pandas as pd
import numpy as np
from scipy.signal import argrelextrema
from datetime import datetime, timedelta
import json
import time

# ─── TRENDLINE ENGINE ────────────────────────────────────────────────────────

def get_sector_order(ticker):
    banking = ['SBIN', 'HDFCBANK', 'ICICIBANK', 'AXISBANK', 'KOTAKBANK',
               'INDUSINDBK', 'FEDERALBNK', 'BANDHANBNK', 'RBLBANK', 'IDFCFIRSTB']
    return 6 if any(b in ticker.upper() for b in banking) else 10

def get_monthly_trendline(ticker):
    """
    Build trendline with wick-based touch detection.
    PRIMARY:  Monthly 8 years
    FALLBACK: Weekly 5 years (if monthly gives < 3 wick touches)
    """
    try:
        def build_trendline_from_df(df, timeframe):
            if df.empty or len(df) < 18:
                return None
            df = df.dropna()
            df['Price_Idx'] = np.arange(len(df))
            low_prices = df['Low'].values.flatten()

            # Adaptive order (weekly uses smaller order)
            order = get_sector_order(ticker)
            if timeframe == 'weekly':
                order = max(3, order // 2)

            touchbacks = argrelextrema(low_prices, np.less, order=order)
            for fallback in [8, 6, 5, 4, 3]:
                if len(touchbacks[0]) >= 2:
                    break
                touchbacks = argrelextrema(low_prices, np.less, order=fallback)

            if len(touchbacks[0]) < 2:
                return None

            num = min(3, len(touchbacks[0]))
            anchor_indices = touchbacks[0][-num:]
            x = [int(df['Price_Idx'].iloc[i]) for i in anchor_indices]
            y = [float(low_prices[i]) for i in anchor_indices]
            slope, intercept = np.polyfit(x, y, 1)

            if slope <= 0:
                return None

            # Count wick touches (within 8% of trendline)
            wick_touches = []
            for i in range(len(df)):
                midx = int(df['Price_Idx'].iloc[i])
                tl = (slope * midx) + intercept
                dist = abs((float(low_prices[i]) - tl) / tl) * 100
                if dist <= 8.0:
                    wick_touches.append(i)

            if len(wick_touches) < 3:
                return None

            # Fibonacci data
            last_touch_idx = int(anchor_indices[-1])
            last_touch_price = float(low_prices[last_touch_idx])
            swing_high = float(df.iloc[last_touch_idx:]['High'].max())
            fib_range = swing_high - last_touch_price

            fib_levels = {}
            if fib_range > 0:
                fib_levels = {
                    '23.6%': round(swing_high - (fib_range * 0.236), 2),
                    '38.2%': round(swing_high - (fib_range * 0.382), 2),
                    '50.0%': round(swing_high - (fib_range * 0.500), 2),
                    '61.8%': round(swing_high - (fib_range * 0.618), 2),
                    '78.6%': round(swing_high - (fib_range * 0.786), 2)
                }

            return {
                'slope': slope,
                'intercept': intercept,
                'last_month_idx': int(df['Price_Idx'].iloc[-1]),
                'last_month_date': df.index[-1],
                'anchor_indices': anchor_indices,
                'wick_touch_count': len(wick_touches),
                'timeframe': timeframe,
                'monthly_df': df
            }

        # PRIMARY: Monthly 8 years
        df_monthly = yf.download(ticker, period="8y", interval="1mo",
                                  auto_adjust=True, progress=False)
        result = build_trendline_from_df(df_monthly, 'monthly')
        if result:
            return result

        # FALLBACK: Weekly 5 years (if monthly < 3 touches)
        df_weekly = yf.download(ticker, period="5y", interval="1wk",
                                 auto_adjust=True, progress=False)
        return build_trendline_from_df(df_weekly, 'weekly')

    except Exception:
        return None

def get_trigger_for_date(tl, target_date):
    """Imaginary vertical line - get trendline price for any date"""
    months_diff = ((target_date.year - tl['last_month_date'].year) * 12 +
                   (target_date.month - tl['last_month_date'].month))
    current_idx = tl['last_month_idx'] + months_diff
    return (tl['slope'] * current_idx) + tl['intercept']

def get_fib_confluence(tl, trigger_price):
    """Fibonacci confluence - only within 2% counts"""
    try:
        df = tl['monthly_df']
        anchor_indices = tl['anchor_indices']
        last_touch_idx = anchor_indices[-1]
        last_touch_price = float(df['Low'].iloc[last_touch_idx])
        swing_high = float(df.iloc[last_touch_idx:]['High'].max())

        fib_range = swing_high - last_touch_price
        if fib_range <= 0:
            return 6

        fib_levels = {
            '23.6%': swing_high - (fib_range * 0.236),
            '38.2%': swing_high - (fib_range * 0.382),
            '50.0%': swing_high - (fib_range * 0.500),
            '61.8%': swing_high - (fib_range * 0.618),
            '78.6%': swing_high - (fib_range * 0.786)
        }

        min_dist = min(abs((trigger_price - p) / p) * 100 for p in fib_levels.values())
        closest = min(fib_levels, key=lambda k: abs((trigger_price - fib_levels[k]) / fib_levels[k]) * 100)

        if min_dist <= 2.0:
            score = 10 if min_dist <= 0.5 else 9 if min_dist <= 1.0 else 8
            if closest == '61.8%':
                score = min(10, score + 1)
            return score
        return 6  # Trendline touch alone is valid

    except Exception:
        return 6

# ─── BACKTEST ENGINE ─────────────────────────────────────────────────────────

def run_nifty500_backtest():
    print("🎯 NIFTY 500 FULL BACKTEST - LAST 1 YEAR")
    print("=" * 70)

    # Load Nifty 500 list
    nifty_df = pd.read_csv('ind_nifty500list.csv')
    tickers = [s + '.NS' for s in nifty_df['Symbol'].tolist()]
    print(f"📊 Total stocks: {len(tickers)}")

    # Backtest period
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    print(f"📅 Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print(f"💰 Capital: ₹5,00,000 | Position: ₹50,000 | Max Positions: 10")

    # ── STEP 1: Build trendlines ──────────────────────────────────────────
    print(f"\n📐 BUILDING TRENDLINES FOR {len(tickers)} STOCKS...")
    print("-" * 50)

    trendlines = {}
    failed = 0
    for i, ticker in enumerate(tickers, 1):
        tl = get_monthly_trendline(ticker)
        if tl:
            trendlines[ticker] = tl
        else:
            failed += 1

        if i % 50 == 0:
            print(f"   Progress: {i}/{len(tickers)} | Valid: {len(trendlines)} | Failed: {failed}")

    print(f"\n✅ Valid trendlines: {len(trendlines)}/{len(tickers)}")

    # ── STEP 2: Download daily data ───────────────────────────────────────
    print(f"\n📥 DOWNLOADING DAILY DATA...")
    print("-" * 50)

    daily_data = {}
    batch_size = 50
    ticker_list = list(trendlines.keys())

    for i in range(0, len(ticker_list), batch_size):
        batch = ticker_list[i:i+batch_size]
        try:
            data = yf.download(batch,
                               start=start_date.strftime('%Y-%m-%d'),
                               end=end_date.strftime('%Y-%m-%d'),
                               interval="1d", auto_adjust=True,
                               progress=False, group_by='ticker')

            for ticker in batch:
                try:
                    if len(batch) == 1:
                        df_t = data
                    else:
                        df_t = data[ticker] if ticker in data.columns.get_level_values(0) else pd.DataFrame()

                    if not df_t.empty and len(df_t) > 100:
                        daily_data[ticker] = df_t.dropna()
                except Exception:
                    pass

        except Exception as e:
            print(f"   Batch {i//batch_size + 1} failed: {e}")

        print(f"   Batch {i//batch_size + 1}/{(len(ticker_list)-1)//batch_size + 1} | Loaded: {len(daily_data)}")
        time.sleep(0.5)

    print(f"\n✅ Daily data loaded: {len(daily_data)} stocks")

    # ── STEP 3: Simulate trades ───────────────────────────────────────────
    print(f"\n🔄 SIMULATING TRADES...")
    print("-" * 50)

    capital = 500000
    position_size = 50000
    max_positions = 10
    open_positions = {}
    all_trades = []
    stopped_out_stocks = {}  # 60-day cooldown after stop loss

    # Get all trading dates
    all_dates = set()
    for df in daily_data.values():
        all_dates.update(df.index.tolist())
    all_dates = sorted(all_dates)

    print(f"📅 Trading days: {len(all_dates)}")

    for current_date in all_dates:
        for ticker in list(daily_data.keys()):
            if ticker not in trendlines:
                continue
            df = daily_data[ticker]
            if current_date not in df.index:
                continue

            try:
                current_price = df.loc[current_date, 'Close']
                if hasattr(current_price, 'item'):
                    current_price = current_price.item()
                if pd.isna(current_price) or current_price <= 0:
                    continue

                # Get trendline trigger (imaginary vertical line)
                trigger_price = get_trigger_for_date(trendlines[ticker], current_date)
                if trigger_price <= 0:
                    continue

                distance_pct = ((current_price - trigger_price) / trigger_price) * 100

                # ── CHECK EXIT ────────────────────────────────────────────
                if ticker in open_positions:
                    pos = open_positions[ticker]
                    exit_reason = None

                    # Dynamic stop: 8% below CURRENT trendline (moves up monthly)
                    dynamic_stop = trigger_price * 0.92

                    if current_price < dynamic_stop:
                        exit_reason = 'Trendline Breakdown'
                    elif current_price <= pos['hard_stop']:
                        exit_reason = 'Hard Stop'
                    elif current_price >= pos['target']:
                        exit_reason = 'Target Hit ✅'
                    elif (current_date - pd.to_datetime(pos['entry_date'])).days >= 90:
                        exit_reason = 'Max Hold'

                    if exit_reason:
                        exit_price = current_price
                        pnl = (exit_price - pos['entry_price']) * pos['quantity']
                        pnl_pct = ((exit_price - pos['entry_price']) / pos['entry_price']) * 100
                        days_held = (current_date - pd.to_datetime(pos['entry_date'])).days

                        capital += pos['quantity'] * exit_price

                        all_trades.append({
                            'ticker': ticker.replace('.NS', ''),
                            'entry_date': pos['entry_date'],
                            'entry_price': round(pos['entry_price'], 2),
                            'exit_date': current_date.strftime('%Y-%m-%d'),
                            'exit_price': round(exit_price, 2),
                            'exit_reason': exit_reason,
                            'pnl': round(pnl, 2),
                            'pnl_pct': round(pnl_pct, 2),
                            'days_held': days_held,
                            'confluence_score': pos['confluence_score'],
                            'wick_touches': pos['wick_touches']
                        })

                        del open_positions[ticker]

                        if 'Breakdown' in exit_reason or 'Stop' in exit_reason:
                            stopped_out_stocks[ticker] = current_date

                        icon = "✅" if pnl > 0 else "❌"
                        print(f"   {icon} EXIT  {ticker.replace('.NS',''):12} | {pnl_pct:+.1f}% | ₹{pnl:+,.0f} | {exit_reason}")

                # ── CHECK ENTRY ───────────────────────────────────────────
                elif (len(open_positions) < max_positions and
                      capital >= position_size and
                      ticker not in open_positions):

                    # Cooldown check (60 days after stop loss)
                    if ticker in stopped_out_stocks:
                        days_since = (current_date - stopped_out_stocks[ticker]).days
                        if days_since < 60:
                            continue
                        else:
                            del stopped_out_stocks[ticker]

                    # Entry: ±2% of trendline only
                    if -2.0 <= distance_pct <= 2.0:

                        # Fibonacci confluence check
                        confluence = get_fib_confluence(trendlines[ticker], trigger_price)

                        quantity = int(position_size / trigger_price)
                        if quantity <= 0:
                            continue

                        investment = quantity * trigger_price
                        capital -= investment

                        open_positions[ticker] = {
                            'entry_date': current_date.strftime('%Y-%m-%d'),
                            'entry_price': trigger_price,       # AT trendline
                            'quantity': quantity,
                            'investment': investment,
                            'hard_stop': trigger_price * 0.92,  # 8% below trendline
                            'target': trigger_price * 1.20,     # 20% above trendline
                            'confluence_score': confluence,
                            'wick_touches': trendlines[ticker]['wick_touch_count']
                        }

                        print(f"   📈 ENTRY {ticker.replace('.NS',''):12} | ₹{trigger_price:.2f} | Dist: {distance_pct:+.1f}% | Fib: {confluence}/10 | Wicks: {trendlines[ticker]['wick_touch_count']}")

            except Exception:
                continue

    # Close remaining open positions
    for ticker, pos in list(open_positions.items()):
        if ticker in daily_data and not daily_data[ticker].empty:
            try:
                final_price = float(daily_data[ticker]['Close'].iloc[-1])
                pnl = (final_price - pos['entry_price']) * pos['quantity']
                pnl_pct = ((final_price - pos['entry_price']) / pos['entry_price']) * 100
                capital += pos['quantity'] * final_price

                all_trades.append({
                    'ticker': ticker.replace('.NS', ''),
                    'entry_date': pos['entry_date'],
                    'entry_price': round(pos['entry_price'], 2),
                    'exit_date': end_date.strftime('%Y-%m-%d'),
                    'exit_price': round(final_price, 2),
                    'exit_reason': 'Still Open',
                    'pnl': round(pnl, 2),
                    'pnl_pct': round(pnl_pct, 2),
                    'days_held': (end_date - pd.to_datetime(pos['entry_date'])).days,
                    'confluence_score': pos['confluence_score'],
                    'wick_touches': pos['wick_touches']
                })
            except Exception:
                pass

    # ── RESULTS ───────────────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print(f"🏆 NIFTY 500 BACKTEST RESULTS - LAST 1 YEAR")
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

    avg_days = np.mean([t['days_held'] for t in all_trades])
    print(f"   Avg Hold Days   : {avg_days:.0f}")

    # Exit reason breakdown
    exit_reasons = {}
    for t in all_trades:
        exit_reasons[t['exit_reason']] = exit_reasons.get(t['exit_reason'], 0) + 1

    print(f"\n📋 EXIT REASONS:")
    for reason, count in sorted(exit_reasons.items(), key=lambda x: -x[1]):
        pct = (count / total_trades) * 100
        print(f"   {reason:25} : {count:3d} ({pct:.1f}%)")

    # Top 10 trades
    top_trades = sorted(all_trades, key=lambda t: t['pnl_pct'], reverse=True)[:10]
    print(f"\n🏆 TOP 10 TRADES:")
    print(f"   {'Stock':12} {'Entry':10} {'Exit':10} {'Entry₹':8} {'Exit₹':8} {'P&L%':7} {'Reason'}")
    print(f"   {'-'*70}")
    for t in top_trades:
        icon = "✅" if t['pnl'] > 0 else "❌"
        print(f"   {icon} {t['ticker']:10} {t['entry_date']:10} {t['exit_date']:10} ₹{t['entry_price']:7.0f} ₹{t['exit_price']:7.0f} {t['pnl_pct']:+6.1f}% {t['exit_reason']}")

    # Bottom 5 trades
    bottom_trades = sorted(all_trades, key=lambda t: t['pnl_pct'])[:5]
    print(f"\n📉 BOTTOM 5 TRADES:")
    for t in bottom_trades:
        print(f"   ❌ {t['ticker']:10} {t['pnl_pct']:+6.1f}% | {t['exit_reason']}")

    # Save results
    results = {
        'backtest': 'Nifty 500 Full Backtest - Last 1 Year',
        'period': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
        'stocks_scanned': len(tickers),
        'valid_trendlines': len(trendlines),
        'initial_capital': 500000,
        'final_capital': final_capital,
        'total_return_pct': round(total_return, 2),
        'total_trades': total_trades,
        'win_rate': round(win_rate, 2),
        'trades': all_trades
    }

    with open('backtest_nifty500_results.json', 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n💾 Full results saved to: backtest_nifty500_results.json")

if __name__ == "__main__":
    run_nifty500_backtest()
