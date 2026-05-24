"""
Fast price-only update for cached trendline stocks.
Runs every 30 min during market hours - does NOT recalculate trendlines.
"""
import json
import yfinance as yf
from datetime import datetime

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
                
                print(f"   ✓ {ticker:12} | ₹{old_price:8.2f} → ₹{current_price:8.2f} | Dist: {distance:+.2f}%")
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
