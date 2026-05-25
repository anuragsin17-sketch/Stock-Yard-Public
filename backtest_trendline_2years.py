"""
Backtest trendline strategy over last 2 years
Tests the geometric_engine trendline logic with real historical data
"""
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from geometric_engine import MacroInstitutionalEngine
import json

def backtest_trendline_strategy():
    print("=" * 80)
    print("TRENDLINE STRATEGY BACKTEST - LAST 2 YEARS")
    print("=" * 80)
    
    # Load stock list
    try:
        df = pd.read_csv('Stock List.csv')
        symbols = df['Symbol'].tolist()[:100]  # Test on first 100 stocks for speed
        print(f"✅ Loaded {len(symbols)} stocks for backtesting\n")
    except Exception as e:
        print(f"❌ Error loading stock list: {e}")
        return
    
    # Backtest parameters
    end_date = datetime.now()
    start_date = end_date - timedelta(days=730)  # 2 years
    position_size = 50000  # ₹50,000 per trade
    stop_loss_pct = 8.0  # 8% stop loss (monthly close)
    
    print(f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print(f"Position Size: ₹{position_size:,.0f}")
    print(f"Stop Loss: {stop_loss_pct}% (Monthly Close)")
    print(f"Target: +20% from entry\n")
    
    # Initialize engine
    engine = MacroInstitutionalEngine(
        position_size=position_size,
        sl_pct=stop_loss_pct,
        touch_tolerance=2.0
    )
    
    # Track results
    trades = []
    total_trades = 0
    winning_trades = 0
    losing_trades = 0
    total_pnl = 0
    
    print("Scanning for trendline setups...\n")
    
    for i, symbol in enumerate(symbols, 1):
        ticker = f"{symbol}.NS"
        
        try:
            # Process with geometric engine
            result = engine.process_ticker_geometry(ticker)
            
            if not result:
                continue
            
            # Check if it was a valid signal (within 2% of trendline)
            signal = result['currentSignal']
            if signal['distanceRemaining'] > 2.0:
                continue
            
            # Simulate trade
            entry_price = signal['triggerPrice']
            stop_loss = result['positionSizing']['dynamicStopLoss']
            target = result['positionSizing']['targetExit']
            shares = result['positionSizing']['sharesToBuy']
            
            # Download historical data to check outcome
            hist = yf.download(ticker, start=start_date, end=end_date, progress=False)
            
            if hist.empty:
                continue
            
            # Find entry point (when price touched trendline)
            entry_idx = None
            for idx in range(len(hist)):
                if abs(hist['Close'].iloc[idx] - entry_price) / entry_price < 0.02:  # Within 2%
                    entry_idx = idx
                    break
            
            if entry_idx is None or entry_idx >= len(hist) - 5:
                continue
            
            # Simulate trade outcome
            entry_date = hist.index[entry_idx]
            future_data = hist.iloc[entry_idx+1:]
            
            # Check for stop loss or target hit
            outcome = None
            exit_price = None
            exit_date = None
            
            for idx, row in future_data.iterrows():
                # Check monthly close for stop loss
                if idx.month != entry_date.month:
                    if row['Close'] < stop_loss:
                        outcome = 'STOP_LOSS'
                        exit_price = stop_loss
                        exit_date = idx
                        break
                
                # Check for target hit
                if row['High'] >= target:
                    outcome = 'TARGET_HIT'
                    exit_price = target
                    exit_date = idx
                    break
            
            # If no exit after 60 days, close at current price
            if outcome is None:
                if len(future_data) >= 60:
                    outcome = 'TIMEOUT'
                    exit_price = future_data.iloc[59]['Close']
                    exit_date = future_data.index[59]
                else:
                    continue
            
            # Calculate P&L
            pnl_pct = ((exit_price - entry_price) / entry_price) * 100
            pnl_amount = (exit_price - entry_price) * shares
            
            total_trades += 1
            if pnl_pct > 0:
                winning_trades += 1
            else:
                losing_trades += 1
            
            total_pnl += pnl_amount
            
            trades.append({
                'symbol': symbol,
                'entry_date': entry_date.strftime('%Y-%m-%d'),
                'exit_date': exit_date.strftime('%Y-%m-%d'),
                'entry_price': round(entry_price, 2),
                'exit_price': round(exit_price, 2),
                'stop_loss': round(stop_loss, 2),
                'target': round(target, 2),
                'shares': shares,
                'outcome': outcome,
                'pnl_pct': round(pnl_pct, 2),
                'pnl_amount': round(pnl_amount, 2),
                'holding_days': (exit_date - entry_date).days
            })
            
            print(f"[{i:3d}/{len(symbols)}] {symbol:12} | Entry: ₹{entry_price:8.2f} | Exit: ₹{exit_price:8.2f} | {outcome:12} | P&L: {pnl_pct:+6.2f}%")
            
        except Exception as e:
            print(f"[{i:3d}/{len(symbols)}] {symbol:12} | Error: {e}")
            continue
    
    # Calculate statistics
    print("\n" + "=" * 80)
    print("BACKTEST RESULTS")
    print("=" * 80)
    
    if total_trades == 0:
        print("❌ No trades found in backtest period")
        return
    
    win_rate = (winning_trades / total_trades) * 100
    avg_win = sum([t['pnl_pct'] for t in trades if t['pnl_pct'] > 0]) / winning_trades if winning_trades > 0 else 0
    avg_loss = sum([t['pnl_pct'] for t in trades if t['pnl_pct'] < 0]) / losing_trades if losing_trades > 0 else 0
    avg_holding = sum([t['holding_days'] for t in trades]) / total_trades
    
    print(f"\nTotal Trades: {total_trades}")
    print(f"Winning Trades: {winning_trades} ({win_rate:.1f}%)")
    print(f"Losing Trades: {losing_trades} ({100-win_rate:.1f}%)")
    print(f"\nAverage Win: {avg_win:+.2f}%")
    print(f"Average Loss: {avg_loss:+.2f}%")
    print(f"Average Holding Period: {avg_holding:.0f} days")
    print(f"\nTotal P&L: ₹{total_pnl:,.2f}")
    print(f"Average P&L per Trade: ₹{total_pnl/total_trades:,.2f}")
    
    # Outcome breakdown
    outcomes = {}
    for trade in trades:
        outcome = trade['outcome']
        outcomes[outcome] = outcomes.get(outcome, 0) + 1
    
    print(f"\nOutcome Breakdown:")
    for outcome, count in outcomes.items():
        print(f"  {outcome:15} : {count:3d} ({count/total_trades*100:.1f}%)")
    
    # Save results
    results = {
        'backtest_period': {
            'start': start_date.strftime('%Y-%m-%d'),
            'end': end_date.strftime('%Y-%m-%d')
        },
        'parameters': {
            'position_size': position_size,
            'stop_loss_pct': stop_loss_pct,
            'target_pct': 20.0
        },
        'summary': {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': round(win_rate, 2),
            'avg_win_pct': round(avg_win, 2),
            'avg_loss_pct': round(avg_loss, 2),
            'avg_holding_days': round(avg_holding, 1),
            'total_pnl': round(total_pnl, 2),
            'avg_pnl_per_trade': round(total_pnl/total_trades, 2)
        },
        'trades': trades
    }
    
    with open('backtest_trendline_2years_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Results saved to: backtest_trendline_2years_results.json")
    print("=" * 80)

if __name__ == "__main__":
    backtest_trendline_strategy()
