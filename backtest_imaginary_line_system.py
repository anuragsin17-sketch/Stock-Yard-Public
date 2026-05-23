#!/usr/bin/env python3
"""
Backtest: Imaginary Vertical Line Trendline System
Testing 1-year performance with ₹5 lakh capital
"""

import yfinance as yf
import pandas as pd
import numpy as np
from scipy.signal import argrelextrema
from datetime import datetime, timedelta
import json
from dataclasses import dataclass
from typing import List, Dict, Optional

@dataclass
class Trade:
    """Trade record for backtest tracking"""
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

class ImaginaryLineTrendlineBacktest:
    """
    Backtest engine for imaginary vertical line trendline system
    """
    
    def __init__(self, initial_capital=500000, position_size=50000, max_positions=10):
        """
        Initialize backtest parameters
        
        Args:
            initial_capital: Starting capital (₹5 lakh)
            position_size: Fixed position size per trade (₹50k)
            max_positions: Maximum concurrent positions
        """
        self.initial_capital = initial_capital
        self.position_size = position_size
        self.max_positions = max_positions
        self.current_capital = initial_capital
        self.trades: List[Trade] = []
        self.open_positions: Dict = {}
        
    def get_sector_parameters(self, ticker):
        """Get sector-specific parameters"""
        banking_stocks = ['SBIN', 'HDFCBANK', 'ICICIBANK', 'AXISBANK', 'KOTAKBANK']
        if any(bank in ticker.upper() for bank in banking_stocks):
            return {'order': 6, 'sector': 'Banking'}
        else:
            return {'order': 12, 'sector': 'Non-Banking'}
    
    def calculate_trendline_trigger(self, df, date_idx):
        """
        Calculate trendline trigger price for a specific date using imaginary line method
        """
        try:
            # Get data up to the specific date
            historical_data = df.iloc[:date_idx+1]
            if len(historical_data) < 24:  # Need minimum 2 years
                return None
            
            historical_data = historical_data.copy()
            historical_data['Price_Idx'] = np.arange(len(historical_data))
            low_prices = historical_data['Low'].values.flatten()
            
            # Determine sector parameters
            sector_params = self.get_sector_parameters(df.attrs.get('ticker', ''))
            
            # Find major bottoms
            touchbacks = argrelextrema(low_prices, np.less, order=sector_params['order'])
            if len(touchbacks[0]) < 3:
                return None
            
            # Use last 3-4 touches
            num_touches = min(4, len(touchbacks[0]))
            recent_touches = touchbacks[0][-num_touches:]
            
            # Extract coordinates
            x_coords = [historical_data['Price_Idx'].iloc[idx] for idx in recent_touches]
            y_coords = [low_prices[idx] for idx in recent_touches]
            
            # Fit trendline
            slope, intercept = np.polyfit(x_coords, y_coords, 1)
            
            # Must be ascending
            if slope <= 0:
                return None
            
            # Calculate current trigger using imaginary vertical line
            current_month_idx = historical_data['Price_Idx'].iloc[-1]
            current_trigger = (slope * current_month_idx) + intercept
            
            # Calculate Fibonacci confluence
            confluence_score = self.calculate_confluence_score(historical_data, recent_touches, current_trigger)
            
            return {
                'trigger_price': current_trigger,
                'slope': slope,
                'confluence_score': confluence_score,
                'num_touches': num_touches
            }
            
        except Exception:
            return None
    
    def calculate_confluence_score(self, df, touch_indices, trigger_price):
        """Calculate Fibonacci confluence score"""
        try:
            last_touch_idx = touch_indices[-1]
            last_touch_price = df['Low'].iloc[last_touch_idx]
            
            # Find swing high after last touch
            data_after_touch = df.iloc[last_touch_idx:]
            swing_high = data_after_touch['High'].max()
            
            # Calculate Fibonacci levels
            fib_range = swing_high - last_touch_price
            if fib_range <= 0:
                return 0
            
            fib_levels = {
                '38.2%': swing_high - (fib_range * 0.382),
                '50.0%': swing_high - (fib_range * 0.500),
                '61.8%': swing_high - (fib_range * 0.618),
            }
            
            # Find closest Fibonacci level
            min_distance = float('inf')
            for fib_price in fib_levels.values():
                distance_pct = abs((trigger_price - fib_price) / fib_price) * 100
                min_distance = min(min_distance, distance_pct)
            
            # Score confluence
            if min_distance <= 1.0:
                return 10
            elif min_distance <= 2.0:
                return 7
            elif min_distance <= 5.0:
                return 5
            else:
                return 2
                
        except Exception:
            return 0
    
    def check_entry_signal(self, df, date_idx, ticker):
        """
        Check if there's an entry signal on a specific date
        """
        try:
            current_price = df['Close'].iloc[date_idx]
            
            # Calculate trendline trigger
            trendline_data = self.calculate_trendline_trigger(df, date_idx)
            if not trendline_data:
                return None
            
            trigger_price = trendline_data['trigger_price']
            confluence_score = trendline_data['confluence_score']
            
            # Calculate distance to trendline
            distance_pct = ((current_price - trigger_price) / trigger_price) * 100
            
            # Entry conditions (learned from teaching):
            # 1. Price within ±5% of trendline
            # 2. Minimum confluence score of 5
            if abs(distance_pct) <= 5.0 and confluence_score >= 5:
                return {
                    'entry_price': current_price,
                    'trigger_price': trigger_price,
                    'distance_pct': distance_pct,
                    'confluence_score': confluence_score,
                    'stop_loss': trigger_price * 0.92,  # 8% below trigger
                    'target': trigger_price * 1.20     # 20% above trigger
                }
            
            return None
            
        except Exception:
            return None
    
    def check_exit_conditions(self, df, date_idx, position):
        """
        Check exit conditions for open position
        """
        try:
            current_price = df['Close'].iloc[date_idx]
            current_date = df.index[date_idx]
            
            # Exit conditions:
            # 1. Stop loss hit (8% below entry trigger)
            if current_price <= position['stop_loss']:
                return 'Stop Loss', current_price
            
            # 2. Target hit (20% above entry trigger)
            if current_price >= position['target']:
                return 'Target Hit', current_price
            
            # 3. Maximum holding period (90 days)
            entry_date = pd.to_datetime(position['entry_date'])
            days_held = (current_date - entry_date).days
            if days_held >= 90:
                return 'Max Hold Period', current_price
            
            # 4. Trendline breakdown (price falls 10% below current trendline)
            trendline_data = self.calculate_trendline_trigger(df, date_idx)
            if trendline_data:
                current_trigger = trendline_data['trigger_price']
                if current_price < (current_trigger * 0.90):
                    return 'Trendline Breakdown', current_price
            
            return None, None
            
        except Exception:
            return None, None
    
    def run_backtest(self, tickers, start_date, end_date):
        """
        Run complete backtest for given period
        """
        print(f"🎯 IMAGINARY VERTICAL LINE TRENDLINE BACKTEST")
        print(f"="*70)
        print(f"📅 Period: {start_date} to {end_date}")
        print(f"💰 Initial Capital: ₹{self.initial_capital:,.0f}")
        print(f"📊 Position Size: ₹{self.position_size:,.0f}")
        print(f"🎯 Max Positions: {self.max_positions}")
        print(f"📈 Stocks to Test: {len(tickers)}")
        
        # Download data for all tickers
        stock_data = {}
        print(f"\n📥 DOWNLOADING DATA...")
        
        for i, ticker in enumerate(tickers, 1):
            try:
                print(f"   {i:2d}/{len(tickers)}: {ticker}", end="")
                df = yf.download(ticker, start="2020-01-01", end=end_date, 
                               interval="1d", auto_adjust=True, progress=False)
                if not df.empty and len(df) > 500:  # Need sufficient history
                    df.attrs['ticker'] = ticker
                    stock_data[ticker] = df
                    print(" ✅")
                else:
                    print(" ❌ Insufficient data")
            except Exception:
                print(" ❌ Error")
        
        print(f"\n✅ Successfully loaded {len(stock_data)} stocks")
        
        # Create date range for backtest
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        
        print(f"\n🔄 RUNNING BACKTEST...")
        print(f"-" * 50)
        
        # Daily backtest loop
        current_date = start_dt
        day_count = 0
        
        while current_date <= end_dt:
            day_count += 1
            
            # Progress update every 30 days
            if day_count % 30 == 0:
                print(f"   Day {day_count}: {current_date.strftime('%Y-%m-%d')} | Capital: ₹{self.current_capital:,.0f} | Positions: {len(self.open_positions)}")
            
            # Check each stock for signals
            for ticker, df in stock_data.items():
                try:
                    # Find date index in data
                    if current_date not in df.index:
                        continue
                    
                    date_idx = df.index.get_loc(current_date)
                    
                    # Check exit conditions for open positions
                    if ticker in self.open_positions:
                        exit_reason, exit_price = self.check_exit_conditions(df, date_idx, self.open_positions[ticker])
                        if exit_reason:
                            self.close_position(ticker, current_date.strftime('%Y-%m-%d'), exit_price, exit_reason)
                    
                    # Check entry conditions (if not already in position and have capital)
                    elif len(self.open_positions) < self.max_positions and self.current_capital >= self.position_size:
                        entry_signal = self.check_entry_signal(df, date_idx, ticker)
                        if entry_signal:
                            self.open_position(ticker, current_date.strftime('%Y-%m-%d'), entry_signal)
                
                except Exception:
                    continue
            
            current_date += timedelta(days=1)
        
        # Close any remaining positions at end date
        for ticker in list(self.open_positions.keys()):
            df = stock_data[ticker]
            if end_dt in df.index:
                final_price = df.loc[end_dt, 'Close']
                self.close_position(ticker, end_date, final_price, 'Backtest End')
        
        # Generate results
        self.generate_backtest_results()
    
    def open_position(self, ticker, date, signal_data):
        """Open a new position"""
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
            'confluence_score': signal_data['confluence_score']
        }
        
        self.current_capital -= actual_investment
    
    def close_position(self, ticker, date, exit_price, exit_reason):
        """Close an open position"""
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
            confluence_score=position['confluence_score']
        )
        
        self.trades.append(trade)
        self.current_capital += exit_value
        del self.open_positions[ticker]
    
    def generate_backtest_results(self):
        """Generate comprehensive backtest results"""
        if not self.trades:
            print("\n❌ No trades executed during backtest period")
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
        
        print(f"\n🏆 BACKTEST RESULTS SUMMARY")
        print(f"="*70)
        print(f"💰 CAPITAL PERFORMANCE:")
        print(f"   Initial Capital: ₹{self.initial_capital:,.0f}")
        print(f"   Final Capital: ₹{final_capital:,.0f}")
        print(f"   Total P&L: ₹{total_pnl:,.0f}")
        print(f"   Total Return: {total_return_pct:+.2f}%")
        print(f"   Annualized Return: {total_return_pct:+.2f}% (1-year test)")
        
        print(f"\n📊 TRADE STATISTICS:")
        print(f"   Total Trades: {total_trades}")
        print(f"   Winning Trades: {len(winning_trades)} ({win_rate:.1f}%)")
        print(f"   Losing Trades: {len(losing_trades)} ({100-win_rate:.1f}%)")
        print(f"   Average Holding: {avg_holding_days:.1f} days")
        
        print(f"\n💹 PERFORMANCE METRICS:")
        print(f"   Average Win: ₹{avg_win:,.0f} ({avg_win_pct:+.2f}%)")
        print(f"   Average Loss: ₹{avg_loss:,.0f} ({avg_loss_pct:+.2f}%)")
        if avg_loss != 0:
            profit_factor = abs(avg_win / avg_loss)
            print(f"   Profit Factor: {profit_factor:.2f}")
        
        # Confluence score analysis
        high_confluence_trades = [t for t in self.trades if t.confluence_score >= 7]
        if high_confluence_trades:
            high_conf_win_rate = (len([t for t in high_confluence_trades if t.pnl > 0]) / len(high_confluence_trades)) * 100
            high_conf_avg_return = np.mean([t.pnl_pct for t in high_confluence_trades])
            print(f"\n🎯 FIBONACCI CONFLUENCE ANALYSIS:")
            print(f"   High Confluence Trades (7+): {len(high_confluence_trades)}")
            print(f"   High Confluence Win Rate: {high_conf_win_rate:.1f}%")
            print(f"   High Confluence Avg Return: {high_conf_avg_return:+.2f}%")
        
        # Best and worst trades
        best_trade = max(self.trades, key=lambda t: t.pnl_pct)
        worst_trade = min(self.trades, key=lambda t: t.pnl_pct)
        
        print(f"\n🏆 BEST TRADE:")
        print(f"   {best_trade.ticker}: {best_trade.pnl_pct:+.2f}% (₹{best_trade.pnl:,.0f}) - {best_trade.exit_reason}")
        
        print(f"\n📉 WORST TRADE:")
        print(f"   {worst_trade.ticker}: {worst_trade.pnl_pct:+.2f}% (₹{worst_trade.pnl:,.0f}) - {worst_trade.exit_reason}")
        
        # Exit reason analysis
        exit_reasons = {}
        for trade in self.trades:
            exit_reasons[trade.exit_reason] = exit_reasons.get(trade.exit_reason, 0) + 1
        
        print(f"\n📋 EXIT REASON BREAKDOWN:")
        for reason, count in exit_reasons.items():
            pct = (count / total_trades) * 100
            print(f"   {reason}: {count} trades ({pct:.1f}%)")
        
        # Save detailed results
        self.save_backtest_results(final_capital, total_return_pct, win_rate)
        
        print(f"\n💾 Detailed results saved to: backtest_imaginary_line_results.json")
    
    def save_backtest_results(self, final_capital, total_return_pct, win_rate):
        """Save detailed backtest results to JSON"""
        results = {
            'backtest_summary': {
                'system': 'Imaginary Vertical Line Trendline System',
                'period': '1 Year',
                'initial_capital': self.initial_capital,
                'final_capital': final_capital,
                'total_return_pct': total_return_pct,
                'total_trades': len(self.trades),
                'win_rate': win_rate,
                'position_size': self.position_size,
                'max_positions': self.max_positions
            },
            'trades': [
                {
                    'ticker': t.ticker,
                    'entry_date': t.entry_date,
                    'entry_price': t.entry_price,
                    'exit_date': t.exit_date,
                    'exit_price': t.exit_price,
                    'exit_reason': t.exit_reason,
                    'pnl': t.pnl,
                    'pnl_pct': t.pnl_pct,
                    'days_held': t.days_held,
                    'confluence_score': t.confluence_score
                } for t in self.trades
            ]
        }
        
        with open('backtest_imaginary_line_results.json', 'w') as f:
            json.dump(results, f, indent=2)

