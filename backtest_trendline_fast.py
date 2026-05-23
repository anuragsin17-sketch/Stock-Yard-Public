#!/usr/bin/env python3
"""
Fast Trendline Strategy Backtester
Uses current signals and simulates forward testing
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json

def backtest_from_current_signals():
    """
    Backtest using the current trendline_screen.json signals
    Simulate what would have happened if we entered these trades
    """
    
    print(f"\n{'='*70}")
    print(f"🔬 TRENDLINE STRATEGY BACKTEST (Current Signals)")
    print(f"{'='*70}\n")
    
    # Load current signals
    try:
        with open('trendline_screen.json', 'r') as f:
            signals = json.load(f)
        print(f"✅ Loaded {len(signals)} current signals from trendline_screen.json\n")
    except Exception as e:
        print(f"❌ Error loading signals: {e}")
        return
    
    if not signals:
        print("❌ No signals found.")
        return
    
    # Backtest parameters
    initial_capital = 500000
    position_size = 50000
    sl_pct = 8.0
    
    print(f"💰 Initial Capital: ₹{initial_capital:,.2f}")
    print(f"💵 Position Size: ₹{position_size:,.2f}")
    print(f"🛑 Stop Loss: {sl_pct}%\n")
    print(f"{'='*70}\n")
    
    trades = []
    
    # Simulate each signal
    for idx, signal in enumerate(signals[:20], 1):  # Test first 20 signals
        ticker = signal['ticker'] + ".NS"
        entry_price = signal['triggerPrice']
        stop_loss = signal['positionSizing']['strictStopLoss']
        target = signal['positionSizing']['pivotTargetExit']
        shares = signal['positionSizing']['sharesToBuy']
        
        print(f"[{idx}/20] Testing {signal['ticker']}...")
        
        try:
            # Download last 1 year of data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365)
            df = yf.download(ticker, start=start_date, end=end_date, progress=False)
            
            # Handle multi-index columns from yfinance
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            if df.empty or len(df) < 10:
                print(f"   ⚠️  Insufficient data\n")
                continue
            
            # Find entry point (when price was near trigger)
            entry_idx = None
            for i in range(len(df)):
                try:
                    close_price = float(df['Close'].iloc[i])
                    if abs(close_price - entry_price) / entry_price <= 0.02:  # Within 2%
                        entry_idx = i
                        break
                except:
                    continue
            
            if entry_idx is None:
                print(f"   ⚠️  No entry point found\n")
                continue
            
            entry_date = df.index[entry_idx]
            actual_entry = float(df['Close'].iloc[entry_idx])
            position_value = actual_entry * shares
            
            # Simulate trade from entry onwards
            exit_price = None
            exit_reason = None
            exit_date = None
            
            for i in range(entry_idx + 1, len(df)):
                high = float(df['High'].iloc[i])
                low = float(df['Low'].iloc[i])
                close = float(df['Close'].iloc[i])
                
                # Check stop loss
                if low <= stop_loss:
                    exit_price = stop_loss
                    exit_reason = 'STOP_LOSS'
                    exit_date = df.index[i]
                    break
                
                # Check target
                if high >= target:
                    exit_price = target
                    exit_reason = 'TARGET'
                    exit_date = df.index[i]
                    break
            
            # If no exit, use current price
            if exit_price is None:
                exit_price = float(df['Close'].iloc[-1])
                exit_reason = 'OPEN'
                exit_date = df.index[-1]
            
            # Calculate P&L
            exit_value = exit_price * shares
            pnl = exit_value - position_value
            pnl_pct = (pnl / position_value) * 100
            holding_days = (exit_date - entry_date).days
            
            trade = {
                'ticker': signal['ticker'],
                'entry_date': entry_date.strftime('%Y-%m-%d'),
                'exit_date': exit_date.strftime('%Y-%m-%d'),
                'entry_price': round(actual_entry, 2),
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
                'fib_zone': signal['patternZone']
            }
            
            trades.append(trade)
            
            status_color = "✅" if pnl > 0 else "❌"
            print(f"   {status_color} {exit_reason:12s} | P&L: ₹{pnl:>10,.2f} ({pnl_pct:>+6.2f}%) | {holding_days} days\n")
            
        except Exception as e:
            print(f"   ❌ Error: {e}\n")
            continue
    
    if not trades:
        print("❌ No trades executed.")
        return
    
    # Generate report
    print(f"\n{'='*70}")
    print(f"📊 BACKTEST RESULTS")
    print(f"{'='*70}\n")
    
    df = pd.DataFrame(trades)
    
    total_trades = len(df)
    winning_trades = len(df[df['pnl'] > 0])
    losing_trades = len(df[df['pnl'] < 0])
    open_trades = len(df[df['exit_reason'] == 'OPEN'])
    
    win_rate = (winning_trades / (total_trades - open_trades)) * 100 if (total_trades - open_trades) > 0 else 0
    
    total_pnl = df['pnl'].sum()
    total_pnl_pct = (total_pnl / initial_capital) * 100
    
    avg_win = df[df['pnl'] > 0]['pnl'].mean() if winning_trades > 0 else 0
    avg_loss = df[df['pnl'] < 0]['pnl'].mean() if losing_trades > 0 else 0
    
    avg_win_pct = df[df['pnl'] > 0]['pnl_pct'].mean() if winning_trades > 0 else 0
    avg_loss_pct = df[df['pnl'] < 0]['pnl_pct'].mean() if losing_trades > 0 else 0
    
    max_win = df['pnl'].max()
    max_loss = df['pnl'].min()
    
    avg_holding = df[df['exit_reason'] != 'OPEN']['holding_days'].mean()
    
    print(f"💰 PERFORMANCE:")
    print(f"   Initial Capital:        ₹{initial_capital:,.2f}")
    print(f"   Total P&L:              ₹{total_pnl:,.2f} ({total_pnl_pct:+.2f}%)")
    print(f"   Final Capital:          ₹{initial_capital + total_pnl:,.2f}\n")
    
    print(f"📈 TRADE STATS:")
    print(f"   Total Trades:           {total_trades}")
    print(f"   Winning Trades:         {winning_trades}")
    print(f"   Losing Trades:          {losing_trades}")
    print(f"   Open Trades:            {open_trades}")
    print(f"   Win Rate:               {win_rate:.1f}%\n")
    
    print(f"💵 P&L ANALYSIS:")
    print(f"   Average Win:            ₹{avg_win:,.2f} ({avg_win_pct:+.2f}%)")
    print(f"   Average Loss:           ₹{avg_loss:,.2f} ({avg_loss_pct:+.2f}%)")
    print(f"   Best Trade:             ₹{max_win:,.2f}")
    print(f"   Worst Trade:            ₹{max_loss:,.2f}")
    print(f"   Profit Factor:          {abs(avg_win/avg_loss) if avg_loss != 0 else 0:.2f}\n")
    
    print(f"⏱️  HOLDING:")
    print(f"   Avg Holding Period:     {avg_holding:.1f} days\n")
    
    # Exit breakdown
    exit_counts = df['exit_reason'].value_counts()
    print(f"🎯 EXIT BREAKDOWN:")
    for reason, count in exit_counts.items():
        pct = (count / total_trades) * 100
        print(f"   {reason:15s} {count:3d} ({pct:.1f}%)")
    
    print(f"\n{'='*70}\n")
    
    # Top trades
    print(f"🏆 TOP 5 BEST TRADES:")
    top = df.nlargest(5, 'pnl')
    for _, t in top.iterrows():
        print(f"   {t['ticker']:10s} ₹{t['pnl']:>10,.2f} ({t['pnl_pct']:>+6.2f}%) | {t['entry_date']} → {t['exit_date']}")
    
    print(f"\n📉 TOP 5 WORST TRADES:")
    worst = df.nsmallest(5, 'pnl')
    for _, t in worst.iterrows():
        print(f"   {t['ticker']:10s} ₹{t['pnl']:>10,.2f} ({t['pnl_pct']:>+6.2f}%) | {t['entry_date']} → {t['exit_date']}")
    
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
            'open_trades': open_trades,
            'win_rate': round(win_rate, 2),
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
            'max_win': round(max_win, 2),
            'max_loss': round(max_loss, 2),
            'avg_holding_days': round(avg_holding, 1)
        },
        'trades': trades
    }
    
    with open('backtest_trendline_results.json', 'w') as f:
        json.dump(results, f, indent=4)
    
    print(f"✅ Results saved to: backtest_trendline_results.json\n")


if __name__ == "__main__":
    backtest_from_current_signals()
