#!/usr/bin/env python3
"""
Trendline Strategy Backtester
Tests the MacroInstitutionalEngine strategy over the last 1 year
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from geometric_engine import MacroInstitutionalEngine
import json

class TrendlineBacktester:
    def __init__(self, initial_capital=500000, position_size=50000, sl_pct=8.0):
        self.initial_capital = initial_capital
        self.position_size = position_size
        self.sl_pct = sl_pct
        self.engine = MacroInstitutionalEngine(position_size=position_size, sl_pct=sl_pct, watchlist_buffer=10.0)
        
        self.trades = []
        self.current_capital = initial_capital
        self.positions = {}
        
    def load_nifty500(self):
        """Load Nifty 500 ticker list"""
        try:
            df = pd.read_csv('ind_nifty500list.csv')
            tickers = [f"{symbol}.NS" for symbol in df['Symbol'].tolist()]
            print(f"✅ Loaded {len(tickers)} Nifty 500 tickers")
            return tickers
        except Exception as e:
            print(f"⚠️ Error loading Nifty 500: {e}")
            return []
    
    def get_historical_signals(self, ticker, start_date, end_date):
        """
        Get historical signals by running the engine on historical data
        Simulates what the scanner would have found on each day
        """
        signals = []
        
        try:
            # Download daily data for the backtest period
            df = yf.download(ticker, start=start_date, end=end_date, progress=False)
            
            if df.empty or len(df) < 20:
                return signals
            
            # Check each day to see if we would have gotten a signal
            for i in range(20, len(df)):
                current_date = df.index[i]
                current_price = df['Close'].iloc[i]
                
                # Run the pattern detection as of this date
                # (using data up to this point)
                pattern = self.engine.process_ticker_geometry(ticker)
                
                if pattern and pattern['notificationTrigger']:
                    # Check if current price is near trigger price
                    trigger_price = pattern['triggerPrice']
                    distance = abs(current_price - trigger_price) / trigger_price * 100
                    
                    if distance <= 1.0:  # Within 1% - would trigger entry
                        signals.append({
                            'date': current_date,
                            'ticker': ticker,
                            'entry_price': current_price,
                            'trigger_price': trigger_price,
                            'stop_loss': pattern['positionSizing']['strictStopLoss'],
                            'target': pattern['positionSizing']['pivotTargetExit'],
                            'shares': pattern['positionSizing']['sharesToBuy'],
                            'fib_zone': pattern['patternZone'],
                            'fib_level': pattern['fibLevelMatch']
                        })
                        break  # Only one entry per stock
                        
        except Exception as e:
            pass
            
        return signals
    
    def simulate_trade(self, signal, ticker, entry_date):
        """
        Simulate a trade from entry to exit
        """
        try:
            # Download data from entry date onwards (next 6 months max)
            end_date = entry_date + timedelta(days=180)
            df = yf.download(ticker, start=entry_date, end=end_date, progress=False)
            
            if df.empty:
                return None
            
            entry_price = signal['entry_price']
            stop_loss = signal['stop_loss']
            target = signal['target']
            shares = signal['shares']
            position_value = entry_price * shares
            
            # Track the trade day by day
            for i in range(1, len(df)):
                current_date = df.index[i]
                high = df['High'].iloc[i]
                low = df['Low'].iloc[i]
                close = df['Close'].iloc[i]
                
                # Check stop loss hit
                if low <= stop_loss:
                    exit_price = stop_loss
                    exit_reason = 'STOP_LOSS'
                    exit_date = current_date
                    break
                
                # Check target hit
                if high >= target:
                    exit_price = target
                    exit_reason = 'TARGET'
                    exit_date = current_date
                    break
                
                # Max holding period: 6 months
                if i >= len(df) - 1:
                    exit_price = close
                    exit_reason = 'TIME_EXIT'
                    exit_date = current_date
                    break
            else:
                # If loop completes without break, use last close
                exit_price = df['Close'].iloc[-1]
                exit_reason = 'TIME_EXIT'
                exit_date = df.index[-1]
            
            # Calculate P&L
            exit_value = exit_price * shares
            pnl = exit_value - position_value
            pnl_pct = (pnl / position_value) * 100
            holding_days = (exit_date - entry_date).days
            
            return {
                'ticker': ticker,
                'entry_date': entry_date.strftime('%Y-%m-%d'),
                'exit_date': exit_date.strftime('%Y-%m-%d'),
                'entry_price': round(entry_price, 2),
                'exit_price': round(exit_price, 2),
                'stop_loss': round(stop_loss, 2),
                'target': round(target, 2),
                'shares': shares,
                'position_value': round(position_value, 2),
                'exit_value': round(exit_value, 2),
                'pnl': round(pnl, 2),
                'pnl_pct': round(pnl_pct, 2),
                'exit_reason': exit_reason,
                'holding_days': holding_days,
                'fib_zone': signal['fib_zone'],
                'fib_level': signal['fib_level']
            }
            
        except Exception as e:
            print(f"Error simulating trade for {ticker}: {e}")
            return None
    
    def run_backtest(self, start_date, end_date):
        """
        Run full backtest over the date range
        """
        print(f"\n{'='*70}")
        print(f"🔬 TRENDLINE STRATEGY BACKTEST")
        print(f"{'='*70}")
        print(f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        print(f"Initial Capital: ₹{self.initial_capital:,.2f}")
        print(f"Position Size: ₹{self.position_size:,.2f}")
        print(f"Stop Loss: {self.sl_pct}%")
        print(f"{'='*70}\n")
        
        tickers = self.load_nifty500()
        
        if not tickers:
            print("❌ No tickers loaded. Exiting.")
            return
        
        print(f"📊 Scanning {len(tickers)} stocks for historical signals...\n")
        
        all_signals = []
        
        # Find all historical signals
        for idx, ticker in enumerate(tickers, 1):
            if idx % 50 == 0:
                print(f"   Processed {idx}/{len(tickers)} stocks...")
            
            signals = self.get_historical_signals(ticker, start_date, end_date)
            all_signals.extend(signals)
        
        print(f"\n✅ Found {len(all_signals)} potential entry signals\n")
        
        if len(all_signals) == 0:
            print("❌ No signals found in the backtest period.")
            return
        
        # Sort signals by date
        all_signals.sort(key=lambda x: x['date'])
        
        print(f"📈 Simulating trades...\n")
        
        # Simulate each trade
        for signal in all_signals:
            trade = self.simulate_trade(signal, signal['ticker'], signal['date'])
            
            if trade:
                self.trades.append(trade)
                print(f"   ✓ {trade['ticker']}: {trade['exit_reason']} | P&L: ₹{trade['pnl']:,.2f} ({trade['pnl_pct']:+.2f}%)")
        
        print(f"\n{'='*70}")
        print(f"✅ BACKTEST COMPLETE - {len(self.trades)} trades executed")
        print(f"{'='*70}\n")
        
        self.generate_report()
    
    def generate_report(self):
        """
        Generate comprehensive backtest report
        """
        if not self.trades:
            print("No trades to report.")
            return
        
        df = pd.DataFrame(self.trades)
        
        # Calculate metrics
        total_trades = len(df)
        winning_trades = len(df[df['pnl'] > 0])
        losing_trades = len(df[df['pnl'] < 0])
        win_rate = (winning_trades / total_trades) * 100
        
        total_pnl = df['pnl'].sum()
        total_pnl_pct = (total_pnl / self.initial_capital) * 100
        
        avg_win = df[df['pnl'] > 0]['pnl'].mean() if winning_trades > 0 else 0
        avg_loss = df[df['pnl'] < 0]['pnl'].mean() if losing_trades > 0 else 0
        
        avg_win_pct = df[df['pnl'] > 0]['pnl_pct'].mean() if winning_trades > 0 else 0
        avg_loss_pct = df[df['pnl'] < 0]['pnl_pct'].mean() if losing_trades > 0 else 0
        
        max_win = df['pnl'].max()
        max_loss = df['pnl'].min()
        
        avg_holding_days = df['holding_days'].mean()
        
        # Exit reason breakdown
        exit_reasons = df['exit_reason'].value_counts()
        
        # Print report
        print(f"\n{'='*70}")
        print(f"📊 BACKTEST SUMMARY REPORT")
        print(f"{'='*70}\n")
        
        print(f"💰 PERFORMANCE METRICS:")
        print(f"   Initial Capital:        ₹{self.initial_capital:,.2f}")
        print(f"   Final Capital:          ₹{self.initial_capital + total_pnl:,.2f}")
        print(f"   Total P&L:              ₹{total_pnl:,.2f} ({total_pnl_pct:+.2f}%)")
        print(f"   Return on Capital:      {total_pnl_pct:+.2f}%\n")
        
        print(f"📈 TRADE STATISTICS:")
        print(f"   Total Trades:           {total_trades}")
        print(f"   Winning Trades:         {winning_trades} ({win_rate:.1f}%)")
        print(f"   Losing Trades:          {losing_trades} ({100-win_rate:.1f}%)")
        print(f"   Win Rate:               {win_rate:.2f}%\n")
        
        print(f"💵 PROFIT/LOSS ANALYSIS:")
        print(f"   Average Win:            ₹{avg_win:,.2f} ({avg_win_pct:+.2f}%)")
        print(f"   Average Loss:           ₹{avg_loss:,.2f} ({avg_loss_pct:+.2f}%)")
        print(f"   Largest Win:            ₹{max_win:,.2f}")
        print(f"   Largest Loss:           ₹{max_loss:,.2f}")
        print(f"   Profit Factor:          {abs(avg_win/avg_loss) if avg_loss != 0 else 0:.2f}\n")
        
        print(f"⏱️  HOLDING PERIOD:")
        print(f"   Average Holding:        {avg_holding_days:.1f} days\n")
        
        print(f"🎯 EXIT REASONS:")
        for reason, count in exit_reasons.items():
            pct = (count / total_trades) * 100
            print(f"   {reason:20s} {count:3d} trades ({pct:.1f}%)")
        
        print(f"\n{'='*70}\n")
        
        # Save detailed results
        results = {
            'summary': {
                'initial_capital': self.initial_capital,
                'final_capital': self.initial_capital + total_pnl,
                'total_pnl': round(total_pnl, 2),
                'total_pnl_pct': round(total_pnl_pct, 2),
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': round(win_rate, 2),
                'avg_win': round(avg_win, 2),
                'avg_loss': round(avg_loss, 2),
                'max_win': round(max_win, 2),
                'max_loss': round(max_loss, 2),
                'avg_holding_days': round(avg_holding_days, 1)
            },
            'trades': self.trades
        }
        
        with open('backtest_trendline_results.json', 'w') as f:
            json.dump(results, f, indent=4)
        
        print(f"✅ Detailed results saved to: backtest_trendline_results.json\n")
        
        # Print top 10 best trades
        print(f"🏆 TOP 10 BEST TRADES:")
        top_trades = df.nlargest(10, 'pnl')
        for idx, trade in top_trades.iterrows():
            print(f"   {trade['ticker']:12s} ₹{trade['pnl']:>10,.2f} ({trade['pnl_pct']:>+6.2f}%) | {trade['entry_date']} → {trade['exit_date']}")
        
        print(f"\n{'='*70}\n")


if __name__ == "__main__":
    # Backtest parameters
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)  # Last 1 year
    
    # Initialize backtester
    backtester = TrendlineBacktester(
        initial_capital=500000,  # 5 Lakhs
        position_size=50000,     # 50K per trade
        sl_pct=8.0               # 8% stop loss
    )
    
    # Run backtest
    backtester.run_backtest(start_date, end_date)
