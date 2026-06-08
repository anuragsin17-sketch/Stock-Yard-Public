#!/usr/bin/env python3
"""
Trigger a Telegram notification with trade confirmation button
Then place an order on Angel One
"""

import os
import json
import secrets
import requests
from datetime import datetime, timedelta

# Configuration
TELEGRAM_BOT_TOKEN = "8253327701:AAGNFzBJ8QwKw8x8Hg-tlvWHg18DD4lgogQ"
TELEGRAM_CHAT_ID = "8901309420"
EC2_API_URL = "http://32.194.58.75:5000"

def send_telegram_notification(stock_symbol, entry_price, target, stop_loss, quantity):
    """Send Telegram notification with confirm/cancel buttons"""
    
    # Create secure token
    token = secrets.token_hex(32)
    
    # Save token with expiry
    token_data = {
        "ticker": stock_symbol,
        "currentPrice": entry_price,
        "targetExit": target,
        "stopLoss": stop_loss,
        "sharesToBuy": quantity,
        "source": "manual_trigger",
        "expires_at": (datetime.now() + timedelta(minutes=10)).isoformat()
    }
    
    # Save token to file
    tokens = {}
    if os.path.exists('active_trade_tokens.json'):
        try:
            with open('active_trade_tokens.json') as f:
                tokens = json.load(f)
        except:
            tokens = {}
    
    tokens[token] = token_data
    
    with open('active_trade_tokens.json', 'w') as f:
        json.dump(tokens, f, indent=2)
    
    print(f"✓ Token created: {token[:20]}...")
    
    # Create message
    message = f"""🎯 TRADE SIGNAL DETECTED

Stock: <b>{stock_symbol}</b>
Current Price: ₹{entry_price:,.2f}
Entry Target: ₹{entry_price:,.2f}
Target Exit: ₹{target:,.2f}
Stop Loss: ₹{stop_loss:,.2f}
Quantity: {quantity} shares

Expected Profit: ₹{(target - entry_price) * quantity:,.2f}
Risk/Reward: 1:{(target - entry_price) / (entry_price - stop_loss):.2f}

Ready to place order?"""
    
    # Send to Telegram
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': 'HTML',
        'reply_markup': {
            'inline_keyboard': [
                [
                    {
                        'text': 'Confirm Trade',
                        'callback_data': token[:50]
                    },
                    {
                        'text': 'Cancel',
                        'callback_data': 'cancel_trade'
                    }
                ]
            ]
        }
    }
    
    print("\n📨 Sending Telegram notification...")
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print("✓ Telegram notification sent successfully!")
            print(f"\n📌 Token: {token}")
            print(f"⏰ Expires in: 10 minutes")
            return token
        else:
            print(f"✗ Failed to send: {response.status_code}")
            print(response.text)
            return None
    except Exception as e:
        print(f"✗ Error: {e}")
        return None

def place_order_directly(token, stock_symbol, entry_price, target, stop_loss, quantity):
    """Place order directly on Angel One"""
    
    print(f"\n🚀 Placing order on Angel One...")
    print(f"Stock: {stock_symbol}")
    print(f"Quantity: {quantity}")
    print(f"Price: ₹{entry_price}")
    
    url = f"{EC2_API_URL}/api/place-order"
    
    payload = {
        "token": token,
        "symbol": stock_symbol,
        "quantity": quantity,
        "entry_price": entry_price,
        "target_price": target,
        "stop_loss": stop_loss
    }
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                order_id = result.get('order_id')
                print(f"\n✅ ORDER PLACED SUCCESSFULLY!")
                print(f"Order ID: {order_id}")
                print(f"Symbol: {stock_symbol}")
                print(f"Quantity: {quantity}")
                print(f"Entry: ₹{entry_price}")
                print(f"Target: ₹{target}")
                print(f"Stop Loss: ₹{stop_loss}")
                
                # Send success notification to Telegram
                success_msg = f"""✅ ORDER PLACED

Order ID: <b>{order_id}</b>
Stock: <b>{stock_symbol}</b>
Quantity: {quantity} shares
Entry Price: ₹{entry_price:,.2f}
Target: ₹{target:,.2f}
Stop Loss: ₹{stop_loss:,.2f}

Trade is now LIVE! Monitor position in Angel One."""
                
                notify_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
                notify_payload = {
                    'chat_id': TELEGRAM_CHAT_ID,
                    'text': success_msg,
                    'parse_mode': 'HTML'
                }
                requests.post(notify_url, json=notify_payload, timeout=10)
                
                return True
            else:
                print(f"✗ Order failed: {result.get('error')}")
                return False
        else:
            print(f"✗ API error: {response.status_code}")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"✗ Connection error: {e}")
        return False

def main():
    print("=" * 60)
    print("TELEGRAM TRADE TRIGGER - MANUAL TEST")
    print("=" * 60)
    
    # Test parameters
    stock = "INFY"
    entry = 1500.00
    target = 1800.00
    stop_loss = 1380.00
    qty = 1
    
    print(f"\n📊 Trade Details:")
    print(f"   Stock: {stock}")
    print(f"   Entry: ₹{entry}")
    print(f"   Target: ₹{target}")
    print(f"   Stop Loss: ₹{stop_loss}")
    print(f"   Quantity: {qty}")
    
    # Step 1: Send Telegram notification
    token = send_telegram_notification(stock, entry, target, stop_loss, qty)
    
    if not token:
        print("✗ Failed to send Telegram notification")
        return
    
    # Step 2: Wait for user confirmation or auto-place
    print("\n" + "=" * 60)
    print("NEXT STEPS:")
    print("=" * 60)
    print(f"\n1. Check your Telegram chat for the notification")
    print(f"2. Click 'Confirm Trade' button OR run auto-place command")
    print(f"\nTo place order automatically (without waiting for Telegram):")
    print(f"python trigger_telegram_trade.py --auto-place {token}")
    print(f"\nToken expires in 10 minutes")
    
    # For testing, auto-place immediately
    auto_place = input("\n▶ Auto-place order now? (y/n): ").lower() == 'y'
    
    if auto_place:
        place_order_directly(token, stock, entry, target, stop_loss, qty)
    else:
        print("\n⏳ Waiting for Telegram confirmation...")
        print("(In production, this would wait for callback from Telegram)")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--auto-place":
        # Auto-place mode with token
        if len(sys.argv) > 2:
            token = sys.argv[2]
            print(f"Auto-placing order with token: {token[:20]}...")
            place_order_directly(token, "INFY", 1500.00, 1800.00, 1380.00, 1)
    else:
        main()
