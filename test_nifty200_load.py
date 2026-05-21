#!/usr/bin/env python3
"""
Test script to verify ind_nifty200list.csv loads correctly
"""

import pandas as pd
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_load_nifty200():
    """Test loading the NIFTY 200 CSV file"""
    try:
        # Load the CSV file
        df = pd.read_csv('ind_nifty200list.csv')
        
        logger.info(f"Successfully loaded {len(df)} stocks from ind_nifty200list.csv")
        logger.info(f"Columns: {list(df.columns)}")
        
        # Verify expected columns exist
        expected_columns = ['Company Name', 'Industry', 'Symbol', 'Series', 'ISIN Code']
        missing_columns = [col for col in expected_columns if col not in df.columns]
        
        if missing_columns:
            logger.error(f"Missing expected columns: {missing_columns}")
            return False
        
        # Show first few rows
        logger.info("First 5 rows:")
        print(df.head())
        
        # Show some statistics
        logger.info(f"Unique industries: {df['Industry'].nunique()}")
        logger.info(f"Sample industries: {df['Industry'].unique()[:5].tolist()}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error loading ind_nifty200list.csv: {e}")
        return False

if __name__ == "__main__":
    success = test_load_nifty200()
    if success:
        print("\n✅ NIFTY 200 CSV file loads successfully!")
    else:
        print("\n❌ Failed to load NIFTY 200 CSV file!")