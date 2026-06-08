#!/usr/bin/env python3
"""
Angel One Trade Execution - REAL API Integration
Places actual orders at Angel One using SmartConnect - DELIVERY product type
"""

import os
import sys
import json
import requests
from datetime import datetime
from typing import Optional, Dict

try:
    from SmartApi import SmartConnect
    import pyotp
except ImportError as e:
    print(f"ERROR: Missing dependency: {e}")
    print("Install with: pip install smartapi-python pyotp")
    sys.exit(1)


class AngelOneTraderReal:
    """Execute trades directly on Angel One via SmartConnect"""
    
    def __init__(self):
        self.api_key = os.environ.get('ANGEL_API_KEY', '').strip()
        self.client_id = os.environ.get('ANGEL_CLIENT_ID', '').strip()
        self.password = os.environ.get('ANGEL_PASSWORD', '').strip()
        self.totp_secret = os.environ.get('ANGEL_TOTP_SECRET', '').strip()
        self.telegram_token = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()
        self.telegram_chat = os.environ.get('TELEGRAM_CHAT_ID', '').strip()
        self.trade_limit = 50000
        self.obj = None
        
        if not all([self.api_key, self.client_id, self.password, self.totp_secret]):
            print("WARNING: Missing credentials")
    
    def authenticate(self) -> bool:
        """Authenticate with Angel One"""
        try:
            print("[AUTH] Authenticating with Angel One...")
            self.obj = SmartConnect(api_key=self.api_key)
            totp = pyotp.TOTP(self.totp_secret)
            otp = totp.now()
            
            data = self.obj.generateSession(
                self.client_id,
                self.password,
                otp
            )
            
            if data['status']:
                print("[AUTH] SUCCESS: Authenticated")
                return True
            else:
                print(f"[AUTH] FAILED: {data.get('message')}")
                return False
                
        except Exception as e:
            print(f"[AUTH] ERROR: {str(e)}")
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
        """Place real BUY order at Angel One"""
        
        trade_value = price * quantity
        if trade_value > self.trade_limit:
            msg = f"REJECTED: Trade value Rs{trade_value:,.0f} > Rs{self.trade_limit:,.0f}\nStock: {ticker}\nDashboard: https://anuragsin17-sketch.github.io/Stock-Yard-Public/"
            print(msg)
            self.send_telegram(msg)
            return None
        
        if not self.obj:
            print("[ORDER] ERROR: Not authenticated")
            return None
        
        try:
            print(f"\n[ORDER] Placing REAL order at Angel One...")
            print(f"[ORDER] Ticker: {ticker} | Qty: {quantity} | Price: Rs{price}")
            
            # Search for symbol (IMPORTANT!)
            print(f"[ORDER] Searching for {ticker}...")
            search_result = self.obj.searchScrip("NSE", ticker)
            print(f"[ORDER] Search result data: {search_result.get('data', [])[:2] if search_result else 'None'}")
            
            symbol_data = None
            trading_symbol = None
            symbol_token = None
            
            if search_result and search_result.get('data'):
                # Try to find -EQ variant first
                for item in search_result['data']:
                    if item.get('tradingsymbol') == f"{ticker}-EQ":
                        symbol_data = item
                        break
                
                # Fallback to first result if -EQ not found
                if not symbol_data:
                    symbol_data = search_result['data'][0]
                
                trading_symbol = symbol_data.get('tradingsymbol')
                symbol_token = symbol_data.get('symboltoken')
                
                print(f"[ORDER] Found: {trading_symbol} (Token: {symbol_token})")
            else:
                print(f"[ORDER] Search failed, using mapped token")
                trading_symbol = f"{ticker}-EQ"
                symbol_token = self._get_symbol_token(ticker)
            
            if not symbol_token:
                print(f"[ORDER] ERROR: No symbol token for {ticker}")
                return None
            
            # Prepare order with DELIVERY product type (NOT MIS)
            orderparams = {
                "variety": "NORMAL",
                "tradingsymbol": trading_symbol,
                "symboltoken": symbol_token,
                "transactiontype": "BUY",
                "exchange": "NSE",
                "ordertype": "LIMIT",
                "producttype": "DELIVERY",  # CRITICAL: DELIVERY not MIS
                "duration": "DAY",
                "price": str(int(price)),
                "quantity": str(quantity),
                "squareoff": "0",
                "stoploss": "0",
                "trailingstoploss": "0"
            }
            
            print(f"[ORDER] Order params: {json.dumps(orderparams, indent=2)}")
            order_response = self.obj.placeOrder(orderparams)
            
            print(f"[ORDER] Response: {order_response}")
            print(f"[ORDER] Response type: {type(order_response)}")
            
            # Handle response (can be string or dict)
            order_id = None
            if isinstance(order_response, str):
                order_id = order_response
            elif isinstance(order_response, dict):
                if order_response.get('status'):
                    order_id = order_response.get('data', {}).get('orderid')
            
            if order_id:
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
                    'execution_platform': 'Angel One (Real - DELIVERY)'
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
                error_msg = order_response if isinstance(order_response, str) else str(order_response)
                print(f"[ORDER] FAILED: {error_msg}")
                msg = f"ORDER FAILED\nStock: {ticker}\nError: {error_msg}\nDashboard: https://anuragsin17-sketch.github.io/Stock-Yard-Public/"
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
        """Get symbol token - use EQ variants for equity trading"""
        tokens = {
            'BALKRISIND': '335',      # BALKRISIND-EQ
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
        print("Usage: python angel_trade_full.py <ticker> <price> <target> <stoploss> [quantity] [source]")
        sys.exit(1)
    
    ticker = sys.argv[1].upper()
    price = float(sys.argv[2])
    target = float(sys.argv[3])
    stoploss = float(sys.argv[4])
    quantity = int(sys.argv[5]) if len(sys.argv) > 5 else 10
    source = sys.argv[6] if len(sys.argv) > 6 else 'Manual'
    
    print(f"\n{'='*60}")
    print(f"ANGEL ONE REAL TRADE EXECUTOR")
    print(f"{'='*60}")
    print(f"Stock: {ticker} | Price: Rs{price} | Qty: {quantity}")
    print(f"Target: Rs{target} | SL: Rs{stoploss} | Source: {source}")
    
    trader = AngelOneTraderReal()
    
    if not trader.authenticate():
        print("[MAIN] Auth failed - exiting")
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
