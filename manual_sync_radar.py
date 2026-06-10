#!/usr/bin/env python3
"""
Manually sync your Angel One trades to Radar tab
This creates radar_trades.json with your open positions
"""

import os
import json
from datetime import datetime
from SmartApi import SmartConnect
import pyotp

def sync_trades_to_radar():
    """Fetch Angel One holdings and create radar_trades.json"""
    
    print("\n" + "="*70)
    print("🔄 MANUAL SYNC: Angel One Holdings → Radar Tab")
    print("="*70)
    
    # Get credentials from environment
    api_key = os.environ.get('ANGEL_API_KEY')
    client_id = os.environ.get('ANGEL_CLIENT_ID')
    password = os.environ.get('ANGEL_PASSWORD')
    totp_secret = os.environ.get('ANGEL_TOTP_SECRET')
    
    if not all([api_key, client_id, password, totp_secret]):
        print("\n❌ Error: Angel One credentials not set in environment variables")
        print("\nSet these environment variables:")
        print("  ANGEL_API_KEY")
        print("  ANGEL_CLIENT_ID")
        print("  ANGEL_PASSWORD")
        print("  ANGEL_TOTP_SECRET")
        return False
    
    try:
        print("\n1️⃣  Connecting to Angel One...")
        smart = SmartConnect(api_key=api_key)
        
        print("2️⃣  Generating TOTP...")
        totp = pyotp.TOTP(totp_secret).now()
        
        print("3️⃣  Authenticating...")
        session = smart.generateSession(client_id, password, totp)
        
        if not session or not session.get('status'):
            print(f"❌ Authentication failed: {session}")
            return False
        
        print("✅ Authenticated!")
        
        print("\n4️⃣  Fetching holdings (open positions)...")
        holdings_response = smart.getHoldings()
        
        if not holdings_response.get('status'):
            print(f"❌ Error fetching holdings: {holdings_response}")
            return False
        
        holdings = holdings_response.get('data', [])
        print(f"✅ Found {len(holdings)} holdings")
        
        if len(holdings) == 0:
            print("⚠️  No open positions found in Angel One")
            return False
        
        # Convert holdings to radar trades format
        radar_trades = []
        
        for holding in holdings:
            symbol = holding.get('symbol', '').replace('-EQ', '')
            quantity = int(holding.get('quantity', 0))
            avg_price = float(holding.get('avgprice', 0))
            
            if quantity > 0 and avg_price > 0:
                trade = {
                    'ticker': symbol,
                    'symbol': symbol,
                    'entry_price': avg_price,
                    'current_price': avg_price,  # Will update via API
                    'quantity': quantity,
                    'status': 'Open',
                    'source': 'Angel One (Manual Sync)',
                    'triggered_at': datetime.now().isoformat(),
                    'is_synced': True
                }
                radar_trades.append(trade)
                print(f"  • {symbol}: {quantity} shares @ ₹{avg_price:,.2f}")
        
        # Save to radar_trades.json
        print(f"\n5️⃣  Saving {len(radar_trades)} trades to radar_trades.json...")
        
        with open('radar_trades.json', 'w') as f:
            json.dump(radar_trades, f, indent=2)
        
        print("✅ Saved!")
        
        print("\n" + "="*70)
        print("✅ SUCCESS!")
        print("="*70)
        print(f"\n✓ Synced {len(radar_trades)} open trades to Radar tab")
        print("✓ Open your dashboard and click Radar tab to see them")
        print("✓ LTP will update automatically every 10 seconds")
        print()
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    sync_trades_to_radar()
