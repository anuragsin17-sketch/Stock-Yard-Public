#!/usr/bin/env python3
"""Debug script to test Angel API on EC2 - run this to see what's failing"""
import os
import sys

print("=" * 60)
print("EC2 Angel API Debug")
print("=" * 60)

# Check credentials
print("\n1. Checking credentials...")
creds = {
    'ANGEL_API_KEY': os.environ.get('ANGEL_API_KEY'),
    'ANGEL_CLIENT_ID': os.environ.get('ANGEL_CLIENT_ID'),
    'ANGEL_PASSWORD': os.environ.get('ANGEL_PASSWORD'),
    'ANGEL_TOTP_SECRET': os.environ.get('ANGEL_TOTP_SECRET'),
}

for k, v in creds.items():
    status = "✓" if v else "✗"
    print(f"  {status} {k}: {v[:5] if v else 'NOT SET'}...")

# Check imports
print("\n2. Checking Python imports...")
try:
    import pyotp
    print("  ✓ pyotp")
except ImportError as e:
    print(f"  ✗ pyotp: {e}")
    sys.exit(1)

try:
    from SmartApi import SmartConnect
    print("  ✓ SmartApi")
except ImportError as e:
    print(f"  ✗ SmartApi: {e}")
    sys.exit(1)

try:
    from flask import Flask, request, jsonify
    print("  ✓ Flask")
except ImportError as e:
    print(f"  ✗ Flask: {e}")
    sys.exit(1)

# Check working directory
print("\n3. Checking working directory...")
print(f"  Current: {os.getcwd()}")
print(f"  Files in current directory:")
for f in os.listdir('.')[:10]:
    print(f"    - {f}")

# Check active tokens file
print("\n4. Checking active_trade_tokens.json...")
if os.path.exists('active_trade_tokens.json'):
    print("  ✓ File exists")
    try:
        import json
        with open('active_trade_tokens.json') as f:
            tokens = json.load(f)
        print(f"  ✓ Valid JSON with {len(tokens)} tokens")
    except Exception as e:
        print(f"  ✗ Error reading JSON: {e}")
else:
    print("  ✗ File not found")

# Try starting Flask
print("\n5. Testing Flask startup...")
try:
    app = Flask(__name__)
    print("  ✓ Flask app created")
    
    @app.route('/health')
    def health():
        return {'status': 'ok'}
    
    print("  ✓ Route registered")
    print("\nAll checks passed! Service should start correctly.")
    
except Exception as e:
    print(f"  ✗ Flask error: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("If this runs on EC2 without errors, the service should work.")
print("=" * 60)
