#!/usr/bin/env python3
"""
Golden Stocks Strategy - 5 Year Backtest (2019-2024)
Local testing with extended historical data
"""

import pandas as pd
import yfinance as yf
import json
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Tuple, Optional
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GoldenStocksBacktest5Y:
    def __init__(self):
        self.start_date = "2019-05-23"  # 5 years ago
        self.end_date = "2024-05-22"    # Recent end
        self.initial_capital = 1000000  # ₹10 lakhs
        self.current_capital = self.initial_capital
        self.position_size_percent = 5.0  # 5% per position
        self.target_profit = 0.20  # 20% target
        self.stop_loss = 0.08      # 8% stop loss
        self.breakeven_trigger = 0.10  # Move to breakeven after 10% gain
        
        self.trades = []
        self.open_positions = []
        
        logger.info(f"🚀 Starting 5-Year Golden Stocks Backtest")
        logger.info(f"📅 Period: {self.start_date} to {self.end_date}")
        logger.info(f"💰 Initial Capital: ₹{self.initial_capital:,}")
        logger.info(f"📊 Position Size: {self.position_size_percent}% per trade")
    
    def load_stock_universe(self) -> List[str]:
        """Load stock symbols for backtesting"""
        try:
            df = pd.read_csv('ind_nifty500list.csv')
            symbols = df['Symbol'].tolist()
            logger.info(f"📋 Loaded {len(symbols)} stocks from NIFTY 500")
            return symbols[:20]  # Test with first 20 stocks for faster execution
        except Exception as e:
            logger.error(f"Error loading stock universe: {e}")
            # Fallback to major stocks
            return ['RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK', 'KOTAKBANK', 
                   'BHARTIARTL', 'ITC', 'SBIN', 'HINDUNILVR', 'LT', 'ASIANPAINT',
                   'MARUTI', 'AXISBANK', 'TITAN', 'NESTLEIND', 'ULTRACEMCO', 'WIPRO',
                   'ONGC', 'NTPC', 'POWERGRID', 'COALINDIA', 'TATAMOTORS', 'TECHM',
                   'SUNPHARMA', 'DRREDDY', 'CIPLA', 'DIVISLAB', 'APOLLOHOSP']
    
    def get_stock_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Download 5-year stock data"""
        try:
            ticker_symbol = f"{symbol}.NS"
            ticker = yf.Ticker(ticker_symbol)
            
            # Download 5+ years of data to ensure we have enough
            data = ticker.history(start="2019-01-01", end="2024-12-31")
            
            if data.empty:
                logger.warning(f"No data for {symbol}")
                return None
                
            logger.info(f"✅ Downloaded {len(data)} days of data for {symbol}")
            return data
            
        except Exception as e:
            logger.error(f"Error downloading {symbol}: {e}")
            return None
    
    def detect_trendline(self, data: pd.DataFrame, lookback_days: int = 252) -> Optional[Dict]:
        """Detect rising trendline using swing lows"""
        try:
            if len(data) < lookback_days:
                return None
            
            # Use last 'lookback_days' for trendline detection
            recent_data = data.tail(lookback_days).copy()
            
            # Find swing lows (local minima)
            window = 10
            recent_data['swing_low'] = recent_data['Low'].rolling(window=window*2+1, center=True).min() == recent_data['Low']
            swing_lows = recent_data[recent_data['swing_low']].copy()
            
            if len(swing_lows) < 3:
                return None
            
            # Get the last 3 swing lows
            last_lows = swing_lows.tail(3)
            
            # Calculate trendline slope using linear regression
            x_values = np.arange(len(last_lows))
            y_values = last_lows['Low'].values
            
            # Linear regression: y = mx + b
            slope, intercept = np.polyfit(x_values, y_values, 1)
            
            # Check if trendline is rising (positive slope)
            if slope <= 0:
                return None
            
            # Calculate current trendline price
            days_since_last_low = len(recent_data) - recent_data.index.get_loc(last_lows.index[-1]) - 1
            current_trendline_price = y_values[-1] + (slope * days_since_last_low)
            
            # Validate trendline touches
            touches = 0
            for _, low_point in last_lows.iterrows():
                if abs(low_point['Low'] - current_trendline_price) / current_trendline_price < 0.02:  # Within 2%
                    touches += 1
            
            if touches < 2:
                return None
            
            return {
                'trendline_price': current_trendline_price,
                'slope': slope,
                'touches': touches,
                'last_lows': last_lows,
                'is_rising': slope > 0
            }
            
        except Exception as e:
            logger.error(f"Error detecting trendline: {e}")
            return None
    
    def is_golden_stock_entry(self, data: pd.DataFrame, date: pd.Timestamp) -> Optional[Dict]:
        """Check if stock qualifies as Golden Stock entry on given date"""
        try:
            # Convert date to timezone-naive if needed for comparison
            if date.tz:
                date_naive = date.tz_localize(None)
            else:
                date_naive = date
            
            # Convert data index to timezone-naive for comparison
            data_tz_naive = data.copy()
            if data_tz_naive.index.tz:
                data_tz_naive.index = data_tz_naive.index.tz_localize(None)
            
            # Get data up to the current date
            historical_data = data_tz_naive[data_tz_naive.index <= date_naive]
            
            if len(historical_data) < 252:  # Need at least 1 year of data
                return None
            
            current_price = historical_data['Close'].iloc[-1]
            
            # Detect trendline
            trendline_result = self.detect_trendline(historical_data)
            if not trendline_result:
                return None
            
            trendline_price = trendline_result['trendline_price']
            
            # Check if price is near trendline (within 1%)
            distance_to_trendline = (current_price - trendline_price) / trendline_price
            
            if not (-0.01 <= distance_to_trendline <= 0.01):  # Must be within 1% of trendline
                return None
            
            # Additional Golden Stock criteria
            recent_20_days = historical_data.tail(20)
            
            # Check for uptrend (higher highs and higher lows)
            highs = recent_20_days['High'].rolling(5).max()
            lows = recent_20_days['Low'].rolling(5).min()
            
            if len(highs.dropna()) < 3 or len(lows.dropna()) < 3:
                return None
            
            # Verify uptrend
            recent_highs = highs.dropna().tail(3)
            recent_lows = lows.dropna().tail(3)
            
            higher_highs = recent_highs.iloc[-1] > recent_highs.iloc[0]
            higher_lows = recent_lows.iloc[-1] > recent_lows.iloc[0]
            
            if not (higher_highs and higher_lows):
                return None
            
            # Volume confirmation (optional but preferred)
            avg_volume = historical_data['Volume'].tail(20).mean()
            current_volume = historical_data['Volume'].iloc[-1]
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
            
            return {
                'entry_price': current_price,
                'trendline_price': trendline_price,
                'distance_to_trendline_percent': distance_to_trendline * 100,
                'volume_ratio': volume_ratio,
                'higher_highs': higher_highs,
                'higher_lows': higher_lows,
                'trendline_slope': trendline_result['slope'],
                'trendline_touches': trendline_result['touches']
            }
            
        except Exception as e:
            logger.error(f"Error checking Golden Stock entry: {e}")
            return None
    
    def calculate_position_size(self, entry_price: float) -> int:
        """Calculate number of shares based on position size percentage"""
        position_value = self.current_capital * (self.position_size_percent / 100)
        shares = int(position_value / entry_price)
        return max(shares, 1)  # At least 1 share
    
    def enter_position(self, symbol: str, entry_date: pd.Timestamp, entry_details: Dict, company_name: str = ""):
        """Enter a new Golden Stock position"""
        entry_price = entry_details['entry_price']
        shares = self.calculate_position_size(entry_price)
        position_value = shares * entry_price
        
        # Calculate targets
        target_price = entry_price * (1 + self.target_profit)
        stoploss_price = entry_price * (1 - self.stop_loss)
        
        position = {
            'symbol': symbol,
            'company_name': company_name,
            'entry_date': entry_date,
            'entry_price': entry_price,
            'shares': shares,
            'position_value': position_value,
            'target_price': target_price,
            'stoploss_price': stoploss_price,
            'breakeven_price': entry_price,
            'breakeven_triggered': False,
            'highest_price': entry_price,
            'trendline_price': entry_details['trendline_price'],
            'entry_details': entry_details
        }
        
        self.open_positions.append(position)
        self.current_capital -= position_value
        
        logger.info(f"📈 ENTRY: {symbol} | ₹{entry_price:.2f} | {shares} shares | ₹{position_value:,.0f}")
    
    def check_exit_conditions(self, position: Dict, current_data: pd.Series, current_date: pd.Timestamp) -> Optional[Dict]:
        """Check if position should be exited"""
        current_price = current_data['Close']
        high_price = current_data['High']
        low_price = current_data['Low']
        
        # Update highest price seen
        position['highest_price'] = max(position['highest_price'], high_price)
        
        # Check for target hit
        if high_price >= position['target_price']:
            return {
                'exit_price': position['target_price'],
                'exit_reason': 'Target Hit (20%)',
                'exit_date': current_date
            }
        
        # Check for stop loss hit
        if low_price <= position['stoploss_price']:
            return {
                'exit_price': position['stoploss_price'],
                'exit_reason': 'Stop Loss Hit (8%)',
                'exit_date': current_date
            }
        
        # Check for breakeven trigger and trailing stop
        if not position['breakeven_triggered']:
            gain_percent = (position['highest_price'] - position['entry_price']) / position['entry_price']
            if gain_percent >= self.breakeven_trigger:
                position['breakeven_triggered'] = True
                position['breakeven_price'] = position['entry_price']
                logger.info(f"🔄 BREAKEVEN: {position['symbol']} moved to breakeven after {gain_percent:.1%} gain")
        
        # If breakeven triggered, check for breakeven stop hit
        if position['breakeven_triggered'] and low_price <= position['breakeven_price']:
            return {
                'exit_price': position['breakeven_price'],
                'exit_reason': 'Breakeven Stop Hit',
                'exit_date': current_date
            }
        
        return None
    
    def exit_position(self, position: Dict, exit_details: Dict):
        """Exit a position and record the trade"""
        exit_price = exit_details['exit_price']
        exit_date = exit_details['exit_date']
        exit_reason = exit_details['exit_reason']
        
        # Calculate P&L
        exit_value = position['shares'] * exit_price
        profit_loss = exit_value - position['position_value']
        profit_loss_percent = (profit_loss / position['position_value']) * 100
        
        # Update capital
        self.current_capital += exit_value
        
        # Calculate holding period
        holding_days = (exit_date - position['entry_date']).days
        
        # Record trade
        trade = {
            'symbol': position['symbol'],
            'company_name': position['company_name'],
            'category': 'Golden Stock',
            'entry_price': position['entry_price'],
            'entry_date': position['entry_date'].strftime('%Y-%m-%d %H:%M:%S%z'),
            'trendline_price': position['trendline_price'],
            'shares': position['shares'],
            'position_value': position['position_value'],
            'target_price': position['target_price'],
            'stoploss_price': position['stoploss_price'],
            'status': 'closed',
            'highest_price': position['highest_price'],
            'exit_price': exit_price,
            'exit_date': exit_date.strftime('%Y-%m-%d %H:%M:%S%z'),
            'exit_value': exit_value,
            'profit_loss': profit_loss,
            'profit_loss_percent': profit_loss_percent,
            'exit_reason': exit_reason,
            'holding_days': holding_days
        }
        
        self.trades.append(trade)
        
        status_emoji = "🟢" if profit_loss > 0 else "🔴"
        logger.info(f"{status_emoji} EXIT: {position['symbol']} | ₹{exit_price:.2f} | {exit_reason} | P&L: ₹{profit_loss:,.0f} ({profit_loss_percent:+.1f}%) | {holding_days}d")
    
    def run_backtest(self):
        """Run the 5-year backtest"""
        logger.info("🔄 Starting 5-year backtest simulation...")
        
        # Load stock universe
        symbols = self.load_stock_universe()
        
        # Create date range for backtesting
        start_date = pd.to_datetime(self.start_date, utc=True)
        end_date = pd.to_datetime(self.end_date, utc=True)
        
        # Download all stock data first
        stock_data = {}
        logger.info(f"📥 Downloading data for {len(symbols)} stocks...")
        
        for i, symbol in enumerate(symbols):
            logger.info(f"Progress: {i+1}/{len(symbols)} - Downloading {symbol}")
            
            data = self.get_stock_data(symbol)
            if data is not None:
                stock_data[symbol] = data
            
            time.sleep(0.2)  # Rate limiting
        
        logger.info(f"✅ Successfully downloaded data for {len(stock_data)} stocks")
        
        # Get company names
        company_names = {}
        try:
            df = pd.read_csv('ind_nifty500list.csv')
            for _, row in df.iterrows():
                company_names[row['Symbol']] = row['Company Name']
        except:
            pass
        
        # Simulate trading day by day
        current_date = start_date
        trading_days = 0
        
        while current_date <= end_date:
            trading_days += 1
            
            if trading_days % 100 == 0:
                logger.info(f"📅 Processing day {trading_days}: {current_date.strftime('%Y-%m-%d')} | Capital: ₹{self.current_capital:,.0f} | Open positions: {len(self.open_positions)}")
            
            # Check exit conditions for open positions
            positions_to_close = []
            for position in self.open_positions:
                symbol = position['symbol']
                if symbol in stock_data:
                    data = stock_data[symbol]
                    # Get data for current date
                    current_day_data = data[data.index.date == current_date.date()]
                    if not current_day_data.empty:
                        exit_result = self.check_exit_conditions(position, current_day_data.iloc[0], current_date)
                        if exit_result:
                            positions_to_close.append((position, exit_result))
            
            # Close positions that hit exit conditions
            for position, exit_details in positions_to_close:
                self.exit_position(position, exit_details)
                self.open_positions.remove(position)
            
            # Look for new Golden Stock entries (limit to avoid over-diversification)
            if len(self.open_positions) < 5:  # Max 5 open positions for faster testing
                for symbol in symbols:
                    if symbol in stock_data and len(self.open_positions) < 5:
                        # Skip if already have position in this stock
                        if any(pos['symbol'] == symbol for pos in self.open_positions):
                            continue
                        
                        data = stock_data[symbol]
                        # Check if we have data for current date - convert both to timezone-naive for comparison
                        data_tz_naive = data.copy()
                        data_tz_naive.index = data_tz_naive.index.tz_localize(None)
                        current_date_naive = current_date.tz_localize(None) if current_date.tz else current_date
                        
                        available_data = data_tz_naive[data_tz_naive.index <= current_date_naive]
                        if len(available_data) > 252:  # Need sufficient history
                            # Pass the original timezone-aware data to the function
                            entry_result = self.is_golden_stock_entry(data, current_date)
                            if entry_result:
                                company_name = company_names.get(symbol, symbol)
                                self.enter_position(symbol, current_date, entry_result, company_name)
            
            # Move to next trading day
            current_date += timedelta(days=1)
        
        # Close any remaining open positions at the end
        logger.info(f"📊 Closing {len(self.open_positions)} remaining positions at backtest end...")
        for position in self.open_positions:
            symbol = position['symbol']
            if symbol in stock_data:
                data = stock_data[symbol]
                # Convert to timezone-naive for comparison
                data_tz_naive = data.copy()
                if data_tz_naive.index.tz:
                    data_tz_naive.index = data_tz_naive.index.tz_localize(None)
                end_date_naive = end_date.tz_localize(None) if end_date.tz else end_date
                
                final_data = data_tz_naive[data_tz_naive.index <= end_date_naive]
                if not final_data.empty:
                    final_price = final_data['Close'].iloc[-1]
                    exit_details = {
                        'exit_price': final_price,
                        'exit_reason': 'Backtest End',
                        'exit_date': end_date
                    }
                    self.exit_position(position, exit_details)
        
        self.open_positions = []
        
        logger.info("✅ 5-year backtest completed!")
    
    def generate_summary(self) -> Dict:
        """Generate backtest summary statistics"""
        if not self.trades:
            return {}
        
        total_trades = len(self.trades)
        winning_trades = len([t for t in self.trades if t['profit_loss'] > 0])
        losing_trades = len([t for t in self.trades if t['profit_loss'] < 0])
        
        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
        
        total_profit = sum(t['profit_loss'] for t in self.trades if t['profit_loss'] > 0)
        total_loss = abs(sum(t['profit_loss'] for t in self.trades if t['profit_loss'] < 0))
        
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
        
        net_profit = self.current_capital - self.initial_capital
        total_return_percent = (net_profit / self.initial_capital) * 100
        
        avg_holding_days = np.mean([t['holding_days'] for t in self.trades])
        
        # Count exit reasons
        target_hits = len([t for t in self.trades if 'Target Hit' in t['exit_reason']])
        stoploss_hits = len([t for t in self.trades if 'Stop Loss' in t['exit_reason']])
        breakeven_hits = len([t for t in self.trades if 'Breakeven' in t['exit_reason']])
        
        return {
            'initial_capital': self.initial_capital,
            'final_capital': self.current_capital,
            'net_profit': net_profit,
            'total_return_percent': total_return_percent,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'avg_holding_days': avg_holding_days,
            'target_hits': target_hits,
            'stoploss_hits': stoploss_hits,
            'breakeven_hits': breakeven_hits,
            'total_profit': total_profit,
            'total_loss': total_loss
        }
    
    def save_results(self):
        """Save backtest results to JSON file"""
        summary = self.generate_summary()
        
        results = {
            'strategy': 'Golden Stocks',
            'period': f'{self.start_date} to {self.end_date}',
            'summary': summary,
            'all_trades': self.trades
        }
        
        filename = 'backtest_golden_5years_results.json'
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"💾 Results saved to {filename}")
        
        # Print summary
        logger.info("=" * 60)
        logger.info("📊 5-YEAR GOLDEN STOCKS BACKTEST SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Period: {self.start_date} to {self.end_date}")
        logger.info(f"Initial Capital: ₹{summary['initial_capital']:,}")
        logger.info(f"Final Capital: ₹{summary['final_capital']:,.0f}")
        logger.info(f"Net Profit: ₹{summary['net_profit']:,.0f}")
        logger.info(f"Total Return: {summary['total_return_percent']:.2f}%")
        logger.info(f"Annualized Return: {(summary['total_return_percent'] / 5):.2f}%")
        logger.info("")
        logger.info(f"Total Trades: {summary['total_trades']}")
        logger.info(f"Winning Trades: {summary['winning_trades']}")
        logger.info(f"Losing Trades: {summary['losing_trades']}")
        logger.info(f"Win Rate: {summary['win_rate']:.2f}%")
        logger.info(f"Profit Factor: {summary['profit_factor']:.2f}")
        logger.info(f"Average Holding: {summary['avg_holding_days']:.1f} days")
        logger.info("")
        logger.info("Exit Reasons:")
        logger.info(f"  Target Hit (20%): {summary['target_hits']}")
        logger.info(f"  Stop Loss (8%): {summary['stoploss_hits']}")
        logger.info(f"  Breakeven Stop: {summary['breakeven_hits']}")
        logger.info(f"  Other: {summary['total_trades'] - summary['target_hits'] - summary['stoploss_hits'] - summary['breakeven_hits']}")
        logger.info("=" * 60)

def main():
    """Run the 5-year Golden Stocks backtest"""
    backtest = GoldenStocksBacktest5Y()
    backtest.run_backtest()
    backtest.save_results()

if __name__ == "__main__":
    main()