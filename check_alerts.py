import os
import json
import requests

BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '').strip()
RADAR_FILE = 'radar_trades.json'

def send_telegram(message):
    if not BOT_TOKEN or not CHAT_ID: return
    try: requests.post(f'https://telegram.org{BOT_TOKEN}/sendMessage', json={'chat_id': CHAT_ID, 'text': message, 'parse_mode': 'Markdown'}, timeout=10)
    except Exception as e: print(e)

def main():
    if not os.path.exists(RADAR_FILE): return
    with open(RADAR_FILE, 'r') as f: trades = json.load(f)
    open_trades = [t for t in trades if t.get('status') == 'Open']
    for trade in open_trades:
        symbol = trade['ticker']
        entry = float(trade['entry_price'])
        target = float(trade.get('target_price', entry * 1.20))
        stoploss = float(trade.get('stop_loss', entry * 0.95))
        url = f'https://yahoo.com{symbol}.NS'
        resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        if resp.status_code == 200:
            try:
                current_price = resp.json()['chart']['result']['meta']['regularMarketPrice']
                print(f'📡 Checking {symbol}: Live ₹{current_price}')
                gain_loss = ((current_price - entry) / entry) * 100
                if current_price >= target:
                    send_telegram(f'🎯 *PROFIT TARGET HIT* 🎯\n\nStock: {symbol}\nLive: ₹{current_price}\nGain: +{gain_loss:.2f}%')
                elif current_price <= stoploss:
                    send_telegram(f'🛑 *STOP LOSS BREACHED* 🛑\n\nStock: {symbol}\nLive: ₹{current_price}\nLoss: {gain_loss:.2f}%')
            except Exception as e: print('Parse error:', e)

if __name__ == '__main__': main()