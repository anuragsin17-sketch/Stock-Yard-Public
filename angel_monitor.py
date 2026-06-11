#!/usr/bin/env python3
"""
Stock Yard Trade Monitor
- Runs every 15 min during market hours
- Checks Volume & Trendline stocks for entry price hits
- Automatically moves triggered stocks to Radar tab
- Monitors Radar stocks for target/stoploss hits
- Sends Telegram notifications on all triggers
"""

import os
import json
import requests
from datetime import datetime

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT = os.environ.get('TELEGRAM_CHAT_ID')
DATA_FILE = 'data.json'
TRENDLINE_FILE = 'trendline_screen.json'
RADAR_FILE = 'radar_trades.json'


def send_telegram(message: str) -> bool:
    """Send Telegram notification"""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT:
        print("⚠️ Telegram not configured")
        return False
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        resp = requests.post(url, json={
            'chat_id': TELEGRAM_CHAT,
            'text': message,
            'parse_mode': 'Markdown'
        }, timeout=10)
        if resp.status_code == 200:
            print("✅ Telegram sent")
            return True
        print(f"❌ Telegram failed: {resp.text[:200]}")
    except Exception as e:
        print(f"❌ Telegram error: {e}")
    return False


def send_telegram_with_action(ticker: str, entry_price: float, current_price: float, 
                              target_price: float, stoploss_price: float, source: str) -> bool:
    """Send Telegram with secure token for order confirmation"""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT:
        print("⚠️ Telegram not configured")
        return False
    
    try:
        import secrets
        from datetime import datetime, timedelta
        from cryptography.fernet import Fernet
        
        # Get encryption key from env or generate
        encryption_key = os.environ.get('ENCRYPTION_KEY')
        if encryption_key:
            cipher_suite = Fernet(encryption_key.encode() if isinstance(encryption_key, str) else encryption_key)
        else:
            cipher_suite = None
        
        # Generate secure token (32 random chars)
        token = secrets.token_urlsafe(24)
        token_expires = datetime.now() + timedelta(minutes=3)  # 3 minutes
        
        # Save token for verification (encrypted)
        tokens_file = 'active_trade_tokens_encrypted.json'
        tokens = {}
        if os.path.exists(tokens_file):
            try:
                with open(tokens_file) as f:
                    tokens = json.load(f)
            except:
                tokens = {}
        
        token_data = {
            'ticker': ticker,
            'entry_price': entry_price,
            'target_price': target_price,
            'stop_loss': stoploss_price,
            'source': source,
            'expires_at': token_expires.isoformat(),
            'created_at': datetime.now().isoformat()
        }
        
        # Encrypt token data if cipher available
        if cipher_suite:
            json_data = json.dumps(token_data).encode()
            encrypted = cipher_suite.encrypt(json_data).decode()
            tokens[token] = encrypted
        else:
            tokens[token] = token_data
        
        with open(tokens_file, 'w') as f:
            json.dump(tokens, f, indent=2)
        
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        
        # Message with secure token (user must enter manually)
        message = (
            f"🎯 *TRADE TRIGGERED - {source.upper()}*\n\n"
            f"Stock: *{ticker}*\n"
            f"Entry Price: ₹{entry_price:,.2f}\n"
            f"Current Price: ₹{current_price:,.2f}\n"
            f"Target: ₹{target_price:,.2f} _(+20%)_\n"
            f"Stop Loss: ₹{stoploss_price:,.2f} _(8% loss)_\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M IST')}\n\n"
            f"🔐 *CONFIRMATION TOKEN:*\n"
            f"`{token}`\n\n"
            f"⏰ Token expires in 3 minutes\n\n"
            f"📱 To confirm trade:\n"
            f"1. Open dashboard\n"
            f"2. Go to Pending Trades\n"
            f"3. Paste token to verify\n"
            f"4. Adjust quantity\n"
            f"5. Click Confirm"
        )
        
        resp = requests.post(url, json={
            'chat_id': TELEGRAM_CHAT,
            'text': message,
            'parse_mode': 'Markdown'
        }, timeout=10)
        
        if resp.status_code == 200:
            print("✅ Telegram with secure token sent")
            return True
        print(f"❌ Telegram failed: {resp.text[:200]}")
    except Exception as e:
        print(f"❌ Telegram error: {e}")
    return False


