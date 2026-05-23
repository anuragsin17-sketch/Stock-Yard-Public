#!/usr/bin/env python3
"""
Simple test to debug the issue
"""

from geometric_engine import MacroInstitutionalEngine

def test_simple():
    """Simple test"""
    
    engine = MacroInstitutionalEngine(position_size=50000, sl_pct=8.0, touch_tolerance=5.0)
    
    print("Testing ASIANPAINT.NS...")
    try:
        result = engine.process_ticker_geometry("ASIANPAINT.NS")
        if result:
            print("✅ Signal found!")
            print(f"Current: {result['currentPrice']}")
            print(f"Trigger: {result['triggerPrice']}")
            if 'fibConfluence' in result:
                print(f"Confluence Score: {result['fibConfluence']['confluenceScore']}")
                print(f"Closest Fib: {result['fibConfluence']['closestLevel']}")
                print(f"Notes: {result['fibConfluence']['confluenceNotes']}")
        else:
            print("❌ No signal")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_simple()