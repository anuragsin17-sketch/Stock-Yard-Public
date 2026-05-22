# 🚀 Quick Start: Run Your First Backtest

## ⚡ Fast Track (3 Steps)

### Step 1: Run the Backtest
```bash
python backtest_runner.py
```

**What happens:**
- Downloads 6 months of historical data for Nifty 500 stocks
- Runs your Golden Stocks screening logic week by week
- Simulates trades with 20% target and 10% stop-loss
- Takes ~30-60 minutes (first run downloads data)

**You'll see:**
```
🚀 STOCK YARD BACKTESTING ENGINE
📅 Period: 2025-11-22 to 2026-05-22
💰 Initial Capital: ₹10,00,000
🎯 Target: 20% | 🛑 Stop-Loss: 10%

[1/26] 📅 Screening Date: 2025-11-22
  ✅ Processed: 495 | ❌ Failed: 5
  🎯 Golden Stocks Found: 12
  ✅ ENTRY: OBEROIRLTY @ ₹1,650.00 | Size: ₹2,00,000
  ...
```

### Step 2: Generate Charts
```bash
python backtest_visualize.py
```

**Creates:**
- 📈 Equity curve chart
- 📊 P&L distribution
- 🎯 Win/Loss analysis
- 📉 Fibonacci performance

### Step 3: Review Results
Open `backtest_results/` folder:
- **`summary_report.txt`** - Read this first!
- **`trades_log.csv`** - All trade details
- **Charts (PNG files)** - Visual analysis

---

## 📊 What to Look For

### Good Results ✅
- Win rate > 50%
- Profit factor > 2.0
- Positive total return
- Max drawdown < 20%

### Warning Signs ⚠️
- Win rate < 40%
- Profit factor < 1.5
- Large drawdowns (>30%)
- Too many timeouts

---

## 🎛️ Customize Your Test

Edit `backtest_config.py` before running:

### Test Different Capital
```python
INITIAL_CAPITAL = 500000  # ₹5 lakh instead of ₹10 lakh
```

### Test Different Rules
```python
TARGET_PERCENT = 15.0     # Lower target (15% instead of 20%)
STOPLOSS_PERCENT = 5.0    # Tighter stop-loss (5% instead of 10%)
```

### Test Specific Strategies
```python
# Only test "Double Signal" entries
ENTRY_QUALITY_FILTER = "Excellent - Double Signal"

# Only test 61.8% Fibonacci level
FIBONACCI_LEVEL_FILTER = "61.8%"
```

### Change Time Period
```python
START_DATE = END_DATE - timedelta(days=365)  # 1 year instead of 6 months
```

---

## 🔧 Troubleshooting

### "ModuleNotFoundError"
```bash
pip install matplotlib seaborn
```

### "No trades executed"
- Lower `MIN_UPSIDE_PERCENT` in config (try 15% instead of 20%)
- Remove `ENTRY_QUALITY_FILTER` (set to `None`)

### "Download errors"
- Check internet connection
- Yahoo Finance may be slow - just wait and retry
- Data is cached, so reruns are faster

### "Takes too long"
- First run downloads data (30-60 min is normal)
- Subsequent runs use cache (5-10 min)
- Reduce to `SCREENING_FREQUENCY = "BIWEEKLY"` for faster testing

---

## 📈 Understanding Your Results

### Example Output:
```
📊 BACKTEST RESULTS
═══════════════════════════════════════════════════════════════

📈 TRADE STATISTICS:
  Total Trades: 45
  Winners (Target Hit): 27 (60.0%)
  Losers (Stop-Loss Hit): 15 (33.3%)
  Timeouts: 3 (6.7%)
  Average Holding Period: 18.5 days

💰 PROFIT & LOSS:
  Total P&L: ₹2,50,000.00
  Average Win: ₹55,000.00
  Average Loss: ₹-22,000.00
  Profit Factor: 2.50

📊 PORTFOLIO PERFORMANCE:
  Initial Capital: ₹10,00,000.00
  Final Equity: ₹12,50,000.00
  Total Return: +25.00%
  Sharpe Ratio: 1.85
  Max Drawdown: 8.50%
```

**This means:**
- ✅ **60% win rate** - Good! Above 50%
- ✅ **Profit factor 2.5** - Excellent! Wins are 2.5x larger than losses
- ✅ **25% return in 6 months** - Strong performance (~50% annualized)
- ✅ **8.5% max drawdown** - Low risk
- ✅ **18.5 days avg holding** - Quick trades, capital efficient

---

## 🎯 Next Steps

### If Results Are Good (>20% return, >50% win rate):
1. ✅ **Extend to 2 years** - Test longer period
2. ✅ **Test different parameters** - Try various target/stop-loss combos
3. ✅ **Analyze best patterns** - Which Fibonacci levels work best?
4. ✅ **Forward test** - Start paper trading with real-time signals

### If Results Are Mixed (10-20% return):
1. 🔍 **Analyze losing trades** - Common patterns?
2. 🔍 **Test filters** - Do "Double Signal" entries perform better?
3. 🔍 **Adjust rules** - Try tighter stop-loss or higher target
4. 🔍 **Check holding period** - Are timeouts hurting performance?

### If Results Are Poor (<10% return or negative):
1. ⚠️ **Review entry quality** - Are signals too aggressive?
2. ⚠️ **Check market conditions** - Was this a bad 6-month period?
3. ⚠️ **Test different timeframes** - Try different 6-month periods
4. ⚠️ **Refine screening logic** - May need to adjust criteria

---

## 💡 Pro Tips

1. **Run multiple tests** - Try different 6-month periods to see consistency
2. **Compare strategies** - Test "Double Signal" vs "Fibonacci only"
3. **Optimize parameters** - Try different target/stop-loss combinations
4. **Check seasonality** - Do certain months perform better?
5. **Analyze by sector** - Which industries give best signals?

---

## ❓ FAQ

**Q: Does this change my screener.py?**
A: No! It only imports and reuses your existing functions.

**Q: How accurate is this?**
A: It's a simulation. Real trading has slippage, liquidity issues, and emotions.

**Q: Can I test 2 years now?**
A: Yes! Change `START_DATE` in config. Will take 2-3 hours for first run.

**Q: What if I get different results each time?**
A: Data is cached, so results should be identical. If not, check Yahoo Finance data quality.

**Q: Should I trade based on these results?**
A: Use this as ONE input. Always paper trade first and consider market conditions.

---

**Ready? Let's run it!**
```bash
python backtest_runner.py
```

Good luck! 🚀
