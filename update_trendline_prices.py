"""
Fast price-only update for cached trendline stocks.
Runs every 30 min during market hours - does NOT recalculate trendlines.
Updates current prices and EMAs.
"""
import json
import yfinance as yf
import pandas as pd
from datetime import datetime

def calculate_emas(ticker: str) -> dict:
    """Calculate 50 EMA and 200 EMA for a given ticker"""
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1y")  # Get 1 year of data for EMA calculation
        
        if hist.empty or len(hist) < 200:
            return {"ema50": None, "ema200": None}
        
        # Calculate EMAs - get the last value
        ema50_series = hist['Close'].ewm(span=50, adjust=False).mean()
        ema200_series = hist['Close'].ewm(span=200, adjust=False).mean()
        
        ema50 = ema50_series.iloc[-1]
        ema200 = ema200_series.iloc[-1]
        
        return {
            "ema50": round(float(ema50), 2) if pd.notna(ema50) else None,
            "ema200": round(float(ema200), 2) if pd.notna(ema200) else None
        }
    except Exception:
        return {"ema50": None, "ema200": None}


def update_cached_prices():
    """Update only current prices for stocks in trendline_screen.json"""
    
    try:
        # Load cached trendline data
        with open('trendline_screen.json', 'r') as f:
            cached_data = json.load(f)
        
        if not cached_data:
            print("No cached trendline data found")
            return
        
        print(f"Updating prices for {len(cached_data)} cached trendline stocks...")
        
        # Extract tickers and add .NS suffix for Yahoo Finance
        tickers = [stock['ticker'] + '.NS' if not stock['ticker'].endswith('.NS') else stock['ticker'] 
                   for stock in cached_data]
        
        # Fetch current prices in batch (much faster)
        ticker_str = ' '.join(tickers)
        data = yf.download(ticker_str, period='1d', progress=False, threads=True)
        
        # Update each stock's current price and recalculate distance
        updated_count = 0
        for i, stock in enumerate(cached_data):
            ticker_with_suffix = tickers[i]
            ticker = stock['ticker']
            try:
                if len(tickers) == 1:
                    current_price = float(data['Close'].iloc[-1])
                else:
                    current_price = float(data['Close'][ticker_with_suffix].iloc[-1])
                
                # Update current price
                old_price = stock['currentPrice']
                stock['currentPrice'] = float(current_price)
                
                # Update EMAs
                emas = calculate_emas(ticker_with_suffix)
                stock['ema50'] = emas['ema50']
                stock['ema200'] = emas['ema200']
                
                # Recalculate distance to trigger
                trigger_price = stock['triggerPrice']
                distance = ((current_price - trigger_price) / trigger_price) * 100
                stock['distanceRemaining'] = round(distance, 2)
                
                # Update notification trigger (within ±1%)
                stock['notificationTrigger'] = abs(distance) <= 1.0
                
                # Recalculate position sizing with new price
                position_size = stock['positionSizing']['allocatedAmount']
                shares = int(position_size / current_price)
                stock['positionSizing']['sharesToBuy'] = shares
                
                ema_info = f"50EMA: ₹{emas['ema50']:.2f}" if emas['ema50'] else "50EMA: N/A"
                ema_info += f" | 200EMA: ₹{emas['ema200']:.2f}" if emas['ema200'] else " | 200EMA: N/A"
                print(f"   ✓ {ticker:12} | ₹{old_price:8.2f} → ₹{current_price:8.2f} | Dist: {distance:+.2f}% | {ema_info}")
                updated_count += 1
                
            except Exception as e:
                print(f"   ✗ {ticker:12} | Error: {e}")
                continue
        
        # Re-sort by distance
        cached_data.sort(key=lambda x: x['distanceRemaining'])
        
        # Save updated data
        with open('trendline_screen.json', 'w') as f:
            json.dump(cached_data, f, indent=4)
        
        print(f"\n✅ Updated {updated_count}/{len(cached_data)} stocks")
        print(f"⏱️  {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}")
        
    except FileNotFoundError:
        print("❌ trendline_screen.json not found - run full scan first")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    update_cached_prices()
