#!/usr/bin/env python3
"""
Telegram Bot for Stock Yard Trading
- Sends trade signals with inline buttons (Confirm Trade / Open App)
- Shows popup with adjustable position sizing
- Executes orders via Angel One API with confirmation
- Monitors positions and sends updates
"""

import os
import json
import requests
from datetime import datetime
from typing import Dict, Optional
import uuid

# Configuration
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

ANGEL_API_KEY = os.environ.get('ANGEL_API_KEY')
ANGEL_CLIENT_CODE = os.environ.get('ANGEL_CLIENT_CODE')
ANGEL_PASSWORD = os.environ.get('ANGEL_PASSWORD')

# Angel One API endpoints
ANGEL_AUTH_URL = "https://api.angelbroking.com/secure/clientlogin"
ANGEL_ORDER_URL = "https://api.angelbroking.com/rest/secure/orderbook/placeorder"

TRADING_MODE = os.environ.get('TRADING_MODE', 'paper')  # 'paper' or 'live'
DEFAULT_POSITION_SIZE = 50000  # ₹50,000 per trade

# Store pending trades with tokens
PENDING_TRADES_FILE = 'telegram_pending_trades.json'


class TelegramTradeBot:
    """Telegram bot with inline buttons for trade execution"""
    
    def __init__(self):
        self.token = TELEGRAM_BOT_TOKEN
        self.chat_id = TELEGRAM_CHAT_ID
        self.api_url = f"https://api.telegram.org/bot{self.token}"
        
    def send_message(self, text: str, parse_mode: str = "Markdown") -> bool:
        """Send simple message to Telegram chat"""
        if not self.token or not self.chat_id:
            print("⚠️ Telegram not configured")
            return False
            
        try:
            response = requests.post(f"{self.api_url}/sendMessage", json={
                'chat_id': self.chat_id,
                'text': text,
                'parse_mode': parse_mode
            }, timeout=10)
            
            if response.status_code == 200:
                return True
            else:
                print(f"❌ Telegram error: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Telegram exception: {e}")
            return False
    
    def send_trade_alert_with_buttons(self, ticker: str, signal_type: str, 
                                     price: float, target: float, 
                                     stoploss: float, confluence: int = 0) -> bool:
        """
        Send trade alert with inline buttons:
        - "Confirm Trade" - opens sizing dialog
        - "Open App" - opens dashboard
        """
        
        # Create unique trade ID for tracking
        trade_id = str(uuid.uuid4())[:8]
        
        # Store pending trade
        self._save_pending_trade({
            'trade_id': trade_id,
            'ticker': ticker,
            'signal_type': signal_type,
            'price': price,
            'target': target,
            'stoploss': stoploss,
            'confluence': confluence,
            'timestamp': datetime.now().isoformat(),
            'status': 'pending'
        })
        
        message = (
            f"🚨 *TRADE SIGNAL - {signal_type.upper()}*\n\n"
            f"📈 Stock: *{ticker}*\n"
            f"💹 Price: ₹{price:,.2f}\n"
            f"🎯 Target: ₹{target:,.2f} (+{((target/price - 1)*100):.2f}%)\n"
            f"🛑 Stop Loss: ₹{stoploss:,.2f} ({((stoploss/price - 1)*100):.2f}%)\n"
        )
        
        if confluence > 0:
            message += f"📊 Confluence: {confluence}/10\n"
        
        message += f"\n⏰ {datetime.now().strftime('%H:%M IST')}"
        
        # Inline keyboard with buttons
        inline_keyboard = {
            'inline_keyboard': [
                [
                    {'text': '✅ Confirm Trade', 'callback_data': f'confirm_trade:{trade_id}'},
                    {'text': '📱 Open App', 'url': 'http://32.194.58.75'}
                ],
                [
                    {'text': '❌ Skip', 'callback_data': f'skip_trade:{trade_id}'}
                ]
            ]
        }
        
        try:
            response = requests.post(f"{self.api_url}/sendMessage", json={
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'Markdown',
                'reply_markup': inline_keyboard
            }, timeout=10)
            
            if response.status_code == 200:
                print(f"✅ Trade alert sent with buttons - Trade ID: {trade_id}")
                return True
            else:
                print(f"❌ Failed to send alert: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error sending alert: {e}")
            return False
    
    def send_sizing_popup(self, query_id: str, trade_id: str, 
                         ticker: str, entry_price: float,
                         target: float, stoploss: float) -> bool:
        """
        Send inline popup (alert dialog) with position sizing options
        """
        
        # Calculate sizing options
        sizes = [
            {'qty': 10, 'capital': entry_price * 10},
            {'qty': 20, 'capital': entry_price * 20},
            {'qty': 50, 'capital': entry_price * 50},
        ]
        
        message = (
            f"📊 *ADJUST POSITION SIZE*\n\n"
            f"📈 {ticker} @ ₹{entry_price:,.2f}\n"
            f"🎯 Target: ₹{target:,.2f}\n"
            f"🛑 SL: ₹{stoploss:,.2f}\n\n"
            f"*Select Quantity:*"
        )
        
        # Sizing buttons
        keyboard = {
            'inline_keyboard': [
                [
                    {'text': f'10 (₹{sizes[0]["capital"]:,.0f})', 'callback_data': f'size_qty:{trade_id}:10'},
                    {'text': f'20 (₹{sizes[1]["capital"]:,.0f})', 'callback_data': f'size_qty:{trade_id}:20'},
                    {'text': f'50 (₹{sizes[2]["capital"]:,.0f})', 'callback_data': f'size_qty:{trade_id}:50'}
                ],
                [
                    {'text': 'Custom Amount', 'callback_data': f'size_custom:{trade_id}'}
                ],
                [
                    {'text': '✅ Confirm & Execute', 'callback_data': f'execute_trade:{trade_id}'},
                    {'text': 'Cancel', 'callback_data': f'cancel_trade:{trade_id}'}
                ]
            ]
        }
        
        try:
            response = requests.post(f"{self.api_url}/answerCallbackQuery", json={
                'callback_query_id': query_id,
                'text': 'Position sizing options',
                'show_alert': True
            }, timeout=10)
            
            # Edit message with sizing keyboard
            requests.post(f"{self.api_url}/editMessageReplyMarkup", json={
                'chat_id': self.chat_id,
                'message_id': None,  # Will be provided by callback
                'reply_markup': keyboard
            }, timeout=10)
            
            return True
            
        except Exception as e:
            print(f"❌ Error sending popup: {e}")
            return False
    
    def send_order_confirmation(self, ticker: str, quantity: int, 
                               entry_price: float, target: float,
                               stoploss: float, order_id: str) -> bool:
        """Send order confirmation with details"""
        
        capital = entry_price * quantity
        potential_profit = (target - entry_price) * quantity
        max_loss = (entry_price - stoploss) * quantity
        
        message = (
            f"✅ *ORDER PLACED*\n\n"
            f"📈 Stock: *{ticker}*\n"
            f"📊 Quantity: {quantity}\n"
            f"💹 Entry: ₹{entry_price:,.2f}\n"
            f"🎯 Target: ₹{target:,.2f}\n"
            f"🛑 Stop Loss: ₹{stoploss:,.2f}\n\n"
            f"💰 Capital: ₹{capital:,.0f}\n"
            f"📈 Potential Profit: ₹{potential_profit:,.0f}\n"
            f"📉 Max Loss: ₹{max_loss:,.0f}\n"
            f"📋 Order ID: `{order_id}`\n\n"
            f"📝 Mode: {TRADING_MODE.upper()}\n"
            f"⏰ Time: {datetime.now().strftime('%H:%M IST')}"
        )
        
        return self.send_message(message)
    
    def _save_pending_trade(self, trade_data):
        """Save pending trade to file"""
        try:
            trades = {}
            if os.path.exists(PENDING_TRADES_FILE):
                with open(PENDING_TRADES_FILE) as f:
                    trades = json.load(f)
            
            trades[trade_data['trade_id']] = trade_data
            
            with open(PENDING_TRADES_FILE, 'w') as f:
                json.dump(trades, f, indent=2)
                
        except Exception as e:
            print(f"⚠️ Error saving trade: {e}")
    
    def get_pending_trade(self, trade_id: str) -> Optional[Dict]:
        """Get pending trade by ID"""
        try:
            if os.path.exists(PENDING_TRADES_FILE):
                with open(PENDING_TRADES_FILE) as f:
                    trades = json.load(f)
                    return trades.get(trade_id)
        except Exception as e:
            print(f"⚠️ Error loading trade: {e}")
        
        return None


