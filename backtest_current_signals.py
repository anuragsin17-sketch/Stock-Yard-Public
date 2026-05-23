#!/usr/bin/env python3
"""
Backtest Current Trendline Signals
Simulates trades based on current trendline_screen.json signals
"""

import json
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

def load_signals():
    """Load current trendline signals"""
    with open('trendline_screen.json', 'r') as f:
        return json.load(f)

def simulate_trade(signal):
    """
    Simulate a trade for a given signal
    Uses last 6 months of data to see what would have happened
    """
    ticker = signal['ticker'] + ".NS"
    entry_price = signal['triggerPrice']
    stop_loss = signal['positionSizing']['strictStopLoss']
    target = signal['positionSizing']['pivotTargetExit']
    shares = signal['positionSizing']['sharesToBuy']
    
    try:
        # Download last 6 months of data
        df = yf.download(ticker, period="6mo", progress=False)
        
        if df.empty:
            return None
        
        # Find if price touched entry level in last 6 months
        entry_found = False
        entry_date = None
        
        for i in range(len(df)):
            low = df['Low'].iloc[i]
            high = df['High'].iloc[i]
            
            # Check if price touched trigger price (within 2%)
            if abs(low - entry_price) / entry_price <= 0.02 or abs(high - entry_price) / entry_price <= 0.02:
                entry_found = True
                entry_date = df.index[i]
                break
        
        if not entry_found:
            # Use current price as entry if close to trigger
            current_price = df['Close'].iloc[-1]
            if abs(current_price - entry_price) / entry_price <= 0.05:
                entry_price = current_price
                entry_date = df.index[-1]
                entry_found = True
        
        if not entry_found:
            return None
        
        # Simulate trade from entry date
        entry_idx = df.index.get_loc(entry_date)
        
        # Track trade day by day
        for i in range(entry_idx + 1, len(df)):
            high = df['High'].iloc[i]
            low = df['Low'].iloc[i]
            close = df['Close'].iloc[i]
            current_date = df.index[i]
            
            # Check stop loss
            if low <= stop_loss:
                exit_price = stop_loss
                exit_reason = 'STOP_LOSS'
                exit_date = current_date
                break
            
            # Check target
            if high >= target:
                exit_price = target
                exit_reason = 'TARGET'
                exit_date = current_date
                break
        else:
            # Still holding - use current price
            exit_price = df['Close'].iloc[-1]
            exit_reason = 'HOLDING'
            exit_date = df.index[-1]
        
        # Calculate P&L
        position_value = entry_price * shares
        exit_value = exit_price * shares
        pnl = exit_value - position_value
        pnl_pct = (pnl / position_value) * 100
        holding_days = (exit_date - entry_date).days
        
        return {
            'ticker': signal['ticker'],
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
            'fib_zone': signal['patternZone'],
            'fib_level': signal['fibLevelMatch'],
            'distance_to_trigger': signal['distanceRemaining']
        }
        
    except Exception as e:
        print(f"Error simulating {ticker}: {e}")
        return None

