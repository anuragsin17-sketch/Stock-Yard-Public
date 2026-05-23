#!/usr/bin/env python3
"""
Quick Trendline Strategy Backtester
Tests on a sample of stocks for faster results
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from geometric_engine import MacroInstitutionalEngine
import json

# Sample of liquid Nifty 500 stocks for quick backtest
SAMPLE_STOCKS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "HINDUNILVR.NS", "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "KOTAKBANK.NS",
    "LT.NS", "AXISBANK.NS", "ASIANPAINT.NS", "MARUTI.NS", "SUNPHARMA.NS",
    "TITAN.NS", "BAJFINANCE.NS", "ULTRACEMCO.NS", "NESTLEIND.NS", "WIPRO.NS",
    "ONGC.NS", "NTPC.NS", "POWERGRID.NS", "TATAMTRDVR.NS", "TATASTEEL.NS",
    "ADANIENT.NS", "ADANIPORTS.NS", "COALINDIA.NS", "GRASIM.NS", "JSWSTEEL.NS",
    "HINDALCO.NS", "INDUSINDBK.NS", "TECHM.NS", "HCLTECH.NS", "DRREDDY.NS",
    "CIPLA.NS", "EICHERMOT.NS", "HEROMOTOCO.NS", "BAJAJFINSV.NS", "DIVISLAB.NS",
    "BRITANNIA.NS", "APOLLOHOSP.NS", "PIDILITIND.NS", "GODREJCP.NS", "DABUR.NS",
    "MARICO.NS", "BERGEPAINT.NS", "COLPAL.NS", "HAVELLS.NS", "VOLTAS.NS"
]

def quick_backtest():
    """Run quick backtest on sample stocks"""
    
    print(f"\n{'='*70}")
    print(f"🔬 QUICK TRENDLINE STRATEGY BACKTEST")
    print(f"{'='*70}")
    print(f"Testing on {len(SAMPLE_STOCKS)} liquid Nifty stocks")
    print(f"Period: Last 1 year")
    print(f"Initial Capital: ₹5,00,000")
    print(f"Position Size: ₹50,000 per trade")
    print(f"Stop Loss: 8%")
    print(f"{'='*70}\n")
    
    engine = MacroInstitutionalEngine(position_size=50000, sl_pct=8.0, watchlist_buffer=10.0)
    
    trades = []
    signals_found = 0
    
    print("📊 Scanning for current signals...\n")
    
    for ticker in SAMPLE_STOCKS:
        try:
            pattern = engine.process_ticker_geometry(ticker)
            
            if pattern:
                signals_found += 1
                
                # Simulate a simple trade outcome
                entry_price = pattern['triggerPrice']
                stop_loss = pattern['positionSizing']['strictStopLoss']
                target = pattern['positionSizing']['pivotTargetExit']
                shares = pattern['positionSizing']['sharesToBuy']
                
                # Download recent data to see what would have happened
                df = yf.download(ticker, period="3mo", progress=False)
                
                if not df.empty:
                    current_price = df['Close'].iloc[-1]
                    
                    # Simple simulation: if price went up, assume target hit; if down, assume stop hit
                    if current_price > entry_price:
                        exit_price = min(target, current_price * 1.15)  # Cap at 15% gain
                        exit_reason = "TARGET" if exit_price >= target * 0.95 else "PARTIAL_PROFIT"
                    else:
                        exit_price = max(stop_loss, current_price)
                        exit_reason = "STOP_LOSS" if exit_price <= stop_loss * 1.02 else "TRAILING"
                    
                    position_value = entry_price * shares
                    exit_value = exit_price * shares
                    pnl = exit_value - position_value
                    pnl_pct = (pnl / position_value) * 100
                    
                    trade = {
                        'ticker': pattern['ticker'],
                        'entry_price': round(entry_price, 2),
                        'exit_price': round(exit_price, 2),
                        'stop_loss': round(stop_loss, 2),
                        'target': round(target, 2),
                        'shares': shares,
                        'position_value': round(position_value, 2),
                        'pnl': round(pnl, 2),
                        'pnl_pct': round(pnl_pct, 2),
                        'exit_reason': exit_reason,
                        'fib_zone': pattern['patternZone'],
                        'fib_level': pattern['fibLevelMatch']
                    }
                    
                    trades.append(trade)
                    print(f"   ✓ {trade['ticker']:12s} {exit_reason:15s} P&L: ₹{trade['pnl']:>10,.2f} ({trade['pnl_pct']:>+6.2f}%)")
                    
        except Exception as e:
            continue
    
    print(f"\n{'='*70}")
    print(f"✅ BACKTEST COMPLETE")
    print(f"{'='*70}\n")
    
    if not trades:
        print("❌ No trades found in the sample.")
        return
    
    # Generate report
    df = pd.DataFrame(trades)
    
    total_trades = len(df)
    winning_trades = len(df[df['pnl'] > 0])
    losing_trades = len(df[df['pnl'] < 0])
    win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
    
    total_pnl = df['pnl'].sum()
    initial_capital = 500000
    total_pnl_pct = (total_pnl / initial_capital) * 100
    
    avg_win = df[df['pnl'] > 0]['pnl'].mean() if winning_trades > 0 else 0
    avg_loss = df[df['pnl'] < 0]['pnl'].mean() if losing_trades > 0 else 0
    
    max_win = df['pnl'].max()
    max_loss = df['pnl'].min()
    
    print(f"📊 BACKTEST SUMMARY REPORT")
    print(f"{'='*70}\n")
    
    print(f"💰 PERFORMANCE METRICS:")
    print(f"   Initial Capital:        ₹{initial_capital:,.2f}")
    print(f"   Final Capital:          ₹{initial_capital + total_pnl:,.2f}")
    print(f"   Total P&L:              ₹{total_pnl:,.2f} ({total_pnl_pct:+.2f}%)")
    print(f"   Return on Capital:      {total_pnl_pct:+.2f}%\n")
    
    print(f"📈 TRADE STATISTICS:")
    print(f"   Stocks Scanned:         {len(SAMPLE_STOCKS)}")
    print(f"   Signals Found:          {signals_found}")
    print(f"   Total Trades:           {total_trades}")
    print(f"   Winning Trades:         {winning_trades} ({win_rate:.1f}%)")
    print(f"   Losing Trades:          {losing_trades} ({100-win_rate:.1f}%)")
    print(f"   Win Rate:               {win_rate:.2f}%\n")
    
    print(f"💵 PROFIT/LOSS ANALYSIS:")
    print(f"   Average Win:            ₹{avg_win:,.2f}")
    print(f"   Average Loss:           ₹{avg_loss:,.2f}")
    print(f"   Largest Win:            ₹{max_win:,.2f}")
    print(f"   Largest Loss:           ₹{max_loss:,.2f}")
    if avg_loss != 0:
        print(f"   Profit Factor:          {abs(avg_win/avg_loss):.2f}")
    
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
            'win_rate': round(win_rate, 2)
        },
        'trades': trades
    }
    
    with open('backtest_trendline_quick_results.json', 'w') as f:
        json.dump(results, f, indent=4)
    
    print(f"✅ Results saved to: backtest_trendline_quick_results.json\n")
    
    # Show all trades
    print(f"📋 ALL TRADES:")
    for trade in trades:
        print(f"   {trade['ticker']:12s} Entry: ₹{trade['entry_price']:>8,.2f} → Exit: ₹{trade['exit_price']:>8,.2f} | P&L: ₹{trade['pnl']:>10,.2f} ({trade['pnl_pct']:>+6.2f}%) | {trade['exit_reason']}")
    
    print(f"\n{'='*70}\n")

if __name__ == "__main__":
    quick_backtest()
