#!/usr/bin/env python3
"""
Test the editable trigger system
"""

from editable_trigger_engine import EditableTriggerEngine

def test_editable_triggers():
    """Test how custom triggers affect signal detection"""
    
    engine = EditableTriggerEngine()
    
    print("🎯 EDITABLE TRIGGER SYSTEM TEST")
    print("="*70)
    
    # Test ASIANPAINT with and without custom trigger
    ticker = "ASIANPAINT.NS"
    
    print(f"\n📊 Testing {ticker.replace('.NS', '')}:")
    print("-" * 50)
    
    # 1. Test with calculated trigger (remove any custom first)
    engine.remove_custom_trigger("ASIANPAINT")
    
    result1 = engine.process_ticker_geometry(ticker)
    if result1:
        calc_trigger = result1['triggerInfo']['effectivePrice']
        calc_distance = result1['currentSignal']['distanceRemaining']
        calc_confluence = result1['currentSignal']['confluenceScore']
        
        print(f"🔢 CALCULATED TRIGGER:")
        print(f"   Trigger Price: ₹{calc_trigger}")
        print(f"   Distance: {calc_distance}%")
        print(f"   Confluence: {calc_confluence}/10")
        print(f"   Source: {result1['triggerInfo']['source']}")
    
    # 2. Set custom trigger and test again
    custom_trigger = 2600.00  # Lower than calculated
    engine.set_custom_trigger("ASIANPAINT", custom_trigger, "Better entry point based on support")
    
    result2 = engine.process_ticker_geometry(ticker)
    if result2:
        custom_trigger_price = result2['triggerInfo']['effectivePrice']
        custom_distance = result2['currentSignal']['distanceRemaining']
        custom_confluence = result2['currentSignal']['confluenceScore']
        
        print(f"\n✏️  CUSTOM TRIGGER:")
        print(f"   Trigger Price: ₹{custom_trigger_price}")
        print(f"   Distance: {custom_distance}%")
        print(f"   Confluence: {custom_confluence}/10")
        print(f"   Source: {result2['triggerInfo']['source']}")
        print(f"   Set Date: {result2['triggerInfo']['setDate']}")
        print(f"   Notes: {result2['triggerInfo']['notes']}")
        
        # Show the difference
        if result1:
            price_diff = custom_trigger_price - calc_trigger
            distance_diff = custom_distance - calc_distance
            
            print(f"\n📈 COMPARISON:")
            print(f"   Price Adjustment: ₹{price_diff:+.2f}")
            print(f"   Distance Change: {distance_diff:+.2f}%")
            print(f"   Impact: {'Closer to entry' if distance_diff < 0 else 'Further from entry'}")
    
    # 3. Test another stock - HDFCBANK
    print(f"\n" + "="*70)
    print(f"📊 Testing HDFCBANK:")
    print("-" * 50)
    
    # Set custom trigger for HDFCBANK
    engine.set_custom_trigger("HDFCBANK", 790.00, "Adjusted for key resistance level")
    
    result3 = engine.process_ticker_geometry("HDFCBANK.NS")
    if result3:
        print(f"✅ HDFCBANK with Custom Trigger:")
        print(f"   Current Price: ₹{result3['currentSignal']['currentPrice']}")
        print(f"   Custom Trigger: ₹{result3['triggerInfo']['effectivePrice']}")
        print(f"   Original Calculated: ₹{result3['triggerInfo']['originalCalculated']}")
        print(f"   Distance: {result3['currentSignal']['distanceRemaining']}%")
        print(f"   Confluence: {result3['currentSignal']['confluenceScore']}/10")
        
        adjustment = result3['triggerInfo']['effectivePrice'] - result3['triggerInfo']['originalCalculated']
        print(f"   Adjustment: ₹{adjustment:+.2f}")
    
    # 4. Show all active custom triggers
    print(f"\n" + "="*70)
    print("📋 ALL ACTIVE CUSTOM TRIGGERS:")
    print("="*70)
    engine.list_custom_triggers()
    
    print(f"\n💡 USAGE TIPS:")
    print("- Use trigger_manager.py for interactive management")
    print("- Custom triggers are saved in trigger_overrides.json")
    print("- Set triggers based on your technical analysis")
    print("- Monitor how custom triggers affect confluence scores")
    print("- Remove custom triggers when no longer needed")

if __name__ == "__main__":
    test_editable_triggers()