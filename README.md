# Stock Yard - Automated Stock Screening System
![Stock Yard Screener](https://github.com/anuragsin17-sketch/Stock-Yard/actions/workflows/run_screener.yml/badge.svg)


A 24/7 automated stock screening system that runs completely FREE using GitHub ecosystem tools and free API relays.

## Features

- **100% Free Operation**: Uses GitHub Actions, GitHub Pages, and free APIs
- **Automated Daily Screening**: Runs Monday-Friday at market close (4:30 PM IST)
- **Fibonacci Retracement Analysis**: Identifies stocks near key retracement levels
- **Volume Breakout Detection**: Flags unusual volume spikes with positive price movement
- **Mobile Notifications**: Telegram bot integration for instant alerts
- **Web Dashboard**: Responsive interface with filtering and diagnostics

## Architecture

- **Execution Engine**: Python script running on GitHub Actions
- **Data Source**: Yahoo Finance (yfinance library)
- **Storage**: GitHub repository (data.json)
- **Frontend**: Static HTML hosted on GitHub Pages
- **Notifications**: Telegram Bot API

## Setup Instructions

1. **Fork this repository**
2. **Enable GitHub Pages**: Go to Settings > Pages > Source: Deploy from a branch > main
3. **Configure Telegram Bot**:
   - Create a bot via @BotFather on Telegram
   - Get your Chat ID by messaging @userinfobot
   - Add secrets in Settings > Secrets and variables > Actions:
     - `TELEGRAM_BOT_TOKEN`: Your bot token
     - `TELEGRAM_CHAT_ID`: Your chat ID
4. **Enable GitHub Actions**: The workflow will run automatically

## Usage

- **Web Dashboard**: Visit your GitHub Pages URL to view the dashboard
- **Mobile Alerts**: Receive daily summaries via Telegram
- **Manual Trigger**: Go to Actions tab and manually run the workflow if needed

## Screening Logic

### Golden Stocks (Triple Confluence Strategy)
Golden Stocks require **ALL THREE signals** to be present simultaneously:

1. **Fibonacci Retracement** (38.2%, 50%, or 61.8%)
   - Calculates 5-year high/low levels
   - Flags stocks within ±1.5% of key Fibonacci levels
   - Shows distance percentage from the level

2. **Ascending Trendline** (Weekly or Monthly)
   - Detects upward-sloping support trendlines
   - Requires minimum 3 touches for validation
   - Analyzes both weekly and monthly timeframes
   - Price must be within ±5% of trendline

3. **Vertical Line Entry Trigger** (Horizontal Support/Resistance)
   - Identifies horizontal price levels with multiple touches (like 601 in Lupin example)
   - **Entry Trigger**: The vertical line touch point price
   - **Alert Zone**: Within 10% of the entry trigger price
   - Minimum 2 touches required (Touch 2 pattern)
   - Target: 20% upside from entry trigger
   - Shows exact entry trigger price and distance to it

**Entry Signal Strength:**
- 🔥 **IMMEDIATE ENTRY ZONE**: Within 2% of vertical line trigger price
- ⚡ **CLOSE TO ENTRY**: Within 5% of trigger price  
- 📍 **WATCH ZONE**: Within 10% of trigger price (Alert threshold)

### Volume Breakout
- Calculates 90-day volume baseline
- Detects volume spikes >300% of average
- Requires positive price movement on the same day

### W-Pattern (Weekly Double Bottom)
- Identifies double bottom formations on weekly charts
- Validates neckline and trough relationships
- Tracks recovery from second trough

### Elliott Wave (Macro Analysis)
- Detects Golden Pocket retracement zones (50%-61.8%)
- Analyzes 200-week SMA alignment
- Validates Wave 1 and Wave 2 structures

### Darvas Box
- Multi-timeframe consolidation detection (2-5 years)
- Progressive targets based on consolidation duration
- Breakout validation and strength scoring

## Files Structure

```
├── .github/workflows/run_screener.yml  # GitHub Actions workflow
├── screener.py                         # Main screening logic
├── index.html                          # Web dashboard
├── data.json                          # Generated screening results
├── ind_nifty500list.csv               # Stock universe data
└── README.md                          # This file
```