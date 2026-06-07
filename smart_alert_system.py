#!/usr/bin/env python3
"""
Smart Alert System for Stock Yard Bot
Sends Telegram alerts without duplicate stocks across runs
Tracks Volume, Trendline, and Radar tabs separately
"""

import json
import requests
import time
from pathlib import Path
from smart_alert_tracker import SmartAlertTracker

class SmartAlertSystem:
    """Sends alerts only for new stocks, preventing duplicates"""
    
    def __init__(self, config_path='/home/ubuntu/stock_yard_config/bot_config.json'):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.tracker = SmartAlertTracker()
        
        self.bot_token = self.config.get('TELEGRAM_BOT_TOKEN', '')
        self.chat_id = self.config.get('TELEGRAM_CHAT_ID', '')
    
    def _load_config(self):
        """Load Telegram config"""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except:
            return {}
    
    def send_message(self, message, parse_mode='HTML'):
        """Send message via Telegram"""
        if not self.bot_token or not self.chat_id:
            print("✗ Telegram credentials not configured")
            return False
        
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': parse_mode
            }
            
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"✗ Error sending message: {e}")
            return False
    
    def alert_volume_stocks(self, stocks_list):
        """Alert for VOLUME tab stocks - only new ones"""
        stocks_dict = {stock['ticker']: stock for stock in stocks_list}
        new_stocks = self.tracker.get_new_alerts(stocks_dict, 'volume')
        
        if not new_stocks:
            print("📊 Volume: No new stocks to alert")
            return
        
        message = "📊 <b>VOLUME Tab - New Entry!</b>\n"
        message += f"Found {len(new_stocks)} new stock(s):\n\n"
        
        for ticker, data in list(new_stocks.items())[:5]:  # Limit to 5 per message
            price = data.get('price', 'N/A')
            volume = data.get('volume', 'N/A')
            message += f"🔹 <b>{ticker}</b> @ ₹{price}\n"
        
        message += "\n✅ Added to Volume Radar"
        
        if self.send_message(message):
            print(f"✓ Volume alert sent for {len(new_stocks)} stock(s)")
        else:
            print(f"✗ Failed to send volume alert")
    
    def alert_trendline_stocks(self, stocks_list):
        """Alert for TRENDLINE tab stocks - only new ones"""
        stocks_dict = {stock['ticker']: stock for stock in stocks_list}
        new_stocks = self.tracker.get_new_alerts(stocks_dict, 'trendline')
        
        if not new_stocks:
            print("📈 Trendline: No new stocks to alert")
            return
        
        message = "📈 <b>TRENDLINE Support Zone - Entry Opportunity!</b>\n"
        message += f"Found {len(new_stocks)} new stock(s) near support:\n\n"
        
        for ticker, data in list(new_stocks.items())[:5]:
            current = data.get('current_price', 'N/A')
            support = data.get('support_price', 'N/A')
            distance = data.get('distance_pct', 'N/A')
            message += f"🎯 <b>{ticker}</b>\n"
            message += f"  Current: ₹{current}\n"
            message += f"  Support: ₹{support}\n"
            message += f"  Distance: {distance}%\n\n"
        
        message += "🚀 Ready for entry signal"
        
        if self.send_message(message):
            print(f"✓ Trendline alert sent for {len(new_stocks)} stock(s)")
        else:
            print(f"✗ Failed to send trendline alert")
    
    def alert_radar_stocks(self, stocks_list):
        """Alert for RADAR tab stocks - only new ones"""
        stocks_dict = {stock['ticker']: stock for stock in stocks_list}
        new_stocks = self.tracker.get_new_alerts(stocks_dict, 'radar')
        
        if not new_stocks:
            print("🎯 Radar: No new stocks to alert")
            return
        
        message = "🎯 <b>RADAR - Critical Entry Zone!</b>\n"
        message += f"⚡ {len(new_stocks)} stock(s) in critical zone:\n\n"
        
        for ticker, data in list(new_stocks.items())[:3]:  # Limit to 3
            status = data.get('status', 'WATCHLIST')
            price = data.get('entry_price', 'N/A')
            target = data.get('target_price', 'N/A')
            
            if status == 'CRITICAL_TOUCH':
                emoji = "🔴"
            else:
                emoji = "🟡"
            
            message += f"{emoji} <b>{ticker}</b>\n"
            message += f"  Entry: ₹{price}\n"
            message += f"  Target: ₹{target}\n"
            message += f"  Status: {status}\n\n"
        
        message += "💰 Prepare position size: ₹50,000"
        
        if self.send_message(message):
            print(f"✓ Radar alert sent for {len(new_stocks)} stock(s)")
        else:
            print(f"✗ Failed to send radar alert")
    
    def send_scan_summary(self, total_stocks, volume_count, trendline_count, radar_count):
        """Send scan completion summary"""
        message = "✅ <b>Scan Complete</b>\n\n"
        message += f"📊 Total Stocks Scanned: {total_stocks}\n"
        message += f"📊 Volume Tab: {volume_count} new\n"
        message += f"📈 Trendline Tab: {trendline_count} new\n"
        message += f"🎯 Radar Tab: {radar_count} new\n\n"
        message += "⏱️ Next scan in 5 minutes\n"
        message += "🤖 Stock Yard Bot Active"
        
        if self.send_message(message):
            print("✓ Scan summary sent")
        else:
            print("✗ Failed to send scan summary")
    
    def get_tracker_status(self):
        """Get current tracking status"""
        return self.tracker.get_status()


def test_alert_system():
    """Test the smart alert system"""
    system = SmartAlertSystem()
    
    print("\n=== Smart Alert System Test ===\n")
    
    # Test volume alert
    volume_stocks = [
        {'ticker': 'RELIANCE', 'price': 2500, 'volume': '50M'},
        {'ticker': 'TCS', 'price': 3500, 'volume': '30M'},
    ]
    system.alert_volume_stocks(volume_stocks)
    
    time.sleep(1)
    
    # Test trendline alert
    trendline_stocks = [
        {'ticker': 'INFY', 'current_price': 1400, 'support_price': 1350, 'distance_pct': '3.5%'},
        {'ticker': 'WIPRO', 'current_price': 400, 'support_price': 385, 'distance_pct': '3.75%'},
    ]
    system.alert_trendline_stocks(trendline_stocks)
    
    time.sleep(1)
    
    # Test radar alert
    radar_stocks = [
        {'ticker': 'HCLTECH', 'status': 'CRITICAL_TOUCH', 'entry_price': 1250, 'target_price': 1530},
        {'ticker': 'TECHM', 'status': 'WATCHLIST', 'entry_price': 900, 'target_price': 1100},
    ]
    system.alert_radar_stocks(radar_stocks)
    
    time.sleep(1)
    
    # Send summary
    system.send_scan_summary(500, 2, 2, 2)
    
    # Show tracker status
    status = system.get_tracker_status()
    print(f"\nTracker Status: {status}\n")


if __name__ == '__main__':
    test_alert_system()
