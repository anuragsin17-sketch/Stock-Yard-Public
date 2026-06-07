#!/usr/bin/env python3
"""
Smart Alert Tracker for Stock Yard Bot
Prevents duplicate notifications by tracking stocks already alerted
Maintains Volume, Trendline, and Radar tabs with state tracking
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

class SmartAlertTracker:
    """Tracks alerted stocks to prevent duplicates across scanner runs"""
    
    def __init__(self, config_dir='/home/ubuntu/stock_yard_config'):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Alert state file
        self.alert_state_file = self.config_dir / 'alert_state.json'
        self.state = self._load_state()
    
    def _load_state(self):
        """Load existing alert state or create new one"""
        if self.alert_state_file.exists():
            try:
                with open(self.alert_state_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        return {
            'volume': {},      # Stocks in volume tab
            'trendline': {},   # Stocks in trendline tab
            'radar': {},       # Stocks in radar tab
            'last_updated': datetime.now().isoformat()
        }
    
    def _save_state(self):
        """Save alert state to file"""
        self.state['last_updated'] = datetime.now().isoformat()
        try:
            with open(self.alert_state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save alert state: {e}")
    
    def is_already_alerted(self, ticker, tab_type):
        """Check if stock was already alerted in this tab"""
        if tab_type not in self.state:
            return False
        
        if ticker in self.state[tab_type]:
            # Check if alert is still fresh (within 24 hours)
            alert_time = self.state[tab_type][ticker]
            alert_datetime = datetime.fromisoformat(alert_time)
            if datetime.now() - alert_datetime < timedelta(hours=24):
                return True
            else:
                # Alert expired, can notify again
                del self.state[tab_type][ticker]
                self._save_state()
                return False
        
        return False
    
    def mark_alerted(self, ticker, tab_type):
        """Mark stock as alerted in specific tab"""
        if tab_type not in self.state:
            self.state[tab_type] = {}
        
        self.state[tab_type][ticker] = datetime.now().isoformat()
        self._save_state()
    
    def get_new_alerts(self, stocks_dict, tab_type):
        """
        Filter stocks to only return NEW ones not previously alerted
        
        Args:
            stocks_dict: Dict of stocks with their data
            tab_type: 'volume', 'trendline', or 'radar'
        
        Returns:
            Dict of only NEW stocks that haven't been alerted
        """
        new_stocks = {}
        
        for ticker, data in stocks_dict.items():
            if not self.is_already_alerted(ticker, tab_type):
                new_stocks[ticker] = data
                # Mark as alerted immediately
                self.mark_alerted(ticker, tab_type)
        
        return new_stocks
    
    def get_status(self):
        """Get current tracking status"""
        return {
            'volume_tracked': len(self.state.get('volume', {})),
            'trendline_tracked': len(self.state.get('trendline', {})),
            'radar_tracked': len(self.state.get('radar', {})),
            'last_updated': self.state.get('last_updated')
        }
    
    def reset_old_alerts(self, hours=24):
        """Remove alerts older than specified hours"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        for tab_type in ['volume', 'trendline', 'radar']:
            if tab_type in self.state:
                expired = []
                for ticker, alert_time_str in self.state[tab_type].items():
                    try:
                        alert_time = datetime.fromisoformat(alert_time_str)
                        if alert_time < cutoff_time:
                            expired.append(ticker)
                    except:
                        expired.append(ticker)
                
                for ticker in expired:
                    del self.state[tab_type][ticker]
        
        self._save_state()


def test_tracker():
    """Test the alert tracker"""
    tracker = SmartAlertTracker()
    
    print("\n=== Smart Alert Tracker Test ===\n")
    
    # Test marking stocks as alerted
    tracker.mark_alerted('RELIANCE', 'volume')
    tracker.mark_alerted('TCS', 'trendline')
    tracker.mark_alerted('INFY', 'radar')
    
    print("✓ Marked stocks as alerted")
    
    # Test checking if already alerted
    print(f"\nRELIANCE in volume? {tracker.is_already_alerted('RELIANCE', 'volume')}")
    print(f"WIPRO in volume? {tracker.is_already_alerted('WIPRO', 'volume')}")
    
    # Test filtering new stocks
    test_stocks = {
        'RELIANCE': {'price': 2500},
        'WIPRO': {'price': 400},
        'HCLTECH': {'price': 1300}
    }
    
    new_stocks = tracker.get_new_alerts(test_stocks, 'volume')
    print(f"\nNew stocks (volume): {list(new_stocks.keys())}")
    
    # Show status
    status = tracker.get_status()
    print(f"\nTracker Status:")
    print(f"  Volume tracked: {status['volume_tracked']}")
    print(f"  Trendline tracked: {status['trendline_tracked']}")
    print(f"  Radar tracked: {status['radar_tracked']}")
    print(f"  Last updated: {status['last_updated']}\n")


if __name__ == '__main__':
    test_tracker()
