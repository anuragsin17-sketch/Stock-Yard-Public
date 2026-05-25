"""
Past Performance Backtest - Trendline Strategy
Supports 1Y, 3Y, 5Y, 10Y lookback periods
Outputs backtest_performance.json for the UI Performance tab

Cache: raw OHLC data is saved to .cache/ohlc/<TICKER>_<interval>.pkl
       so interrupted runs resume without re-downloading.
"""
import pandas as pd
import yfinance as yf
import numpy as np
from scipy.signal import argrelextrema
from datetime import datetime, timedelta
import json
import argparse
import sys
import os
import pickle
import hashlib

# ─────────────────────────────────────────────
# Cache helpers
# ─────────────────────────────────────────────
CACHE_DIR = os.path.join(os.path.dirname(__file__), '.cache', 'ohlc')
os.makedirs(CACHE_DIR, exist_ok=True)

def _cache_path(ticker, interval, period_or_start):
    key = f"{ticker}_{interval}_{period_or_start}"
    h = hashlib.md5(key.encode()).hexdigest()[:8]
    return os.path.join(CACHE_DIR, f"{ticker.replace('.', '_')}_{interval}_{h}.pkl")

def load_cached(ticker, interval, period_or_start):
    path = _cache_path(ticker, interval, period_or_start)
    if os.path.exists(path):
        try:
            with open(path, 'rb') as f:
                return pickle.load(f)
        except Exception:
            pass
    return None

def save_cache(ticker, interval, period_or_start, df):
    path = _cache_path(ticker, interval, period_or_start)
    try:
        with open(path, 'wb') as f:
            pickle.dump(df, f)
    except Exception:
        pass

def download_with_cache(ticker, interval, period=None, start=None, end=None):
    """Download OHLC data with local pickle cache."""
    cache_key = period or start
    cached = load_cached(ticker, interval, cache_key)
    if cached is not None:
        return cached

    if period:
        df = yf.download(ticker, period=period, interval=interval,
                         auto_adjust=True, progress=False)
    else:
        df = yf.download(ticker, start=start, end=end, interval=interval,
                         auto_adjust=True, progress=False)

    if not df.empty:
        # Flatten MultiIndex columns (yfinance >=0.2 single-ticker quirk)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        save_cache(ticker, interval, cache_key, df)

    return df

# ─────────────────────────────────────────────
# Lightweight trendline detector (no ±2% filter
# so we can find ALL historical touches)
# ─────────────────────────────────────────────

def get_sector_order(ticker):
    banking = ['SBIN', 'HDFCBANK', 'ICICIBANK', 'AXISBANK', 'KOTAKBANK',
               'INDUSINDBK', 'FEDERALBNK', 'BANDHANBNK', 'RBLBANK', 'IDFCFIRSTB']
    return 6 if any(b in ticker.upper() for b in banking) else 10


def find_trendline_signals(df_monthly):
    """
    Scan a monthly OHLC dataframe for ascending trendline touch signals.
    Returns list of signal dicts: {date, entry_price, stop_loss, target}
    """
    signals = []
    low_prices = df_monthly['Low'].values.flatten()
    df_monthly = df_monthly.copy()
    df_monthly['Price_Idx'] = np.arange(len(df_monthly))

    base_order = 10
    touchbacks = argrelextrema(low_prices, np.less, order=base_order)
    for fallback in [8, 6, 5]:
        if len(touchbacks[0]) >= 2:
            break
        touchbacks = argrelextrema(low_prices, np.less, order=fallback)

    if len(touchbacks[0]) < 2:
        return signals

    # Slide a window: for each anchor pair, project trendline forward
    anchor_idxs = touchbacks[0]

    for win_end in range(2, len(anchor_idxs) + 1):
        window_anchors = anchor_idxs[:win_end]
        num_anchors = min(3, len(window_anchors))
        used_anchors = window_anchors[-num_anchors:]

        x = [df_monthly['Price_Idx'].iloc[i] for i in used_anchors]
        y = [low_prices[i] for i in used_anchors]
        slope, intercept = np.polyfit(x, y, 1)

        if slope <= 0:
            continue

        last_anchor_bar = used_anchors[-1]

        # Scan bars AFTER the last anchor for a touch (within ±2%)
        for bar in range(last_anchor_bar + 1, len(df_monthly)):
            bar_idx = df_monthly['Price_Idx'].iloc[bar]
            trendline_price = slope * bar_idx + intercept
            candle_low = float(low_prices[bar])
            close_val = df_monthly['Close'].iloc[bar]
            candle_close = float(close_val.iloc[0] if hasattr(close_val, 'iloc') else close_val)

            dist_pct = (candle_close - trendline_price) / trendline_price * 100

            if abs(dist_pct) <= 2.0:
                entry_price = round(trendline_price, 2)
                stop_loss = round(trendline_price * 0.92, 2)   # 8% below
                target = round(trendline_price * 1.20, 2)       # 20% above
                touch_date = df_monthly.index[bar].strftime('%Y-%m-%d')

                # Avoid duplicate signals within 3 months
                if signals and (
                    datetime.strptime(touch_date, '%Y-%m-%d') -
                    datetime.strptime(signals[-1]['signal_date'], '%Y-%m-%d')
                ).days < 90:
                    continue

                signals.append({
                    'signal_date': touch_date,
                    'entry_price': entry_price,
                    'stop_loss': stop_loss,
                    'target': target,
                    'bar_idx': bar
                })
                break  # one signal per trendline window

    return signals


