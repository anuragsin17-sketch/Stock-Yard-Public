#!/usr/bin/env python3
"""
Recent 1-Year Backtest: 2024-2026 (Last 1 Year)
Testing Imaginary Vertical Line System on Recent Data
"""

import yfinance as yf
import pandas as pd
import numpy as np
from scipy.signal import argrelextrema
from datetime import datetime, timedelta
import json
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class Trade:
    ticker: str
    entry_date: str
    entry_price: float
    exit_date: str
    exit_price: float
    exit_reason: str
    quantity: int
    investment: float
    pnl: float
    pnl_pct: float
    days_held: int
    confluence_score: int
    distance_at_entry: float

class Recent1YearBacktest:
    """
    Backtest for recent 1-year period (2025-2026)
    """
    
    def __init__(self, initial_capital=500000, position_size=50000, max_positions=10):
        self.initial_capital = initial_capital
        self.position_size = position_size
        self.max_positions = max_positions
        self.current_capital = initial_capital
        self.trades: List[Trade] = []
        self.open_positions: Dict = {}
        
    def get_sector_parameters(self, ticker):
        """Get sector-specific parameters (learned from teaching)"""
        banking_stocks = ['SBIN', 'HDFCBANK', 'ICICIBANK', 'AXISBANK', 'KOTAKBANK', 
                         'INDUSINDBK', 'FEDERALBNK', 'BANDHANBNK']
        if any(bank in ticker.upper() for bank in banking_stocks):
            return {'order': 6, 'sector': 'Banking'}  # Banking uses order=6
        else:
            return {'order': 8, 'sector': 'Non-Banking'}  # Reduced for more signals
    
    def calculate_trendline_trigger(self, df, date_idx):
        """Calculate trendline using imaginary vertical line method"""
        try:
            # Get historical data up to current date
            historical_data = df.iloc[:date_idx+1]
            if len(historical_data) < 36:  # Need minimum 3 years for monthly trendline
                return None
            
            # Create monthly data for trendline calculation
            monthly_data = historical_data.resample('M').agg({
                'Open': 'first',
                'High': 'max', 
                'Low': 'min',
                'Close': 'last',
                'Volume': 'sum'
            }).dropna()
            
            if len(monthly_data) < 24:  # Need minimum 2 years monthly
                return None
            
            monthly_data['Price_Idx'] = np.arange(len(monthly_data))
            low_prices = monthly_data['Low'].values.flatten()
            
            # Get sector parameters
            sector_params = self.get_sector_parameters(df.attrs.get('ticker', ''))
            
            # Find major bottoms using learned order parameters
            touchbacks = argrelextrema(low_prices, np.less, order=sector_params['order'])
            if len(touchbacks[0]) < 3:  # Need minimum 3 touches (learned requirement)
                return None
            
            # Use last 3-4 touches for most relevant trendline
            num_touches = min(4, len(touchbacks[0]))
            recent_touches = touchbacks[0][-num_touches:]
            
            # Extract coordinates for trendline
            x_coords = [monthly_data['Price_Idx'].iloc[idx] for idx in recent_touches]
            y_coords = [low_prices[idx] for idx in recent_touches]
            
            # Fit trendline
            slope, intercept = np.polyfit(x_coords, y_coords, 1)
            
            # Must be ascending (learned requirement)
            if slope <= 0:
                return None
            
            # Apply imaginary vertical line method
            current_month_idx = monthly_data['Price_Idx'].iloc[-1]
            current_trigger = (slope * current_month_idx) + intercept
            
            # Validate trigger price is reasonable
            current_price = historical_data['Close'].iloc[-1]
            if current_trigger <= 0 or current_trigger > current_price * 1.5:
                return None
            
            # Calculate Fibonacci confluence
            confluence_score = self.calculate_fibonacci_confluence(monthly_data, recent_touches, current_trigger)
            
            # Calculate R-squared for trendline strength
            predicted_prices = [slope * x + intercept for x in x_coords]
            correlation = np.corrcoef(y_coords, predicted_prices)[0, 1]
            r_squared = correlation ** 2 if not np.isnan(correlation) else 0
            
            return {
                'trigger_price': current_trigger,
                'slope': slope,
                'confluence_score': confluence_score,
                'num_touches': num_touches,
                'r_squared': r_squared,
                'monthly_growth': slope,  # Monthly growth rate (learned concept)
                'touch_dates': [monthly_data.index[idx].strftime('%Y-%m') for idx in recent_touches]
            }
            
        except Exception as e:
            return None
    
    def calculate_fibonacci_confluence(self, monthly_data, touch_indices, trigger_price):
        """Calculate Fibonacci confluence score (learned from teaching)"""
        try:
            if len(touch_indices) < 2:
                return 3
            
            # Get last touch point
            last_touch_idx = touch_indices[-1]
            last_touch_price = monthly_data['Low'].iloc[last_touch_idx]
            
            # Find swing high after last touch
            data_after_touch = monthly_data.iloc[last_touch_idx:]
            if len(data_after_touch) == 0:
                return 3
            
            swing_high = data_after_touch['High'].max()
            
            # Calculate Fibonacci retracement levels
            fib_range = swing_high - last_touch_price
            if fib_range <= 0:
                return 3
            
            # Key Fibonacci levels (learned from teaching)
            fib_levels = {
                '23.6%': swing_high - (fib_range * 0.236),
                '38.2%': swing_high - (fib_range * 0.382),
                '50.0%': swing_high - (fib_range * 0.500),
                '61.8%': swing_high - (fib_range * 0.618),  # Golden ratio
                '78.6%': swing_high - (fib_range * 0.786)
            }
            
            # Find closest Fibonacci level to trigger price
            min_distance = float('inf')
            closest_level = None
            
            for level_name, fib_price in fib_levels.items():
                distance_pct = abs((trigger_price - fib_price) / fib_price) * 100
                if distance_pct < min_distance:
                    min_distance = distance_pct
                    closest_level = level_name
            
            # Score confluence based on learned system
            if min_distance <= 1.0 and closest_level in ['38.2%', '50.0%', '61.8%']:
                confluence_score = 10  # Perfect confluence
            elif min_distance <= 2.0:
                confluence_score = 7   # Good confluence
            elif min_distance <= 5.0 and closest_level in ['38.2%', '50.0%', '61.8%']:
                confluence_score = 5   # Moderate confluence
            else:
                confluence_score = 2   # Weak confluence
            
            # Golden ratio bonus (learned enhancement)
            if closest_level == '61.8%' and min_distance <= 3.0:
                confluence_score += 3
                confluence_score = min(10, confluence_score)
            
            return confluence_score
                
        except Exception:
            return 3
    
    def check_entry_signal(self, df, date_idx, ticker):
        """Check for entry signal using learned methodology"""
        try:
            current_price = df['Close'].iloc[date_idx]
            
            # Calculate trendline trigger using imaginary vertical line
            trendline_data = self.calculate_trendline_trigger(df, date_idx)
            if not trendline_data:
                return None
            
            trigger_price = trendline_data['trigger_price']
            confluence_score = trendline_data['confluence_score']
            r_squared = trendline_data['r_squared']
            
            # Calculate distance to trendline (learned tolerance)
            distance_pct = ((current_price - trigger_price) / trigger_price) * 100
            
            # Entry conditions based on learned system:
            # 1. Price within ±5% of trendline (learned tolerance)
            # 2. Minimum confluence score of 5 (institutional zones)
            # 3. Strong trendline (R² > 0.7)
            # 4. Minimum 3 touch points
            if (abs(distance_pct) <= 5.0 and 
                confluence_score >= 5 and 
                r_squared >= 0.7 and 
                trendline_data['num_touches'] >= 3):
                
                return {
                    'entry_price': current_price,
                    'trigger_price': trigger_price,
                    'distance_pct': distance_pct,
                    'confluence_score': confluence_score,
                    'r_squared': r_squared,
                    'monthly_growth': trendline_data['monthly_growth'],
                    'stop_loss': trigger_price * 0.92,  # 8% below trigger (learned)
                    'target': trigger_price * 1.20,    # 20% above trigger (learned)
                    'touch_dates': trendline_data['touch_dates']
                }
            
            return None
            
        except Exception:
            return None
    
    def check_exit_conditions(self, df, date_idx, position):
        """Check exit conditions"""
        try:
            current_price = df['Close'].iloc[date_idx]
            current_date = df.index[date_idx]
            
            # Exit conditions:
            # 1. Stop loss hit (8% below trigger)
            if current_price <= position['stop_loss']:
                return 'Stop Loss', current_price
            
            # 2. Target hit (20% above trigger)
            if current_price >= position['target']:
                return 'Target Hit', current_price
            
            # 3. Maximum holding period (90 days)
            entry_date = pd.to_datetime(position['entry_date'])
            days_held = (current_date - entry_date).days
            if days_held >= 90:
                return 'Max Hold Period', current_price
            
            # 4. Trendline breakdown check
            trendline_data = self.calculate_trendline_trigger(df, date_idx)
            if trendline_data:
                current_trigger = trendline_data['trigger_price']
                # Exit if price falls 10% below current trendline
                if current_price < (current_trigger * 0.90):
                    return 'Trendline Breakdown', current_price
            
            return None, None
            
        except Exception:
            return None, None
    
    def run_backtest(self, tickers, start_date, end_date):
        """Run backtest for recent 1-year period"""
        print(f"🎯 RECENT 1-YEAR IMAGINARY VERTICAL LINE BACKTEST")
        print(f"="*70)
        print(f"📅 Period: {start_date} to {end_date}")
        print(f"💰 Initial Capital: ₹{self.initial_capital:,.0f}")
        print(f"📊 Position Size: ₹{self.position_size:,.0f}")
        print(f"🎯 Max Positions: {self.max_positions}")
        print(f"📈 Stocks to Test: {len(tickers)}")
        print(f"📚 METHODOLOGY:")
        print(f"   • Imaginary vertical line method")
        print(f"   • Monthly trendline calculation")
        print(f"   • Banking: order=6, Others: order=8")
        print(f"   • Entry tolerance: ±5%")
        print(f"   • Min confluence: 5/10")
        print(f"   • Min R²: 0.7")
        
        # Download data for all tickers
        stock_data = {}
        print(f"\n📥 DOWNLOADING DATA...")
        
        for i, ticker in enumerate(tickers, 1):
            try:
                print(f"   {i:2d}/{len(tickers)}: {ticker}", end="")
                # Download 5 years of data to ensure sufficient history
                df = yf.download(ticker, start="2020-01-01", end=end_date, 
                               interval="1d", auto_adjust=True, progress=False)
                if not df.empty and len(df) > 500:
                    df.attrs['ticker'] = ticker
                    stock_data[ticker] = df
                    print(" ✅")
                else:
                    print(" ❌ Insufficient data")
            except Exception:
                print(" ❌ Error")
        
        print(f"\n✅ Successfully loaded {len(stock_data)} stocks")
        
        # Run backtest
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        
        print(f"\n🔄 RUNNING BACKTEST...")
        print(f"-" * 50)
        
        current_date = start_dt
        day_count = 0
        signal_count = 0
        
        while current_date <= end_dt:
            day_count += 1
            
            # Progress update every 30 days
            if day_count % 30 == 0:
                print(f"   Day {day_count}: {current_date.strftime('%Y-%m-%d')} | Capital: ₹{self.current_capital:,.0f} | Positions: {len(self.open_positions)} | Signals: {signal_count}")
            
            # Check each stock
            for ticker, df in stock_data.items():
                try:
                    # Skip weekends and holidays
                    if current_date not in df.index:
                        continue
                    
                    date_idx = df.index.get_loc(current_date)
                    
                    # Check exit conditions for open positions
                    if ticker in self.open_positions:
                        exit_reason, exit_price = self.check_exit_conditions(df, date_idx, self.open_positions[ticker])
                        if exit_reason:
                            self.close_position(ticker, current_date.strftime('%Y-%m-%d'), exit_price, exit_reason)
                    
                    # Check entry conditions
                    elif len(self.open_positions) < self.max_positions and self.current_capital >= self.position_size:
                        entry_signal = self.check_entry_signal(df, date_idx, ticker)
                        if entry_signal:
                            signal_count += 1
                            self.open_position(ticker, current_date.strftime('%Y-%m-%d'), entry_signal)
                            print(f"   📈 ENTRY: {ticker} at ₹{entry_signal['entry_price']:.2f} | Distance: {entry_signal['distance_pct']:+.1f}% | Confluence: {entry_signal['confluence_score']}/10")
                
                except Exception:
                    continue
            
            current_date += timedelta(days=1)
        
        # Close any remaining positions at end
        for ticker in list(self.open_positions.keys()):
            df = stock_data[ticker]
            if end_dt in df.index:
                final_price = df.loc[end_dt, 'Close']
                self.close_position(ticker, end_date, final_price, 'Backtest End')
        
        # Generate comprehensive results
        self.generate_results()
    
    def open_position(self, ticker, date, signal_data):
        """Open new position"""
        entry_price = signal_data['entry_price']
        quantity = int(self.position_size / entry_price)
        actual_investment = quantity * entry_price
        
        self.open_positions[ticker] = {
            'ticker': ticker,
            'entry_date': date,
            'entry_price': entry_price,
            'quantity': quantity,
            'investment': actual_investment,
            'stop_loss': signal_data['stop_loss'],
            'target': signal_data['target'],
            'confluence_score': signal_data['confluence_score'],
            'distance_at_entry': signal_data['distance_pct'],
            'r_squared': signal_data['r_squared'],
            'monthly_growth': signal_data['monthly_growth'],
            'touch_dates': signal_data['touch_dates']
        }
        
        self.current_capital -= actual_investment
    
    def close_position(self, ticker, date, exit_price, exit_reason):
        """Close position and record trade"""
        position = self.open_positions[ticker]
        
        exit_value = position['quantity'] * exit_price
        pnl = exit_value - position['investment']
        pnl_pct = (pnl / position['investment']) * 100
        
        entry_date = pd.to_datetime(position['entry_date'])
        exit_date = pd.to_datetime(date)
        days_held = (exit_date - entry_date).days
        
        trade = Trade(
            ticker=ticker,
            entry_date=position['entry_date'],
            entry_price=position['entry_price'],
            exit_date=date,
            exit_price=exit_price,
            exit_reason=exit_reason,
            quantity=position['quantity'],
            investment=position['investment'],
            pnl=pnl,
            pnl_pct=pnl_pct,
            days_held=days_held,
            confluence_score=position['confluence_score'],
            distance_at_entry=position['distance_at_entry']
        )
        
        self.trades.append(trade)
        self.current_capital += exit_value
        del self.open_positions[ticker]
        
        print(f"   📊 EXIT: {ticker} at ₹{exit_price:.2f} | P&L: {pnl_pct:+.1f}% | Days: {days_held} | Reason: {exit_reason}")
    
    def generate_results(self):
        """Generate comprehensive backtest results"""
        print(f"\n🏆 RECENT 1-YEAR BACKTEST RESULTS")
        print(f"="*70)
        
        if not self.trades:
            print("❌ No trades executed during backtest period")
            print("\n🔍 POSSIBLE REASONS:")
            print("   • Market conditions didn't provide trendline touches")
            print("   • Entry criteria too strict (±5% tolerance)")
            print("   • High confluence requirement (5/10 minimum)")
            print("   • Strong trendline requirement (R² > 0.7)")
            return
        
        # Calculate performance metrics
        total_trades = len(self.trades)
        winning_trades = [t for t in self.trades if t.pnl > 0]
        losing_trades = [t for t in self.trades if t.pnl <= 0]
        
        win_rate = (len(winning_trades) / total_trades) * 100
        total_pnl = sum(t.pnl for t in self.trades)
        total_return_pct = (total_pnl / self.initial_capital) * 100
        final_capital = self.initial_capital + total_pnl
        
        avg_win = np.mean([t.pnl for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t.pnl for t in losing_trades]) if losing_trades else 0
        avg_win_pct = np.mean([t.pnl_pct for t in winning_trades]) if winning_trades else 0
        avg_loss_pct = np.mean([t.pnl_pct for t in losing_trades]) if losing_trades else 0
        
        avg_holding_days = np.mean([t.days_held for t in self.trades])
        
        print(f"💰 CAPITAL PERFORMANCE:")
        print(f"   Initial Capital: ₹{self.initial_capital:,.0f}")
        print(f"   Final Capital: ₹{final_capital:,.0f}")
        print(f"   Total P&L: ₹{total_pnl:,.0f}")
        print(f"   Total Return: {total_return_pct:+.2f}%")
        print(f"   Annualized Return: {total_return_pct:+.2f}% (1-year)")
        
        print(f"\n📊 TRADE STATISTICS:")
        print(f"   Total Trades: {total_trades}")
        print(f"   Winning Trades: {len(winning_trades)} ({win_rate:.1f}%)")
        print(f"   Losing Trades: {len(losing_trades)} ({100-win_rate:.1f}%)")
        print(f"   Average Holding: {avg_holding_days:.1f} days")
        
        print(f"\n💹 PERFORMANCE METRICS:")
        print(f"   Average Win: ₹{avg_win:,.0f} ({avg_win_pct:+.2f}%)")
        print(f"   Average Loss: ₹{avg_loss:,.0f} ({avg_loss_pct:+.2f}%)")
        
        if len(winning_trades) > 0 and len(losing_trades) > 0:
            total_wins = sum(t.pnl for t in winning_trades)
            total_losses = abs(sum(t.pnl for t in losing_trades))
            profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
            print(f"   Profit Factor: {profit_factor:.2f}")
        
        # System validation
        print(f"\n🎯 IMAGINARY VERTICAL LINE SYSTEM VALIDATION:")
        if total_return_pct > 15 and win_rate >= 60:
            print(f"   ✅ EXCELLENT SYSTEM: {total_return_pct:+.1f}% return, {win_rate:.1f}% win rate")
        elif total_return_pct > 10 and win_rate >= 50:
            print(f"   ✅ GOOD SYSTEM: {total_return_pct:+.1f}% return, {win_rate:.1f}% win rate")
        elif total_return_pct > 0:
            print(f"   ⚠️  MARGINAL SYSTEM: {total_return_pct:+.1f}% return, {win_rate:.1f}% win rate")
        else:
            print(f"   ❌ NEEDS OPTIMIZATION: {total_return_pct:+.1f}% return, {win_rate:.1f}% win rate")
        
        # Best trades analysis
        if len(self.trades) >= 3:
            best_trades = sorted(self.trades, key=lambda t: t.pnl_pct, reverse=True)[:3]
            print(f"\n🏆 TOP 3 TRADES:")
            for i, trade in enumerate(best_trades, 1):
                print(f"   {i}. {trade.ticker}: {trade.pnl_pct:+.2f}% (₹{trade.pnl:,.0f}) - {trade.days_held} days - Confluence: {trade.confluence_score}/10")
        
        # Exit reason analysis
        exit_reasons = {}
        for trade in self.trades:
            exit_reasons[trade.exit_reason] = exit_reasons.get(trade.exit_reason, 0) + 1
        
        print(f"\n📋 EXIT ANALYSIS:")
        for reason, count in exit_reasons.items():
            pct = (count / total_trades) * 100
            print(f"   {reason}: {count} trades ({pct:.1f}%)")
        
        # Save results
        self.save_results(final_capital, total_return_pct, win_rate)
        print(f"\n💾 Results saved to: backtest_recent_1year_results.json")

    def save_results(self, final_capital, total_return_pct, win_rate):
        """Save detailed results"""
        results = {
            'system': 'Imaginary Vertical Line Trendline System',
            'period': 'Recent 1 Year (2025-2026)',
            'methodology': 'Monthly trendline with imaginary vertical line trigger points',
            'initial_capital': self.initial_capital,
            'final_capital': final_capital,
            'total_return_pct': total_return_pct,
            'total_trades': len(self.trades),
            'win_rate': win_rate,
            'entry_criteria': {
                'tolerance': '±5%',
                'min_confluence': 5,
                'min_r_squared': 0.7,
                'min_touches': 3
            },
            'trades': [
                {
                    'ticker': t.ticker,
                    'entry_date': t.entry_date,
                    'entry_price': t.entry_price,
                    'exit_date': t.exit_date,
                    'exit_price': t.exit_price,
                    'pnl_pct': t.pnl_pct,
                    'days_held': t.days_held,
                    'exit_reason': t.exit_reason,
                    'confluence_score': t.confluence_score,
                    'distance_at_entry': t.distance_at_entry
                } for t in self.trades
            ]
        }
        
        with open('backtest_recent_1year_results.json', 'w') as f:
            json.dump(results, f, indent=2)

