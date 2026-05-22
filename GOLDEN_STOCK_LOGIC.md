# Golden Stock Logic - Vertical Line Entry Trigger Implementation

## Overview
This document explains the Golden Stock screening logic based on the pattern analysis from the provided screenshots (Oberoi Realty, Pidilite, BEML, Lupin).

## Pattern Analysis from Screenshots

### Key Observations:
1. **Lupin**: Horizontal support at **601** with multiple touches over many years
2. **BEML**: Clear horizontal support at ~1,200-1,300 with sharp bounces
3. **Pidilite**: Horizontal support at ~1,200-1,300 with consolidation
4. **Oberoi Realty**: Horizontal line at ~1,400-1,500 with multiple tests

### Common Pattern Elements:
- ✅ **Ascending Trendline** (blue diagonal line from bottom-left)
- ✅ **Horizontal Support Level** (the "Vertical Line" - tested multiple times)
- ✅ **Fibonacci Retracement** (price near key levels)

---

## Implementation Logic

### Golden Stock Requirements (ALL THREE MUST BE PRESENT):

#### 1. Fibonacci Retracement
- **Levels**: 38.2%, 50%, 61.8%
- **Tolerance**: Within 1.5% of any key level
- **Output**: 
  - `fibonacci_level`: Which level (e.g., "61.8%")
  - `fibonacci_level_price`: The actual price of that level
  - `fibonacci_distance_percent`: Distance from level (just the number, e.g., 0.8%)

#### 2. Ascending Trendline
- **Detection**: Connects multiple lows over time
- **Timeframes**: Weekly and Monthly
- **Validation**: Minimum 3 touches required
- **Tolerance**: Price within ±5% of trendline
- **Output**:
  - `trendline_price`: Current trendline price
  - `distance_to_trendline_percent`: Distance from trendline
  - `trendline_touches`: Number of touches
  - `trendline_strength`: Strength score (0-100)

#### 3. Vertical Line Entry Trigger (NEW IMPLEMENTATION)
This is the **CORE ENTRY SIGNAL** based on your screenshots.

**What is a "Vertical Line"?**
- A horizontal price level that has been tested multiple times
- Acts as support or resistance
- When price returns to this level, it's an entry trigger
- Examples: Lupin at 601, BEML at 1,200-1,300

**Detection Logic:**
```python
# Analyze 3-5 years of weekly data
# Find local highs and lows (extrema)
# Group similar price levels (within 3% tolerance)
# Count touches at each level
# Identify levels with 2+ touches (Touch 2 pattern)
# Alert when price is within 10% of the level
```

**Alert Thresholds:**
- 🔥 **IMMEDIATE ENTRY ZONE**: Within 2% of trigger price
- ⚡ **CLOSE TO ENTRY**: Within 5% of trigger price
- 📍 **WATCH ZONE**: Within 10% of trigger price (Alert threshold)
- 👀 **MONITORING**: Beyond 10%

**Output Fields:**
- `vertical_line_price`: The horizontal support/resistance level
- `entry_trigger_price`: Same as vertical_line_price (explicit entry point)
- `distance_to_trigger_percent`: Signed distance (+ if above, - if below)
- `distance_to_trigger_abs_percent`: Absolute distance percentage
- `position_vs_trigger`: "ABOVE" or "BELOW"
- `touch_count`: Number of times this level was tested
- `alert_status`: Current alert status (emoji + text)
- `signal_strength`: Quality of the signal
- `target_price_20_percent`: 20% upside target from entry trigger
- `all_touch_dates`: List of all dates when price touched this level

---

## Entry Strategy

### When to Enter:
1. **All three signals present** (Fibonacci + Trendline + Vertical Line)
2. **Price within 10% of vertical line trigger** (Alert zone)
3. **Best entry**: Within 2% of vertical line trigger price

### Position Sizing:
- **Aggressive**: Enter when within 5% of trigger
- **Conservative**: Wait for price to touch trigger (within 2%)

### Target:
- **Primary Target**: 20% from entry trigger price
- **Secondary Target**: 52-week high

### Stop Loss:
- Below the vertical line support level
- Typically 3-5% below entry trigger

