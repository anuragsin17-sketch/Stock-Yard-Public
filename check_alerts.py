import os
import json
import requests

# Only needs Telegram details to message your phone
BOT_TOKEN  = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()
CHAT_ID    = os.environ.get('TELEGRAM_CHAT_ID', '').strip()
RADAR_FILE = 'radar_trades.json'

def send_telegram(message):
    if not BOT_TOKEN or not CHAT_ID: 
        print("⚠️ Telegram keys missing")
        return
    try:
        requests.post(
            f"https://telegram.org{BOT_TOKEN}/sendMessage",
            json={'chat_id': CHAT_ID, 'text': message, 'parse_mode': 'Markdown'},
            timeout=10
        )
        print("📨 Notification sent successfully!")
    except Exception as e:
        print(f"Telegram error: {e}")

def main():
    if not os.path.exists(RADAR_FILE):
        print("No trades file found.")
        return

    with open(RADAR_FILE, 'r') as f:
        trades = json.load(f)

    open_trades = [t for t in trades if t.get('status') == 'Open']
    if not open_trades:
        print("No open positions to monitor.")
        return

    for trade in open_trades:
        symbol = trade['ticker']
        entry = float(trade['entry_price'])
        
        # Pull targets from your JSON data, or fallback to default (+20% / -5%)
        target = float(trade.get('target_price', entry * 1.20))
        stoploss = float(trade.get('stop_loss', entry * 0.95))

        # Fetch Live Price from Yahoo Finance
        url = f"https://yahoo.com{symbol}.NS"
        resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
        
        if resp.status_code == 200:
            try:
                current_price = resp.json()['chart']['result']['meta']['regularMarketPrice']
                print(f"📡 Checking {symbol}: Live ₹{current_price} | Target: ₹{target} | SL: ₹{stoploss}")
                
                gain_loss_pct = ((current_price - entry) / entry) * 100

                # 🎯 Target Hit Alert
                if current_price >= target:
                    msg = (
                        f"🎯 *PROFIT TARGET HIT* 🎯\n\n"
                        f"Stock: `{symbol}`\n"
                        f"Entry Price: ₹{entry:,.2f}\n"
                        f"Current Price: ₹{current_price:,.2f}\n"
                        f"Current Gain: *+{gain_loss_pct:.2f}%*\n"
                        f"Target Level: ₹{target:,.2f}\n\n"
                        f"📱 Check your dashboard: https://github.io"
                    )
                    send_telegram(msg)

                # 🛑 Stop Loss Hit Alert
                elif current_price <= stoploss:
                    msg = (
                        f"🛑 *STOP LOSS BREACHED* 🛑\n\n"
                        f"Stock: `{symbol}`\n"
                        f"Entry Price: ₹{entry:,.2f}\n"
                        f"Current Price: ₹{current_price:,.2f}\n"
                        f"Current Loss: *{gain_loss_pct:.2f}%*\n"
                        f"Stop Loss Level: ₹{stoploss:,.2f}\n\n"
                        f"📱 Check your dashboard: https://github.io"
                    )
                    send_telegram(msg)
            except Exception as parse_err:
                print(f"Failed to parse price for {symbol}: {parse_err}")

if __name__ == "__main__":
    main()
