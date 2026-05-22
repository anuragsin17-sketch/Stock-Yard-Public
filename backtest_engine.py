"""
Backtesting Engine
Core logic for simulating trades based on historical screening signals
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf
from typing import Dict, List, Tuple, Optional
import json
import os

class Trade:
    """Represents a single trade"""
    def __init__(self, symbol, entry_date, entry_price, position_size, signal_data):
        self.symbol = symbol
        self.entry_date = entry_date
        self.entry_price = entry_price
        self.position_size = position_size
        self.signal_data = signal_data  # Store original signal info
        
        # To be filled on exit
        self.exit_date = None
        self.exit_price = None
        self.exit_reason = None
        self.pnl_percent = None
        self.pnl_amount = None
        self.holding_days = None
        
    def to_dict(self):
        """Convert trade to dictionary for reporting"""
        return {
            'symbol': self.symbol,
            'entry_date': self.entry_date.strftime('%Y-%m-%d'),
            'entry_price': round(self.entry_price, 2),
            'exit_date': self.exit_date.strftime('%Y-%m-%d') if self.exit_date else None,
            'exit_price': round(self.exit_price, 2) if self.exit_price else None,
            'exit_reason': self.exit_reason,
            'holding_days': self.holding_days,
            'pnl_percent': round(self.pnl_percent, 2) if self.pnl_percent else None,
            'pnl_amount': round(self.pnl_amount, 2) if self.pnl_amount else None,
            'position_size': round(self.position_size, 2),
            'entry_quality': self.signal_data.get('entry_quality', 'Unknown'),
            'fibonacci_level': self.signal_data.get('fibonacci_level', 'N/A'),
            'has_trendline': self.signal_data.get('has_trendline', False),
            'has_fibonacci': self.signal_data.get('has_fibonacci', False),
        }


class BacktestEngine:
    """Main backtesting engine"""
    
    def __init__(self, config):
        self.config = config
        self.trades = []
        self.open_positions = []
        self.capital = config.INITIAL_CAPITAL
        self.equity_curve = []
        self.price_cache = {}
        
        # Create results folder
        os.makedirs(config.RESULTS_FOLDER, exist_ok=True)
        if config.CACHE_DATA:
            os.makedirs(config.CACHE_FOLDER, exist_ok=True)
    
    def download_price_data(self, symbol: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Download historical price data with caching"""
        cache_key = f"{symbol}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
        
        # Check cache first
        if self.config.CACHE_DATA:
            cache_file = os.path.join(self.config.CACHE_FOLDER, f"{cache_key}.csv")
            if os.path.exists(cache_file):
                return pd.read_csv(cache_file, index_col=0, parse_dates=True)
        
        # Download from Yahoo Finance
        try:
            ticker = yf.Ticker(f"{symbol}.NS")
            df = ticker.history(start=start_date, end=end_date)
            
            if df.empty:
                return None
            
            # Cache the data
            if self.config.CACHE_DATA:
                df.to_csv(cache_file)
            
            return df
        except Exception as e:
            if self.config.VERBOSE:
                print(f"⚠️ Error downloading {symbol}: {e}")
            return None
    
    def check_exit_conditions(self, trade: Trade, current_date: datetime) -> Tuple[bool, Optional[float], Optional[str]]:
        """
        Check if trade should exit based on target/stop-loss/timeout
        Returns: (should_exit, exit_price, exit_reason)
        """
        # Download price data from entry to current date
        price_data = self.download_price_data(
            trade.symbol,
            trade.entry_date,
            current_date + timedelta(days=1)
        )
        
        if price_data is None or price_data.empty:
            return False, None, None
        
        # Calculate target and stop-loss prices
        target_price = trade.entry_price * (1 + self.config.TARGET_PERCENT / 100)
        stoploss_price = trade.entry_price * (1 - self.config.STOPLOSS_PERCENT / 100)
        
        # Check each day's price
        for date, row in price_data.iterrows():
            days_held = (date.date() - trade.entry_date.date()).days
            
            # Check stop-loss first (intraday low)
            if row['Low'] <= stoploss_price:
                # Apply slippage
                exit_price = stoploss_price * (1 - self.config.SLIPPAGE_PERCENT / 100)
                return True, exit_price, 'STOPLOSS'
            
            # Check target (intraday high)
            if row['High'] >= target_price:
                # Apply slippage
                exit_price = target_price * (1 - self.config.SLIPPAGE_PERCENT / 100)
                return True, exit_price, 'TARGET'
            
            # Check timeout
            if days_held >= self.config.MAX_HOLDING_DAYS:
                exit_price = row['Close'] * (1 - self.config.SLIPPAGE_PERCENT / 100)
                return True, exit_price, 'TIMEOUT'
        
        return False, None, None
    
    def execute_trade_entry(self, signal: Dict, entry_date: datetime) -> Optional[Trade]:
        """Execute trade entry with position sizing"""
        symbol = signal['symbol']
        entry_price = signal['current_price']
        
        # Apply slippage to entry
        entry_price_with_slippage = entry_price * (1 + self.config.SLIPPAGE_PERCENT / 100)
        
        # Calculate position size based on strategy
        if self.config.POSITION_SIZING == "SEQUENTIAL":
            # One trade at a time
            if len(self.open_positions) > 0:
                return None
            position_size = self.capital
        
        elif self.config.POSITION_SIZING == "EQUAL_WEIGHT":
            # Divide capital among max concurrent positions
            if len(self.open_positions) >= self.config.MAX_CONCURRENT_POSITIONS:
                return None
            position_size = self.capital / self.config.MAX_CONCURRENT_POSITIONS
        
        elif self.config.POSITION_SIZING == "FIXED_AMOUNT":
            # Fixed amount per trade
            if self.capital < self.config.FIXED_POSITION_SIZE:
                return None
            position_size = self.config.FIXED_POSITION_SIZE
        
        else:
            position_size = self.capital / self.config.MAX_CONCURRENT_POSITIONS
        
        # Check if we have enough capital
        if position_size > self.capital:
            return None
        
        # Create trade
        trade = Trade(symbol, entry_date, entry_price_with_slippage, position_size, signal)
        
        # Deduct capital
        self.capital -= position_size
        
        # Add to open positions
        self.open_positions.append(trade)
        
        if self.config.VERBOSE:
            print(f"  ✅ ENTRY: {symbol} @ ₹{entry_price_with_slippage:.2f} | Size: ₹{position_size:,.0f} | Quality: {signal.get('entry_quality', 'Unknown')}")
        
        return trade
    
    def execute_trade_exit(self, trade: Trade, exit_date: datetime, exit_price: float, exit_reason: str):
        """Execute trade exit and calculate P&L"""
        # Apply transaction costs
        total_cost_percent = self.config.TRANSACTION_COST * 2  # Entry + Exit
        exit_price_after_costs = exit_price * (1 - total_cost_percent / 100)
        
        # Calculate P&L
        trade.exit_date = exit_date
        trade.exit_price = exit_price_after_costs
        trade.exit_reason = exit_reason
        trade.holding_days = (exit_date.date() - trade.entry_date.date()).days
        
        # Calculate returns
        trade.pnl_percent = ((exit_price_after_costs - trade.entry_price) / trade.entry_price) * 100
        trade.pnl_amount = (exit_price_after_costs - trade.entry_price) * (trade.position_size / trade.entry_price)
        
        # Return capital + P&L
        self.capital += trade.position_size + trade.pnl_amount
        
        # Remove from open positions
        self.open_positions.remove(trade)
        
        # Add to completed trades
        self.trades.append(trade)
        
        if self.config.VERBOSE:
            pnl_symbol = "🟢" if trade.pnl_amount > 0 else "🔴"
            print(f"  {pnl_symbol} EXIT: {trade.symbol} @ ₹{exit_price_after_costs:.2f} | {exit_reason} | P&L: {trade.pnl_percent:+.2f}% (₹{trade.pnl_amount:+,.0f}) | Held: {trade.holding_days} days")
    
    def update_equity_curve(self, date: datetime):
        """Calculate current portfolio value"""
        # Current capital + value of open positions (at current price)
        open_positions_value = sum([pos.position_size for pos in self.open_positions])
        total_equity = self.capital + open_positions_value
        
        self.equity_curve.append({
            'date': date,
            'equity': total_equity,
            'capital': self.capital,
            'open_positions': len(self.open_positions)
        })
    
    def get_performance_metrics(self) -> Dict:
        """Calculate comprehensive performance metrics"""
        if not self.trades:
            return {
                'error': 'No trades executed',
                'total_trades': 0
            }
        
        # Basic metrics
        total_trades = len(self.trades)
        winners = [t for t in self.trades if t.exit_reason == 'TARGET']
        losers = [t for t in self.trades if t.exit_reason == 'STOPLOSS']
        timeouts = [t for t in self.trades if t.exit_reason == 'TIMEOUT']
        
        win_rate = (len(winners) / total_trades * 100) if total_trades > 0 else 0
        
        # P&L metrics
        total_pnl = sum([t.pnl_amount for t in self.trades])
        avg_win = np.mean([t.pnl_amount for t in winners]) if winners else 0
        avg_loss = np.mean([t.pnl_amount for t in losers]) if losers else 0
        
        # Returns
        final_equity = self.equity_curve[-1]['equity'] if self.equity_curve else self.config.INITIAL_CAPITAL
        total_return_percent = ((final_equity - self.config.INITIAL_CAPITAL) / self.config.INITIAL_CAPITAL) * 100
        
        # Risk metrics
        returns = [t.pnl_percent for t in self.trades]
        sharpe_ratio = (np.mean(returns) / np.std(returns)) * np.sqrt(252 / 7) if len(returns) > 1 else 0  # Assuming weekly
        
        # Max drawdown
        equity_values = [e['equity'] for e in self.equity_curve]
        peak = equity_values[0]
        max_dd = 0
        for value in equity_values:
            if value > peak:
                peak = value
            dd = ((peak - value) / peak) * 100
            if dd > max_dd:
                max_dd = dd
        
        return {
            'total_trades': total_trades,
            'winners': len(winners),
            'losers': len(losers),
            'timeouts': len(timeouts),
            'win_rate': round(win_rate, 2),
            'total_pnl': round(total_pnl, 2),
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
            'profit_factor': round(abs(avg_win / avg_loss), 2) if avg_loss != 0 else 0,
            'initial_capital': self.config.INITIAL_CAPITAL,
            'final_equity': round(final_equity, 2),
            'total_return_percent': round(total_return_percent, 2),
            'sharpe_ratio': round(sharpe_ratio, 2),
            'max_drawdown_percent': round(max_dd, 2),
            'avg_holding_days': round(np.mean([t.holding_days for t in self.trades]), 1)
        }
    
    def save_results(self):
        """Save backtest results to files"""
        # Save trade log
        if self.config.SAVE_TRADE_LOG:
            trades_df = pd.DataFrame([t.to_dict() for t in self.trades])
            trades_file = os.path.join(self.config.RESULTS_FOLDER, 'trades_log.csv')
            trades_df.to_csv(trades_file, index=False)
            print(f"💾 Trade log saved: {trades_file}")
        
        # Save performance metrics
        metrics = self.get_performance_metrics()
        metrics_file = os.path.join(self.config.RESULTS_FOLDER, 'performance_summary.json')
        with open(metrics_file, 'w') as f:
            json.dump(metrics, f, indent=2)
        print(f"💾 Performance summary saved: {metrics_file}")
        
        # Save equity curve
        equity_df = pd.DataFrame(self.equity_curve)
        equity_file = os.path.join(self.config.RESULTS_FOLDER, 'equity_curve.csv')
        equity_df.to_csv(equity_file, index=False)
        print(f"💾 Equity curve saved: {equity_file}")
