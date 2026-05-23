#!/usr/bin/env python3
"""
Test the dual signal system - Current + Future predictions
"""

from geometric_engine import MacroInstitutionalEngine

def test_dual_signals():
    """Test both current and future signals"""
    
    engine = MacroInstitutionalEngine(position_size=50000, sl_pct=8.0, touch_tolerance=5.0)
    
    # Test more stocks to find new examples
    test_stocks = ["LT.NS", "AXISBANK.NS", "TITAN.NS", "BAJFINANCE.NS", "ULTRACEMCO.NS", 
                   "NESTLEIND.NS", "NTPC.NS", "POWERGRID.NS", "TATASTEEL.NS", "ADANIENT.NS",
                   "MARUTI.NS", "SUNPHARMA.NS", "ONGC.NS", "COALINDIA.NS", "GRASIM.NS"]
    
    print("🎯 DUAL SIGNAL SYSTEM TEST")
    print("="*80)
    
    for ticker in test_stocks:
        print(f"\n📊 ANALYZING {ticker.replace('.NS', '')}")
        print("-" * 60)
        
        try:
            result = engine.process_ticker_geometry(ticker)
            
            if result:
                # Current Signal
                current = result['currentSignal']
                print(f"🔥 CURRENT SIGNAL:")
                print(f"   Status: {'✅ ACTIVE' if current['isActive'] else '❌ INACTIVE'}")
                if current['isActive']:
                    print(f"   Current Price: ₹{current['currentPrice']}")
                    print(f"   Trigger Price: ₹{current['triggerPrice']}")
                    print(f"   Distance: {current['distanceRemaining']}%")
                    print(f"   Confluence: {current['confluenceScore']}/10 ({current['fibLevelMatch']})")
                    print(f"   Notes: {', '.join(current['confluenceNotes'])}")
                
                print()
                
                # Future Signal
                future = result['futureSignal']
                print(f"🔮 FUTURE PREDICTION:")
                print(f"   Status: {'✅ ACTIVE' if future['isActive'] else '❌ INACTIVE'}")
                if future['isActive']:
                    print(f"   Next Touch Date: {future['nextTouchDate']}")
                    print(f"   Predicted Price: ₹{future['predictedPrice']}")
                    print(f"   Expected Fib Level: {future['predictedFibLevel']}")
                    print(f"   Confidence: {future['confidenceScore']}%")
                    print(f"   Days to Touch: {future['daysToTouch']} days ({future['monthsToTouch']} months)")
                    
                    print(f"\n   📈 Historical Pattern:")
                    pattern = future['historicalPattern']
                    print(f"      Touch Count: {pattern['touchCount']}")
                    print(f"      Avg Interval: {pattern['avgTouchInterval']} months")
                    print(f"      Historical Accuracy: {pattern['historicalAccuracy']}%")
                    print(f"      Fib Preferences: {pattern['fibPreferences']}")
                    
                    print(f"\n   📝 Notes:")
                    for note in future['predictionNotes']:
                        print(f"      • {note}")
                else:
                    print(f"   Reason: {future.get('reason', 'Unknown')}")
                
                print()
                
                # Summary
                if current['isActive'] and future['isActive']:
                    print(f"🎯 DUAL OPPORTUNITY:")
                    print(f"   Trade NOW: ₹{current['triggerPrice']} (Score: {current['confluenceScore']})")
                    print(f"   Plan AHEAD: ₹{future['predictedPrice']} in {future['monthsToTouch']} months")
                elif current['isActive']:
                    print(f"🎯 CURRENT OPPORTUNITY ONLY:")
                    print(f"   Trade NOW: ₹{current['triggerPrice']} (Score: {current['confluenceScore']})")
                elif future['isActive']:
                    print(f"🎯 FUTURE OPPORTUNITY ONLY:")
                    print(f"   Plan AHEAD: ₹{future['predictedPrice']} in {future['monthsToTouch']} months")
                
            else:
                print(f"❌ No signals found")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n" + "="*80)

if __name__ == "__main__":
    test_dual_signals()