---

## Example: Lupin at 601

### Pattern:
- **Vertical Line**: 601 (multiple touches over years)
- **Entry Trigger**: 601
- **Current Price**: Let's say 650
- **Distance**: +8.15% (above trigger)
- **Alert Status**: 📍 WATCH ZONE
- **Target**: 721 (20% from 601)

### Interpretation:
- Stock is approaching the 601 support level
- Within 10% alert zone - start monitoring
- Best entry would be near 601 (within 2%)
- If price touches 601 and bounces, enter
- Target 721 for 20% gain

---

## Code Changes Summary

### Modified Function: `detect_vertical_line_pattern()`
**Location**: `screener.py` line ~885

**Key Changes:**
1. Increased analysis period to 5 years (260 weeks)
2. Increased tolerance to 3% for better level grouping
3. Changed alert threshold from 3% to **10%**
4. Added explicit `entry_trigger_price` field
5. Added `alert_status` with emojis
6. Added `position_vs_trigger` (ABOVE/BELOW)
7. Added `distance_to_trigger_abs_percent`
8. Added `all_touch_dates` for transparency
9. Improved signal strength categorization

### Modified Function: `detect_golden_stocks_combined()`
**Location**: `screener.py` line ~712

**Key Changes:**
1. Added vertical line fields to result output
2. Added `vertical_line_entry_trigger`
3. Added `vertical_line_distance_percent`
4. Added `vertical_line_alert_status`
5. Added `vertical_line_position`
6. Added `vertical_line_target_price`

---

## Testing Recommendations

### Test Stocks:
1. **LUPIN** - Should show vertical line at ~601
2. **BEML** - Should show vertical line at ~1,200-1,300
3. **PIDILITE** - Should show vertical line at ~1,200-1,300
4. **OBEROIRLTY** - Should show vertical line at ~1,400-1,500

### Validation:
- Check if vertical line price matches historical support
- Verify touch count is accurate
- Confirm alert status changes as price moves
- Validate 20% target calculation

---

## Dashboard Display Recommendations

### Golden Stocks Table Columns:
1. **Symbol**
2. **Current Price**
3. **Entry Trigger** (Vertical Line Price) - **HIGHLIGHT THIS**
4. **Distance to Entry** (%) - Color coded:
   - Green: Within 2%
   - Yellow: Within 5%
   - Orange: Within 10%
5. **Alert Status** (with emoji)
6. **Target Price** (20% upside)
7. **Fibonacci Level** (e.g., "61.8%")
8. **Trendline Price**
9. **Touch Count**

### Alert Priority:
- Sort by `distance_to_trigger_abs_percent` (ascending)
- Stocks closest to entry trigger appear first

---

## Future Enhancements

1. **Volume Confirmation**: Add volume spike detection at vertical line touches
2. **Breakout Detection**: Alert when price breaks above resistance vertical lines
3. **Multiple Timeframes**: Detect vertical lines on daily, weekly, and monthly charts
4. **Historical Success Rate**: Track how often vertical line entries lead to 20% gains
5. **Risk/Reward Ratio**: Calculate based on distance to stop loss vs target

---

## Questions & Answers

**Q: Why 10% alert threshold?**
A: Gives enough time to prepare for entry while price approaches the trigger level. More conservative than 3%.

**Q: What if price is above the vertical line?**
A: Still valid if within 10%. Price may be pulling back to test support. Monitor for bounce.

**Q: Can a stock have multiple vertical lines?**
A: Yes, but the algorithm picks the one closest to current price within 10%.

**Q: What if no vertical line is found?**
A: Stock won't qualify as Golden Stock. All three signals (Fib + Trendline + Vertical Line) are required.

---

## Conclusion

The vertical line entry trigger is the **key actionable signal** in the Golden Stock strategy. It provides:
- ✅ Clear entry price
- ✅ Defined target (20% upside)
- ✅ Risk management (stop below support)
- ✅ Historical validation (multiple touches)
- ✅ Early alerts (10% threshold)

This implementation matches the pattern shown in your screenshots and provides a systematic way to identify and act on these high-probability setups.
