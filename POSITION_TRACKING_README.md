# Automatic Position Tracking System

## Overview
The Position Tracking system automatically monitors stocks across all categories and tracks positions from entry to exit - completely hands-free, running 24/7 via GitHub Actions.

## How It Works

### 1. Automatic Position Entry
- **Trigger**: When current price reaches trigger price (within 1%)
- **Action**: Position automatically marked as "Position Taken"
- **Target**: 20% gain from entry price
- **Sources**: All stocks from Golden, Volume, W-Pattern, Darvas, Elliott tabs

### 2. Automatic Position Exit
- **Trigger**: When current price hits 20% target
- **Action**: Position automatically marked as "Position Closed"
- **Tracking**: Entry price, exit price, gain percentage, dates

### 3. Updates Schedule
Positions are checked and updated **4 times daily**:
- 10:00 AM IST
- 02:00 PM IST
- 04:40 PM IST
- 08:00 PM IST

## Files Created

### 1. `position_tracker.py`
- Core position tracking logic
- Monitors all stocks with trigger prices
- Opens positions when price hits trigger (±1%)
- Closes positions when 20% target is hit
- Saves to `positions.json`

### 2. `positions.json`
- Stores all position data
- Structure:
  ```json
  {
    "open_positions": [...],
    "closed_positions": [...]
  }
  ```
- Automatically updated by GitHub Actions
- Deployed to public repository

### 3. `positions_ui.js`
- UI component for Radar tab
- Displays open and closed positions
- Filter buttons to switch views
- Progress bars for open positions
- Statistics dashboard

## Integration

### Screener Integration
Added to `screener.py` main execution:
```python
# After screening, update position tracking
from position_tracker import PositionTracker

tracker = PositionTracker()
tracker.check_and_update_positions(screening_results)
```

### GitHub Actions Integration
Updated `.github/workflows/run_screener.yml`:
- Commits `positions.json` to private repo
- Deploys `positions.json` to public repo
- Runs automatically 4x daily

### HTML Integration
To enable in `index.html`, add before `</body>`:
```html
<script src="positions_ui.js"></script>
```

Then replace the `displayPerformanceTracking()` function with the one from `positions_ui.js`.

## Features

### Open Positions View
- Symbol and company name
- Entry price and current price
- Target price (20% from entry)
- Current gain/loss percentage
- Progress bar to target
- Entry date
- Category (Golden, Volume, etc.)

### Closed Positions View
- Symbol and company name
- Entry and exit prices
- Gain percentage
- Entry and exit dates
- Category

### Statistics Dashboard
- Total open positions
- Total closed positions
- Total unrealized gain
- Average gain on closed positions

## Position Tracking Logic

### Entry Criteria
```python
distance_to_trigger = abs(current_price - trigger_price) / trigger_price * 100
if distance_to_trigger <= 1.0:  # Within 1%
    open_position()
```

### Exit Criteria
```python
target_price = entry_price * 1.20  # 20% target
if current_price >= target_price:
    close_position()
```

### Trigger Price Sources
- **Golden Stocks**: `trendline_price`
- **Volume Breakout**: `radar_trigger_price` (breakout low)
- **W-Pattern**: `radar_trigger_price` (trough low)
- **Darvas Box**: `box_low`
- **Elliott Wave**: `golden_pocket_low`

## No Laptop Required

Everything runs automatically on GitHub's servers:
1. Screener runs 4x daily
2. Position tracker checks all stocks
3. Opens/closes positions automatically
4. Updates `positions.json`
5. Deploys to public website
6. You just view the results!

## Next Steps

1. **Commit all files**:
   ```bash
   git add position_tracker.py positions_ui.js POSITION_TRACKING_README.md
   git add screener.py .github/workflows/run_screener.yml
   git commit -m "Add automatic position tracking system"
   git push
   ```

2. **Integrate UI** (optional - can be done later):
   - Add `<script src="positions_ui.js"></script>` to `index.html`
   - Replace `displayPerformanceTracking()` function

3. **Test**:
   - Trigger GitHub Actions workflow manually
   - Check if `positions.json` is created
   - View Radar tab on website

## Benefits

✅ **Fully Automatic** - No manual tracking needed
✅ **24/7 Monitoring** - Runs even when laptop is off
✅ **Multi-Category** - Tracks stocks from all tabs
✅ **Clear Targets** - 20% gain target for all positions
✅ **Historical Record** - All closed positions saved
✅ **Performance Metrics** - Average gains, unrealized gains
✅ **Mobile Friendly** - View on any device

## Future Enhancements

- Email/Telegram notifications when positions open/close
- Adjustable target percentages per category
- Stop-loss tracking
- Performance analytics and charts
- Export to CSV for tax reporting
