#!/usr/bin/env python3
"""
Enhanced debug script showing Fibonacci confluence analysis
"""

from geometric_engine import MacroInstitutionalEngine

def debug_confluence_analysis():
    """Test confluence analysis on our known signals"""
    
    engine = MacroInstitutionalEngine(position_size=50000, sl_pct=8.0, touch_tolerance=5.0)
    
    # Test stocks that we know have signals
    test_stocks = ["HDFCBANK.NS", "ASIANPAINT.NS", "WIPRO.NS", "HINDUNILVR.NS"]
    
    print("🎯 FIBONACCI CONFLUENCE ANALYSIS")
    print("="*80)
    
    for ticker in test_stocks:
        print(f"\n📊 ANALYZING {ticker.replace('.NS', '')}")
        print("-" * 60)
        
        try:
            result = engine.process_ticker_geometry(ticker)
            
            if result:
                print(f"✅ SIGNAL FOUND!")
                print(f"   Current Price:     ₹{result['currentPrice']}")
                print(f"   Trendline Price:   ₹{result['triggerPrice']}")
                print(f"   Distance to Line:  {result['distanceRemaining']}%")
                print()
                
                # Show all Fibonacci levels
                fib_grid = result['fullFibGridPrices']
                print(f"📈 FIBONACCI LEVELS:")
                print(f"   23.6%: ₹{fib_grid['level_236']}")
                print(f"   38.2%: ₹{fib_grid['level_382']}")
                print(f"   50.0%: ₹{fib_grid['level_500']}")
                print(f"   61.8%: ₹{fib_grid['level_618']} (Golden Ratio)")
                print(f"   78.6%: ₹{fib_grid['level_786']}")
                print(f"  100.0%: ₹{fib_grid['level_1000']} (Last Touch)")
                print()
                
                # Show confluence analysis
                confluence = result['fibConfluence']
                print(f"🎯 CONFLUENCE ANALYSIS:")
                print(f"   Closest Fib Level: {confluence['closestLevel']}")
                print(f"   Distance to Closest: {confluence['distanceToClosest']}%")
                print(f"   Confluence Score: {confluence['confluenceScore']}/10")
                print(f"   Notes: {', '.join(confluence['confluenceNotes'])}")
                print()
                
                # Show distances to all levels
                print(f"📏 TRENDLINE DISTANCES TO ALL FIB LEVELS:")
                for level, distance in confluence['allDistances'].items():
                    status = "🎯" if level == confluence['closestLevel'] else "  "
                    print(f"   {status} {level}: {distance}% away")
                
                # Highlight golden catch points
                if confluence['confluenceScore'] >= 8:
                    print(f"\n🏆 GOLDEN CATCH POINT! High confluence setup!")
                elif confluence['confluenceScore'] >= 5:
                    print(f"\n⭐ GOOD SETUP! Moderate confluence.")
                
            else:
                print(f"❌ No signal found")
                
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print("\n" + "="*80)

if __name__ == "__main__":
    debug_confluence_analysis()