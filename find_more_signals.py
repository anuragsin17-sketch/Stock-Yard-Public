#!/usr/bin/env python3
"""
Find more dual signal examples by testing a broader range of stocks
"""

from geometric_engine import MacroInstitutionalEngine

def find_dual_signals():
    """Test a wide range of stocks to find dual signal examples"""
    
    # Test with wider tolerance to find more examples
    engine = MacroInstitutionalEngine(position_size=50000, sl_pct=8.0, touch_tolerance=8.0)
    
    # Broader list of popular stocks
    test_stocks = [
        "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
        "HINDUNILVR.NS", "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "KOTAKBANK.NS",
        "LT.NS", "AXISBANK.NS", "ASIANPAINT.NS", "MARUTI.NS", "SUNPHARMA.NS",
        "TITAN.NS", "BAJFINANCE.NS", "ULTRACEMCO.NS", "NESTLEIND.NS", "WIPRO.NS",
        "ONGC.NS", "NTPC.NS", "POWERGRID.NS", "TATASTEEL.NS", "ADANIENT.NS",
        "COALINDIA.NS", "GRASIM.NS", "HINDALCO.NS", "INDUSINDBK.NS", "TECHM.NS",
        "HCLTECH.NS", "DRREDDY.NS", "CIPLA.NS", "EICHERMOT.NS", "HEROMOTOCO.NS",
        "BAJAJFINSV.NS", "DIVISLAB.NS", "BRITANNIA.NS", "APOLLOHOSP.NS", "PIDILITIND.NS"
    ]
    
    print("🔍 SEARCHING FOR DUAL SIGNAL EXAMPLES")
    print("="*80)
    print(f"Testing {len(test_stocks)} stocks with ±8% tolerance...")
    print()
    
    found_signals = []
    
    for i, ticker in enumerate(test_stocks, 1):
        try:
            result = engine.process_ticker_geometry(ticker)
            
            if result and result['currentSignal']['isActive']:
                current = result['currentSignal']
                future = result['futureSignal']
                
                stock_name = ticker.replace('.NS', '')
                
                print(f"✅ SIGNAL FOUND: {stock_name}")
                print(f"   Current: ₹{current['currentPrice']} → ₹{current['triggerPrice']} (Score: {current['confluenceScore']})")
                
                if future['isActive']:
                    print(f"   Future: ₹{future['predictedPrice']} in {future['monthsToTouch']} months ({future['confidenceScore']}% confidence)")
                    signal_type = "DUAL"
                else:
                    print(f"   Future: No prediction available")
                    signal_type = "CURRENT_ONLY"
                
                found_signals.append({
                    'ticker': stock_name,
                    'type': signal_type,
                    'current_score': current['confluenceScore'],
                    'current_price': current['currentPrice'],
                    'trigger_price': current['triggerPrice'],
                    'distance': current['distanceRemaining'],
                    'fib_level': current['fibLevelMatch'],
                    'future_active': future['isActive'],
                    'future_confidence': future.get('confidenceScore', 0) if future['isActive'] else 0
                })
                print()
            
            # Progress indicator
            if i % 10 == 0:
                print(f"   ... processed {i}/{len(test_stocks)} stocks")
                
        except Exception as e:
            continue
    
    print("="*80)
    print(f"📊 SUMMARY: Found {len(found_signals)} signals")
    print("="*80)
    
    # Sort by confluence score
    found_signals.sort(key=lambda x: x['current_score'], reverse=True)
    
    dual_signals = [s for s in found_signals if s['type'] == 'DUAL']
    current_only = [s for s in found_signals if s['type'] == 'CURRENT_ONLY']
    
    print(f"\n🎯 DUAL SIGNALS ({len(dual_signals)}):")
    for signal in dual_signals[:5]:  # Top 5
        print(f"   {signal['ticker']:12s} Score: {signal['current_score']:2d} | Distance: {signal['distance']:5.2f}% | Fib: {signal['fib_level']}")
    
    print(f"\n📈 CURRENT ONLY ({len(current_only)}):")
    for signal in current_only[:5]:  # Top 5
        print(f"   {signal['ticker']:12s} Score: {signal['current_score']:2d} | Distance: {signal['distance']:5.2f}% | Fib: {signal['fib_level']}")
    
    # Show detailed analysis for top 2 dual signals
    if len(dual_signals) >= 2:
        print(f"\n" + "="*80)
        print(f"🏆 TOP 2 DUAL SIGNAL EXAMPLES:")
        print("="*80)
        
        for i, signal in enumerate(dual_signals[:2], 1):
            ticker = signal['ticker'] + ".NS"
            result = engine.process_ticker_geometry(ticker)
            
            if result:
                current = result['currentSignal']
                future = result['futureSignal']
                
                print(f"\n{i}. {signal['ticker']} - DUAL OPPORTUNITY")
                print("-" * 50)
                print(f"🔥 CURRENT SIGNAL:")
                print(f"   Current Price: ₹{current['currentPrice']}")
                print(f"   Trigger Price: ₹{current['triggerPrice']}")
                print(f"   Distance: {current['distanceRemaining']}%")
                print(f"   Confluence: {current['confluenceScore']}/10 ({current['fibLevelMatch']})")
                print(f"   Notes: {', '.join(current['confluenceNotes'])}")
                
                print(f"\n🔮 FUTURE PREDICTION:")
                print(f"   Next Touch: {future['nextTouchDate']}")
                print(f"   Predicted Price: ₹{future['predictedPrice']}")
                print(f"   Expected Fib: {future['predictedFibLevel']}")
                print(f"   Confidence: {future['confidenceScore']}%")
                print(f"   Time to Touch: {future['daysToTouch']} days ({future['monthsToTouch']} months)")
                
                pattern = future['historicalPattern']
                print(f"\n📊 Pattern Analysis:")
                print(f"   Historical Touches: {pattern['touchCount']}")
                print(f"   Avg Interval: {pattern['avgTouchInterval']} months")
                print(f"   Fib Preferences: {pattern['fibPreferences']}")

if __name__ == "__main__":
    find_dual_signals()