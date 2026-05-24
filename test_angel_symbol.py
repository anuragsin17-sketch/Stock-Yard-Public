#!/usr/bin/env python3
"""
Test Angel One symbol token lookup locally
Run: python test_angel_symbol.py
"""

import os
import pyotp
from SmartApi import SmartConnect

# Load from environment or prompt
API_KEY      = os.environ.get('ANGEL_API_KEY') or input("Enter ANGEL_API_KEY: ")
CLIENT_ID    = os.environ.get('ANGEL_CLIENT_ID') or input("Enter CLIENT_ID: ")
PASSWORD     = os.environ.get('ANGEL_PASSWORD') or input("Enter PASSWORD: ")
TOTP_SECRET  = os.environ.get('ANGEL_TOTP_SECRET') or input("Enter TOTP_SECRET: ")

print("\nLogging in to Angel One...")
smart = SmartConnect(api_key=API_KEY)
totp = pyotp.TOTP(TOTP_SECRET).now()
session = smart.generateSession(CLIENT_ID, PASSWORD, totp)

if not session or session.get('status') == False:
    print(f"Login failed: {session}")
    exit(1)

print(f"Logged in successfully!\n")

# Test symbols
test_symbols = ['CENTRALBK', 'CENTRALBNK', 'CENTRAL BANK', 'CENTRALBANKOF']

for sym in test_symbols:
    print(f"\nSearching for: {sym}")
    try:
        data = smart.searchScrip("NSE", sym)
        if data and data.get('data'):
            print(f"  Results ({len(data['data'])}):")
            for item in data['data'][:5]:
                print(f"    tradingsymbol: {item.get('tradingsymbol'):20} | token: {item.get('symboltoken'):8} | exch: {item.get('exch_seg')}")
        else:
            print(f"  No results found")
    except Exception as e:
        print(f"  Error: {e}")
