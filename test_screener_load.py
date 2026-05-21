#!/usr/bin/env python3
"""
Test script to verify the updated screener loads the NIFTY 200 file correctly
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from screener import StockScreener
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_screener_load():
    """Test that the screener loads the NIFTY 200 file"""
    try:
        # Create screener instance
        screener = StockScreener()
        
        # Load stock universe
        stocks_df = screener.load_stock_universe()
        
        if stocks_df.empty:
            logger.error("No stocks loaded!")
            return False
        
        logger.info(f"Screener loaded {len(stocks_df)} stocks")
        logger.info(f"Columns: {list(stocks_df.columns)}")
        
        # Show first few stocks
        logger.info("First 5 stocks loaded:")
        for idx, row in stocks_df.head().iterrows():
            logger.info(f"  {row['Symbol']} - {row['Company Name']} ({row['Industry']})")
        
        return True
        
    except Exception as e:
        logger.error(f"Error testing screener load: {e}")
        return False

if __name__ == "__main__":
    success = test_screener_load()
    if success:
        print("\n✅ Screener successfully loads NIFTY 200 stocks!")
    else:
        print("\n❌ Screener failed to load stocks!")