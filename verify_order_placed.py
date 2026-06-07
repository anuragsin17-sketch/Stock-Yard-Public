#!/usr/bin/env python3
"""
Verify Order Placement
Fetch order book to confirm the order was registered
"""

import os
import json
from datetime import datetime
import pyotp
from SmartApi import SmartConnect

def load_env():
    """Load credentials from .env file"""
    credentials = {}
    if os.path.exists('.env'):
        with open('.env') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    credentials[key] = value
    return credentials

def main():
    print(f"\n{'='*70}")
    print("✅ VERIFY ORDER PLACEMENT")
    print(f"{'='*70}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}\n")
    
    # Load credentials
    credentials = load_env()
    if not all(k in credentials for k in ['ANGEL_API_KEY', 'ANGEL_CLIENT_ID', 'ANGEL_PASSWORD', 'ANGEL_TOTP_SECRET']):
        print("❌ Missing credentials in .env file")
        return False
    
    try:
        # Login
        print("🔑 Logging into Angel One...")
        smart = SmartConnect(api_key=credentials['ANGEL_API_KEY'])
        totp = pyotp.TOTP(credentials['ANGEL_TOTP_SECRET']).now()
        
        session = smart.generateSession(
            credentials['ANGEL_CLIENT_ID'],
            credentials['ANGEL_PASSWORD'],
            totp
        )
        
        if not isinstance(session, dict) or not session.get('status'):
            print(f"❌ Login failed")
            return False
        
        print(f"✅ Logged in as {session['data']['name']}\n")
        
        # Fetch order book
        print("📋 Fetching Order Book from Angel One...\n")
        orders_response = smart.orderBook()
        
        if not isinstance(orders_response, dict):
            print(f"❌ Unexpected response type: {type(orders_response)}")
            return False
        
        if not orders_response.get('status'):
            print(f"❌ Failed to fetch order book: {orders_response.get('message')}")
            return False
        
        orders = orders_response.get('data', [])
        
        if not orders:
            print("⚠️  No orders found in order book")
            return False
        
        print(f"✅ Found {len(orders)} order(s) in order book:\n")
        print(f"{'='*70}")
        
        # Look for our test order
        test_order_found = False
        
        for i, order in enumerate(orders):
            order_id = order.get('orderid', 'N/A')
            symbol = order.get('tradingsymbol', 'N/A')
            quantity = order.get('quantity', 'N/A')
            price = order.get('price', 'N/A')
            status = order.get('status', 'N/A')
            filled_qty = order.get('filledshares', 0)
            pending_qty = order.get('pendingshares', quantity)
            
            print(f"\n📍 ORDER #{i+1}")
            print(f"   Order ID: {order_id}")
            print(f"   Stock: {symbol}")
            print(f"   Quantity: {quantity}")
            print(f"   Price: ₹{price}")
            print(f"   Status: {status}")
            print(f"   Filled: {filled_qty} | Pending: {pending_qty}")
            
            # Check if this is our test order
            try:
                price_float = float(price) if isinstance(price, str) else price
                if symbol == 'INFY-EQ' and price_float == 2490.0:
                    test_order_found = True
            except:
                pass
                print(f"\n   ✅ ✅ ✅ THIS IS OUR TEST ORDER! ✅ ✅ ✅")
                print(f"   \n   What happens next:")
                print(f"   1. Order is PENDING - waiting for price to reach ₹2490")
                print(f"   2. When INFY hits ₹2490 or lower, order EXECUTES")
                print(f"   3. We'll get Telegram notification: 'INFY Entry Triggered'")
                print(f"   4. Stock moves to Radar tab automatically")
                print(f"   5. Target: ₹2988 (+20%) | Stoploss: ₹2291 (-8%)")
        
        print(f"\n{'='*70}\n")
        
        if test_order_found:
            print("✅ TEST ORDER SUCCESSFULLY PLACED IN ANGEL ONE!")
            print(f"\n   You can verify in Angel One app:")
            print(f"   1. Open Angel One mobile/web app")
            print(f"   2. Go to Orders section")
            print(f"   3. You should see: INFY-EQ BUY 1 @ ₹2490 [PENDING]")
            print(f"\n   Next step: Wait for price to hit ₹2490 or cancel the order\n")
        else:
            print("⚠️  Test order not found in order book yet")
            print("   (May take a few seconds to appear)\n")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    main()
