import json

class ProductionPortfolioManager:
    def __init__(self, master_capital=500000.0, total_slots=10):
        self.total_equity = float(master_capital)
        self.num_slots = int(total_slots)
        # Sizing scales up dynamically after every trade exit
        self.current_slot_allocation = self.total_equity / self.num_slots

    def register_closed_trade_outcome(self, trade_allocated_capital, net_profit_or_loss):
        """
        Processes your exited positions, merges profits straight back into 
        the master pool, and increases your next trade allocation automatically.
        """
        # 1. Update your total master equity pool with the realized trade return
        self.total_equity += float(net_profit_or_loss)
        
        # 2. Recalculate your dynamic buying power for the very next entry slot
        self.current_slot_allocation = self.total_equity / self.num_slots
        
        print(f"💰 TRANSACTION LOGGED | New Account Equity: ₹{self.total_equity:,.2f}")
        print(f"🚀 DYNAMIC SCALING     | Next Slot Allocation Size: ₹{self.current_slot_allocation:,.2f}")
        
        return {
            "updated_total_equity": round(self.total_equity, 2),
            "next_slot_allocation": round(self.current_slot_allocation, 2),
            "strict_8pct_stoploss_cap": round(self.current_slot_allocation * 0.08, 2)
        }

    def save_summary_metrics(self):
        """
        Saves the current portfolio state to summary_metrics.json for dashboard consumption
        """
        metrics = {
            "compounding_account_state": {
                "master_equity_pool": round(self.total_equity, 2),
                "active_slot_allocation_limit": round(self.current_slot_allocation, 2),
                "strict_risk_per_trade": round(self.current_slot_allocation * 0.08, 2),
                "compounding_mode": "TOTAL_EQUITY_ACTIVE",
                "available_open_slots": self.num_slots
            }
        }
        
        with open("summary_metrics.json", "w") as f:
            json.dump(metrics, f, indent=4)
        
        print(f"✅ summary_metrics.json updated successfully")
        return metrics

# ==========================================
# SIMULATION IN KIRO TERMINAL
# ==========================================
if __name__ == "__main__":
    # Start your system tracker with 5 Lakhs capital and 10 open slots
    manager = ProductionPortfolioManager(master_capital=500000.0, total_slots=10)
    
    # Save initial state
    manager.save_summary_metrics()
    
    # Simulate closing out your GAIL trade with a massive target bounce profit of ₹28,260
    result = manager.register_closed_trade_outcome(trade_allocated_capital=50000.0, net_profit_or_loss=28260.0)
    
    # Save updated state
    manager.save_summary_metrics()
    
    print(f"\n📊 Updated Portfolio Metrics:")
    print(f"   Total Equity: ₹{result['updated_total_equity']:,.2f}")
    print(f"   Next Slot: ₹{result['next_slot_allocation']:,.2f}")
    print(f"   Max Risk per Trade: ₹{result['strict_8pct_stoploss_cap']:,.2f}")
