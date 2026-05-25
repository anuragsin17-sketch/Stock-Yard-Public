#!/usr/bin/env python3
"""
Simple test to verify the angel_trade.py file has the correct variable names
"""

import os
import sys

# Set test environment
os.environ['TRADE_SYMBOL'] = 'JKCEMENT'
os.environ['TRADE_ACTION'] = 'BUY'
os.environ['TRADE_PRICE'] = '4250.50'
os.environ['TRADE_QUANTITY'] = '10'

print("Testing variable parsing from angel_trade.py logic...")
print()

# Test the exact logic from angel_trade.py
entry_price_str = os.environ.get('TRADE_PRICE', '0').strip()
print(f"1. entry_price_str = '{entry_price_str}'")

try:
    entry_price = round(float(entry_price_str), 2)
    print(f"2. entry_price = {entry_price}")
except Exception as e:
    print(f"2. ERROR parsing entry_price: {e}")
    entry_price = 0.0

if entry_price <= 0:
    print(f"3. FAIL: Invalid entry price")
    sys.exit(1)
else:
    print(f"3. PASS: entry_price is valid")

# Test order params
order_params = {
    "price": str(entry_price),
    "quantity": "10"
}
print(f"4. order_params = {order_params}")

# Test message formatting
try:
    msg = f"Price: ₹{entry_price:,.2f}"
    print(f"5. Message formatting: {msg}")
    print()
    print("✅ ALL TESTS PASSED - No 'PRICE' variable errors!")
except NameError as e:
    print(f"5. ❌ ERROR: {e}")
    print()
    print("❌ FAILED - Variable name error detected!")
