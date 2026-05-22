# 📊 Stock Yard Backtesting System

## Overview
This backtesting system tests your Golden Stocks screening strategy on historical data **without modifying any of your existing screening logic**. It simulates trades with realistic entry/exit rules and provides comprehensive performance metrics.

## 🎯 What It Does

1. **Runs your screening logic** on historical data (week by week for 6 months)
2. **Simulates trades** with:
   - Entry: When a stock appears in Golden Stocks screening
   - Exit: 20% target OR 10% stop-loss OR 90-day timeout
3. **Tracks performance** with detailed metrics and visualizations

## 📁 Files

- **`backtest_config.py`** - Configuration (capital, target, stop-loss, dates)
- **`backtest_engine.py`** - Core backtesting engine
- **`backtest_runner.py`** - Main execution script
- **`backtest_visualize.py`** - Generate charts and reports
- **`backtest_results/`** - Output folder (created automatically)

## 🚀 How to Run

### Step 1: Install Dependencies (if needed)
```bash
pip install matplotlib seaborn
```

### Step 2: Configure Settings (Optional)
Edit `backtest_config.py` to customize:
- Capital amount
- Target/Stop-loss percentages
- Backtest period
- Position sizing strategy

### Step 3: Run Backtest
```bash
python backtest_runner.py
```

This will:
- Download historical data for Nifty 500 stocks
- Run screening logic week by week
- Simulate trades with your rules
- Save results to `backtest_results/` folder

**Expected Runtime:** 30-60 minutes (depending on internet speed)

### Step 4: Generate Visualizations
```bash
python backtest_visualize.py
```

This creates:
- Equity curve chart
- P&L distribution
- Win/Loss analysis
- Fibonacci level performance
- Summary report

## 📊 Output Files

After running, check `backtest_results/` folder:

1. **`trades_log.csv`** - Detailed log of all trades
2. **`performance_summary.json`** - Overall metrics
3. **`equity_curve.csv`** - Portfolio value over time
4. **`equity_curve.png`** - Visual chart
5. **`pnl_distribution.png`** - P&L histogram
6. **`win_loss_analysis.png`** - Multiple analysis charts
7. **`fibonacci_analysis.png`** - Fibonacci level performance
8. **`summary_report.txt`** - Text summary with top trades

## 🎛️ Configuration Options

### Capital & Position Sizing
```python
INITIAL_CAPITAL = 1000000  # ₹10 lakh

# Position sizing strategies:
POSITION_SIZING = "EQUAL_WEIGHT"  # Divide capital among max positions
# OR
POSITION_SIZING = "SEQUENTIAL"    # One trade at a time
# OR
POSITION_SIZING = "FIXED_AMOUNT"  # Fixed ₹2 lakh per trade
```

### Trade Rules
```python
TARGET_PERCENT = 20.0      # 20% profit target
STOPLOSS_PERCENT = 10.0    # 10% stop loss
MAX_HOLDING_DAYS = 90      # Exit after 90 days if neither hit
```

### Screening Frequency
```python
SCREENING_FREQUENCY = "WEEKLY"  # How often to run screening
# Options: "DAILY", "WEEKLY", "BIWEEKLY"
```

### Filters (Test Specific Strategies)
```python
# Only test "Excellent - Double Signal" entries
ENTRY_QUALITY_FILTER = "Excellent - Double Signal"

# Only test 61.8% Fibonacci level
FIBONACCI_LEVEL_FILTER = "61.8%"

# Minimum upside to consider
MIN_UPSIDE_PERCENT = 20.0
```

## 📈 Key Metrics Explained

### Trade Statistics
- **Total Trades**: Number of trades executed
- **Winners**: Trades that hit 20% target
- **Losers**: Trades that hit 10% stop-loss
- **Win Rate**: Percentage of winning trades
- **Average Holding**: Average days per trade

### Performance Metrics
- **Total Return**: Overall portfolio return %
- **Profit Factor**: Avg Win / Avg Loss ratio
- **Sharpe Ratio**: Risk-adjusted return
- **Max Drawdown**: Largest peak-to-trough decline

## 🔍 Example Results Interpretation

```
Total Trades: 45
Winners: 27 (60%)
Losers: 15 (33%)
Timeouts: 3 (7%)

Initial Capital: ₹10,00,000
Final Equity: ₹12,50,000
Total Return: +25%

Average Win: ₹55,000
Average Loss: ₹-22,000
Profit Factor: 2.5
```

**Interpretation:**
- 60% win rate is good (above 50%)
- Profit factor of 2.5 means wins are 2.5x larger than losses
- 25% return over 6 months = ~50% annualized
- Low timeout rate (7%) means strategy is decisive

## ⚠️ Important Notes

### What This Tests
✅ Your screening logic accuracy
✅ Entry/exit rule effectiveness
✅ Capital allocation strategy
✅ Risk/reward ratio

### What This Doesn't Include
❌ Slippage (added as 0.5%)
❌ Transaction costs (added as 0.1%)
❌ Liquidity constraints
❌ Market impact
❌ Overnight gaps
❌ Dividends/bonuses

### Limitations
- **Look-ahead bias prevention**: Only uses data available up to screening date
- **Survivorship bias**: Uses current Nifty 500 list (doesn't account for delisted stocks)
- **Data quality**: Yahoo Finance data may have gaps
- **Execution assumptions**: Assumes you can buy/sell at exact prices

## 🎯 Next Steps After 6-Month Test

If results are promising:
1. **Extend to 2 years**: Change `START_DATE` in config
2. **Test different parameters**: Try different target/stop-loss combinations
3. **Test specific strategies**: Use filters to isolate best-performing patterns
4. **Walk-forward analysis**: Test on different time periods

## 🛠️ Troubleshooting

### "No trades executed"
- Check if `MIN_UPSIDE_PERCENT` is too high
- Verify `ENTRY_QUALITY_FILTER` isn't too restrictive
- Ensure data is downloading correctly

### "Download errors"
- Yahoo Finance may be rate-limiting
- Try running again (data is cached)
- Check internet connection

### "Backtest taking too long"
- Reduce `SCREENING_FREQUENCY` to "BIWEEKLY"
- Enable `CACHE_DATA = True` (default)
- First run always takes longer (downloading data)

## 📞 Support

If you encounter issues:
1. Check `backtest_results/` for error logs
2. Verify all dependencies are installed
3. Ensure `ind_nifty500list.csv` exists
4. Check that `screener.py` functions are importable

---

**Remember**: Past performance doesn't guarantee future results. Use backtest results as one input in your decision-making process, not the only factor.
