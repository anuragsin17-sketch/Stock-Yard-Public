#!/usr/bin/env python3
"""
Stock Yard - Automated Stock Screening System
A 24/7 automated stock screener using GitHub Actions and free APIs
"""

import pandas as pd
import yfinance as yf
import json
import os
import requests
from datetime import datetime, timedelta
import numpy as np
import time
import logging
from typing import Dict, List, Tuple, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class StockScreener:
    def __init__(self):
        self.telegram_bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        self.telegram_chat_id = os.environ.get('TELEGRAM_CHAT_ID')
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'fibonacci_stocks': [],
            'volume_breakout_stocks': [],
            'w_pattern_stocks': [],
            'diagnostics': {
                'total_stocks_processed': 0,
                'successful_downloads': 0,
                'failed_downloads': 0,
                'fibonacci_matches': 0,
                'volume_breakout_matches': 0,
                'w_pattern_matches': 0,
                'errors': []
            }
        }
    
    def load_stock_universe(self) -> pd.DataFrame:
        """Load the NIFTY stock list"""
        try:
            # Try different possible file names
            possible_files = ['ind_nifty50list.csv', 'ind_nifty500list.csv', 'ind_nifty500list.xlsx', 'nifty500.csv', 'nifty50.csv']
            
            for filename in possible_files:
                try:
                    if filename.endswith('.csv'):
                        df = pd.read_csv(filename)
                    else:
                        df = pd.read_excel(filename)
                    
                    logger.info(f"Successfully loaded {len(df)} stocks from {filename}")
                    logger.info(f"Columns: {list(df.columns)}")
                    return df
                except FileNotFoundError:
                    logger.warning(f"File {filename} not found, trying next option...")
                    continue
                except Exception as e:
                    logger.warning(f"Error reading {filename}: {e}")
                    continue
            
            # If no file found, create a minimal test dataset
            logger.warning("No stock universe file found, creating minimal test dataset")
            test_data = {
                'Company Name': ['Reliance Industries Ltd.', 'Tata Consultancy Services Ltd.', 'Infosys Ltd.'],
                'Industry': ['Oil Gas & Consumable Fuels', 'Information Technology', 'Information Technology'],
                'Symbol': ['RELIANCE', 'TCS', 'INFY'],
                'Series': ['EQ', 'EQ', 'EQ'],
                'ISIN Code': ['INE002A01018', 'INE467B01029', 'INE009A01021']
            }
            df = pd.DataFrame(test_data)
            logger.info(f"Created test dataset with {len(df)} stocks")
            return df
            
        except Exception as e:
            logger.error(f"Critical error loading stock universe: {e}")
            self.results['diagnostics']['errors'].append(f"Failed to load stock universe: {e}")
            return pd.DataFrame()
    
    def get_stock_data(self, symbol: str, period: str = "5y") -> Optional[pd.DataFrame]:
        """Download stock data with error handling and rate limiting"""
        try:
            # Add .NS suffix for NSE stocks
            ticker_symbol = f"{symbol}.NS"
            ticker = yf.Ticker(ticker_symbol)
            
            # Download data with retry logic
            for attempt in range(3):
                try:
                    data = ticker.history(period=period)
                    if not data.empty:
                        logger.info(f"Successfully downloaded data for {symbol}")
                        return data
                    else:
                        logger.warning(f"No data returned for {symbol}, attempt {attempt + 1}")
                except Exception as e:
                    logger.warning(f"Attempt {attempt + 1} failed for {symbol}: {e}")
                    if attempt < 2:
                        time.sleep(1)  # Rate limiting
            
            logger.error(f"Failed to download data for {symbol} after 3 attempts")
            return None
            
        except Exception as e:
            logger.error(f"Error downloading {symbol}: {e}")
            return None
    
    def get_weekly_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Download weekly stock data for W-pattern analysis"""
        try:
            # Add .NS suffix for NSE stocks
            ticker_symbol = f"{symbol}.NS"
            ticker = yf.Ticker(ticker_symbol)
            
            # Download 12 months of data and resample to weekly
            for attempt in range(3):
                try:
                    data = ticker.history(period="1y", interval="1d")
                    if not data.empty:
                        # Resample to weekly data (Friday close)
                        weekly_data = data.resample('W-FRI').agg({
                            'Open': 'first',
                            'High': 'max',
                            'Low': 'min',
                            'Close': 'last',
                            'Volume': 'sum'
                        }).dropna()
                        
                        logger.info(f"Successfully downloaded weekly data for {symbol}")
                        return weekly_data
                    else:
                        logger.warning(f"No weekly data returned for {symbol}, attempt {attempt + 1}")
                except Exception as e:
                    logger.warning(f"Weekly data attempt {attempt + 1} failed for {symbol}: {e}")
                    if attempt < 2:
                        time.sleep(1)
            
            logger.error(f"Failed to download weekly data for {symbol} after 3 attempts")
            return None
            
        except Exception as e:
            logger.error(f"Error downloading weekly data for {symbol}: {e}")
            return None
    
    def calculate_fibonacci_levels(self, data: pd.DataFrame) -> Dict:
        """Calculate Fibonacci retracement levels"""
        try:
            high_5y = data['High'].max()
            low_5y = data['Low'].min()
            current_price = data['Close'].iloc[-1]
            
            # Calculate retracement levels
            diff = high_5y - low_5y
            fib_100 = high_5y
            fib_618 = high_5y - (diff * 0.618)
            fib_50 = high_5y - (diff * 0.50)
            fib_382 = high_5y - (diff * 0.382)
            fib_0 = low_5y
            
            levels = {
                '100%': fib_100,
                '61.8%': fib_618,
                '50%': fib_50,
                '38.2%': fib_382,
                '0%': fib_0
            }
            
            # Check if current price is within 1.5% of key levels
            tolerance = 0.015  # 1.5%
            key_levels = [fib_100, fib_618, fib_50]
            
            for level_name, level_price in [('100%', fib_100), ('61.8%', fib_618), ('50%', fib_50)]:
                if abs(current_price - level_price) / level_price <= tolerance:
                    return {
                        'is_near_fibonacci': True,
                        'level': level_name,
                        'level_price': round(level_price, 2),
                        'current_price': round(current_price, 2),
                        'distance_percent': round(((current_price - level_price) / level_price) * 100, 2),
                        'high_5y': round(high_5y, 2),
                        'low_5y': round(low_5y, 2),
                        'all_levels': {k: round(v, 2) for k, v in levels.items()}
                    }
            
            return {'is_near_fibonacci': False}
            
        except Exception as e:
            logger.error(f"Error calculating Fibonacci levels: {e}")
            return {'is_near_fibonacci': False, 'error': str(e)}
    
    def check_volume_breakout(self, data: pd.DataFrame) -> Dict:
        """Check for enhanced volume breakout with retracement pattern"""
        try:
            if len(data) < 90:
                return {'is_volume_breakout': False, 'error': 'Insufficient data'}
            
            # Calculate 90-day volume baseline
            volume_90d = data['Volume'].tail(90)
            avg_volume_90d = volume_90d.mean()
            
            # Get recent data for analysis (last 30 days)
            recent_data = data.tail(30).copy()
            current_price = data['Close'].iloc[-1]
            
            # Step 1: Find historical volume breakouts in recent data
            volume_breakout_days = []
            
            for i in range(len(recent_data)):
                day_volume = recent_data['Volume'].iloc[i]
                day_close = recent_data['Close'].iloc[i]
                
                if i > 0:
                    prev_close = recent_data['Close'].iloc[i-1]
                    price_change = ((day_close - prev_close) / prev_close) * 100
                    volume_ratio = day_volume / avg_volume_90d
                    
                    # Identify significant volume breakouts (5x+ volume with positive price)
                    if volume_ratio >= 5.0 and price_change > 2.0:
                        volume_breakout_days.append({
                            'index': i,
                            'date': recent_data.index[i],
                            'breakout_price': day_close,
                            'volume_ratio': volume_ratio,
                            'price_change': price_change
                        })
            
            if not volume_breakout_days:
                return {'is_volume_breakout': False, 'error': 'No significant volume breakouts found'}
            
            # Step 2: Check for retracement back to breakout levels
            for breakout in volume_breakout_days:
                breakout_price = breakout['breakout_price']
                breakout_index = breakout['index']
                
                # Look for retracement in days after the breakout
                post_breakout_data = recent_data.iloc[breakout_index + 1:]
                
                if len(post_breakout_data) < 3:  # Need at least 3 days after breakout
                    continue
                
                # Check if price has retraced back to within 3% of breakout price
                retracement_tolerance = 0.03  # 3%
                lower_bound = breakout_price * (1 - retracement_tolerance)
                upper_bound = breakout_price * (1 + retracement_tolerance)
                
                # Check recent prices for retracement
                recent_prices = post_breakout_data['Close'].tail(5)  # Last 5 days
                
                for price in recent_prices:
                    if lower_bound <= price <= upper_bound:
                        # Found retracement! Check if it's showing signs of reversal
                        days_since_breakout = len(post_breakout_data)
                        retracement_percent = ((breakout_price - current_price) / breakout_price) * 100
                        
                        # Additional validation: ensure there was a meaningful pullback
                        max_price_after_breakout = post_breakout_data['Close'].max()
                        min_price_after_breakout = post_breakout_data['Close'].min()
                        pullback_depth = ((max_price_after_breakout - min_price_after_breakout) / max_price_after_breakout) * 100
                        
                        if pullback_depth >= 5.0:  # At least 5% pullback after breakout
                            return {
                                'is_volume_breakout': True,
                                'breakout_date': breakout['date'].strftime('%Y-%m-%d'),
                                'breakout_price': round(breakout_price, 2),
                                'breakout_volume_ratio': round(breakout['volume_ratio'], 2),
                                'breakout_price_change': round(breakout['price_change'], 2),
                                'current_price': round(current_price, 2),
                                'retracement_percent': round(abs(retracement_percent), 2),
                                'days_since_breakout': days_since_breakout,
                                'pullback_depth_percent': round(pullback_depth, 2),
                                'max_price_after_breakout': round(max_price_after_breakout, 2),
                                'pattern_type': 'Volume Breakout with Retracement'
                            }
            
            return {'is_volume_breakout': False, 'error': 'No valid retracement patterns found'}
            
        except Exception as e:
            logger.error(f"Error checking volume breakout: {e}")
            return {'is_volume_breakout': False, 'error': str(e)}
    
    def detect_w_pattern(self, weekly_data: pd.DataFrame) -> Dict:
        """Detect Weekly W-Pattern (Double Bottom) formation"""
        try:
            if len(weekly_data) < 20:  # Need at least 20 weeks of data
                return {'is_w_pattern': False, 'error': 'Insufficient weekly data'}
            
            closes = weekly_data['Close'].values
            lows = weekly_data['Low'].values
            highs = weekly_data['High'].values
            
            # Find local minima and maxima using a rolling window approach
            window = 3  # Look for peaks/troughs over 3-week periods
            
            # Identify potential troughs (local minima)
            troughs = []
            for i in range(window, len(lows) - window):
                if lows[i] == min(lows[i-window:i+window+1]):
                    troughs.append((i, lows[i]))
            
            # Identify potential peaks (local maxima) 
            peaks = []
            for i in range(window, len(highs) - window):
                if highs[i] == max(highs[i-window:i+window+1]):
                    peaks.append((i, highs[i]))
            
            if len(troughs) < 2 or len(peaks) < 1:
                return {'is_w_pattern': False, 'error': 'Insufficient pivot points'}
            
            # Look for W-pattern in the most recent data (last 6 months)
            recent_weeks = min(26, len(weekly_data))  # 6 months or available data
            start_idx = len(weekly_data) - recent_weeks
            
            # Filter pivots to recent period
            recent_troughs = [(i, price) for i, price in troughs if i >= start_idx]
            recent_peaks = [(i, price) for i, price in peaks if i >= start_idx]
            
            if len(recent_troughs) < 2:
                return {'is_w_pattern': False, 'error': 'No recent double bottom pattern'}
            
            # Find the best W-pattern candidate
            current_price = closes[-1]
            
            for i in range(len(recent_troughs) - 1):
                t1_idx, t1_price = recent_troughs[i]
                
                for j in range(i + 1, len(recent_troughs)):
                    t2_idx, t2_price = recent_troughs[j]
                    
                    # Find peak between the two troughs
                    intermediate_peaks = [p for p in recent_peaks if t1_idx < p[0] < t2_idx]
                    if not intermediate_peaks:
                        continue
                    
                    # Get the highest peak between troughs
                    p1_idx, p1_price = max(intermediate_peaks, key=lambda x: x[1])
                    
                    # Validate W-pattern conditions
                    # 1. T2 should be within tolerance of T1 (equal +/-2% OR higher low up to +8%)
                    t1_tolerance_low = t1_price * 0.98  # -2%
                    t1_tolerance_high = t1_price * 1.08  # +8%
                    
                    if not (t1_tolerance_low <= t2_price <= t1_tolerance_high):
                        continue
                    
                    # 2. Peak should be significantly higher than troughs (at least 15% above)
                    if p1_price < max(t1_price, t2_price) * 1.15:
                        continue
                    
                    # 3. Current price should be recovering from T2 (at least 2% above T2)
                    if current_price < t2_price * 1.02:
                        continue
                    
                    # 4. Current price should not have broken above neckline yet (leave room for breakout)
                    if current_price >= p1_price * 0.98:  # Within 2% of neckline
                        continue
                    
                    # Calculate metrics
                    distance_to_neckline = ((p1_price - current_price) / current_price) * 100
                    t2_vs_t1_percent = ((t2_price - t1_price) / t1_price) * 100
                    recovery_from_t2 = ((current_price - t2_price) / t2_price) * 100
                    
                    # Valid W-pattern found
                    return {
                        'is_w_pattern': True,
                        'left_trough_price': round(t1_price, 2),
                        'right_trough_price': round(t2_price, 2),
                        'neckline_peak_price': round(p1_price, 2),
                        'current_price': round(current_price, 2),
                        'distance_to_neckline_percent': round(distance_to_neckline, 2),
                        't2_vs_t1_percent': round(t2_vs_t1_percent, 2),
                        'recovery_from_t2_percent': round(recovery_from_t2, 2),
                        'pattern_timeframe_weeks': t2_idx - t1_idx + 1,
                        'left_trough_date': weekly_data.index[t1_idx].strftime('%Y-%m-%d'),
                        'neckline_peak_date': weekly_data.index[p1_idx].strftime('%Y-%m-%d'),
                        'right_trough_date': weekly_data.index[t2_idx].strftime('%Y-%m-%d')
                    }
            
            return {'is_w_pattern': False, 'error': 'No valid W-pattern found in recent data'}
            
        except Exception as e:
            logger.error(f"Error detecting W-pattern: {e}")
            return {'is_w_pattern': False, 'error': str(e)}
    
    def screen_stock(self, symbol: str, company_name: str, industry: str) -> None:
        """Screen a single stock for all three conditions"""
        try:
            self.results['diagnostics']['total_stocks_processed'] += 1
            
            # Download daily stock data
            data = self.get_stock_data(symbol)
            if data is None or data.empty:
                self.results['diagnostics']['failed_downloads'] += 1
                return
            
            self.results['diagnostics']['successful_downloads'] += 1
            
            # Check Fibonacci retracement
            fib_result = self.calculate_fibonacci_levels(data)
            if fib_result.get('is_near_fibonacci', False):
                stock_info = {
                    'symbol': symbol,
                    'company_name': company_name,
                    'industry': industry,
                    **fib_result
                }
                self.results['fibonacci_stocks'].append(stock_info)
                self.results['diagnostics']['fibonacci_matches'] += 1
                logger.info(f"Fibonacci match: {symbol} near {fib_result['level']} level")
            
            # Check volume breakout
            volume_result = self.check_volume_breakout(data)
            if volume_result.get('is_volume_breakout', False):
                stock_info = {
                    'symbol': symbol,
                    'company_name': company_name,
                    'industry': industry,
                    **volume_result
                }
                self.results['volume_breakout_stocks'].append(stock_info)
                self.results['diagnostics']['volume_breakout_matches'] += 1
                logger.info(f"Volume breakout: {symbol} with {volume_result.get('breakout_volume_ratio', 'N/A')}x volume")
            
            # Check W-Pattern (weekly data)
            weekly_data = self.get_weekly_data(symbol)
            if weekly_data is not None and not weekly_data.empty:
                w_pattern_result = self.detect_w_pattern(weekly_data)
                if w_pattern_result.get('is_w_pattern', False):
                    stock_info = {
                        'symbol': symbol,
                        'company_name': company_name,
                        'industry': industry,
                        **w_pattern_result
                    }
                    self.results['w_pattern_stocks'].append(stock_info)
                    self.results['diagnostics']['w_pattern_matches'] += 1
                    logger.info(f"W-Pattern match: {symbol} with {w_pattern_result['distance_to_neckline_percent']:.1f}% to neckline")
            
            # Rate limiting to avoid overwhelming the API
            time.sleep(0.1)
            
        except Exception as e:
            logger.error(f"Error screening {symbol}: {e}")
            self.results['diagnostics']['errors'].append(f"Error screening {symbol}: {e}")
    
    def run_screening(self) -> None:
        """Run the complete screening process"""
        logger.info("Starting stock screening process...")
        
        # Load stock universe
        stocks_df = self.load_stock_universe()
        if stocks_df.empty:
            logger.error("No stocks to process")
            return
        
        # Process each stock
        total_stocks = len(stocks_df)
        for idx, row in stocks_df.iterrows():
            symbol = row['Symbol']
            company_name = row['Company Name']
            industry = row['Industry']
            
            logger.info(f"Processing {idx + 1}/{total_stocks}: {symbol}")
            self.screen_stock(symbol, company_name, industry)
            
            # Progress update every 50 stocks
            if (idx + 1) % 50 == 0:
                logger.info(f"Progress: {idx + 1}/{total_stocks} stocks processed")
        
        logger.info("Screening process completed")
        self.log_summary()
    
    def log_summary(self) -> None:
        """Log screening summary"""
        diag = self.results['diagnostics']
        logger.info(f"""
        Screening Summary:
        - Total stocks processed: {diag['total_stocks_processed']}
        - Successful downloads: {diag['successful_downloads']}
        - Failed downloads: {diag['failed_downloads']}
        - Fibonacci matches: {diag['fibonacci_matches']}
        - Volume breakout matches: {diag['volume_breakout_matches']}
        - W-Pattern matches: {diag['w_pattern_matches']}
        - Errors: {len(diag['errors'])}
        """)
    
    def save_results(self) -> None:
        """Save results to JSON file"""
        try:
            with open('data.json', 'w') as f:
                json.dump(self.results, f, indent=2)
            logger.info("Results saved to data.json")
        except Exception as e:
            logger.error(f"Error saving results: {e}")
    
    def send_telegram_notification(self) -> None:
        """Send summary notification via Telegram"""
        if not self.telegram_bot_token or not self.telegram_chat_id:
            logger.warning("Telegram credentials not configured")
            return
        
        try:
            # Prepare message
            fib_count = len(self.results['fibonacci_stocks'])
            vol_count = len(self.results['volume_breakout_stocks'])
            w_pattern_count = len(self.results['w_pattern_stocks'])
            
            message = f"""🔍 *Stock Yard Daily Screening Report*
