#!/usr/bin/env python3
"""
Optimized Backtest: Imaginary Vertical Line System
Adjusted parameters for realistic trading opportunities
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

class OptimizedImaginaryLineBacktest:
    """
    Optimized backtest with more realistic entry conditions
    """
    
    def __init__(self, initial_capital=500000, position_size=50000, max_positions=10):
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
            return {'order': 10, 'sector': 'Non-Banking'}  # Reduced from 12 to 10 for more signals
    
    def calculate_trendline_trigger(self, df, date_idx):
        """Calculate trendline with optimized parameters"""
        try:
            # Get data up to specific date
            historical_data = df.iloc[:date_idx+1]
            if len(historical_data) < 50:  # Reduced minimum requirement
                return None
            
            historical_data = historical_data.copy()
            historical_data['Price_Idx'] = np.arange(len(historical_data))
            low_prices = historical_data['Low'].values.flatten()
            
            # Get sector parameters
            sector_params = self.get_sector_parameters(df.attrs.get('ticker', ''))
            
            # Find major bottoms with relaxed order
            touchbacks = argrelextrema(low_prices, np.less, order=sector_params['order'])
            if len(touchbacks[0]) < 2:  # Reduced from 3 to 2
                return None
            
            # Use last 2-3 touches for more recent relevance
            num_touches = min(3, len(touchbacks[0]))
            recent_touches = touchbacks[0][-num_touches:]
            
            # Extract coordinates
            x_coords = [historical_data['Price_Idx'].iloc[idx] for idx in recent_touches]
            y_coords = [low_prices[idx] for idx in recent_touches]
            
            # Fit trendline
            slope, intercept = np.polyfit(x_coords, y_coords, 1)
            
            # Must be ascending (relaxed requirement)
            if slope <= 0:
                return None
            
            # Calculate current trigger
            current_month_idx = historical_data['Price_Idx'].iloc[-1]
            current_trigger = (slope * current_month_idx) + intercept
            
            # Ensure trigger is reasonable (not too far from current price)
            current_price = historical_data['Close'].iloc[-1]
            if current_trigger <= 0 or current_trigger > current_price * 2:
                return None
            
            # Calculate confluence score (simplified)
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
        """Simplified confluence calculation"""
        try:
            if len(touch_indices) < 2:
                return 3
            
            last_touch_idx = touch_indices[-1]
            last_touch_price = df['Low'].iloc[last_touch_idx]
            
            # Find recent high
            recent_data = df.iloc[max(0, last_touch_idx-20):last_touch_idx+20]
            if len(recent_data) == 0:
                return 3
            
            swing_high = recent_data['High'].max()
            
            # Simple Fibonacci calculation
            fib_range = swing_high - last_touch_price
            if fib_range <= 0:
                return 3
            
            # Check if trigger is near key Fibonacci levels
            fib_618 = swing_high - (fib_range * 0.618)
            fib_500 = swing_high - (fib_range * 0.500)
            fib_382 = swing_high - (fib_range * 0.382)
            
            distances = [
                abs((trigger_price - fib_618) / fib_618) * 100,
                abs((trigger_price - fib_500) / fib_500) * 100,
                abs((trigger_price - fib_382) / fib_382) * 100
            ]
            
            min_distance = min(distances)
            
            if min_distance <= 3.0:
                return 8
            elif min_distance <= 5.0:
                return 6
            elif min_distance <= 10.0:
                return 4
            else:
                return 3
                
        except Exception:
            return 3
    
    def check_entry_signal(self, df, date_idx, ticker):
        """Optimized entry signal detection"""
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
            
            # OPTIMIZED Entry conditions:
            # 1. Price within ±15% of trendline (increased from ±5%)
            # 2. Minimum confluence score of 3 (reduced from 5)
            # 3. Price above trigger (buying on strength near support)
            if -5.0 <= distance_pct <= 15.0 and confluence_score >= 3:
                return {
                    'entry_price': current_price,
                    'trigger_price': trigger_price,
                    'distance_pct': distance_pct,
                    'confluence_score': confluence_score,
                    'stop_loss': trigger_price * 0.90,  # 10% below trigger (wider stop)
                    'target': current_price * 1.25     # 25% above entry (higher target)
                }
            
            return None
            
        except Exception:
            return None
    
    def check_exit_conditions(self, df, date_idx, position):
        """Optimized exit conditions"""
        try:
            current_price = df['Close'].iloc[date_idx]
            current_date = df.index[date_idx]
            
            # Exit conditions:
            # 1. Stop loss hit
            if current_price <= position['stop_loss']:
                return 'Stop Loss', current_price
            
            # 2. Target hit
            if current_price >= position['target']:
                return 'Target Hit', current_price
            
            # 3. Maximum holding period (120 days - extended)
            entry_date = pd.to_datetime(position['entry_date'])
            days_held = (current_date - entry_date).days
            if days_held >= 120:
                return 'Max Hold Period', current_price
            
            # 4. Trailing stop (if up 10%, trail stop to breakeven)
            entry_price = position['entry_price']
            if current_price >= entry_price * 1.10:  # Up 10%
                if current_price <= entry_price * 1.02:  # Trail to 2% profit
                    return 'Trailing Stop', current_price
            
            return None, None
            
        except Exception:
            return None, None
    
    def run_backtest(self, tickers, start_date, end_date):
        """Run optimized backtest"""
        print(f"🎯 OPTIMIZED IMAGINARY VERTICAL LINE BACKTEST")
        print(f"="*70)
        print(f"📅 Period: {start_date} to {end_date}")
        print(f"💰 Initial Capital: ₹{self.initial_capital:,.0f}")
        print(f"📊 Position Size: ₹{self.position_size:,.0f}")
        print(f"🎯 Max Positions: {self.max_positions}")
        print(f"📈 Stocks to Test: {len(tickers)}")
        print(f"⚙️  OPTIMIZATIONS:")
        print(f"   • Entry tolerance: ±15% (vs ±5%)")
        print(f"   • Min confluence: 3 (vs 5)")
        print(f"   • Wider stops: 10% (vs 8%)")
        print(f"   • Higher targets: 25% (vs 20%)")
        
        # Download data
        stock_data = {}
        print(f"\n📥 DOWNLOADING DATA...")
        
        for i, ticker in enumerate(tickers, 1):
            try:
                print(f"   {i:2d}/{len(tickers)}: {ticker}", end="")
                df = yf.download(ticker, start="2020-01-01", end=end_date, 
                               interval="1d", auto_adjust=True, progress=False)
                if not df.empty and len(df) > 200:
                    df.attrs['ticker'] = ticker
                    stock_data[ticker] = df
                    print(" ✅")
                else:
                    print(" ❌")
            except Exception:
                print(" ❌")
        
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
            
            # Progress update
            if day_count % 60 == 0:
                print(f"   Day {day_count}: {current_date.strftime('%Y-%m-%d')} | Capital: ₹{self.current_capital:,.0f} | Positions: {len(self.open_positions)} | Signals: {signal_count}")
            
            # Check each stock
            for ticker, df in stock_data.items():
                try:
                    if current_date not in df.index:
                        continue
                    
                    date_idx = df.index.get_loc(current_date)
                    
                    # Check exits first
                    if ticker in self.open_positions:
                        exit_reason, exit_price = self.check_exit_conditions(df, date_idx, self.open_positions[ticker])
                        if exit_reason:
                            self.close_position(ticker, current_date.strftime('%Y-%m-%d'), exit_price, exit_reason)
                    
                    # Check entries
                    elif len(self.open_positions) < self.max_positions and self.current_capital >= self.position_size:
                        entry_signal = self.check_entry_signal(df, date_idx, ticker)
                        if entry_signal:
                            signal_count += 1
                            self.open_position(ticker, current_date.strftime('%Y-%m-%d'), entry_signal)
                            print(f"   📈 ENTRY: {ticker} at ₹{entry_signal['entry_price']:.2f} (Distance: {entry_signal['distance_pct']:+.1f}%)")
                
                except Exception:
                    continue
            
            current_date += timedelta(days=1)
        
        # Close remaining positions
        for ticker in list(self.open_positions.keys()):
            df = stock_data[ticker]
            if end_dt in df.index:
                final_price = df.loc[end_dt, 'Close']
                self.close_position(ticker, end_date, final_price, 'Backtest End')
        
        # Generate results
        self.generate_results()
    
    def open_position(self, ticker, date, signal_data):
        """Open position"""
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
            'distance_at_entry': signal_data['distance_pct']
        }
        
        self.current_capital -= actual_investment
    
    def close_position(self, ticker, date, exit_price, exit_reason):
        """Close position"""
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
        
        print(f"   📊 EXIT: {ticker} at ₹{exit_price:.2f} | P&L: {pnl_pct:+.1f}% | Reason: {exit_reason}")
    
    def generate_results(self):
        """Generate comprehensive results"""
        if not self.trades:
            print("\n❌ No trades executed during backtest period")
            return
        
        # Performance metrics
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
        
        print(f"\n🏆 OPTIMIZED BACKTEST RESULTS")
        print(f"="*70)
        print(f"💰 CAPITAL PERFORMANCE:")
        print(f"   Initial Capital: ₹{self.initial_capital:,.0f}")
        print(f"   Final Capital: ₹{final_capital:,.0f}")
        print(f"   Total P&L: ₹{total_pnl:,.0f}")
        print(f"   Total Return: {total_return_pct:+.2f}%")
        print(f"   Annualized Return: {total_return_pct:+.2f}% (1-year)")
        
        if total_return_pct > 0:
            print(f"   🎯 SYSTEM PROFITABILITY: PROFITABLE ✅")
        else:
            print(f"   ❌ SYSTEM PROFITABILITY: LOSS")
        
        print(f"\n📊 TRADE STATISTICS:")
        print(f"   Total Trades: {total_trades}")
        print(f"   Winning Trades: {len(winning_trades)} ({win_rate:.1f}%)")
        print(f"   Losing Trades: {len(losing_trades)} ({100-win_rate:.1f}%)")
        print(f"   Average Holding: {avg_holding_days:.1f} days")
        
        print(f"\n💹 PERFORMANCE METRICS:")
        print(f"   Average Win: ₹{avg_win:,.0f} ({avg_win_pct:+.2f}%)")
        print(f"   Average Loss: ₹{avg_loss:,.0f} ({avg_loss_pct:+.2f}%)")
        
        if avg_loss != 0:
            profit_factor = abs(sum(t.pnl for t in winning_trades) / sum(t.pnl for t in losing_trades))
            print(f"   Profit Factor: {profit_factor:.2f}")
        
        # Best performing trades
        if len(self.trades) >= 5:
            top_trades = sorted(self.trades, key=lambda t: t.pnl_pct, reverse=True)[:5]
            print(f"\n🏆 TOP 5 TRADES:")
            for i, trade in enumerate(top_trades, 1):
                print(f"   {i}. {trade.ticker}: {trade.pnl_pct:+.2f}% (₹{trade.pnl:,.0f}) - {trade.days_held} days")
        
        # Exit analysis
        exit_reasons = {}
        for trade in self.trades:
            exit_reasons[trade.exit_reason] = exit_reasons.get(trade.exit_reason, 0) + 1
        
        print(f"\n📋 EXIT REASON ANALYSIS:")
        for reason, count in exit_reasons.items():
            pct = (count / total_trades) * 100
            print(f"   {reason}: {count} trades ({pct:.1f}%)")
        
        # System validation
        print(f"\n🎯 SYSTEM VALIDATION:")
        if win_rate >= 50 and total_return_pct > 10:
            print(f"   ✅ STRONG SYSTEM: {win_rate:.1f}% win rate, {total_return_pct:+.1f}% return")
        elif win_rate >= 40 and total_return_pct > 5:
            print(f"   ✅ GOOD SYSTEM: {win_rate:.1f}% win rate, {total_return_pct:+.1f}% return")
        elif total_return_pct > 0:
            print(f"   ⚠️  MARGINAL SYSTEM: {win_rate:.1f}% win rate, {total_return_pct:+.1f}% return")
        else:
            print(f"   ❌ NEEDS IMPROVEMENT: {win_rate:.1f}% win rate, {total_return_pct:+.1f}% return")
        
        # Save results
        self.save_results(final_capital, total_return_pct, win_rate)

    def save_results(self, final_capital, total_return_pct, win_rate):
        """Save results to JSON"""
        results = {
            'system': 'Optimized Imaginary Vertical Line Trendline System',
            'backtest_period': '2023 (1 Year)',
            'initial_capital': self.initial_capital,
            'final_capital': final_capital,
            'total_return_pct': total_return_pct,
            'total_trades': len(self.trades),
            'win_rate': win_rate,
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
                    'confluence_score': t.confluence_score
                } for t in self.trades
            ]
        }
        
        with open('backtest_optimized_results.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n💾 Results saved to: backtest_optimized_results.json")

def run_optimized_backtest():
    """Run the optimized backtest"""
    
    # Test with popular stocks
    test_tickers = [
        'RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'HINDUNILVR.NS',
        'ICICIBANK.NS', 'SBIN.NS', 'BHARTIARTL.NS', 'KOTAKBANK.NS', 'ASIANPAINT.NS',
        'ITC.NS', 'AXISBANK.NS', 'LT.NS', 'TITAN.NS', 'WIPRO.NS',
        'MARUTI.NS', 'BAJFINANCE.NS', 'HCLTECH.NS', 'SUNPHARMA.NS', 'ULTRACEMCO.NS'
    ]
    
    # Backtest period
    start_date = "2023-01-01"
    end_date = "2023-12-31"
    
    # Run backtest
    backtest = OptimizedImaginaryLineBacktest(
        initial_capital=500000,
        position_size=50000,
        max_positions=10
    )
    
    backtest.run_backtest(test_tickers, start_date, end_date)

if __name__ == "__main__":
    run_optimized_backtest()