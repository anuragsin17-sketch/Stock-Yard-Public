#!/usr/bin/env python3
"""
Telegram Trade Bot - Simple version
- Receives button clicks
- Executes trades via Angel One (existing integration)
- Sends confirmations
"""

import os
import json
import requests
from datetime import datetime

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

class TelegramTradeBot:
    """Simple Telegram bot for trade execution"""
    
    def __init__(self):
        self.token = TELEGRAM_BOT_TOKEN
        self.chat_id = TELEGRAM_CHAT_ID
        self.api_url = f"https://api.telegram.org/bot{self.token}"
    
    def send_message(self, text: str) -> bool:
        """Send message to Telegram"""
        if not self.token or not self.chat_id:
            return False
        
        try:
            response = requests.post(f"{self.api_url}/sendMessage", json={
                'chat_id': self.chat_id,
                'text': text,
                'parse_mode': 'Markdown'
            }, timeout=10)
            return response.status_code == 200
        except:
            return False
    
    def send_trade_alert(self, ticker: str, price: float, target: float, 
                        stoploss: float, signal_type: str):
        """Send simple trade alert"""
        message = (
            f"🚨 *TRADE SIGNAL*\n\n"
            f"📈 {ticker}\n"
            f"💹 Price: ₹{price:,.2f}\n"
            f"🎯 Target: ₹{target:,.2f}\n"
            f"🛑 SL: ₹{stoploss:,.2f}\n"
            f"📊 Type: {signal_type}\n\n"
            f"⏰ {datetime.now().strftime('%H:%M IST')}"
        )
        return self.send_message(message)
    
    def send_confirmation(self, ticker: str, quantity: int, entry_price: float,
                         target: float, stoploss: float, order_id: str):
        """Send order confirmation"""
        message = (
            f"✅ *ORDER PLACED*\n\n"
            f"📈 {ticker}\n"
            f"📊 Qty: {quantity}\n"
            f"💹 Entry: ₹{entry_price:,.2f}\n"
            f"🎯 Target: ₹{target:,.2f}\n"
            f"🛑 SL: ₹{stoploss:,.2f}\n"
            f"📋 ID: {order_id}\n\n"
            f"✨ Trade is LIVE!"
        )
        return self.send_message(message)


if __name__ == "__main__":
    bot = TelegramTradeBot()
    bot.send_message("🤖 Stock Yard Bot Ready")

