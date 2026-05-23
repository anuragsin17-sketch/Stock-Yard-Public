#!/usr/bin/env python3
"""
Test single stock to debug trendline logic
"""

from geometric_engine import MacroInstitutionalEngine

def test_single_stock():
    """Test a single stock to see what's happening"""
    
    engine = MacroInstitutionalEngine(position_size=50000, sl_pct=8.0, touch_tolerance=2.0)
    
    # Test a few popular stocks
    test_stocks = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS"]
    
    print("🔍 Testing individual stocks to debug trendline logic...\n")
    
    for ticker in test_stocks:
        print(f"Testing {ticker}...")
        try:
            result = engine.process_ticker_geometry(ticker)
            if result:
                print(f"✅ FOUND SIGNAL: {result['ticker']}")
                print(f"   Current Price: ₹{result['currentPrice']}")
                print(f"   Trigger Price: ₹{result['triggerPrice']}")
                print(f"   Distance: {result['distanceRemaining']}%")
                print(f"   Fib Level: {result['fibLevelMatch']}")
                print(f"   Zone: {result['patternZone']}")
                print(f"   Alert Active: {result['notificationTrigger']}")
                print()
            else:
                print(f"❌ No signal - filtered out")
                print()
        except Exception as e:
            print(f"❌ Error: {e}")
            print()

if __name__ == "__main__":
    test_single_stock()