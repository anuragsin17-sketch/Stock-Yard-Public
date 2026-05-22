#!/usr/bin/env python3
"""
Golden Stocks Backtest
Simulates the Golden Stocks strategy over 6 months historical data
Capital: ₹10,00,000
Strategy: Trendline touch point entry, 20% target, 8% stop loss
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

class GoldenStocksBacktest:
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
    
    def detect_golden_stock_trendline(self, data: pd.DataFrame) -> Tuple[float, bool]:
        """
        Detect Golden Stock trendline touch point
        
        Golden Stock Criteria:
        1. Stock must be in uptrend (higher highs and higher lows)
        2. Find trendline support by connecting recent lows
        3. Trendline touch point is the entry trigger
        
        Returns: (trendline_price, is_golden_stock)
        """
        if len(data) < 90:  # Need at least 3 months of data
            return None, False
        
        # Get last 3 months of data
        recent_data = data.tail(90)
        
        # Check for uptrend: Compare first half vs second half
        first_half = recent_data.head(45)
        second_half = recent_data.tail(45)
        
        first_half_avg = first_half['Close'].mean()
        second_half_avg = second_half['Close'].mean()
        
        # Must be in uptrend (second half higher than first half)
        if second_half_avg <= first_half_avg:
            return None, False
        
        # Find recent lows for trendline
        # Look for swing lows (local minima)
        lows = []
        for i in range(5, len(recent_data) - 5):
            if (recent_data['Low'].iloc[i] < recent_data['Low'].iloc[i-5:i].min() and
                recent_data['Low'].iloc[i] < recent_data['Low'].iloc[i+1:i+6].min()):
                lows.append({
                    'date': recent_data.index[i],
                    'price': recent_data['Low'].iloc[i],
                    'index': i
                })
        
        if len(lows) < 2:
            return None, False
        
        # Get last two swing lows to form trendline
        last_two_lows = sorted(lows, key=lambda x: x['index'])[-2:]
        
        # Calculate trendline slope
        x1, y1 = last_two_lows[0]['index'], last_two_lows[0]['price']
        x2, y2 = last_two_lows[1]['index'], last_two_lows[1]['price']
        
        # Trendline must be rising (higher lows)
        if y2 <= y1:
            return None, False
        
        # Calculate current trendline price (extrapolate to current date)
        slope = (y2 - y1) / (x2 - x1)
        current_index = len(recent_data) - 1
        trendline_price = y2 + slope * (current_index - x2)
        
        # Trendline price should be reasonable (not too far from current price)
        current_price = recent_data['Close'].iloc[-1]
        distance_percent = abs(current_price - trendline_price) / current_price * 100
        
        if distance_percent > 15:  # Trendline too far away
            return None, False
        
        # Check if stock is above trendline (bullish)
        if current_price < trendline_price * 0.95:  # More than 5% below trendline
            return None, False
        
        return trendline_price, True
    
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
                     entry_date: datetime, trendline_price: float) -> Dict:
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
            'category': 'Golden Stock',
            'entry_price': entry_price,
            'entry_date': entry_date,
            'trendline_price': trendline_price,
            'shares': shares,
            'position_value': position_value,
            'target_price': entry_price * 1.20,  # 20% target
            'stoploss_price': entry_price * 0.92,  # 8% stop loss
            'status': 'open',
            'highest_price': entry_price
        }
        
        self.positions.append(position)
        self.current_capital -= position_value
        
        logger.info(f"✅ GOLDEN STOCK POSITION: {symbol} | Shares: {shares} | Entry: ₹{entry_price:.2f} | Trendline: ₹{trendline_price:.2f} | Value: ₹{position_value:,.0f}")
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
        
        emoji = "🎯" if profit_loss > 0 else "🛑"
        logger.info(f"{emoji} POSITION CLOSED: {position['symbol']} | Exit: ₹{exit_price:.2f} | P&L: ₹{profit_loss:,.0f} ({profit_loss_percent:+.2f}%) | {exit_reason}")
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
            entry_price = position['entry_price']
            
            # Update highest price
            if current_price > position['highest_price']:
                position['highest_price'] = current_price
            
            # Calculate current gain
            current_gain_percent = ((current_price - entry_price) / entry_price) * 100
            
            # Trailing stop loss: If position is +10%, move stop to breakeven
            stoploss_price = position['stoploss_price']
            if current_gain_percent >= 10:
                stoploss_price = entry_price  # Breakeven stop
                position['stoploss_price'] = stoploss_price
            
            # Check for target hit (20%)
            if current_price >= position['target_price']:
                self.close_position(position, current_price, date, 'Target Hit (20%)')
            
            # Check for stop loss hit (8% or breakeven)
            elif current_price <= stoploss_price:
                reason = 'Stop Loss Hit (8%)' if stoploss_price < entry_price else 'Breakeven Stop Hit'
                self.close_position(position, current_price, date, reason)
    
    def run_backtest(self, start_date: str, end_date: str, max_stocks: int = 100):
        """Run the backtest simulation"""
        logger.info("=" * 80)
        logger.info("GOLDEN STOCKS STRATEGY BACKTEST")
        logger.info("=" * 80)
        logger.info(f"Initial Capital: ₹{self.initial_capital:,.0f}")
        logger.info(f"Period: {start_date} to {end_date}")
        logger.info(f"Max Concurrent Positions: {self.max_positions}")
        logger.info(f"Position Size: {self.position_size_percent * 100}% per trade")
        logger.info(f"Target: 20% | Stop Loss: 8% | Trailing Stop: Breakeven at +10%")
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
                    'trendline_price': None,
                    'is_golden_stock': False,
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
            
            # Check for new Golden Stock entry opportunities
            for symbol, info in stock_data.items():
                if info['position_opened']:
                    continue
                
                if current_date not in info['data'].index:
                    continue
                
                # Detect Golden Stock trendline if not already detected
                if not info['is_golden_stock']:
                    # Need at least 90 days of history
                    historical_data = info['data'].loc[:current_date]
                    if len(historical_data) >= 90:
                        trendline_price, is_golden = self.detect_golden_stock_trendline(historical_data)
                        if is_golden:
                            info['trendline_price'] = trendline_price
                            info['is_golden_stock'] = True
                            logger.info(f"🌟 GOLDEN STOCK DETECTED: {symbol} | Trendline: ₹{trendline_price:.2f}")
                
                # Check if current price is near trendline (within 1%)
                if info['is_golden_stock'] and info['trendline_price'] is not None:
                    current_price = current_prices[symbol]
                    distance = abs(current_price - info['trendline_price']) / info['trendline_price'] * 100
                    
                    if distance <= 1.0 and self.can_open_position():
                        # Open position
                        position = self.open_position(
                            symbol=symbol,
                            company_name=info['company_name'],
                            entry_price=current_price,
                            entry_date=current_date,
                            trendline_price=info['trendline_price']
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
        logger.info("GOLDEN STOCKS BACKTEST RESULTS")
        logger.info("=" * 80)
        
        # Calculate metrics
        total_trades = len(self.closed_trades)
        
        if total_trades == 0:
            logger.warning("No trades executed during backtest period")
            return
        
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
        breakeven_hits = [t for t in self.closed_trades if 'Breakeven' in t['exit_reason']]
        
        logger.info(f"\n🎯 EXIT REASONS:")
        logger.info(f"Target Hit (20%):       {len(target_hits)} trades ({len(target_hits)/total_trades*100:.1f}%)")
        logger.info(f"Stop Loss Hit (8%):     {len(stoploss_hits)} trades ({len(stoploss_hits)/total_trades*100:.1f}%)")
        logger.info(f"Breakeven Stop:         {len(breakeven_hits)} trades ({len(breakeven_hits)/total_trades*100:.1f}%)")
        logger.info(f"Other:                  {total_trades - len(target_hits) - len(stoploss_hits) - len(breakeven_hits)} trades")
        
        # Top 5 winners
        if winning_trades:
            logger.info(f"\n🏆 TOP 5 WINNING TRADES:")
            top_winners = sorted(winning_trades, key=lambda x: x['profit_loss'], reverse=True)[:5]
            for i, trade in enumerate(top_winners, 1):
                logger.info(f"{i}. {trade['symbol']}: ₹{trade['profit_loss']:,.0f} ({trade['profit_loss_percent']:+.2f}%) | {trade['holding_days']} days | Entry: ₹{trade['entry_price']:.2f}")
        
        # Top 5 losers
        if losing_trades:
            logger.info(f"\n📉 TOP 5 LOSING TRADES:")
            top_losers = sorted(losing_trades, key=lambda x: x['profit_loss'])[:5]
            for i, trade in enumerate(top_losers, 1):
                logger.info(f"{i}. {trade['symbol']}: ₹{trade['profit_loss']:,.0f} ({trade['profit_loss_percent']:+.2f}%) | {trade['holding_days']} days | Entry: ₹{trade['entry_price']:.2f}")
        
        logger.info("\n" + "=" * 80)
        
        # Save detailed results to JSON
        results = {
            'strategy': 'Golden Stocks',
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
                'stoploss_hits': len(stoploss_hits),
                'breakeven_hits': len(breakeven_hits)
            },
            'all_trades': self.closed_trades
        }
        
        with open('backtest_golden_results.json', 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info("✅ Detailed results saved to backtest_golden_results.json")

def main():
    # Calculate dates - 6 months back
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)  # 6 months
    
    logger.info(f"Backtest Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    
    # Run backtest
    backtest = GoldenStocksBacktest(initial_capital=1000000)
    backtest.run_backtest(
        start_date=start_date.strftime('%Y-%m-%d'),
        end_date=end_date.strftime('%Y-%m-%d'),
        max_stocks=100  # Test with 100 stocks for reasonable speed
    )

if __name__ == "__main__":
    main()