def run_imaginary_line_backtest():
    """Run the complete backtest"""
    
    # Test stocks (mix of sectors)
    test_tickers = [
        'RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'HINDUNILVR.NS',
        'ICICIBANK.NS', 'SBIN.NS', 'BHARTIARTL.NS', 'KOTAKBANK.NS', 'ASIANPAINT.NS',
        'ITC.NS', 'AXISBANK.NS', 'LT.NS', 'NESTLEIND.NS', 'ULTRACEMCO.NS',
        'TITAN.NS', 'SUNPHARMA.NS', 'WIPRO.NS', 'MARUTI.NS', 'POWERGRID.NS',
        'BAJFINANCE.NS', 'BAJAJFINSV.NS', 'HCLTECH.NS', 'TECHM.NS', 'DRREDDY.NS'
    ]
    
    # Backtest period (1 year)
    start_date = "2023-01-01"
    end_date = "2023-12-31"
    
    # Initialize and run backtest
    backtest = ImaginaryLineTrendlineBacktest(
        initial_capital=500000,  # ₹5 lakh
        position_size=50000,     # ₹50k per position
        max_positions=10         # Max 10 concurrent positions
    )
    
    backtest.run_backtest(test_tickers, start_date, end_date)

if __name__ == "__main__":
    run_imaginary_line_backtest()