def get_live_price(ticker: str) -> float:
    """Get current price from Angel One API"""
    try:
        # Call the backend endpoint to get live quote
        symbol = ticker.replace('.NS', '')  # Remove .NS suffix for API call
        
        api_url = f"http://32.194.58.75:5000/api/get-quote?symbol={symbol}"
        
        response = requests.get(api_url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                ltp = float(data.get('ltp', 0))
                if ltp > 0:
                    return ltp
        
        print(f"Price fetch error for {ticker}: API returned {response.status_code}")
        
    except Exception as e:
        print(f"Price fetch error for {ticker}: {e}")
    
    return None


def load_json(filepath: str) -> dict:
    """Load JSON file"""
    if not os.path.exists(filepath):
        return {}
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
        return {}


def save_json(filepath: str, data):
    """Save JSON file"""
    try:
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving {filepath}: {e}")


def load_radar() -> list:
    """Load radar trades"""
    data = load_json(RADAR_FILE)
    return data if isinstance(data, list) else []


def save_radar(trades: list):
    """Save radar trades"""
    save_json(RADAR_FILE, trades)


def check_volume_stocks_for_entry():
    """Volume stocks are NOT monitored - only for reference"""
    print("\n📊 Skipping Volume Breakout stocks (monitoring Trendline only)")
    return False


def check_trendline_stocks_for_entry():
    """Check Trendline stocks for entry price hits"""
    print("\n📈 Checking Trendline stocks...")
    trendline_data = load_json(TRENDLINE_FILE)
    if not isinstance(trendline_data, list):
        trendline_data = []
    
    radar_trades = load_radar()
    changed = False
    
    # Load stocks already in dashboard tabs
    main_data = load_json(DATA_FILE)
    volume_stocks = main_data.get('volume_breakout_stocks', []) if isinstance(main_data, dict) else []
    golden_stocks = main_data.get('golden_stocks', []) if isinstance(main_data, dict) else []
    
    # Load orders already placed (prevent duplicate orders)
    orders_data = load_json('angel_orders.json')
    ordered_stocks = set()
    if isinstance(orders_data, list):
        ordered_stocks = {o.get('symbol', '') for o in orders_data if o.get('symbol')}
    print(f"  Already ordered: {len(ordered_stocks)} stocks - {', '.join(sorted(ordered_stocks)[:5])}")

    for stock in trendline_data:
        ticker = stock.get('ticker', '')
        entry_price = float(stock.get('triggerPrice', 0))
        pos_sizing = stock.get('positionSizing', {})
        target_price = float(pos_sizing.get('pivotTargetExit', entry_price * 1.20))
        stoploss_price = float(pos_sizing.get('strictStopLoss', entry_price * 0.92))

        if not ticker or entry_price <= 0:
            continue

        # CRITICAL: Skip if already ordered in angel_orders.json
        if ticker in ordered_stocks:
            print(f"  ⊘ {ticker}: Already has order in Angel One (skip)")
            continue

        # Skip if already in radar
        if any(t.get('ticker') == ticker and t.get('source') == 'Trendline' for t in radar_trades):
            print(f"  ⊘ {ticker}: Already in Radar (skip)")
            continue
        
        # Skip if already in Volume tab
        if any(v.get('symbol') == ticker for v in volume_stocks):
            print(f"  ⊘ {ticker}: Already in Volume tab (skip)")
            continue
        
        # Skip if already in Trendline tab
        if any(g.get('symbol') == ticker for g in golden_stocks):
            print(f"  ⊘ {ticker}: Already in Trendline tab (skip)")
            continue

        # Get live price
        current_price = get_live_price(ticker)
        if not current_price:
            continue

        print(f"  {ticker}: Entry ₹{entry_price:.2f} | Current ₹{current_price:.2f}")

        # Check if price hit entry (within 1%)
        if current_price >= entry_price * 0.99:
            print(f"  ✅ Entry hit! Moving to Radar...")

            # Add to radar
            radar_trades.append({
                'ticker': ticker,
                'source': 'Trendline',
                'entry_price': round(entry_price, 2),
                'target': round(target_price, 2),
                'stop_loss': round(stoploss_price, 2),
                'current_price': round(current_price, 2),
                'status': 'Triggered',
                'triggered_at': datetime.now().isoformat()
            })
            changed = True

            # Send Telegram with Confirm Trade button
            send_telegram_with_action(
                ticker=ticker,
                entry_price=entry_price,
                current_price=current_price,
                target_price=target_price,
                stoploss_price=stoploss_price,
                source='Trendline'
            )

    if changed:
        save_radar(radar_trades)
    
    return changed


def monitor_radar_positions():
    """Monitor Radar stocks for target/stoploss hits"""
    print("\n🎯 Monitoring Radar positions...")
    radar_trades = load_radar()
    if not radar_trades:
        print("  No trades in Radar")
        return False

    triggered_trades = [t for t in radar_trades if t.get('status') == 'Triggered']
    if not triggered_trades:
        print("  No triggered trades to monitor")
        return False

    print(f"  Monitoring {len(triggered_trades)} triggered trades...")
    changed = False

    for trade in radar_trades:
        if trade.get('status') != 'Triggered':
            continue

        ticker = trade.get('ticker', '')
        entry_price = float(trade.get('entry_price', 0))
        target_price = float(trade.get('target', entry_price * 1.20))
        stoploss_price = float(trade.get('stop_loss', entry_price * 0.92))
        source = trade.get('source', 'Unknown')

        # Get live price
        current_price = get_live_price(ticker)
        if not current_price:
            continue

        pnl_pct = ((current_price - entry_price) / entry_price) * 100
        print(f"  {ticker}: Entry ₹{entry_price:.2f} | Current ₹{current_price:.2f} | P&L {pnl_pct:+.2f}%")

        # Check if position should be closed (target or stoploss hit)
        if current_price >= target_price or current_price <= stoploss_price:
            exit_reason = "Target Hit" if current_price >= target_price else "Stop Loss Hit"
            trade['status'] = 'Closed'
            trade['exit_price'] = round(current_price, 2)
            trade['closed_at'] = datetime.now().isoformat()
            trade['pnl_pct'] = round(pnl_pct, 2)
            trade['exit_reason'] = exit_reason
            changed = True

            icon = "🎯" if current_price >= target_price else "🛑"
            msg = (
                f"{icon} *POSITION CLOSED - {exit_reason}*\n\n"
                f"Stock: *{ticker}*\n"
                f"Entry: ₹{entry_price:,.2f}\n"
                f"Exit: ₹{current_price:,.2f}\n"
                f"P&L: *{pnl_pct:+.2f}%*\n"
                f"Source: {source}\n"
                f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M IST')}"
            )
            send_telegram(msg)
            print(f"  ✅ {exit_reason} - Telegram sent!")

        else:
            # Still open - update current price
            trade['current_price'] = round(current_price, 2)
            trade['current_pnl_pct'] = round(pnl_pct, 2)
            changed = True

    if changed:
        save_radar(radar_trades)
    return changed


def main():
    print(f"\n{'='*60}")
    print(f"TRADE MONITOR - {datetime.now().strftime('%Y-%m-%d %H:%M IST')}")
    print(f"{'='*60}")

    # Check Trendline stocks for entry hits ONLY
    tl_changed = check_trendline_stocks_for_entry()

    # Monitor Radar positions for target/stoploss
    radar_changed = monitor_radar_positions()

    if tl_changed or radar_changed:
        print(f"\n✅ Updates saved to radar_trades.json")
    else:
        print(f"\n✅ No changes")

    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
