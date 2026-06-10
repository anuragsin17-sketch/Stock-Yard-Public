#!/usr/bin/env python3
"""
Live Price Updater for Stock Yard Dashboard
Runs continuously to fetch live prices and update data files every 10 seconds
Can be deployed on EC2 as a systemd service
"""

import json
import time
import requests
from datetime import datetime
from pathlib import Path
import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class LivePriceUpdater:
    def __init__(self, data_file='./data.json', update_interval=10):
        self.data_file = Path(data_file)
        self.update_interval = update_interval
        self.live_prices = {}
        
    def fetch_live_price(self, symbol):
        """Fetch live price for a single stock using Yahoo Finance"""
        try:
            url = f'https://query1.finance.yahoo.com/v8/finance/chart/{symbol}.NS'
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                price = data.get('chart', {}).get('result', [{}])[0].get('meta', {}).get('regularMarketPrice')
                if price:
                    self.live_prices[symbol] = price
                    logger.debug(f'✓ {symbol}: ₹{price:.2f}')
                    return price
        except requests.exceptions.Timeout:
            logger.warning(f'⏱ Timeout fetching {symbol}')
        except Exception as e:
            logger.warning(f'✗ Failed to fetch {symbol}: {str(e)}')
        
        return None
    
    def fetch_all_live_prices(self, stocks):
        """Fetch live prices for multiple stocks in parallel"""
        symbols = [s.get('symbol') for s in stocks if s.get('symbol')]
        
        if not symbols:
            return
        
        logger.info(f'📊 Fetching live prices for {len(symbols)} stocks...')
        
        # Use ThreadPoolExecutor for parallel requests
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(self.fetch_live_price, symbol): symbol for symbol in symbols}
            
            completed = 0
            for future in as_completed(futures):
                completed += 1
                if completed % 10 == 0:
                    logger.info(f'  Fetched {completed}/{len(symbols)} prices...')
        
        logger.info(f'✅ Fetched {len(self.live_prices)} live prices')
    
    def update_data_file(self):
        """Update data.json with latest live prices"""
        if not self.data_file.exists():
            logger.warning(f'Data file not found: {self.data_file}')
            return False
        
        try:
            # Read current data
            with open(self.data_file, 'r') as f:
                data = json.load(f)
            
            # Collect all stocks that need price updates
            all_stocks = []
            
            if 'volume_breakout_stocks' in data:
                all_stocks.extend(data['volume_breakout_stocks'])
            
            if 'golden_stocks' in data:
                all_stocks.extend(data['golden_stocks'])
            
            # Fetch live prices
            self.fetch_all_live_prices(all_stocks)
            
            # Update prices in data
            updated_count = 0
            
            if 'volume_breakout_stocks' in data:
                for stock in data['volume_breakout_stocks']:
                    if stock['symbol'] in self.live_prices:
                        old_price = stock.get('current_price')
                        stock['current_price'] = self.live_prices[stock['symbol']]
                        stock['is_live_updated'] = True
                        
                        # Recalculate distance percentages
                        if stock.get('radar_trigger_price'):
                            pct = ((stock['current_price'] - stock['radar_trigger_price']) / stock['radar_trigger_price']) * 100
                            stock['distance_to_trigger_abs_percent'] = abs(pct)
                        
                        updated_count += 1
            
            if 'golden_stocks' in data:
                for stock in data['golden_stocks']:
                    if stock['symbol'] in self.live_prices:
                        stock['current_price'] = self.live_prices[stock['symbol']]
                        stock['is_live_updated'] = True
                        
                        # Recalculate distance percentages
                        if stock.get('trendline_price'):
                            pct = ((stock['current_price'] - stock['trendline_price']) / stock['trendline_price']) * 100
                            stock['distance_to_trendline_percent'] = pct
                        
                        updated_count += 1
            
            # Update timestamp
            data['timestamp'] = datetime.utcnow().isoformat() + 'Z'
            data['last_price_update'] = datetime.utcnow().isoformat() + 'Z'
            
            # Write updated data back
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f'📝 Updated {updated_count} stock prices in data.json')
            return True
            
        except Exception as e:
            logger.error(f'Failed to update data file: {str(e)}')
            return False
    
    def start(self):
        """Start continuous live price updates"""
        logger.info(f'🟢 Live Price Updater started (interval: {self.update_interval}s)')
        logger.info(f'📁 Data file: {self.data_file.absolute()}')
        
        try:
            while True:
                start_time = time.time()
                
                self.update_data_file()
                
                elapsed = time.time() - start_time
                sleep_time = max(0, self.update_interval - elapsed)
                
                if sleep_time > 0:
                    time.sleep(sleep_time)
                else:
                    logger.warning(f'⏱ Update took {elapsed:.1f}s (longer than interval {self.update_interval}s)')
        
        except KeyboardInterrupt:
            logger.info('🔴 Live Price Updater stopped')
        except Exception as e:
            logger.error(f'Fatal error: {str(e)}')
            sys.exit(1)


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Live Price Updater for Stock Yard')
    parser.add_argument('--data-file', default='./data.json', help='Path to data.json file')
    parser.add_argument('--interval', type=int, default=10, help='Update interval in seconds')
    args = parser.parse_args()
    
    updater = LivePriceUpdater(data_file=args.data_file, update_interval=args.interval)
    updater.start()