def run_backtest():
    """Run backtest on current signals"""
    
    print(f"\n{'='*70}")
    print(f"🔬 TRENDLINE SIGNALS BACKTEST")
    print(f"{'='*70}")
    print(f"Simulating trades based on current trendline_screen.json signals")
    print(f"Period: Last 6 months")
    print(f"Initial Capital: ₹5,00,000")
    print(f"Position Size: ₹50,000 per trade")
    print(f"Stop Loss: 8%")
    print(f"{'='*70}\n")
    
    signals = load_signals()
    print(f"📊 Found {len(signals)} signals to test\n")
    
    trades = []
    
    print("📈 Simulating trades...\n")
    
    for signal in signals:
        trade = simulate_trade(signal)
        
        if trade:
            trades.append(trade)
            status_icon = "✓" if trade['pnl'] > 0 else "✗"
            print(f"   {status_icon} {trade['ticker']:12s} {trade['exit_reason']:12s} P&L: ₹{trade['pnl']:>10,.2f} ({trade['pnl_pct']:>+6.2f}%) | {trade['holding_days']} days")
    
    print(f"\n{'='*70}")
    print(f"✅ BACKTEST COMPLETE - {len(trades)} trades simulated")
    print(f"{'='*70}\n")
    
    if not trades:
        print("❌ No trades could be simulated.")
        return
    
    # Generate report
    df = pd.DataFrame(trades)
    
    total_trades = len(df)
    winning_trades = len(df[df['pnl'] > 0])
    losing_trades = len(df[df['pnl'] < 0])
    holding_trades = len(df[df['exit_reason'] == 'HOLDING'])
    win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
    
    total_pnl = df['pnl'].sum()
    initial_capital = 500000
    total_pnl_pct = (total_pnl / initial_capital) * 100
    
    avg_win = df[df['pnl'] > 0]['pnl'].mean() if winning_trades > 0 else 0
    avg_loss = df[df['pnl'] < 0]['pnl'].mean() if losing_trades > 0 else 0
    
    avg_win_pct = df[df['pnl'] > 0]['pnl_pct'].mean() if winning_trades > 0 else 0
    avg_loss_pct = df[df['pnl'] < 0]['pnl_pct'].mean() if losing_trades > 0 else 0
    
    max_win = df['pnl'].max()
    max_loss = df['pnl'].min()
    
    avg_holding_days = df['holding_days'].mean()
    
    # Exit reason breakdown
    exit_reasons = df['exit_reason'].value_counts()
    
    print(f"📊 BACKTEST SUMMARY REPORT")
    print(f"{'='*70}\n")
    
    print(f"💰 PERFORMANCE METRICS:")
    print(f"   Initial Capital:        ₹{initial_capital:,.2f}")
    print(f"   Final Capital:          ₹{initial_capital + total_pnl:,.2f}")
    print(f"   Total P&L:              ₹{total_pnl:,.2f} ({total_pnl_pct:+.2f}%)")
    print(f"   Return on Capital:      {total_pnl_pct:+.2f}%\n")
    
    print(f"📈 TRADE STATISTICS:")
    print(f"   Total Signals:          {len(signals)}")
    print(f"   Tradeable Signals:      {total_trades}")
    print(f"   Winning Trades:         {winning_trades} ({win_rate:.1f}%)")
    print(f"   Losing Trades:          {losing_trades}")
    print(f"   Still Holding:          {holding_trades}")
    print(f"   Win Rate:               {win_rate:.2f}%\n")
    
    print(f"💵 PROFIT/LOSS ANALYSIS:")
    print(f"   Average Win:            ₹{avg_win:,.2f} ({avg_win_pct:+.2f}%)")
    print(f"   Average Loss:           ₹{avg_loss:,.2f} ({avg_loss_pct:+.2f}%)")
    print(f"   Largest Win:            ₹{max_win:,.2f}")
    print(f"   Largest Loss:           ₹{max_loss:,.2f}")
    if avg_loss != 0:
        print(f"   Profit Factor:          {abs(avg_win/avg_loss):.2f}")
    print()
    
    print(f"⏱️  HOLDING PERIOD:")
    print(f"   Average Holding:        {avg_holding_days:.1f} days\n")
    
    print(f"🎯 EXIT REASONS:")
    for reason, count in exit_reasons.items():
        pct = (count / total_trades) * 100
        print(f"   {reason:20s} {count:3d} trades ({pct:.1f}%)")
    
    print(f"\n{'='*70}\n")
    
    # Save results
    results = {
        'summary': {
            'initial_capital': initial_capital,
            'final_capital': initial_capital + total_pnl,
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
        'trades': trades
    }
    
    with open('backtest_current_signals_results.json', 'w') as f:
        json.dump(results, f, indent=4)
    
    print(f"✅ Detailed results saved to: backtest_current_signals_results.json\n")
    
    # Print top winners and losers
    print(f"🏆 TOP 5 BEST TRADES:")
    top_trades = df.nlargest(5, 'pnl')
    for idx, trade in top_trades.iterrows():
        print(f"   {trade['ticker']:12s} ₹{trade['pnl']:>10,.2f} ({trade['pnl_pct']:>+6.2f}%) | {trade['exit_reason']:12s} | {trade['fib_zone']}")
    
    print(f"\n📉 TOP 5 WORST TRADES:")
    worst_trades = df.nsmallest(5, 'pnl')
    for idx, trade in worst_trades.iterrows():
        print(f"   {trade['ticker']:12s} ₹{trade['pnl']:>10,.2f} ({trade['pnl_pct']:>+6.2f}%) | {trade['exit_reason']:12s} | {trade['fib_zone']}")
    
    print(f"\n{'='*70}\n")

if __name__ == "__main__":
    run_backtest()
