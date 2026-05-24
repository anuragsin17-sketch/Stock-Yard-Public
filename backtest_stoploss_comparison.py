#!/usr/bin/env python3
"""
Stop Loss Comparison Backtest
Option 2: Weekly close stop (checked on weekly candle close)
Option 3: Monthly close stop (checked on monthly candle close)
vs Current: Daily close stop
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json

def load_cache():
    with open('trendline_cache.json', 'r') as f:
        return json.load(f)

def get_trigger_for_date(tl, target_date):
    last_date = tl['last_month_date']
    if isinstance(last_date, str):
        last_date = datetime.strptime(last_date[:10], '%Y-%m-%d')
    months_diff = ((target_date.year - last_date.year) * 12 +
                   (target_date.month - last_date.month))
    return (tl['slope'] * (tl['last_month_idx'] + months_diff)) + tl['intercept']

def get_fib_score(tl, trigger_price):
    try:
        fib_levels = tl.get('fib_levels', {})
        if not fib_levels:
            return 6
        min_dist = min(abs((trigger_price - p) / p * 100) for p in fib_levels.values())
        closest = min(fib_levels, key=lambda k: abs((trigger_price - fib_levels[k]) / fib_levels[k] * 100))
        if min_dist <= 2.0:
            score = 10 if min_dist <= 0.5 else 9 if min_dist <= 1.0 else 8
            if closest == '61.8%': score = min(10, score + 1)
            return score
        return 6
    except:
        return 6

def run_backtest(stop_mode, daily_data, weekly_data, monthly_data, trendlines, label):
    """
    stop_mode: 'daily', 'weekly', 'monthly'
    """
    print(f"\n{'='*70}")
    print(f"🔄 RUNNING: {label}")
    print(f"{'='*70}")

    capital = 500000
    position_size = 50000
    max_positions = 10
    open_positions = {}
    all_trades = []
    stopped_out = {}

    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)

    # Get all daily trading dates for entry checking
    all_dates = set()
    for df in daily_data.values():
        all_dates.update(df.index.tolist())
    all_dates = sorted(all_dates)

    for current_date in all_dates:
        for ticker in list(daily_data.keys()):
            cache_key = ticker  # Cache keys have .NS suffix
            if cache_key not in trendlines:
                continue

            df_daily = daily_data[ticker]
            if current_date not in df_daily.index:
                continue

            try:
                current_price = df_daily.loc[current_date, 'Close']
                if hasattr(current_price, 'item'):
                    current_price = current_price.item()
                if pd.isna(current_price) or current_price <= 0:
                    continue

                tl = trendlines[cache_key]
                trigger_price = get_trigger_for_date(tl, current_date)
                if trigger_price <= 0:
                    continue

                distance_pct = ((current_price - trigger_price) / trigger_price) * 100

                # ── CHECK EXIT ────────────────────────────────────────
                if ticker in open_positions:
                    pos = open_positions[ticker]
                    exit_reason = None
                    exit_price = current_price

                    # Dynamic stop: 8% below current trendline
                    dynamic_stop = trigger_price * 0.92
                    hard_stop = pos['hard_stop']

                    if stop_mode == 'daily':
                        # Check stop on every daily close
                        if current_price < dynamic_stop:
                            exit_reason = 'Trendline Breakdown'
                        elif current_price <= hard_stop:
                            exit_reason = 'Hard Stop'

                    elif stop_mode == 'weekly':
                        # Only check stop on weekly close (Friday or last trading day of week)
                        is_week_end = (current_date.weekday() == 4 or  # Friday
                                      (current_date + timedelta(days=1)).weekday() == 0)  # Next day is Monday
                        if is_week_end:
                            if current_price < dynamic_stop:
                                exit_reason = 'Trendline Breakdown (Weekly)'
                            elif current_price <= hard_stop:
                                exit_reason = 'Hard Stop (Weekly)'

                    elif stop_mode == 'monthly':
                        # Only check stop on monthly close (last trading day of month)
                        next_day = current_date + timedelta(days=1)
                        is_month_end = (next_day.month != current_date.month)
                        if is_month_end:
                            if current_price < dynamic_stop:
                                exit_reason = 'Trendline Breakdown (Monthly)'
                            elif current_price <= hard_stop:
                                exit_reason = 'Hard Stop (Monthly)'

                    # Target and max hold checked daily regardless
                    if not exit_reason:
                        if current_price >= pos['target']:
                            exit_reason = 'Target Hit ✅'
                        elif (current_date - pd.to_datetime(pos['entry_date'])).days >= 90:
                            exit_reason = 'Max Hold'

                    if exit_reason:
                        pnl = (exit_price - pos['entry_price']) * pos['quantity']
                        pnl_pct = ((exit_price - pos['entry_price']) / pos['entry_price']) * 100
                        days_held = (current_date - pd.to_datetime(pos['entry_date'])).days
                        capital += pos['quantity'] * exit_price

                        all_trades.append({
                            'ticker': cache_key.replace('.NS',''),
                            'entry_date': pos['entry_date'],
                            'entry_price': round(pos['entry_price'], 2),
                            'exit_date': current_date.strftime('%Y-%m-%d'),
                            'exit_price': round(exit_price, 2),
                            'exit_reason': exit_reason,
                            'pnl': round(pnl, 2),
                            'pnl_pct': round(pnl_pct, 2),
                            'days_held': days_held
                        })
                        del open_positions[ticker]

                        if 'Breakdown' in exit_reason or 'Stop' in exit_reason:
                            stopped_out[ticker] = current_date

                # ── CHECK ENTRY ───────────────────────────────────────
                elif (len(open_positions) < max_positions and
                      capital >= position_size and
                      ticker not in open_positions):

                    if ticker in stopped_out:
                        if (current_date - stopped_out[ticker]).days < 60:
                            continue
                        else:
                            del stopped_out[ticker]

                    if -2.0 <= distance_pct <= 2.0:
                        fib_score = get_fib_score(tl, trigger_price)
                        quantity = int(position_size / trigger_price)
                        if quantity <= 0:
                            continue

                        investment = quantity * trigger_price
                        capital -= investment

                        open_positions[ticker] = {
                            'entry_date': current_date.strftime('%Y-%m-%d'),
                            'entry_price': trigger_price,
                            'quantity': quantity,
                            'investment': investment,
                            'hard_stop': trigger_price * 0.92,
                            'target': trigger_price * 1.20,
                            'fib_score': fib_score
                        }

            except Exception:
                continue

    # Close remaining
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
                    'days_held': (end_date - pd.to_datetime(pos['entry_date'])).days
                })
            except:
                pass

    # Results
    if not all_trades:
        print("❌ No trades")
        return {}

    total_trades = len(all_trades)
    winning = [t for t in all_trades if t['pnl'] > 0]
    losing = [t for t in all_trades if t['pnl'] <= 0]
    total_pnl = sum(t['pnl'] for t in all_trades)
    total_return = (total_pnl / 500000) * 100
    final_capital = 500000 + total_pnl
    win_rate = (len(winning) / total_trades) * 100

    print(f"💰 Initial: ₹5,00,000 → Final: ₹{final_capital:,.0f} ({total_return:+.2f}%)")
    print(f"📊 Trades: {total_trades} | Win: {len(winning)} ({win_rate:.1f}%) | Loss: {len(losing)}")
    if winning:
        print(f"   Avg Win: {np.mean([t['pnl_pct'] for t in winning]):+.2f}%")
    if losing:
        print(f"   Avg Loss: {np.mean([t['pnl_pct'] for t in losing]):+.2f}%")
    print(f"   Avg Hold: {np.mean([t['days_held'] for t in all_trades]):.0f} days")

    # Exit reasons
    exit_reasons = {}
    for t in all_trades:
        exit_reasons[t['exit_reason']] = exit_reasons.get(t['exit_reason'], 0) + 1
    print(f"📋 Exit Reasons:")
    for reason, count in sorted(exit_reasons.items(), key=lambda x: -x[1]):
        print(f"   {reason:30}: {count:3d} ({count/total_trades*100:.1f}%)")

    return {
        'label': label,
        'final_capital': final_capital,
        'total_return': total_return,
        'total_trades': total_trades,
        'win_rate': win_rate,
        'avg_win': np.mean([t['pnl_pct'] for t in winning]) if winning else 0,
        'avg_loss': np.mean([t['pnl_pct'] for t in losing]) if losing else 0,
        'trades': all_trades
    }

def main():
    print("🎯 STOP LOSS COMPARISON: DAILY vs WEEKLY vs MONTHLY")
    print("="*70)

    # Load cache
    cache = load_cache()
    trendlines = cache['trendlines']
    print(f"✅ Loaded {len(trendlines)} trendlines")

    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)

    # Download daily data
    print(f"\n📥 Downloading daily data...")
    ticker_list = [t if t.endswith('.NS') else t + '.NS' for t in trendlines.keys()]
    daily_data = {}
    import time
    for i in range(0, len(ticker_list), 50):
        batch = ticker_list[i:i+50]
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
                    if not df_t.empty and len(df_t) > 50:
                        daily_data[ticker] = df_t.dropna()
                except:
                    pass
        except:
            pass
        print(f"   Batch {i//50+1}/{(len(ticker_list)-1)//50+1} | Loaded: {len(daily_data)}")
        time.sleep(0.3)

    print(f"✅ Daily data: {len(daily_data)} stocks")

    # Run all 3 options
    results = []

    r1 = run_backtest('daily', daily_data, None, None, trendlines, "Option 1: DAILY Stop Loss (Current)")
    results.append(r1)

    r2 = run_backtest('weekly', daily_data, None, None, trendlines, "Option 2: WEEKLY Close Stop Loss")
    results.append(r2)

    r3 = run_backtest('monthly', daily_data, None, None, trendlines, "Option 3: MONTHLY Close Stop Loss")
    results.append(r3)

    # Final comparison
    print(f"\n{'='*70}")
    print(f"🏆 FINAL COMPARISON")
    print(f"{'='*70}")
    print(f"{'Option':40} {'Return':8} {'Win%':6} {'Trades':7} {'AvgWin':8} {'AvgLoss':8}")
    print(f"{'-'*70}")
    for r in results:
        if r:
            print(f"{r['label']:40} {r['total_return']:+7.2f}% {r['win_rate']:5.1f}% {r['total_trades']:6d} {r['avg_win']:+7.2f}% {r['avg_loss']:+7.2f}%")

    # Save results
    with open('stoploss_comparison_results.json', 'w') as f:
        json.dump([{k: v for k, v in r.items() if k != 'trades'} for r in results if r], f, indent=2)
    print(f"\n💾 Results saved to stoploss_comparison_results.json")

if __name__ == "__main__":
    main()
