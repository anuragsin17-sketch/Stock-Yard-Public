#!/usr/bin/env python3
"""
Angel One Direct Trade Execution
Places actual orders at Angel One via SmartConnect API
Enforces strict ₹50,000 trade value limit
"""

import os
import sys
import json
import requests
from datetime import datetime
from typing import Optional, Dict

# Try importing Angel One SmartConnect
try:
    from smartapi import SmartConnect
    import pyotp
except ImportError:
    print("❌ SmartConnect not installed. Run: pip install smartapi-python pyotp")
    sys.exit(1)


class AngelOneTrader:
    """Execute trades directly on Angel One"""
    
    def __init__(self):
        self.api_key = os.environ.get('ANGEL_API_KEY', '').strip()
        self.client_id = os.environ.get('ANGEL_CLIENT_ID', '').strip()
        self.password = os.environ.get('ANGEL_PASSWORD', '').strip()
        self.totp_secret = os.environ.get('ANGEL_TOTP_SECRET', '').strip()
        self.telegram_token = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()
        self.telegram_chat = os.environ.get('TELEGRAM_CHAT_ID', '').strip()
        self.trade_limit = 50000  # ₹50,000 strict limit
        self.obj = None
        self.auth_token = None
        self.feed_token = None
        
        if not all([self.api_key, self.client_id, self.password, self.totp_secret]):
            print("⚠️ Missing Angel One credentials")
    
    def authenticate(self) -> bool:
        """Authenticate with Angel One"""
        try:
            print("🔐 Authenticating with Angel One...")
            self.obj = SmartConnect(api_key=self.api_key)
            
            # Generate TOTP
            totp = pyotp.TOTP(self.totp_secret)
            otp = totp.now()
            
            # Login
            data = self.obj.generateSession(
                self.client_id,
                self.password,
                otp
            )
            
            if data['status']:
                self.auth_token = data['data']['authToken']
                self.feed_token = data['data']['feedToken']
                print(f"✅ Authenticated successfully")
                return True
            else:
                print(f"❌ Authentication failed: {data.get('message', 'Unknown error')}")
                return False
                
        except Exception as e:
            print(f"❌ Authentication error: {str(e)}")
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
            print(f"⚠️ Telegram error: {e}")
            return False
    
    def place_order(self, ticker: str, price: float, quantity: int, 
                   target: float, stoploss: float, source: str = 'GitHub') -> Optional[Dict]:
        """
        Place a BUY order with Angel One
        
        Args:
            ticker: Stock symbol (without .NS)
            price: Entry price
            quantity: Number of shares
            target: Target exit price
            stoploss: Stop loss price
            source: Order source
            
        Returns:
            Order result dict or None if failed
        """
        
        # Validate trade value
        trade_value = price * quantity
        if trade_value > self.trade_limit:
            msg = (
                f"❌ *TRADE REJECTED*\n"
                f"Stock: {ticker}\n"
                f"Qty: {quantity} @ ₹{price}\n"
                f"Value: ₹{trade_value:,.0f} > ₹{self.trade_limit:,.0f}\n"
                f"*Reason: Exceeds ₹50,000 limit*\n\n"
                f"📊 [View Dashboard](https://anuragsin17-sketch.github.io/Stock-Yard-Public/)"
            )
            print(msg)
            self.send_telegram(msg)
            return None
        
        if not self.obj:
            print("❌ Not authenticated")
            return None
        
        try:
            print(f"\n📊 Placing order...")
            print(f"Ticker: {ticker} | Qty: {quantity} | Price: ₹{price}")
            print(f"Trade Value: ₹{trade_value:,.0f}")
            
            # Prepare order
            orderparams = {
                "variety": "NORMAL",
                "tradingsymbol": f"{ticker}.NS",
                "symboltoken": self._get_symbol_token(ticker),
                "transactiontype": "BUY",
                "exchange": "NSE",
                "ordertype": "LIMIT",
                "producttype": "MIS",  # Intraday
                "price": str(price),
                "quantity": str(quantity),
                "timeframe": "1"
            }
            
            # Place order
            order_response = self.obj.placeOrder(orderparams)
            
            if order_response['status']:
                order_id = order_response['data']['orderid']
                print(f"✅ Order placed successfully!")
                print(f"Order ID: {order_id}")
                
                # Save to radar
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
                    'execution_platform': 'Angel One'
                })
                
                # Send Telegram notification
                msg = (
                    f"✅ *ORDER PLACED*\n"
                    f"Stock: *{ticker}*\n"
                    f"Qty: {quantity} @ ₹{price}\n"
                    f"Value: ₹{trade_value:,.0f}\n"
                    f"Target: ₹{target}\n"
                    f"SL: ₹{stoploss}\n"
                    f"Order ID: `{order_id}`\n"
                    f"Time: {datetime.now().strftime('%H:%M IST')}\n\n"
                    f"📊 [View Dashboard](https://anuragsin17-sketch.github.io/Stock-Yard-Public/)"
                )
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
                error_msg = order_response.get('message', 'Unknown error')
                print(f"❌ Order failed: {error_msg}")
                
                msg = (
                    f"❌ *ORDER FAILED*\n"
                    f"Stock: {ticker}\n"
                    f"Error: {error_msg}\n\n"
                    f"📊 [View Dashboard](https://anuragsin17-sketch.github.io/Stock-Yard-Public/)"
                )
                self.send_telegram(msg)
                return None
                
        except Exception as e:
            print(f"❌ Order placement error: {str(e)}")
            msg = (
                f"❌ *ERROR*: {str(e)}\n\n"
                f"📊 [View Dashboard](https://anuragsin17-sketch.github.io/Stock-Yard-Public/)"
            )
            self.send_telegram(msg)
            return None
    
    def _get_symbol_token(self, ticker: str) -> str:
        """Get symbol token from ticker (simplified)"""
        # This is a simplified version - in production you'd fetch this from Angel's data
        # For now returning a placeholder that would need to be looked up
        symbol_tokens = {
            'RELIANCE': '2885',
            'INFY': '1594',
            'TCS': '3429',
            'WIPRO': '6051',
            'HCLTECH': '2055',
            'TECHM': '3420'
        }
        return symbol_tokens.get(ticker.upper(), '')
    
    def _save_to_radar(self, order_data: Dict):
        """Save order to radar_trades.json"""
        try:
            radar_file = 'radar_trades.json'
            trades = []
            
            if os.path.exists(radar_file):
                with open(radar_file, 'r') as f:
                    trades = json.load(f)
            
            trades.append(order_data)
            
            with open(radar_file, 'w') as f:
                json.dump(trades, f, indent=2)
                
            print(f"💾 Trade saved to radar_trades.json")
        except Exception as e:
            print(f"⚠️ Error saving to radar: {e}")