📅 {datetime.now().strftime('%Y-%m-%d %H:%M IST')}

📊 *Results Summary:*
• Fibonacci Retracement Matches: {fib_count}
• Volume Breakout Matches: {vol_count}
• W-Pattern Matches: {w_pattern_count}

"""
            
            # Add Fibonacci matches
            if fib_count > 0:
                message += "🔢 *Fibonacci Retracement Stocks:*\n"
                for stock in self.results['fibonacci_stocks'][:5]:  # Limit to top 5
                    message += f"• {stock['symbol']} ({stock['company_name'][:20]}...)\n"
                    message += f"  Near {stock['level']} level at ₹{stock['current_price']}\n"
                if fib_count > 5:
                    message += f"... and {fib_count - 5} more\n"
                message += "\n"
            
            # Add volume breakout matches
            if vol_count > 0:
                message += "📈 *Volume Breakout Stocks:*\n"
                for stock in self.results['volume_breakout_stocks'][:5]:  # Limit to top 5
                    message += f"• {stock['symbol']} ({stock['company_name'][:20]}...)\n"
                    message += f"  {stock['breakout_volume_ratio']}x volume, +{stock['breakout_price_change']:.1f}%\n"
                if vol_count > 5:
                    message += f"... and {vol_count - 5} more\n"
                message += "\n"
            
            # Add W-Pattern matches
            if w_pattern_count > 0:
                message += "📈 *LOGIC 3: WEEKLY W-PATTERN TRIGGERS:*\n"
                for stock in self.results['w_pattern_stocks'][:5]:  # Limit to top 5
                    message += f"• {stock['symbol']} ({stock['company_name'][:20]}...)\n"
                    message += f"  {stock['distance_to_neckline_percent']:.1f}% to neckline breakout at ₹{stock['neckline_peak_price']}\n"
                if w_pattern_count > 5:
                    message += f"... and {w_pattern_count - 5} more\n"
                message += "\n"
            
            message += f"📱 View full report: https://anuragsin17-sketch.github.io/Stock-Yard/"
            
            # Send message
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            payload = {
                'chat_id': self.telegram_chat_id,
                'text': message,
                'parse_mode': 'Markdown'
            }
            
            response = requests.post(url, json=payload)
            if response.status_code == 200:
                logger.info("Telegram notification sent successfully")
            else:
                logger.error(f"Failed to send Telegram notification: {response.text}")
                
        except Exception as e:
            logger.error(f"Error sending Telegram notification: {e}")

def main():
    """Main execution function"""
    logger.info("Stock Yard Screener Starting...")
    
    # Check if stock universe file exists
    import os
    available_files = [f for f in os.listdir('.') if 'nifty' in f.lower() and f.endswith('.csv')]
    logger.info(f"Available NIFTY files: {available_files}")
    
    screener = StockScreener()
    screener.run_screening()
    screener.save_results()
    screener.send_telegram_notification()
    
    logger.info("Stock Yard Screener Completed!")

if __name__ == "__main__":
    main()