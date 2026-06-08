#!/usr/bin/env python3
"""
Angel One Trade Execution - REST API (No SmartConnect dependency)
Places orders at Angel One using direct REST calls
"""

import os
import sys
import json
import requests
import hashlib
import hmac
from datetime import datetime
from typing import Optional, Dict

try:
    import pyotp
except ImportError:
    print("ERROR: Missing pyotp. Install with: pip install pyotp")
    sys.exit(1)


class AngelOneTraderREST:
    """Execute trades using Angel One REST API"""
    
    def __init__(self):
        self.api_key = os.environ.get('ANGEL_API_KEY', '').strip()
        self.client_id = os.environ.get('ANGEL_CLIENT_ID', '').strip()
        self.password = os.environ.get('ANGEL_PASSWORD', '').strip()
        self.totp_secret = os.environ.get('ANGEL_TOTP_SECRET', '').strip()
        self.telegram_token = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()
        self.telegram_chat = os.environ.get('TELEGRAM_CHAT_ID', '').strip()
        self.trade_limit = 50000
        
        self.base_url = "https://api.angelbroking.com"
        self.auth_token = None
        self.feed_token = None
        self.client_code = None
        
        if not all([self.api_key, self.client_id, self.password, self.totp_secret]):
            print("WARNING: Missing credentials")
    
    def authenticate(self) -> bool:
        """Authenticate with Angel One REST API"""
        try:
            print("[AUTH] Authenticating with Angel One REST API...")
            
            # Generate TOTP
            totp = pyotp.TOTP(self.totp_secret)
            otp = totp.now()
            
            # Login endpoint
            login_url = f"{self.base_url}/rest/secure/angelbroking/user/v1/loginbyotp"
            
            login_data = {
                "apikey": self.api_key,
                "clientcode": self.client_id,
                "password": self.password,
                "totp": otp
            }
            
            print(f"[AUTH] Login URL: {login_url}")
            print(f"[AUTH] Client ID: {self.client_id}")
            
            response = requests.post(login_url, json=login_data, timeout=30)
            print(f"[AUTH] Response status: {response.status_code}")
            print(f"[AUTH] Response: {response.text[:500]}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status'):
                    self.auth_token = data['data'].get('authToken')
                    self.feed_token = data['data'].get('feedToken')
                    self.client_code = data['data'].get('clientcode')
                    print(f"[AUTH] SUCCESS: Token: {self.auth_token[:20]}...")
                    return True
                else:
                    print(f"[AUTH] FAILED: {data.get('message')}")
                    return False
            else:
                print(f"[AUTH] HTTP ERROR: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"[AUTH] ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def send_telegram(self, message: str) -> bool:
        """Send Telegram notification"""
        if not self.telegram_token or not self.telegram_chat:
            return False
        try:
            resp = requests.post(
                f"https://api.telegram.org/bot{self.telegram_token}/sendMessage",
                json={'chat_id': self.telegram_chat, 'text': message, 'parse_mode': 'Markdown'},
                timeout=10
            )
            return resp.status_code == 200
        except Exception as e:
            print(f"[TELEGRAM] ERROR: {e}")
            return False
    
    def place_order(self, ticker: str, price: float, quantity: int, 
                   target: float, stoploss: float, source: str = 'GitHub') -> Optional[Dict]:
        """Place real BUY order at Angel One via REST"""
        
        trade_value = price * quantity
        if trade_value > self.trade_limit:
            msg = f"REJECTED: Trade value Rs{trade_value:,.0f} > Rs{self.trade_limit:,.0f}\nStock: {ticker}\nDashboard: https://anuragsin17-sketch.github.io/Stock-Yard-Public/"
            print(msg)
            self.send_telegram(msg)
            return None
        
        if not self.auth_token:
            print("[ORDER] ERROR: Not authenticated")
            return None
        
        try:
            print(f"\n[ORDER] Placing REAL order at Angel One (REST)...")
            print(f"[ORDER] Ticker: {ticker} | Qty: {quantity} | Price: Rs{price}")
            
            symbol_token = self._get_symbol_token(ticker)
            if not symbol_token:
                print(f"[ORDER] ERROR: No symbol token for {ticker}")
                return None
            
            # Place order endpoint
            order_url = f"{self.base_url}/rest/secure/angelbroking/order/v1/placeorder"
            
            order_data = {
                "mode": "REGULAR",
                "exchangetokens": {
                    "NSE": symbol_token
                },
                "tradingsymbol": ticker,
                "symboltoken": symbol_token,
                "quantity": quantity,
                "price": price,
                "pricetype": "LIMIT",
                "transactiontype": "BUY",
                "ordertype": "REGULAR",
                "producttype": "MIS",
                "duration": "DAY",
                "clientcode": self.client_code
            }
            
            headers = {
                "Authorization": f"Bearer {self.auth_token}",
                "Content-Type": "application/json"
            }
            
            print(f"[ORDER] URL: {order_url}")
            print(f"[ORDER] Data: {order_data}")
            
            response = requests.post(order_url, json=order_data, headers=headers, timeout=30)
            
            print(f"[ORDER] Response status: {response.status_code}")
            print(f"[ORDER] Response: {response.text[:500]}")
            
            if response.status_code == 200:
                result = response.json()
                if result.get('status'):
                    order_id = result['data'].get('orderid')
                    print(f"[ORDER] SUCCESS: Order ID: {order_id}")
                    
                    self._save_to_radar({
                        'ticker': ticker,
                        'order_id': order_id,
                        'entry_price': price,
                        'quantity': quantity,
                        'target': target,
                        'stoploss': stoploss,
                        'trade_value': trade_value,
                        'status': 'Open',
                        'source': source,
                        'timestamp': datetime.now().isoformat(),
                        'execution_platform': 'Angel One (REST - Real)'
                    })
                    
                    msg = f"ORDER PLACED AT ANGEL ONE\nStock: {ticker}\nQty: {quantity} @ Rs{price}\nValue: Rs{trade_value:,.0f}\nTarget: Rs{target}\nSL: Rs{stoploss}\nOrder ID: {order_id}\nDashboard: https://anuragsin17-sketch.github.io/Stock-Yard-Public/"
                    self.send_telegram(msg)
                    
                    return {
                        'status': 'success',
                        'order_id': order_id,
                        'ticker': ticker,
                        'quantity': quantity,
                        'price': price,
                        'trade_value': trade_value
                    }
                else:
                    print(f"[ORDER] FAILED: {result.get('message')}")
                    msg = f"ORDER FAILED\nStock: {ticker}\nError: {result.get('message')}\nDashboard: https://anuragsin17-sketch.github.io/Stock-Yard-Public/"
                    self.send_telegram(msg)
                    return None
            else:
                print(f"[ORDER] HTTP ERROR: {response.status_code}")
                msg = f"ORDER ERROR\nStock: {ticker}\nHTTP: {response.status_code}\nDashboard: https://anuragsin17-sketch.github.io/Stock-Yard-Public/"
                self.send_telegram(msg)
                return None
                
        except Exception as e:
            print(f"[ORDER] ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            msg = f"ERROR: {str(e)}\nDashboard: https://anuragsin17-sketch.github.io/Stock-Yard-Public/"
            self.send_telegram(msg)
            return None
    
    def _get_symbol_token(self, ticker: str) -> str:
        """Get symbol token"""
        tokens = {
            'BALKRISIND': '335',
            'APOLLOTYRE': '3385',
            'BSOFT': '3045',
            'JKCEMENT': '1961',
            'HCLTECH': '2055',
            'SHREECEM': '3422',
            'BAYERCROP': '3408',
            'INFY': '1594',
            'SAFARI': '3097',
            'DCMSHRIRAM': '1747',
            'GSFC': '2104',
            'BRITANNIA': '500087',
            'UTIAMC': '3475',
            'ORIENTCEM': '3393'
        }
        return tokens.get(ticker.upper(), '')
    
    def _save_to_radar(self, order_data: Dict):
        """Save order to radar_trades.json"""
        try:
            radar_file = 'radar_trades.json'
            trades = []
            
            if os.path.exists(radar_file):
                try:
                    with open(radar_file, 'r') as f:
                        trades = json.load(f)
                except:
                    trades = []
            
            trades.append(order_data)
            
            with open(radar_file, 'w') as f:
                json.dump(trades, f, indent=2)
                
            print(f"[RADAR] Saved to radar_trades.json")
        except Exception as e:
            print(f"[RADAR] ERROR: {e}")


def main():
    """Main entry point"""
    if len(sys.argv) < 5:
        print("Usage: python angel_trade_rest.py <ticker> <price> <target> <stoploss> [quantity] [source]")
        sys.exit(1)
    
    ticker = sys.argv[1].upper()
    price = float(sys.argv[2])
    target = float(sys.argv[3])
    stoploss = float(sys.argv[4])
    quantity = int(sys.argv[5]) if len(sys.argv) > 5 else 10
    source = sys.argv[6] if len(sys.argv) > 6 else 'Manual'
    
    print(f"\n{'='*60}")
    print(f"ANGEL ONE REST API TRADE EXECUTOR")
    print(f"{'='*60}")
    print(f"Stock: {ticker} | Price: Rs{price} | Qty: {quantity}")
    print(f"Target: Rs{target} | SL: Rs{stoploss} | Source: {source}")
    
    trader = AngelOneTraderREST()
    
    if not trader.authenticate():
        print("[MAIN] Auth failed")
        sys.exit(1)
    
    result = trader.place_order(ticker, price, quantity, target, stoploss, source)
    
    if result:
        print(f"\n[MAIN] SUCCESS: Trade placed")
        print(f"{'='*60}\n")
        sys.exit(0)
    else:
        print(f"\n[MAIN] FAILED: Trade not placed")
        print(f"{'='*60}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
