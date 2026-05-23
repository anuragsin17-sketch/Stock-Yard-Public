#!/usr/bin/env python3
"""
Trendline Scanner Backend
Generates trendline_screen.json for the frontend dashboard
"""

import json
import pandas as pd
from geometric_engine import GeometricTrendlineEngine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_nifty500_tickers():
    """Load Nifty 500 ticker symbols from CSV file"""
    try:
        df = pd.read_csv('ind_nifty500list.csv')
        # Add .NS suffix for Yahoo Finance
        tickers = [f"{symbol}.NS" for symbol in df['Symbol'].tolist()]
        logger.info(f"Loaded {len(tickers)} Nifty 500 tickers")
        return tickers
    except Exception as e:
        logger.error(f"Error loading Nifty 500 list: {e}")
        # Fallback to sample tickers
        return ["BHEL.NS", "CDSL.NS", "SBIN.NS", "AXISBANK.NS", "TATACONSUM.NS", "ICICIBANK.NS"]


def update_trendline_json_feed():
    """
    Runs the scanner across your ticker universe and updates the JSON file
    that your HTML front-end screen reads from.
    """
    engine = GeometricTrendlineEngine(buffer_percentage=10.0, critical_trigger_percentage=1.0)
    
    # Load full Nifty 500 watchlist
    watchlist = load_nifty500_tickers()
    
    screen_data = []
    processed = 0
    skipped = 0
    
    logger.info(f"Starting trendline scan for {len(watchlist)} stocks...")
    
    for ticker in watchlist:
        try:
            metrics = engine.extract_pattern_metrics(ticker)
            if metrics:
                # Format clean key names that your HTML Javascript can map directly into table cells
                screen_data.append({
                    "ticker": metrics["ticker"].replace(".NS", ""),  # Clean ticker name for UI
                    "currentPrice": metrics["current_price"],
                    "triggerPrice": metrics["expected_entry"],
                    "distance": metrics["distance_pct"],
                    "targetExit": metrics["expected_exit"],
                    "status": metrics["status"]
                })
                
                # Hook your existing live production Telegram notification system right here:
                if metrics["status"] == "CRITICAL_TOUCH":
                    logger.info(f"🚨 CRITICAL: {ticker} hit trendline entry target!")
                    # send_telegram_alert(f"🚨 {ticker} hit trendline entry target!")
                    pass
                
                processed += 1
            else:
                skipped += 1
                
        except Exception as e:
            logger.warning(f"Error processing {ticker}: {e}")
            skipped += 1
            continue
    
    # Sort by distance percentage (closest to trendline first)
    screen_data.sort(key=lambda x: abs(x["distance"]))
    
    # Save to your static asset directory or API data path so the HTML UI can load it
    with open("trendline_screen.json", "w") as f:
        json.dump(screen_data, f, indent=4)
    
    logger.info(f"✅ trendline_screen.json updated successfully.")
    logger.info(f"📊 Processed: {processed} stocks | Skipped: {skipped} stocks")
    logger.info(f"🎯 Found {len([s for s in screen_data if s['status'] == 'CRITICAL_TOUCH'])} CRITICAL_TOUCH opportunities")
    logger.info(f"👀 Found {len([s for s in screen_data if s['status'] == 'WATCHLIST'])} WATCHLIST opportunities")


# Run it to generate the initial data load file
if __name__ == "__main__":
    update_trendline_json_feed()
