#!/usr/bin/env python3
"""
Trigger Manager - Interface to manage custom trigger points
"""

from editable_trigger_engine import EditableTriggerEngine
import sys

class TriggerManager:
    def __init__(self):
        self.engine = EditableTriggerEngine()
    
    def show_menu(self):
        """Display the trigger management menu"""
        print("\n" + "="*60)
        print("🎯 TRIGGER POINT MANAGER")
        print("="*60)
        print("1. Set Custom Trigger")
        print("2. Remove Custom Trigger") 
        print("3. List All Custom Triggers")
        print("4. Test Stock with Current Triggers")
        print("5. Compare Calculated vs Custom Triggers")
        print("6. Exit")
        print("="*60)
    
    def set_trigger(self):
        """Set a custom trigger for a stock"""
        print("\n📝 SET CUSTOM TRIGGER")
        print("-" * 30)
        
        ticker = input("Enter stock symbol (e.g., ASIANPAINT): ").strip().upper()
        if not ticker:
            print("❌ Invalid ticker")
            return
        
        try:
            price = float(input(f"Enter custom trigger price for {ticker}: ₹"))
            notes = input("Enter notes (optional): ").strip()
            
            if not notes:
                notes = "Manual override"
            
            self.engine.set_custom_trigger(ticker, price, notes)
            
        except ValueError:
            print("❌ Invalid price format")
    
    def remove_trigger(self):
        """Remove a custom trigger"""
        print("\n🗑️  REMOVE CUSTOM TRIGGER")
        print("-" * 30)
        
        ticker = input("Enter stock symbol to remove: ").strip().upper()
        if ticker:
            self.engine.remove_custom_trigger(ticker)
    
    def list_triggers(self):
        """List all custom triggers"""
        print("\n📋 CUSTOM TRIGGERS")
        print("-" * 30)
        self.engine.list_custom_triggers()
    
    def test_stock(self):
        """Test a stock with current trigger settings"""
        print("\n🧪 TEST STOCK")
        print("-" * 30)
        
        ticker = input("Enter stock symbol to test: ").strip().upper()
        if not ticker:
            return
        
        # Add .NS if not present
        if not ticker.endswith(".NS"):
            ticker += ".NS"
        
        print(f"\nAnalyzing {ticker}...")
        result = self.engine.process_ticker_geometry(ticker)
        
        if result:
            current = result['currentSignal']
            trigger_info = result['triggerInfo']
            
            print(f"\n✅ SIGNAL FOUND:")
            print(f"   Current Price: ₹{current['currentPrice']}")
            print(f"   Trigger Price: ₹{trigger_info['effectivePrice']} ({trigger_info['source']})")
            
            if trigger_info['isCustom']:
                print(f"   📝 CUSTOM TRIGGER:")
                print(f"      Set Date: {trigger_info['setDate']}")
                print(f"      Notes: {trigger_info['notes']}")
                print(f"      Original Calculated: ₹{trigger_info['originalCalculated']}")
                
                # Show difference
                diff = trigger_info['effectivePrice'] - trigger_info['originalCalculated']
                diff_pct = (diff / trigger_info['originalCalculated']) * 100
                print(f"      Adjustment: ₹{diff:+.2f} ({diff_pct:+.2f}%)")
            
            print(f"   Distance: {current['distanceRemaining']}%")
            print(f"   Confluence: {current['confluenceScore']}/10 ({current['fibLevelMatch']})")
            print(f"   Zone: {current['patternZone']}")
            print(f"   Alert Active: {'Yes' if current['notificationTrigger'] else 'No'}")
            
        else:
            print("❌ No signal found for this stock")
    
    def compare_triggers(self):
        """Compare calculated vs custom triggers for all stocks"""
        print("\n⚖️  TRIGGER COMPARISON")
        print("-" * 50)
        
        if not self.engine.trigger_overrides:
            print("No custom triggers to compare.")
            return
        
        print(f"{'Stock':<12} {'Calculated':<12} {'Custom':<12} {'Diff':<10} {'Status'}")
        print("-" * 60)
        
        for ticker in self.engine.trigger_overrides.keys():
            ticker_ns = ticker + ".NS"
            
            # Temporarily remove custom trigger to get calculated value
            original_override = self.engine.trigger_overrides[ticker].copy()
            self.engine.trigger_overrides[ticker]['isActive'] = False
            
            result = self.engine.process_ticker_geometry(ticker_ns)
            
            # Restore custom trigger
            self.engine.trigger_overrides[ticker] = original_override
            
            if result:
                calculated = result['triggerInfo']['originalCalculated']
                custom = original_override['customTrigger']
                diff = custom - calculated
                diff_pct = (diff / calculated) * 100
                
                # Check if stock is currently signaling
                current_result = self.engine.process_ticker_geometry(ticker_ns)
                status = "🟢 ACTIVE" if current_result else "🔴 INACTIVE"
                
                print(f"{ticker:<12} ₹{calculated:<11.2f} ₹{custom:<11.2f} {diff_pct:>+6.2f}% {status}")
            else:
                print(f"{ticker:<12} {'N/A':<12} ₹{original_override['customTrigger']:<11.2f} {'N/A':<10} 🔴 NO SIGNAL")
    
    def run(self):
        """Run the trigger manager interface"""
        while True:
            self.show_menu()
            
            try:
                choice = input("\nSelect option (1-6): ").strip()
                
                if choice == '1':
                    self.set_trigger()
                elif choice == '2':
                    self.remove_trigger()
                elif choice == '3':
                    self.list_triggers()
                elif choice == '4':
                    self.test_stock()
                elif choice == '5':
                    self.compare_triggers()
                elif choice == '6':
                    print("👋 Goodbye!")
                    break
                else:
                    print("❌ Invalid option. Please select 1-6.")
                    
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")

if __name__ == "__main__":
    manager = TriggerManager()
    manager.run()