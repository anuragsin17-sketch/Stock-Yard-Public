#!/usr/bin/env python3
"""
Position Tracking Backtest
Simulates the automatic position tracking strategy over historical data
Capital: ₹10,00,000
Strategy: 20% target, 5% stop loss
"""

import pandas as pd
import yfinance as yf
import json
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Tuple
import numpy as np

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PositionBacktest:
    def __init__(self, initial_capital=1000000):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.positions = []
        self.closed_trades = []
        self.max_positions = 10  # Maximum concurrent positions
        self.position_size_percent = 0.10  # 10% of capital per position
        
    def load_stock_universe(self) -> pd.DataFrame:
        """Load NIFTY 500 stock list"""
        try:
            df = pd.read_csv('ind_nifty500list.csv')
            logger.info(f"Loaded {len(df)} stocks from NIFTY 500")
            return df
        except Exception as e:
            logger.error(f"Error loading stock universe: {e}")
            return pd.DataFrame()
    
    def get_historical_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Download historical data for backtesting"""
        try:
            ticker_symbol = f"{symbol}.NS"
            ticker = yf.Ticker(ticker_symbol)
            data = ticker.history(start=start_date, end=end_date)
            
            if not data.empty:
                logger.info(f"Downloaded {len(data)} days of data for {symbol}")
                return data
            else:
                logger.warning(f"No data for {symbol}")
                return pd.DataFrame()
        except Exception as e:
            logger.error(f"Error downloading {symbol}: {e}")
            return pd.DataFrame()
    
    def detect_trigger_price(self, data: pd.DataFrame) -> float:
        """
        Detect trigger price using simple support level logic
        Returns the lowest low in the last 3 months as trigger
        """
        if len(data) < 60:
            return None
        
        # Get last 3 months of data
        recent_data = data.tail(60)
        
        # Find support level (lowest low)
        trigger_price = recent_data['Low'].min()
        
        return trigger_price
    
    def calculate_position_size(self, price: float) -> int:
        """Calculate number of shares to buy based on position size"""
        position_value = self.current_capital * self.position_size_percent
        shares = int(position_value / price)
        return max(shares, 1)  # At least 1 share
    
    def can_open_position(self) -> bool:
        """Check if we can open a new position"""
        open_positions = [p for p in self.positions if p['status'] == 'open']
        return len(open_positions) < self.max_positions
    
    def open_position(self, symbol: str, company_name: str, entry_price: float, 
                     entry_date: datetime, category: str) -> Dict:
        """Open a new position"""
        if not self.can_open_position():
            return None
        
        shares = self.calculate_position_size(entry_price)
        position_value = shares * entry_price
        
        # Check if we have enough capital
        if position_value > self.current_capital:
            logger.warning(f"Insufficient capital for {symbol}")
            return None
        
        position = {
            'symbol': symbol,
            'company_name': company_name,
            'category': category,
            'entry_price': entry_price,
            'entry_date': entry_date,
            'shares': shares,
            'position_value': position_value,
            'target_price': entry_price * 1.20,  # 20% target
            'stoploss_price': entry_price * 0.95,  # 5% stop loss
            'status': 'open',
            'highest_price': entry_price
        }
        
        self.positions.append(position)
        self.current_capital -= position_value
        
        logger.info(f"✅ POSITION OPENED: {symbol} | Shares: {shares} | Entry: ₹{entry_price:.2f} | Value: ₹{position_value:,.0f}")
        return position
    
    def close_position(self, position: Dict, exit_price: float, exit_date: datetime, 
                      exit_reason: str) -> Dict:
        """Close an existing position"""
        exit_value = position['shares'] * exit_price
        profit_loss = exit_value - position['position_value']
        profit_loss_percent = (profit_loss / position['position_value']) * 100
        
        # Update capital
        self.current_capital += exit_value
        
        # Mark position as closed
        position['status'] = 'closed'
        position['exit_price'] = exit_price
        position['exit_date'] = exit_date
        position['exit_value'] = exit_value
        position['profit_loss'] = profit_loss
        position['profit_loss_percent'] = profit_loss_percent
        position['exit_reason'] = exit_reason
        position['holding_days'] = (exit_date - position['entry_date']).days
        
        self.closed_trades.append(position)
        
        logger.info(f"🔴 POSITION CLOSED: {position['symbol']} | Exit: ₹{exit_price:.2f} | P&L: ₹{profit_loss:,.0f} ({profit_loss_percent:+.2f}%) | Reason: {exit_reason}")
        return position
    
    def update_positions(self, date: datetime, prices: Dict):
        """Update all open positions with current prices"""
        for position in self.positions:
            if position['status'] != 'open':
                continue
            
            symbol = position['symbol']
            if symbol not in prices:
                continue
            
            current_price = prices[symbol]
            
            # Update highest price
            if current_price > position['highest_price']:
                position['highest_price'] = current_price
            
            # Check for target hit (20%)
            if current_price >= position['target_price']:
                self.close_position(position, current_price, date, 'Target Hit (20%)')
            
            # Check for stop loss hit (5%)
            elif current_price <= position['stoploss_price']:
                self.close_position(position, current_price, date, 'Stop Loss Hit (5%)')
    
    def run_backtest(self, start_date: str, end_date: str, max_stocks: int = 50):
        """Run the backtest simulation"""
        logger.info("=" * 80)
        logger.info("STARTING POSITION TRACKING BACKTEST")
        logger.info("=" * 80)
        logger.info(f"Initial Capital: ₹{self.initial_capital:,.0f}")
        logger.info(f"Period: {start_date} to {end_date}")
        logger.info(f"Max Concurrent Positions: {self.max_positions}")
        logger.info(f"Position Size: {self.position_size_percent * 100}% per trade")
        logger.info(f"Target: 20% | Stop Loss: 5%")
        logger.info("=" * 80)
        
        # Load stock universe
        stocks_df = self.load_stock_universe()
        if stocks_df.empty:
            logger.error("No stocks to backtest")
            return
        
        # Limit to first N stocks for faster backtesting
        stocks_df = stocks_df.head(max_stocks)
        
        # Download historical data for all stocks
        stock_data = {}
        for idx, row in stocks_df.iterrows():
            symbol = row['Symbol']
            company_name = row['Company Name']
            
            data = self.get_historical_data(symbol, start_date, end_date)
            if not data.empty:
                stock_data[symbol] = {
                    'data': data,
                    'company_name': company_name,
                    'trigger_price': None,
                    'position_opened': False
                }
        
        logger.info(f"Successfully loaded data for {len(stock_data)} stocks")
        
        # Get all unique dates
        all_dates = set()
        for symbol, info in stock_data.items():
            all_dates.update(info['data'].index)
        
        all_dates = sorted(list(all_dates))
        logger.info(f"Backtesting over {len(all_dates)} trading days")
        
        # Simulate day by day
        for date_idx, current_date in enumerate(all_dates):
            # Get current prices for all stocks
            current_prices = {}
            for symbol, info in stock_data.items():
                if current_date in info['data'].index:
                    current_prices[symbol] = info['data'].loc[current_date, 'Close']
            
            # Update existing positions
            self.update_positions(current_date, current_prices)
            
            # Check for new entry opportunities
            for symbol, info in stock_data.items():
                if info['position_opened']:
                    continue
                
                if current_date not in info['data'].index:
                    continue
                
                # Detect trigger price if not already detected
                if info['trigger_price'] is None:
                    # Need at least 60 days of history
                    historical_data = info['data'].loc[:current_date]
                    if len(historical_data) >= 60:
                        info['trigger_price'] = self.detect_trigger_price(historical_data)
                
                # Check if current price is near trigger price (within 1%)
                if info['trigger_price'] is not None:
                    current_price = current_prices[symbol]
                    distance = abs(current_price - info['trigger_price']) / info['trigger_price'] * 100
                    
                    if distance <= 1.0 and self.can_open_position():
                        # Open position
                        position = self.open_position(
                            symbol=symbol,
                            company_name=info['company_name'],
                            entry_price=current_price,
                            entry_date=current_date,
                            category='Backtest'
                        )
                        
                        if position:
                            info['position_opened'] = True
            
            # Log progress every 30 days
            if (date_idx + 1) % 30 == 0:
                open_count = len([p for p in self.positions if p['status'] == 'open'])
                logger.info(f"Progress: Day {date_idx + 1}/{len(all_dates)} | Date: {current_date.strftime('%Y-%m-%d')} | Open: {open_count} | Closed: {len(self.closed_trades)} | Capital: ₹{self.current_capital:,.0f}")
        
        # Close all remaining open positions at end date
        logger.info("\nClosing all remaining open positions...")
        for position in self.positions:
            if position['status'] == 'open':
                symbol = position['symbol']
                if symbol in stock_data:
                    final_price = stock_data[symbol]['data'].iloc[-1]['Close']
                    self.close_position(position, final_price, all_dates[-1], 'Backtest End')
        
        # Generate report
        self.generate_report()
    
    def generate_report(self):
        """Generate comprehensive backtest report"""
        logger.info("\n" + "=" * 80)
        logger.info("BACKTEST RESULTS")
        logger.info("=" * 80)
        
        # Calculate metrics
        total_trades = len(self.closed_trades)
        winning_trades = [t for t in self.closed_trades if t['profit_loss'] > 0]
        losing_trades = [t for t in self.closed_trades if t['profit_loss'] < 0]
        
        win_rate = (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0
        
        total_profit = sum(t['profit_loss'] for t in winning_trades)
        total_loss = sum(t['profit_loss'] for t in losing_trades)
        net_profit = total_profit + total_loss
        
        final_capital = self.current_capital
        total_return = ((final_capital - self.initial_capital) / self.initial_capital) * 100
        
        avg_win = (total_profit / len(winning_trades)) if winning_trades else 0
        avg_loss = (total_loss / len(losing_trades)) if losing_trades else 0
        
        avg_holding_days = sum(t['holding_days'] for t in self.closed_trades) / total_trades if total_trades > 0 else 0
        
        # Print summary
        logger.info(f"\n📊 PERFORMANCE SUMMARY:")
        logger.info(f"Initial Capital:        ₹{self.initial_capital:,.0f}")
        logger.info(f"Final Capital:          ₹{final_capital:,.0f}")
        logger.info(f"Net Profit/Loss:        ₹{net_profit:,.0f}")
        logger.info(f"Total Return:           {total_return:+.2f}%")
        logger.info(f"\n📈 TRADE STATISTICS:")
        logger.info(f"Total Trades:           {total_trades}")
        logger.info(f"Winning Trades:         {len(winning_trades)} ({win_rate:.1f}%)")
        logger.info(f"Losing Trades:          {len(losing_trades)} ({100-win_rate:.1f}%)")
        logger.info(f"Win Rate:               {win_rate:.2f}%")
        logger.info(f"\n💰 PROFIT/LOSS BREAKDOWN:")
        logger.info(f"Total Profit:           ₹{total_profit:,.0f}")
        logger.info(f"Total Loss:             ₹{total_loss:,.0f}")
        logger.info(f"Average Win:            ₹{avg_win:,.0f}")
        logger.info(f"Average Loss:           ₹{avg_loss:,.0f}")
        logger.info(f"Profit Factor:          {abs(total_profit/total_loss):.2f}" if total_loss != 0 else "N/A")
        logger.info(f"\n⏱️  HOLDING PERIOD:")
        logger.info(f"Average Holding Days:   {avg_holding_days:.1f} days")
        
        # Target vs Stop Loss breakdown
        target_hits = [t for t in self.closed_trades if 'Target Hit' in t['exit_reason']]
        stoploss_hits = [t for t in self.closed_trades if 'Stop Loss' in t['exit_reason']]
        
        logger.info(f"\n🎯 EXIT REASONS:")
        logger.info(f"Target Hit (20%):       {len(target_hits)} trades")
        logger.info(f"Stop Loss Hit (5%):     {len(stoploss_hits)} trades")
        logger.info(f"Other:                  {total_trades - len(target_hits) - len(stoploss_hits)} trades")
        
        # Top 5 winners
        logger.info(f"\n🏆 TOP 5 WINNING TRADES:")
        top_winners = sorted(winning_trades, key=lambda x: x['profit_loss'], reverse=True)[:5]
        for i, trade in enumerate(top_winners, 1):
            logger.info(f"{i}. {trade['symbol']}: ₹{trade['profit_loss']:,.0f} ({trade['profit_loss_percent']:+.2f}%) | {trade['holding_days']} days")
        
        # Top 5 losers
        logger.info(f"\n📉 TOP 5 LOSING TRADES:")
        top_losers = sorted(losing_trades, key=lambda x: x['profit_loss'])[:5]
        for i, trade in enumerate(top_losers, 1):
            logger.info(f"{i}. {trade['symbol']}: ₹{trade['profit_loss']:,.0f} ({trade['profit_loss_percent']:+.2f}%) | {trade['holding_days']} days")
        
        logger.info("\n" + "=" * 80)
        
        # Save detailed results to JSON
        results = {
            'summary': {
                'initial_capital': self.initial_capital,
                'final_capital': final_capital,
                'net_profit': net_profit,
                'total_return_percent': total_return,
                'total_trades': total_trades,
                'winning_trades': len(winning_trades),
                'losing_trades': len(losing_trades),
                'win_rate': win_rate,
                'avg_holding_days': avg_holding_days,
                'target_hits': len(target_hits),
                'stoploss_hits': len(stoploss_hits)
            },
            'all_trades': self.closed_trades
        }
        
        with open('backtest_results.json', 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info("✅ Detailed results saved to backtest_results.json")

def main():
    # Calculate dates
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)  # 6 months
    
    # Run backtest
    backtest = PositionBacktest(initial_capital=1000000)
    backtest.run_backtest(
        start_date=start_date.strftime('%Y-%m-%d'),
        end_date=end_date.strftime('%Y-%m-%d'),
        max_stocks=100  # Test with 100 stocks for reasonable speed
    )

if __name__ == "__main__":
    main()
