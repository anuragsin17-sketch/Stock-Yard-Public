"""
Backtesting Configuration
Configure all backtest parameters here
"""

from datetime import datetime, timedelta

# ============================================================================
# BACKTEST PERIOD
# ============================================================================
END_DATE = datetime.now()
START_DATE = END_DATE - timedelta(days=180)  # 6 months back

# Format for display
START_DATE_STR = START_DATE.strftime('%Y-%m-%d')
END_DATE_STR = END_DATE.strftime('%Y-%m-%d')

# ============================================================================
# CAPITAL & POSITION SIZING
# ============================================================================
INITIAL_CAPITAL = 1000000  # ₹10 lakh

# Position sizing strategy
POSITION_SIZING = "EQUAL_WEIGHT"  # Options: "EQUAL_WEIGHT", "SEQUENTIAL", "FIXED_AMOUNT"
MAX_CONCURRENT_POSITIONS = 5      # Maximum positions at once (for EQUAL_WEIGHT)
FIXED_POSITION_SIZE = 200000      # ₹2 lakh per trade (for FIXED_AMOUNT)

# ============================================================================
# TRADE RULES
# ============================================================================
TARGET_PERCENT = 20.0      # 20% profit target
STOPLOSS_PERCENT = 10.0    # 10% stop loss
MAX_HOLDING_DAYS = 90      # Exit after 90 days if neither target nor SL hit

# ============================================================================
# TRANSACTION COSTS
# ============================================================================
SLIPPAGE_PERCENT = 0.5     # 0.5% slippage on entry/exit
TRANSACTION_COST = 0.1     # 0.1% brokerage + taxes per trade

# ============================================================================
# SCREENING FREQUENCY
# ============================================================================
SCREENING_FREQUENCY = "WEEKLY"  # Options: "DAILY", "WEEKLY", "BIWEEKLY"

# ============================================================================
# FILTERS (Optional - to test specific strategies)
# ============================================================================
# Filter by entry quality (None = all signals)
ENTRY_QUALITY_FILTER = None  # Options: None, "Excellent - Double Signal", "Excellent - Fibonacci", etc.

# Filter by Fibonacci level (None = all levels)
FIBONACCI_LEVEL_FILTER = None  # Options: None, "61.8%", "50%", "38.2%"

# Minimum potential upside to consider
MIN_UPSIDE_PERCENT = 20.0

# ============================================================================
# OUTPUT SETTINGS
# ============================================================================
RESULTS_FOLDER = "backtest_results"
GENERATE_CHARTS = True
SAVE_TRADE_LOG = True
VERBOSE = True  # Print progress during backtest

# ============================================================================
# DATA SETTINGS
# ============================================================================
DATA_SOURCE = "YAHOO"  # Yahoo Finance
CACHE_DATA = True      # Cache downloaded data to speed up reruns
CACHE_FOLDER = "backtest_cache"

print(f"📊 Backtest Configuration Loaded")
print(f"Period: {START_DATE_STR} to {END_DATE_STR}")
print(f"Capital: ₹{INITIAL_CAPITAL:,}")
print(f"Target: {TARGET_PERCENT}% | Stop-Loss: {STOPLOSS_PERCENT}%")
print(f"Max Holding: {MAX_HOLDING_DAYS} days")
