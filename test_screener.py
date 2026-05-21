#!/usr/bin/env python3
"""
Test script to verify the screener works locally
"""

import os
import sys
import pandas as pd

def test_imports():
    """Test if all required imports work"""
    try:
        import pandas
        import yfinance
        import requests
        import numpy
        print("✅ All imports successful")
        print(f"   - pandas: {pandas.__version__}")
        print(f"   - yfinance: {yfinance.__version__}")
        print(f"   - requests: {requests.__version__}")
        print(f"   - numpy: {numpy.__version__}")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_data_file():
    """Test if data file exists and is readable"""
    files_to_check = ['ind_nifty500list.csv', 'ind_nifty500list.xlsx']
    
    for filename in files_to_check:
        if os.path.exists(filename):
            try:
                if filename.endswith('.csv'):
                    df = pd.read_csv(filename)
                else:
                    df = pd.read_excel(filename)
                
                print(f"✅ Successfully loaded {filename}")
                print(f"   - Rows: {len(df)}")
                print(f"   - Columns: {list(df.columns)}")
                print(f"   - Sample data:")
                print(df.head(3).to_string(index=False))
                return True
            except Exception as e:
                print(f"❌ Error reading {filename}: {e}")
        else:
            print(f"⚠️  File not found: {filename}")
    
    return False

def test_screener():
    """Test the screener with minimal data"""
    try:
        from screener import StockScreener
        
        print("✅ Screener import successful")
        
        # Create screener instance
        screener = StockScreener()
        
        # Test with minimal data
        print("🧪 Testing with minimal dataset...")
        
        # Load stock universe
        stocks_df = screener.load_stock_universe()
        if stocks_df.empty:
            print("❌ No stock data loaded")
            return False
        
        print(f"✅ Loaded {len(stocks_df)} stocks")
        
        # Test screening on first stock only
        if len(stocks_df) > 0:
            first_stock = stocks_df.iloc[0]
            symbol = first_stock['Symbol']
            company_name = first_stock['Company Name']
            industry = first_stock['Industry']
            
            print(f"🧪 Testing screening logic on {symbol}...")
            screener.screen_stock(symbol, company_name, industry)
            
            print("✅ Screening test completed")
            print(f"   - Results: {len(screener.results['fibonacci_stocks'])} Fibonacci, {len(screener.results['volume_breakout_stocks'])} Volume, {len(screener.results['w_pattern_stocks'])} W-Pattern")
        
        return True
        
    except Exception as e:
        print(f"❌ Screener test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("🚀 Stock Yard Screener Test Suite")
    print("=" * 50)
    
    print("\n1. Testing imports...")
    imports_ok = test_imports()
    
    print("\n2. Testing data file...")
    data_ok = test_data_file()
    
    print("\n3. Testing screener logic...")
    screener_ok = test_screener()
    
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    print(f"   - Imports: {'✅ PASS' if imports_ok else '❌ FAIL'}")
    print(f"   - Data File: {'✅ PASS' if data_ok else '❌ FAIL'}")
    print(f"   - Screener: {'✅ PASS' if screener_ok else '❌ FAIL'}")
    
    if imports_ok and data_ok and screener_ok:
        print("\n🎉 All tests passed! The screener should work in GitHub Actions.")
    else:
        print("\n⚠️  Some tests failed. Check the errors above.")
    
    return imports_ok and data_ok and screener_ok

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)