def run_recent_1year_backtest():
    """Run backtest for recent 1-year period"""
    
    # Popular Indian stocks for testing
    test_tickers = [
        'RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'HINDUNILVR.NS',
        'ICICIBANK.NS', 'SBIN.NS', 'BHARTIARTL.NS', 'KOTAKBANK.NS', 'ASIANPAINT.NS',
        'ITC.NS', 'AXISBANK.NS', 'LT.NS', 'TITAN.NS', 'WIPRO.NS',
        'MARUTI.NS', 'BAJFINANCE.NS', 'HCLTECH.NS', 'SUNPHARMA.NS', 'ULTRACEMCO.NS',
        'NESTLEIND.NS', 'POWERGRID.NS', 'TECHM.NS', 'DRREDDY.NS', 'COALINDIA.NS'
    ]
    
    # Recent 1-year period (May 2025 to May 2026)
    start_date = "2025-05-01"
    end_date = "2026-05-01"
    
    # Initialize and run backtest
    backtest = Recent1YearBacktest(
        initial_capital=500000,  # ₹5 lakh
        position_size=50000,     # ₹50k per position
        max_positions=10         # Max 10 concurrent positions
    )
    
    backtest.run_backtest(test_tickers, start_date, end_date)

if __name__ == "__main__":
    run_recent_1year_backtest()