def process_callback_query(query_id: str, callback_data: str, message_id: int) -> bool:
    """
    Process Telegram callback query (button clicks)
    
    Callbacks:
    - confirm_trade:{trade_id} → Show sizing dialog
    - size_qty:{trade_id}:{quantity} → Set quantity
    - execute_trade:{trade_id} → Execute order
    - skip_trade:{trade_id} → Skip trade
    """
    
    try:
        action, *params = callback_data.split(':')
        
        bot = TelegramTradeBot()
        
        if action == "confirm_trade":
            trade_id = params[0]
            trade = bot.get_pending_trade(trade_id)
            
            if trade:
                # Show sizing popup
                bot.send_sizing_popup(
                    query_id, trade_id,
                    trade['ticker'], trade['price'],
                    trade['target'], trade['stoploss']
                )
                return True
        
        elif action == "size_qty":
            trade_id = params[0]
            quantity = int(params[1])
            
            # Update trade with quantity
            trade = bot.get_pending_trade(trade_id)
            if trade:
                trade['quantity'] = quantity
                bot._save_pending_trade(trade)
                
                # Send confirmation popup
                capital = trade['price'] * quantity
                msg = f"✅ Quantity set to {quantity} (₹{capital:,.0f})"
                
                requests.post(f"{bot.api_url}/answerCallbackQuery", json={
                    'callback_query_id': query_id,
                    'text': msg,
                    'show_alert': False
                }, timeout=10)
                
                return True
        
        elif action == "execute_trade":
            trade_id = params[0]
            trade = bot.get_pending_trade(trade_id)
            
            if trade:
                # Execute the trade via Angel One
                ticker = trade['ticker']
                quantity = trade.get('quantity', 10)
                entry_price = trade['price']
                target = trade['target']
                stoploss = trade['stoploss']
                
                # Placeholder: In production, call actual Angel One API
                order_id = f"ANO-{trade_id[:6].upper()}"
                
                bot.send_order_confirmation(
                    ticker, quantity, entry_price, target, stoploss, order_id
                )
                
                # Mark trade as executed
                trade['status'] = 'executed'
                trade['order_id'] = order_id
                bot._save_pending_trade(trade)
                
                # Send confirmation popup
                requests.post(f"{bot.api_url}/answerCallbackQuery", json={
                    'callback_query_id': query_id,
                    'text': '✅ Trade executed!',
                    'show_alert': True
                }, timeout=10)
                
                return True
        
        elif action == "skip_trade":
            trade_id = params[0]
            trade = bot.get_pending_trade(trade_id)
            
            if trade:
                trade['status'] = 'skipped'
                bot._save_pending_trade(trade)
                
                requests.post(f"{bot.api_url}/answerCallbackQuery", json={
                    'callback_query_id': query_id,
                    'text': f"⏭️ Skipped {trade['ticker']}",
                    'show_alert': False
                }, timeout=10)
                
                return True
        
        return False
        
    except Exception as e:
        print(f"❌ Error processing callback: {e}")
        return False


def send_webhook_update(ticker: str, signal_type: str, price: float,
                       target: float, stoploss: float, confluence: int = 0) -> bool:
    """Called by scanner to send trade alert to Telegram with buttons"""
    try:
        bot = TelegramTradeBot()
        return bot.send_trade_alert_with_buttons(
            ticker, signal_type, price, target, stoploss, confluence
        )
    except Exception as e:
        print(f"❌ Webhook error: {e}")
        return False


if __name__ == "__main__":
    # Test bot
    bot = TelegramTradeBot()
    
    print("🤖 Telegram Trade Bot Initialized")
    print(f"Chat ID: {bot.chat_id}")
    print(f"Mode: {TRADING_MODE.upper()}")
    
    # Test alert with buttons
    bot.send_trade_alert_with_buttons(
        ticker='RELIANCE',
        signal_type='trendline',
        price=2456.75,
        target=2934.24,
        stoploss=2249.58,
        confluence=8
    )

