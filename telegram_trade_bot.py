#!/usr/bin/env python3
"""
Telegram Trade Bot - With buttons linking to trade form
- Sends alerts with buttons
- Buttons open trade confirmation page
- Trade execution happens via Angel One API
"""

import os
import json
import requests
from datetime import datetime
import urllib.parse

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

# Dashboard URL with trade form
DASHBOARD_URL = "https://anuragsin17-sketch.github.io/Stock-Yard-Public/"
TRADE_FORM_URL = "https://anuragsin17-sketch.github.io/Stock-Yard-Public/trade.html"

class TelegramTradeBot:
    """Telegram bot with buttons to trade form"""
    
    def __init__(self):
        self.token = TELEGRAM_BOT_TOKEN
        self.chat_id = TELEGRAM_CHAT_ID
        self.api_url = f"https://api.telegram.org/bot{self.token}"
    
    def send_message(self, text: str) -> bool:
        """Send simple message"""
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
    
    def send_trade_alert_with_buttons(self, ticker: str, price: float, target: float, 
                                     stoploss: float, signal_type: str, quantity: int = 10, 
                                     confluence: int = 0) -> bool:
        """Send trade alert WITH confirm button (callback, not URL)"""
        
        message = (
            f"🚨 *TRADE SIGNAL*\n\n"
            f"📈 *{ticker}*\n"
            f"💹 Entry: ₹{price:,.0f}\n"
            f"🎯 Target: ₹{target:,.0f}\n"
            f"🛑 SL: ₹{stoploss:,.0f}\n"
            f"📊 Size: {quantity} units\n"
        )
        
        if confluence > 0:
            message += f"⭐ Confidence: {confluence}/10\n"
        
        message += f"⏰ {datetime.now().strftime('%H:%M IST')}"
        
        # Callback button data: confirm_trade:TICKER:PRICE:TARGET:SL:QTY
        callback_data = f"confirm_trade:{ticker}:{price:.2f}:{target:.2f}:{stoploss:.2f}:{quantity}"
        
        # Inline keyboard with callback button (NOT URL)
        keyboard = {
            'inline_keyboard': [
                [
                    {'text': '✅ Confirm Trade', 'callback_data': callback_data},
                    {'text': '⏭️ Skip', 'callback_data': f'skip_trade:{ticker}'}
                ]
            ]
        }
        
        try:
            response = requests.post(f"{self.api_url}/sendMessage", json={
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'Markdown',
                'reply_markup': keyboard
            }, timeout=10)
            
            if response.status_code == 200:
                print(f"✅ Alert sent for {ticker}")
                return True
            else:
                print(f"❌ Failed: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
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

