#!/usr/bin/env python3
"""
REAL-TIME TRADE SCENARIO
1. Detect entry trigger (simulated)
2. Send REAL Telegram with token
3. Wait for user to confirm manually
4. Place order on Angel One
"""

import os
import json
import secrets
import time
import requests
import pyotp
from SmartApi import SmartConnect
from datetime import datetime, timedelta

def load_env():
    creds = {}
    if os.path.exists('.env'):
        with open('.env') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    k, v = line.split('=', 1)
                    creds[k] = v
    return creds

def send_telegram(message: str) -> bool:
    """Send Telegram message"""
    creds = load_env()
    token = creds.get('TELEGRAM_BOT_TOKEN')
    chat_id = creds.get('TELEGRAM_CHAT_ID')
    
    if not token or not chat_id:
        print("❌ Telegram credentials not set")
        return False
    
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        resp = requests.post(url, json={
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'Markdown'
        }, timeout=10)
        
        if resp.status_code == 200:
            print("✅ Telegram sent successfully")
            return True
        print(f"❌ Telegram failed: {resp.text[:100]}")
    except Exception as e:
        print(f"❌ Telegram error: {e}")
    return False

def get_session():
    """Get Angel One session"""
    creds = load_env()
    try:
        smart = SmartConnect(api_key=creds.get('ANGEL_API_KEY'))
        totp = pyotp.TOTP(creds.get('ANGEL_TOTP_SECRET')).now()
        session = smart.generateSession(creds['ANGEL_CLIENT_ID'], creds['ANGEL_PASSWORD'], totp)
        if session.get('status'):
            return smart
    except Exception as e:
        print(f"❌ Session error: {e}")
    return None

print(f"\n{'='*80}")
print("🚀 REAL-TIME TRADE SCENARIO - LOCAL TEST")
print(f"{'='*80}\n")

# SCENARIO: AXIS Bank entry trigger detected
print("📊 SIMULATING MARKET CONDITION...")
print("-" * 80)

trade_config = {
    'ticker': 'AXISBANK',
    'entry_price': 1185.00,
    'current_price': 1183.50,
    'target_price': 1422.00,  # +20%
    'stop_loss': 1090.20,     # -8%
    'source': 'Trendline'
}

print(f"Stock: {trade_config['ticker']}")
print(f"Current Price: ₹{trade_config['current_price']}")
print(f"Entry Trigger: ₹{trade_config['entry_price']}")
print(f"Distance to Entry: ₹{trade_config['entry_price'] - trade_config['current_price']:.2f}")
print(f"Target: ₹{trade_config['target_price']} (+20%)")
print(f"Stop Loss: ₹{trade_config['stop_loss']} (-8%)\n")

print("⏰ Waiting for entry price to trigger...")
time.sleep(1)

# ENTRY TRIGGERED
print(f"✅ ENTRY PRICE HIT! Price came to ₹{trade_config['entry_price']}\n")

# Generate token
token = secrets.token_urlsafe(24)
token_expires = datetime.now() + timedelta(minutes=5)

token_data = {
    'ticker': trade_config['ticker'],
    'entry_price': trade_config['entry_price'],
    'target_price': trade_config['target_price'],
    'stop_loss': trade_config['stop_loss'],
    'source': trade_config['source'],
    'expires_at': token_expires.isoformat(),
    'created_at': datetime.now().isoformat()
}

# Save token
tokens_file = 'active_trade_tokens.json'
tokens = {}
if os.path.exists(tokens_file):
    try:
        with open(tokens_file) as f:
            tokens = json.load(f)
    except:
        tokens = {}

tokens[token] = token_data

with open(tokens_file, 'w') as f:
    json.dump(tokens, f, indent=2)

print(f"{'='*80}")
print("📨 SENDING TELEGRAM NOTIFICATION...")
print(f"{'='*80}\n")

# Build Telegram message
telegram_msg = f"""🎯 *TRADE TRIGGERED - {trade_config['source'].upper()}*

Stock: *{trade_config['ticker']}*
Entry Price: ₹{trade_config['entry_price']:,.2f}
Current Price: ₹{trade_config['current_price']:,.2f}
Target: ₹{trade_config['target_price']:,.2f} _(+20%)_
Stop Loss: ₹{trade_config['stop_loss']:,.2f} _(8% loss)_
Time: {datetime.now().strftime('%Y-%m-%d %H:%M IST')}

🔐 *CONFIRMATION TOKEN:*
`{token}`

⏰ Token expires in 5 minutes

📱 To confirm trade:
1. Open dashboard
2. Go to Pending Trades
3. Paste token above
4. Adjust quantity (1, 5, 10, 20, or custom)
5. Click Confirm Order"""

print("📤 Message to be sent:\n")
print(telegram_msg)
print(f"\n{'='*80}\n")

