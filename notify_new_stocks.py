"""
notify_new_stocks.py
Sends Telegram alerts for newly detected stocks in both:
  - Volume tab  (data.json → volume_breakout_stocks)
  - Trendline tab (trendline_screen.json)

Tracks previously alerted stocks in alerted_today.json to avoid spam.
Runs after screener.py and update_feed.py in the GitHub Actions workflow.
"""
import json
import os
import requests
from datetime import datetime

BASE_URL = "https://anuragsin17-sketch.github.io/Stock-Yard-Public"
ALERTED_FILE = "alerted_today.json"
TODAY = datetime.now().strftime("%Y-%m-%d")


def send_telegram(message: str) -> bool:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("⚠️  Telegram not configured — skipping")
        return False
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"},
            timeout=10,
        )
        if resp.status_code == 200:
            print(f"✅ Telegram sent")
            return True
        print(f"❌ Telegram failed: {resp.text[:200]}")
    except Exception as e:
        print(f"❌ Telegram error: {e}")
    return False


def load_alerted() -> dict:
    """Load today's alerted stocks dict {symbol: {vol: bool, trendline: bool}}"""
    if os.path.exists(ALERTED_FILE):
        try:
            with open(ALERTED_FILE) as f:
                data = json.load(f)
            if data.get("date") == TODAY:
                return data.get("stocks", {})
        except Exception:
            pass
    return {}


def save_alerted(alerted: dict):
    with open(ALERTED_FILE, "w") as f:
        json.dump({"date": TODAY, "stocks": alerted}, f, indent=2)


def notify_volume(alerted: dict) -> int:
    """Alert new volume breakout stocks. Returns count of new alerts sent."""
    try:
        with open("data.json") as f:
            data = json.load(f)
    except Exception as e:
        print(f"⚠️  Could not load data.json: {e}")
        return 0

    stocks = data.get("volume_breakout_stocks", [])
    sent = 0

    for s in stocks:
        sym = s.get("symbol", "")
        if not sym:
            continue

        entry = alerted.setdefault(sym, {})
        if entry.get("vol"):
            print(f"   ⏭️  {sym} volume already alerted today")
            continue

        ratio = s.get("breakout_volume_ratio", 0)
        price = s.get("current_price", 0)
        trigger = s.get("radar_trigger_price", price)
        stop = round(trigger * 0.92, 2)
        target = round(trigger * 1.20, 2)
        breakout_date = s.get("breakout_date", "")
        week_high = s.get("week_52_high", 0)
        week_low = s.get("week_52_low", 0)
        company = s.get("company_name", sym)

        chart_url = f"https://in.tradingview.com/chart/?symbol=NSE:{sym}"

        msg = (
            f"🔥 *VOLUME BREAKOUT — {sym}*\n"
            f"_{company}_\n\n"
            f"📊 Volume Spike: *{ratio}x*\n"
            f"💰 Current Price: ₹{price:,.2f}\n"
            f"🎯 Entry Trigger: ₹{trigger:,.2f}\n"
            f"🛑 Stop Loss: ₹{stop:,.2f} _(monthly close)_\n"
            f"✅ Target: ₹{target:,.2f} _(+20%)_\n"
            f"📅 Breakout Date: {breakout_date}\n"
            f"📈 52W: ₹{week_low:,.2f} – ₹{week_high:,.2f}\n\n"
            f"[📉 View Chart]({chart_url}) | [📱 Open App]({BASE_URL}/)"
        )

        if send_telegram(msg):
            entry["vol"] = True
            sent += 1

    return sent


def notify_trendline(alerted: dict) -> int:
    """Alert new trendline touch stocks. Returns count of new alerts sent."""
    try:
        with open("trendline_screen.json") as f:
            stocks = json.load(f)
    except Exception as e:
        print(f"⚠️  Could not load trendline_screen.json: {e}")
        return 0

    sent = 0

    for s in stocks:
        sym = s.get("ticker", "")
        if not sym:
            continue

        entry = alerted.setdefault(sym, {})
        if entry.get("trendline"):
            print(f"   ⏭️  {sym} trendline already alerted today")
            continue

        dist = s.get("distanceRemaining", 99)
        price = s.get("currentPrice", 0)
        trigger = s.get("triggerPrice", price)
        stop = s.get("positionSizing", {}).get("strictStopLoss", round(trigger * 0.92, 2))
        target = s.get("positionSizing", {}).get("pivotTargetExit", round(trigger * 1.20, 2))
        fib = s.get("fibLevelMatch", "—")
        score = s.get("confluenceScore", "—")
        wicks = s.get("wickTouches", "—")
        is_critical = s.get("notificationTrigger", False)

        status_emoji = "🎯" if is_critical else "👀"
        status_label = "CRITICAL ENTRY" if is_critical else "WATCHLIST"

        chart_url = f"https://in.tradingview.com/chart/?symbol=NSE:{sym}"
        confirm_url = (
            f"{BASE_URL}/?confirm={sym}"
            f"&price={trigger}&stop={stop}&target={target}&source=Trendline"
        )

        msg = (
            f"{status_emoji} *TRENDLINE TOUCH — {sym}* ({status_label})\n\n"
            f"💰 Current Price: ₹{price:,.2f}\n"
            f"📍 Trendline Entry: ₹{trigger:,.2f} _({dist:.2f}% away)_\n"
            f"🛑 Stop Loss: ₹{stop:,.2f} _(monthly close)_\n"
            f"✅ Target: ₹{target:,.2f} _(+20%)_\n"
            f"📐 Fib Level: {fib} | Score: {score}/10 | Wicks: {wicks}\n\n"
            f"[📉 View Chart]({chart_url})"
        )
        if is_critical:
            msg += f" | [📥 Confirm Trade]({confirm_url})"

        if send_telegram(msg):
            entry["trendline"] = True
            sent += 1

    return sent


def main():
    print("=" * 60)
    print(f"STOCK YARD NOTIFIER — {datetime.now().strftime('%Y-%m-%d %H:%M IST')}")
    print("=" * 60)

    alerted = load_alerted()

    print("\n📊 Checking Volume breakouts...")
    vol_sent = notify_volume(alerted)

    print("\n📈 Checking Trendline touches...")
    tl_sent = notify_trendline(alerted)

    save_alerted(alerted)

    total = vol_sent + tl_sent
    print(f"\n✅ Done — {vol_sent} volume + {tl_sent} trendline alerts sent ({total} total)")

    # Send a combined summary if anything new was found
    if total > 0:
        summary = (
            f"📋 *Stock Yard — {datetime.now().strftime('%d %b %Y, %H:%M IST')}*\n\n"
            f"🔥 Volume alerts: {vol_sent}\n"
            f"📈 Trendline alerts: {tl_sent}\n\n"
            f"[Open App]({BASE_URL}/)"
        )
        send_telegram(summary)


if __name__ == "__main__":
    main()
