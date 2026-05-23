from geometric_engine import MacroInstitutionalEngine

engine = MacroInstitutionalEngine()

test_stocks = ["SBIN.NS", "AXISBANK.NS", "TITAN.NS", "ICICIBANK.NS", "HDFCBANK.NS"]

print("Testing New Trendline Logic on Sample Stocks:")
print("=" * 80)

found = 0
for ticker in test_stocks:
    result = engine.process_ticker_geometry(ticker)
    if result:
        found += 1
        print(f"\nFOUND: {result['ticker']}")
        print(f"  Current: Rs{result['currentPrice']}")
        print(f"  Trendline: Rs{result['triggerPrice']}")
        print(f"  Distance: {result['distanceRemaining']}%")
        print(f"  Zone: {result['patternZone']}")
        print(f"  Alert: {result['notificationTrigger']}")
    else:
        print(f"SKIP: {ticker.replace('.NS', '')} - Not within +/-2% of trendline")

print(f"\n{'=' * 80}")
print(f"Total Found: {found} out of {len(test_stocks)}")
print(f"{'=' * 80}")
