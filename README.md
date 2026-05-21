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

### Fibonacci Retracement
- Calculates 5-year high/low levels
- Identifies 100%, 61.8%, and 50% retracement levels
- Flags stocks within ±1.5% of these key levels

### Volume Breakout
- Calculates 90-day volume baseline
- Detects volume spikes >300% of average
- Requires positive price movement on the same day

## Files Structure

```
├── .github/workflows/run_screener.yml  # GitHub Actions workflow
├── screener.py                         # Main screening logic
├── index.html                          # Web dashboard
├── data.json                          # Generated screening results
├── ind_nifty500list.csv               # Stock universe data
└── README.md                          # This file
```