def simulate_trade(daily_df, signal, position_size=50000):
    """
    Given a signal dict and daily OHLC data, simulate the trade outcome.
    Stop: monthly close below stop_loss
    Target: intraday high >= target
    Timeout: 180 calendar days
    """
    entry_date = datetime.strptime(signal['signal_date'], '%Y-%m-%d')
    entry_price = signal['entry_price']
    stop_loss = signal['stop_loss']
    target = signal['target']

    # Filter daily data after signal date
    future = daily_df[daily_df.index > pd.Timestamp(entry_date)]
    if future.empty:
        return None

    shares = max(1, int(position_size // entry_price))
    outcome = None
    exit_price = None
    exit_date = None
    current_month = entry_date.month

    for ts, row in future.iterrows():
        days_held = (ts.to_pydatetime() - entry_date).days

        # Target hit (intraday)
        if float(row['High'].iloc[0] if hasattr(row['High'], 'iloc') else row['High']) >= target:
            outcome = 'TARGET_HIT'
            exit_price = target
            exit_date = ts
            break

        # Monthly close stop loss check
        close_val = float(row['Close'].iloc[0] if hasattr(row['Close'], 'iloc') else row['Close'])
        if ts.month != current_month:
            if close_val < stop_loss:
                outcome = 'STOP_LOSS'
                exit_price = stop_loss
                exit_date = ts
                break
            current_month = ts.month

        # Timeout after 180 days
        if days_held >= 180:
            outcome = 'TIMEOUT'
            exit_price = close_val
            exit_date = ts
            break

    if outcome is None:
        if len(future) > 0:
            outcome = 'OPEN'
            last_close = future.iloc[-1]['Close']
            exit_price = float(last_close.iloc[0] if hasattr(last_close, 'iloc') else last_close)
            exit_date = future.index[-1]
        else:
            return None

    pnl_pct = round((exit_price - entry_price) / entry_price * 100, 2)
    pnl_amount = round((exit_price - entry_price) * shares, 2)
    holding_days = (exit_date.to_pydatetime() - entry_date).days

    return {
        'entry_date': entry_date.strftime('%Y-%m-%d'),
        'exit_date': exit_date.strftime('%Y-%m-%d'),
        'entry_price': entry_price,
        'exit_price': round(exit_price, 2),
        'stop_loss': stop_loss,
        'target': target,
        'shares': shares,
        'outcome': outcome,
        'pnl_pct': pnl_pct,
        'pnl_amount': pnl_amount,
        'holding_days': holding_days
    }


def run_backtest(years=10, max_stocks=752, position_size=50000):
    print("=" * 70)
    print(f"PAST PERFORMANCE BACKTEST — LAST {years} YEAR(S)")
    print("=" * 70)

    # Load stock list
    try:
        df_stocks = pd.read_csv('Stock List.csv')
        symbols = df_stocks['Symbol'].dropna().tolist()[:max_stocks]
        print(f"✅ Loaded {len(symbols)} stocks\n")
    except Exception as e:
        print(f"❌ Cannot load Stock List.csv: {e}")
        sys.exit(1)

    end_date = datetime.now()
    start_date = end_date - timedelta(days=years * 365 + 60)  # extra buffer for monthly data

    print(f"Period : {start_date.strftime('%Y-%m-%d')} → {end_date.strftime('%Y-%m-%d')}")
    print(f"Stocks : {len(symbols)}")
    print(f"Capital: ₹{position_size:,} per trade")
    print(f"Cache  : {CACHE_DIR}\n")

    # Resume support: load partial results if they exist
    partial_file = 'backtest_performance_partial.json'
    done_symbols = set()
    all_trades = []
    stock_summaries = []

    if os.path.exists(partial_file):
        try:
            with open(partial_file) as f:
                partial = json.load(f)
            stock_summaries = partial.get('stocks', [])
            all_trades = [t for s in stock_summaries for t in s.get('trades', [])]
            done_symbols = {s['symbol'] for s in stock_summaries}
            print(f"♻️  Resuming — {len(done_symbols)} stocks already processed\n")
        except Exception:
            pass

    errors = 0

    for i, symbol in enumerate(symbols, 1):
        if symbol in done_symbols:
            print(f"[{i:3d}/{len(symbols)}] {symbol:15} ⏭️  cached")
            continue

        ticker = f"{symbol}.NS"
        try:
            # Monthly data for trendline detection (need full history)
            monthly = download_with_cache(ticker, '1mo', period='10y')
            if monthly.empty or len(monthly) < 24:
                continue

            # Flatten MultiIndex columns (yfinance >=0.2 returns MultiIndex for single ticker)
            if isinstance(monthly.columns, pd.MultiIndex):
                monthly.columns = monthly.columns.get_level_values(0)

            monthly = monthly.dropna()

            # Daily data for trade simulation (only within backtest window)
            daily = download_with_cache(ticker, '1d',
                                        start=start_date.strftime('%Y-%m-%d'),
                                        end=end_date.strftime('%Y-%m-%d'))
            if daily.empty:
                continue

            # Flatten MultiIndex columns
            if isinstance(daily.columns, pd.MultiIndex):
                daily.columns = daily.columns.get_level_values(0)

            daily = daily.dropna()

            # Find trendline signals
            signals = find_trendline_signals(monthly)
            if not signals:
                continue

            # Filter signals within backtest window
            window_signals = [
                s for s in signals
                if datetime.strptime(s['signal_date'], '%Y-%m-%d') >= start_date
            ]
            if not window_signals:
                continue

            stock_trades = []
            for sig in window_signals:
                trade = simulate_trade(daily, sig, position_size)
                if trade:
                    trade['symbol'] = symbol
                    stock_trades.append(trade)
                    all_trades.append(trade)

            if not stock_trades:
                continue

            # Per-stock summary
            wins = [t for t in stock_trades if t['pnl_pct'] > 0]
            losses = [t for t in stock_trades if t['pnl_pct'] <= 0]
            total_pnl = sum(t['pnl_amount'] for t in stock_trades)
            win_rate = round(len(wins) / len(stock_trades) * 100, 1)
            avg_return = round(sum(t['pnl_pct'] for t in stock_trades) / len(stock_trades), 2)
            best = max(stock_trades, key=lambda t: t['pnl_pct'])
            worst = min(stock_trades, key=lambda t: t['pnl_pct'])

            stock_summaries.append({
                'symbol': symbol,
                'total_trades': len(stock_trades),
                'wins': len(wins),
                'losses': len(losses),
                'win_rate': win_rate,
                'avg_return_pct': avg_return,
                'total_pnl': round(total_pnl, 2),
                'best_trade_pct': best['pnl_pct'],
                'worst_trade_pct': worst['pnl_pct'],
                'avg_holding_days': round(sum(t['holding_days'] for t in stock_trades) / len(stock_trades), 0),
                'trades': stock_trades
            })

            status = f"✅ {len(stock_trades)} trades | WR: {win_rate}% | Avg: {avg_return:+.1f}%"
            print(f"[{i:3d}/{len(symbols)}] {symbol:15} {status}")

            # Save partial progress every 10 stocks — crash-safe resume
            if len(stock_summaries) % 10 == 0:
                with open(partial_file, 'w') as pf:
                    json.dump({'stocks': stock_summaries}, pf)
                print(f"    💾 Progress saved ({len(stock_summaries)} stocks done)")

        except Exception as e:
            errors += 1
            print(f"[{i:3d}/{len(symbols)}] {symbol:15} ❌ {e}")
            continue

    # ── Overall summary ──────────────────────────────────────────────────
    total = len(all_trades)
    if total == 0:
        print("\n❌ No trades found in backtest period")
        summary = {
            'total_trades': 0, 'winning_trades': 0, 'losing_trades': 0,
            'win_rate': 0, 'avg_win_pct': 0, 'avg_loss_pct': 0,
            'avg_return_pct': 0, 'total_pnl': 0, 'avg_pnl_per_trade': 0,
            'avg_holding_days': 0, 'profit_factor': 0
        }
    else:
        wins_all = [t for t in all_trades if t['pnl_pct'] > 0]
        losses_all = [t for t in all_trades if t['pnl_pct'] <= 0]
        win_rate_all = round(len(wins_all) / total * 100, 2)
        avg_win = round(sum(t['pnl_pct'] for t in wins_all) / len(wins_all), 2) if wins_all else 0
        avg_loss = round(sum(t['pnl_pct'] for t in losses_all) / len(losses_all), 2) if losses_all else 0
        total_pnl_all = round(sum(t['pnl_amount'] for t in all_trades), 2)
        avg_holding = round(sum(t['holding_days'] for t in all_trades) / total, 1)
        gross_profit = sum(t['pnl_amount'] for t in wins_all) if wins_all else 0
        gross_loss = abs(sum(t['pnl_amount'] for t in losses_all)) if losses_all else 1
        profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else 0

        outcomes = {}
        for t in all_trades:
            outcomes[t['outcome']] = outcomes.get(t['outcome'], 0) + 1

        summary = {
            'total_trades': total,
            'winning_trades': len(wins_all),
            'losing_trades': len(losses_all),
            'win_rate': win_rate_all,
            'avg_win_pct': avg_win,
            'avg_loss_pct': avg_loss,
            'avg_return_pct': round(sum(t['pnl_pct'] for t in all_trades) / total, 2),
            'total_pnl': total_pnl_all,
            'avg_pnl_per_trade': round(total_pnl_all / total, 2),
            'avg_holding_days': avg_holding,
            'profit_factor': profit_factor,
            'outcome_breakdown': outcomes
        }

        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"Total Trades   : {total}")
        print(f"Win Rate       : {win_rate_all}%")
        print(f"Avg Win        : {avg_win:+.2f}%")
        print(f"Avg Loss       : {avg_loss:+.2f}%")
        print(f"Profit Factor  : {profit_factor}")
        print(f"Total P&L      : ₹{total_pnl_all:,.2f}")
        print(f"Avg Holding    : {avg_holding} days")
        print(f"Errors         : {errors}")

    # Sort stock summaries by total P&L descending
    stock_summaries.sort(key=lambda x: x['total_pnl'], reverse=True)

    result = {
        'generated_at': datetime.now().isoformat(),
        'backtest_years': years,
        'period': {
            'start': start_date.strftime('%Y-%m-%d'),
            'end': end_date.strftime('%Y-%m-%d')
        },
        'parameters': {
            'position_size': position_size,
            'stop_loss_pct': 8.0,
            'target_pct': 20.0,
            'entry_tolerance_pct': 2.0,
            'timeout_days': 180
        },
        'summary': summary,
        'stocks': stock_summaries
    }

    out_file = 'backtest_performance.json'
    with open(out_file, 'w') as f:
        json.dump(result, f, indent=2)

    # Clean up partial file now that we have the final result
    if os.path.exists(partial_file):
        os.remove(partial_file)
        print("🗑️  Partial progress file removed")

    print(f"\n✅ Saved → {out_file}")
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Trendline backtest')
    parser.add_argument('--years', type=int, default=10,
                        choices=[1, 3, 5, 10],
                        help='Lookback period in years (default: 10)')
    parser.add_argument('--stocks', type=int, default=752,
                        help='Max stocks to process (default: 752)')
    parser.add_argument('--capital', type=int, default=50000,
                        help='Position size in INR (default: 50000)')
    args = parser.parse_args()

    run_backtest(years=args.years, max_stocks=args.stocks, position_size=args.capital)
