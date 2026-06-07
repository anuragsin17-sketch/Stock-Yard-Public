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
                                     stoploss: float, signal_type: str, confluence: int = 0) -> bool:
        """Send trade alert WITH inline buttons"""
        
        message = (
            f"🚨 *TRADE SIGNAL*\n\n"
            f"📈 Stock: *{ticker}*\n"
            f"💹 Entry Price: ₹{price:,.2f}\n"
            f"🎯 Target: ₹{target:,.2f} (+{((target/price - 1)*100):.2f}%)\n"
            f"🛑 Stop Loss: ₹{stoploss:,.2f}\n"
        )
        
        if confluence > 0:
            message += f"📊 Confidence: {confluence}/10\n"
        
        message += f"\n⏰ {datetime.now().strftime('%H:%M IST')}"
        
        # Create trade URL with parameters (but don't show it in message)
        trade_params = {
            'ticker': ticker,
            'price': f"{price:.2f}",
            'target': f"{target:.2f}",
            'stoploss': f"{stoploss:.2f}",
            'type': signal_type
        }
        trade_url = f"https://anuragsin17-sketch.github.io/Stock-Yard-Public/trade.html?{urllib.parse.urlencode(trade_params)}"
        
        # Inline keyboard buttons (NO URL shown in message)
        keyboard = {
            'inline_keyboard': [
                [
                    {'text': '✅ Confirm Trade', 'url': trade_url}
                ],
                [
                    {'text': '📊 Dashboard', 'url': 'https://anuragsin17-sketch.github.io/Stock-Yard-Public/'}
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
            
            return response.status_code == 200
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

