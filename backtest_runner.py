"""
Backtest Runner
Main script to execute backtesting using existing screener logic
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf
import sys
import os

# Import configuration
import backtest_config as config
from backtest_engine import BacktestEngine

# Import existing screener functions (NO MODIFICATIONS TO SCREENER.PY)
from screener import (
    detect_fibonacci_retracement,
    detect_trendline,
    detect_vertical_line_pattern
)

print("=" * 80)
print("🚀 STOCK YARD BACKTESTING ENGINE")
print("=" * 80)
print(f"📅 Period: {config.START_DATE_STR} to {config.END_DATE_STR}")
print(f"💰 Initial Capital: ₹{config.INITIAL_CAPITAL:,}")
print(f"🎯 Target: {config.TARGET_PERCENT}% | 🛑 Stop-Loss: {config.STOPLOSS_PERCENT}%")
print(f"⏱️  Max Holding: {config.MAX_HOLDING_DAYS} days")
print(f"📊 Screening Frequency: {config.SCREENING_FREQUENCY}")
print("=" * 80)
print()


def load_nifty_500_symbols():
    """Load Nifty 500 stock symbols"""
    try:
        df = pd.read_csv('ind_nifty500list.csv')
        symbols = df['Symbol'].tolist()
        print(f"✅ Loaded {len(symbols)} Nifty 500 stocks")
        return symbols
    except Exception as e:
        print(f"❌ Error loading Nifty 500 list: {e}")
        return []


def download_historical_data(symbol, start_date, end_date):
    """Download historical data for a symbol"""
    try:
        ticker = yf.Ticker(f"{symbol}.NS")
        df = ticker.history(start=start_date, end=end_date)
        
        if df.empty:
            return None
        
        return df
    except Exception as e:
        return None


def run_screening_on_date(symbols, screening_date, engine):
    """
    Run Golden Stocks screening logic on a specific date
    This simulates what the screener would have found on that date
    """
    print(f"\n📅 Screening Date: {screening_date.strftime('%Y-%m-%d')}")
    
    golden_stocks = []
    successful = 0
    failed = 0
    
    for i, symbol in enumerate(symbols):
        if config.VERBOSE and (i + 1) % 50 == 0:
            print(f"  Progress: {i+1}/{len(symbols)} stocks processed...")
        
        try:
            # Download data UP TO screening date (avoid look-ahead bias)
            # Get 5 years of history for pattern detection
            data_start = screening_date - timedelta(days=5*365)
            df = download_historical_data(symbol, data_start, screening_date)
            
            if df is None or len(df) < 100:  # Need minimum data
                failed += 1
                continue
            
            # Get current price (as of screening date)
            current_price = df['Close'].iloc[-1]
            
            # Calculate 52-week high/low
            last_year_data = df.tail(252)  # ~1 year of trading days
            week_52_high = last_year_data['High'].max()
            week_52_low = last_year_data['Low'].min()
            
            # Run Fibonacci detection (from your screener.py)
            fib_result = detect_fibonacci_retracement(df, current_price)
            
            # Run Trendline detection (from your screener.py)
            trendline_result = detect_trendline(df, current_price)
            
            # Run Vertical Line detection (from your screener.py)
            vertical_result = detect_vertical_line_pattern(df, current_price)
            
            # Determine if this is a Golden Stock signal
            has_fibonacci = fib_result is not None
            has_trendline = trendline_result is not None
            has_vertical = vertical_result is not None
            
            # Must have at least Fibonacci OR Trendline
            if not (has_fibonacci or has_trendline):
                successful += 1
                continue
            
            # Calculate potential upside
            if has_fibonacci:
                potential_upside = ((week_52_high - current_price) / current_price) * 100
            elif has_trendline:
                potential_upside = ((week_52_high - current_price) / current_price) * 100
            else:
                potential_upside = 0
            
            # Filter by minimum upside
            if potential_upside < config.MIN_UPSIDE_PERCENT:
                successful += 1
                continue
            
            # Determine entry quality
            if has_fibonacci and has_trendline:
                if fib_result.get('distance_percent', 100) < 1.0 and trendline_result.get('distance_percent', 100) < 1.0:
                    entry_quality = "Excellent - Double Signal"
                else:
                    entry_quality = "Good - Double Signal"
            elif has_fibonacci:
                entry_quality = f"Excellent - Fibonacci"
            elif has_trendline:
                entry_quality = f"Excellent - Trendline"
            else:
                entry_quality = "Good"
            
            # Apply filters if configured
            if config.ENTRY_QUALITY_FILTER and entry_quality != config.ENTRY_QUALITY_FILTER:
                successful += 1
                continue
            
            if config.FIBONACCI_LEVEL_FILTER and has_fibonacci:
                if fib_result.get('level') != config.FIBONACCI_LEVEL_FILTER:
                    successful += 1
                    continue
            
            # Create signal
            signal = {
                'symbol': symbol,
                'current_price': current_price,
                'week_52_high': week_52_high,
                'week_52_low': week_52_low,
                'potential_upside_percent': potential_upside,
                'entry_quality': entry_quality,
                'has_fibonacci': has_fibonacci,
                'has_trendline': has_trendline,
                'has_vertical_line': has_vertical,
                'fibonacci_level': fib_result.get('level') if has_fibonacci else None,
                'fibonacci_level_price': fib_result.get('level_price') if has_fibonacci else None,
                'trendline_price': trendline_result.get('trendline_price') if has_trendline else None,
                'vertical_line_price': vertical_result.get('vertical_line_price') if has_vertical else None,
            }
            
            golden_stocks.append(signal)
            successful += 1
            
        except Exception as e:
            if config.VERBOSE:
                print(f"  ⚠️ Error processing {symbol}: {e}")
            failed += 1
            continue
    
    print(f"  ✅ Processed: {successful} | ❌ Failed: {failed}")
    print(f"  🎯 Golden Stocks Found: {len(golden_stocks)}")
    
    # Process signals - attempt to enter trades
    for signal in golden_stocks:
        engine.execute_trade_entry(signal, screening_date)
    
    return golden_stocks


def generate_screening_dates(start_date, end_date, frequency):
    """Generate dates for screening based on frequency"""
    dates = []
    current = start_date
    
    if frequency == "DAILY":
        delta = timedelta(days=1)
    elif frequency == "WEEKLY":
        delta = timedelta(weeks=1)
    elif frequency == "BIWEEKLY":
        delta = timedelta(weeks=2)
    else:
        delta = timedelta(weeks=1)
    
    while current <= end_date:
        # Skip weekends
        if current.weekday() < 5:  # Monday = 0, Friday = 4
            dates.append(current)
        current += delta
    
    return dates


def main():
    """Main backtesting execution"""
    
    # Initialize engine
    engine = BacktestEngine(config)
    
    # Load stock symbols
    symbols = load_nifty_500_symbols()
    if not symbols:
        print("❌ Failed to load stock symbols. Exiting.")
        return
    
    # Generate screening dates
    screening_dates = generate_screening_dates(
        config.START_DATE,
        config.END_DATE,
        config.SCREENING_FREQUENCY
    )
    
    print(f"\n📊 Total screening dates: {len(screening_dates)}")
    print(f"First: {screening_dates[0].strftime('%Y-%m-%d')}")
    print(f"Last: {screening_dates[-1].strftime('%Y-%m-%d')}")
    
    # Main backtest loop
    print("\n" + "=" * 80)
    print("🔄 STARTING BACKTEST")
    print("=" * 80)
    
    for date_idx, screening_date in enumerate(screening_dates):
        print(f"\n[{date_idx + 1}/{len(screening_dates)}] ", end="")
        
        # Run screening on this date
        signals = run_screening_on_date(symbols, screening_date, engine)
        
        # Check exit conditions for all open positions
        for trade in engine.open_positions[:]:  # Use slice to avoid modification during iteration
            should_exit, exit_price, exit_reason = engine.check_exit_conditions(trade, screening_date)
            
            if should_exit:
                engine.execute_trade_exit(trade, screening_date, exit_price, exit_reason)
        
        # Update equity curve
        engine.update_equity_curve(screening_date)
        
        # Show current status
        print(f"  💼 Open Positions: {len(engine.open_positions)} | 💰 Available Capital: ₹{engine.capital:,.0f}")
    
    # Close any remaining open positions at the end
    print("\n" + "=" * 80)
    print("🔚 CLOSING REMAINING POSITIONS")
    print("=" * 80)
    
    for trade in engine.open_positions[:]:
        # Get final price
        final_data = engine.download_price_data(trade.symbol, trade.entry_date, config.END_DATE)
        if final_data is not None and not final_data.empty:
            final_price = final_data['Close'].iloc[-1]
            engine.execute_trade_exit(trade, config.END_DATE, final_price, 'BACKTEST_END')
    
    # Generate results
    print("\n" + "=" * 80)
    print("📊 BACKTEST RESULTS")
    print("=" * 80)
    
    metrics = engine.get_performance_metrics()
    
    print(f"\n📈 TRADE STATISTICS:")
    print(f"  Total Trades: {metrics['total_trades']}")
    print(f"  Winners (Target Hit): {metrics['winners']} ({metrics['win_rate']:.1f}%)")
    print(f"  Losers (Stop-Loss Hit): {metrics['losers']}")
    print(f"  Timeouts: {metrics['timeouts']}")
    print(f"  Average Holding Period: {metrics['avg_holding_days']:.1f} days")
    
    print(f"\n💰 PROFIT & LOSS:")
    print(f"  Total P&L: ₹{metrics['total_pnl']:,.2f}")
    print(f"  Average Win: ₹{metrics['avg_win']:,.2f}")
    print(f"  Average Loss: ₹{metrics['avg_loss']:,.2f}")
    print(f"  Profit Factor: {metrics['profit_factor']:.2f}")
    
    print(f"\n📊 PORTFOLIO PERFORMANCE:")
    print(f"  Initial Capital: ₹{metrics['initial_capital']:,.2f}")
    print(f"  Final Equity: ₹{metrics['final_equity']:,.2f}")
    print(f"  Total Return: {metrics['total_return_percent']:+.2f}%")
    print(f"  Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
    print(f"  Max Drawdown: {metrics['max_drawdown_percent']:.2f}%")
    
    # Save results
    print("\n" + "=" * 80)
    print("💾 SAVING RESULTS")
    print("=" * 80)
    engine.save_results()
    
    print("\n✅ Backtest completed successfully!")
    print(f"📁 Results saved in: {config.RESULTS_FOLDER}/")
    print("=" * 80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Backtest interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error during backtest: {e}")
        import traceback
        traceback.print_exc()