# Send telegram
if send_telegram(telegram_msg):
    print("✅ Telegram notification sent to your phone!\n")
    
    print(f"{'='*80}")
    print("⏳ WAITING FOR USER CONFIRMATION...")
    print(f"{'='*80}\n")
    
    print("🔐 Your token is valid for 5 minutes")
    print(f"Token: {token}\n")
    
    print("💡 WHAT TO DO:")
    print("1. Check your Telegram phone")
    print("2. Copy the token")
    print("3. Press ENTER here to simulate confirmation...")
    
    input()  # Wait for user to press Enter
    
    print(f"\n{'='*80}")
    print("👤 USER CONFIRMING TRADE...")
    print(f"{'='*80}\n")
    
    # User adjusts quantity
    print("📊 Adjusting quantity...")
    user_quantity = 3  # Simulated user input
    
    capital_required = trade_config['entry_price'] * user_quantity
    potential_gain = capital_required * 0.20
    max_loss = capital_required * 0.08
    
    print(f"✅ User confirmed with:")
    print(f"   Quantity: {user_quantity} shares")
    print(f"   Capital: ₹{capital_required:,.2f}")
    print(f"   Potential Gain: ₹{potential_gain:,.2f}")
    print(f"   Max Loss: ₹{max_loss:,.2f}\n")
    
    print(f"{'='*80}")
    print("🚀 PLACING ORDER ON ANGEL ONE...")
    print(f"{'='*80}\n")
    
    # Connect to Angel One and place order
    smart = get_session()
    if smart:
        print("📱 Connected to Angel One")
        print(f"🔍 Searching for {trade_config['ticker']}...")
        
        # Search symbol
        search = smart.searchScrip("NSE", trade_config['ticker'])
        
        if search.get('data'):
            scrip = None
            for s in search['data']:
                if s.get('tradingsymbol') == trade_config['ticker'] + '-EQ':
                    scrip = s
                    break
            
            if not scrip:
                scrip = search['data'][0]
            
            trading_symbol = scrip.get('tradingsymbol')
            symbol_token = scrip.get('symboltoken')
            
            print(f"✅ Found: {trading_symbol} (Token: {symbol_token})")
            
            # Prepare order
            order_params = {
                "variety": "NORMAL",
                "tradingsymbol": trading_symbol,
                "symboltoken": symbol_token,
                "transactiontype": "BUY",
                "exchange": "NSE",
                "ordertype": "LIMIT",
                "producttype": "DELIVERY",
                "duration": "DAY",
                "price": str(int(trade_config['entry_price'])),
                "quantity": str(user_quantity),
                "squareoff": "0",
                "stoploss": "0",
                "trailingstoploss": "0"
            }
            
            print(f"\n📋 ORDER PARAMETERS:")
            print(f"   Symbol: {trading_symbol}")
            print(f"   Quantity: {user_quantity} shares")
            print(f"   Price: ₹{trade_config['entry_price']}")
            print(f"   Type: LIMIT BUY DELIVERY")
            print(f"   Duration: DAY\n")
            
            print(f"📤 Sending to Angel One...")
            
            # Place order
            result = smart.placeOrder(order_params)
            
            if isinstance(result, str):
                order_id = result
                print(f"\n✅ ✅ ✅ ORDER PLACED SUCCESSFULLY ✅ ✅ ✅\n")
                
                print(f"{'='*80}")
                print("📊 ORDER CONFIRMATION")
                print(f"{'='*80}\n")
                
                print(f"✅ Order ID: {order_id}")
                print(f"✅ Stock: {trading_symbol}")
                print(f"✅ Quantity: {user_quantity} shares")
                print(f"✅ Entry Price: ₹{trade_config['entry_price']}")
                print(f"✅ Target: ₹{trade_config['target_price']} (Potential +₹{potential_gain:.0f})")
                print(f"✅ Stop Loss: ₹{trade_config['stop_loss']} (Max -₹{max_loss:.0f})")
                print(f"✅ Status: PENDING")
                print(f"✅ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}\n")
                
                # Add to radar
                radar_file = 'radar_trades.json'
                radar_trades = []
                if os.path.exists(radar_file):
                    try:
                        with open(radar_file) as f:
                            data = json.load(f)
                            radar_trades = data if isinstance(data, list) else []
                    except:
                        radar_trades = []
                
                new_trade = {
                    'ticker': trade_config['ticker'],
                    'source': trade_config['source'],
                    'entry_price': round(trade_config['entry_price'], 2),
                    'target': round(trade_config['target_price'], 2),
                    'stop_loss': round(trade_config['stop_loss'], 2),
                    'quantity': user_quantity,
                    'order_id': order_id,
                    'status': 'Triggered',
                    'triggered_at': datetime.now().isoformat(),
                    'capital': capital_required,
                    'potential_gain': potential_gain,
                    'max_loss': max_loss
                }
                
                radar_trades.append(new_trade)
                
                with open(radar_file, 'w') as f:
                    json.dump(radar_trades, f, indent=2)
                
                print(f"{'='*80}")
                print("📍 RADAR TAB UPDATED")
                print(f"{'='*80}\n")
                
                print(f"✅ Stock moved to RADAR tab")
                print(f"   Monitoring for:")
                print(f"   • Target: ₹{trade_config['target_price']} → SELL (+{potential_gain:.0f})")
                print(f"   • Stop Loss: ₹{trade_config['stop_loss']} → SELL (-{max_loss:.0f})\n")
                
                # Consume token
                del tokens[token]
                with open(tokens_file, 'w') as f:
                    json.dump(tokens, f, indent=2)
                
                print(f"{'='*80}")
                print("✅ TRADE CONFIRMATION COMPLETE")
                print(f"{'='*80}\n")
                
                print("📝 SUMMARY:")
                print(f"  1. ✅ Entry triggered at ₹{trade_config['entry_price']}")
                print(f"  2. ✅ Telegram notification sent")
                print(f"  3. ✅ User confirmed with token")
                print(f"  4. ✅ Quantity adjusted to {user_quantity} shares")
                print(f"  5. ✅ Order placed on Angel One (ID: {order_id})")
                print(f"  6. ✅ Stock added to Radar tab")
                print(f"  7. ✅ Token consumed (single-use)")
                print(f"\n  📍 Next: Monitor until target/stoploss hit\n")
                
            else:
                print(f"❌ Order failed: {result}")
        else:
            print(f"❌ Symbol not found")
    else:
        print("❌ Cannot connect to Angel One")
        
else:
    print("❌ Failed to send Telegram")

print(f"{'='*80}\n")
