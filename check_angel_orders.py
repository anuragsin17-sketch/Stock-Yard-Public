#!/usr/bin/env python3
"""
Check what orders are actually in Angel One right now
"""

import os
import pyotp
from SmartApi import SmartConnect
from datetime import datetime

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

creds = load_env()
smart = SmartConnect(api_key=creds.get('ANGEL_API_KEY'))
totp = pyotp.TOTP(creds.get('ANGEL_TOTP_SECRET')).now()

session = smart.generateSession(creds['ANGEL_CLIENT_ID'], creds['ANGEL_PASSWORD'], totp)

if session.get('status'):
    print("\n" + "="*80)
    print("📊 CURRENT ORDERS IN ANGEL ONE")
    print("="*80 + "\n")
    
    orders = smart.orderBook()
    
    if orders.get('data'):
        for i, order in enumerate(orders['data'], 1):
            print(f"ORDER #{i}")
            print(f"  Order ID: {order.get('orderid')}")
            print(f"  Symbol: {order.get('tradingsymbol')}")
            print(f"  Quantity: {order.get('quantity')}")
            print(f"  Price: ₹{order.get('price')}")
            print(f"  Status: {order.get('status')}")
            print(f"  Filled: {order.get('filledshares')} | Pending: {order.get('pendingshares')}")
            print()
    else:
        print("✅ NO ORDERS IN ANGEL ONE (Order book is empty)")
    
    print("="*80 + "\n")