def main():
    """Main entry point"""
    if len(sys.argv) < 5:
        print("Usage: python angel_trade_full.py <ticker> <price> <target> <stoploss> [quantity] [source]")
        print("Example: python angel_trade_full.py INFY 2150 2580 1978 10 GitHub")
        sys.exit(1)
    
    ticker = sys.argv[1].upper()
    price = float(sys.argv[2])
    target = float(sys.argv[3])
    stoploss = float(sys.argv[4])
    quantity = int(sys.argv[5]) if len(sys.argv) > 5 else 10
    source = sys.argv[6] if len(sys.argv) > 6 else 'Manual'
    
    print(f"\n{'='*60}")
    print(f"ANGEL ONE TRADE EXECUTOR")
    print(f"{'='*60}")
    print(f"Stock: {ticker}")
    print(f"Price: ₹{price}")
    print(f"Qty: {quantity}")
    print(f"Target: ₹{target}")
    print(f"Stop Loss: ₹{stoploss}")
    print(f"Source: {source}")
    
    # Create trader instance
    trader = AngelOneTrader()
    
    # Authenticate
    if not trader.authenticate():
        print("❌ Failed to authenticate")
        sys.exit(1)
    
    # Place order
    result = trader.place_order(ticker, price, quantity, target, stoploss, source)
    
    if result:
        print(f"\n✅ Trade execution completed successfully")
        print(f"{'='*60}\n")
        sys.exit(0)
    else:
        print(f"\n❌ Trade execution failed")
        print(f"{'='*60}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
