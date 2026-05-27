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
            'golden_stocks': [],  # Trendline + Optional Fibonacci (Weekly or Monthly)
            'volume_breakout_stocks': [],
            'diagnostics': {
                'total_stocks_processed': 0,
                'successful_downloads': 0,
                'failed_downloads': 0,
                'golden_matches': 0,
                'volume_breakout_matches': 0,
                'errors': []
            }
        }
    
    def load_stock_universe(self) -> pd.DataFrame:
        """Load the NIFTY stock list"""
        try:
            # Try different possible file names - prioritize Stock List
            possible_files = ['Stock List.csv', 'ind_nifty500list.csv', 'ind_nifty200list.csv', 'ind_nifty50list.csv', 'ind_nifty500list.xlsx', 'nifty500.csv', 'nifty50.csv']
            
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
            
            # Download data with retry logic and longer delays
            for attempt in range(2):  # Reduced from 3 to 2 attempts
                try:
                    data = ticker.history(period=period)
                    if not data.empty:
                        logger.info(f"Successfully downloaded data for {symbol}")
                        return data
                    else:
                        logger.warning(f"No data returned for {symbol}, attempt {attempt + 1}")
                except Exception as e:
                    logger.warning(f"Attempt {attempt + 1} failed for {symbol}: {e}")
                    if attempt < 1:  # Only sleep between attempts, not after last
                        time.sleep(2)  # Increased from 1 to 2 seconds
            
            logger.error(f"Failed to download data for {symbol} after 2 attempts")
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
        """Calculate Fibonacci retracement levels - Only 38.2%, 50%, and 61.8%"""
        try:
            high_5y = data['High'].max()
            low_5y = data['Low'].min()
            current_price = data['Close'].iloc[-1]
            
            # Calculate 52-week high and low
            week_52_high = data['High'].tail(252).max() if len(data) >= 252 else data['High'].max()
            week_52_low = data['Low'].tail(252).min() if len(data) >= 252 else data['Low'].min()
            
            # Calculate only the three key retracement levels
            diff = high_5y - low_5y
            fib_618 = high_5y - (diff * 0.618)
            fib_50 = high_5y - (diff * 0.50)
            fib_382 = high_5y - (diff * 0.382)
            
            levels = {
                '61.8%': fib_618,
                '50%': fib_50,
                '38.2%': fib_382
            }
            
            # Check if current price is within 5% of key levels
            tolerance = 0.05  # 5%
            
            for level_name, level_price in levels.items():
                if abs(current_price - level_price) / level_price <= tolerance:
                    return {
                        'is_near_fibonacci': True,
                        'level': level_name,
                        'level_price': round(level_price, 2),
                        'current_price': round(current_price, 2),
                        'distance_percent': round(((current_price - level_price) / level_price) * 100, 2),
                        'high_5y': round(high_5y, 2),
                        'low_5y': round(low_5y, 2),
                        'week_52_high': round(week_52_high, 2),
                        'week_52_low': round(week_52_low, 2),
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
            
            # Calculate 52-week high and low
            week_52_high = data['High'].tail(252).max() if len(data) >= 252 else data['High'].max()
            week_52_low = data['Low'].tail(252).min() if len(data) >= 252 else data['Low'].min()
            
            # Step 1: Find historical volume breakouts in recent data
            volume_breakout_days = []
            
            for i in range(len(recent_data)):
                day_volume = recent_data['Volume'].iloc[i]
                day_close = recent_data['Close'].iloc[i]
                day_low = recent_data['Low'].iloc[i]
                day_high = recent_data['High'].iloc[i]
                day_date = recent_data.index[i]
                
                if i > 0:
                    prev_close = recent_data['Close'].iloc[i-1]
                    price_change = ((day_close - prev_close) / prev_close) * 100
                    volume_ratio = day_volume / avg_volume_90d
                    
                    # Identify significant volume breakouts (5x+ volume with positive price)
                    if volume_ratio >= 5.0 and price_change > 2.0:
                        volume_breakout_days.append({
                            'index': i,
                            'date': day_date,
                            'breakout_price': day_close,
                            'breakout_low': day_low,
                            'breakout_high': day_high,
                            'volume_ratio': volume_ratio,
                            'price_change': price_change
                        })
            
            if not volume_breakout_days:
                return {'is_volume_breakout': False, 'error': 'No significant volume breakouts found'}
            
            # Step 2: Check for retracement back to breakout levels
            for breakout in volume_breakout_days:
                breakout_price = breakout['breakout_price']
                breakout_low = breakout['breakout_low']
                breakout_date = breakout['date']
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
                
                # Check if current price is near breakout low (radar condition)
                near_breakout_low = abs(current_price - breakout_low) / breakout_low <= 0.02  # Within 2%
                
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
                                'breakout_date': breakout_date.strftime('%Y-%m-%d'),
                                'breakout_price': round(breakout_price, 2),
                                'breakout_low': round(breakout_low, 2),
                                'breakout_high': round(breakout['breakout_high'], 2),
                                'breakout_volume_ratio': round(breakout['volume_ratio'], 2),
                                'breakout_price_change': round(breakout['price_change'], 2),
                                'current_price': round(current_price, 2),
                                'retracement_percent': round(abs(retracement_percent), 2),
                                'days_since_breakout': days_since_breakout,
                                'pullback_depth_percent': round(pullback_depth, 2),
                                'max_price_after_breakout': round(max_price_after_breakout, 2),
                                'pattern_type': 'Volume Breakout with Retracement',
                                'week_52_high': round(week_52_high, 2),
                                'week_52_low': round(week_52_low, 2),
                                'near_breakout_low': near_breakout_low,
                                'radar_trigger_price': round(breakout_low, 2),
                                'radar_status': 'Active' if near_breakout_low else 'Monitoring'
                            }
            
            return {'is_volume_breakout': False, 'error': 'No valid retracement patterns found'}
            
        except Exception as e:
            logger.error(f"Error checking volume breakout: {e}")
            return {'is_volume_breakout': False, 'error': str(e)}
    
    def get_macro_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Download maximum historical data for Elliott Wave macro analysis"""
        try:
            ticker_symbol = f"{symbol}.NS"
            ticker = yf.Ticker(ticker_symbol)
            
            # Download maximum available data (5-10 years)
            for attempt in range(3):
                try:
                    data = ticker.history(period="max", interval="1wk")  # Weekly data
                    if not data.empty and len(data) >= 200:  # Need at least 4 years of weekly data
                        logger.info(f"Successfully downloaded macro data for {symbol}: {len(data)} weeks")
                        return data
                    else:
                        logger.warning(f"Insufficient macro data for {symbol}, attempt {attempt + 1}")
                except Exception as e:
                    logger.warning(f"Macro data attempt {attempt + 1} failed for {symbol}: {e}")
                    if attempt < 2:
                        time.sleep(1)
            
            logger.error(f"Failed to download macro data for {symbol} after 3 attempts")
            return None
            
        except Exception as e:
            logger.error(f"Error downloading macro data for {symbol}: {e}")
            return None
    
    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI indicator"""
        try:
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi
        except Exception as e:
            logger.error(f"Error calculating RSI: {e}")
            return pd.Series()
    
    def calculate_emas(self, data: pd.DataFrame) -> dict:
        """Calculate 50 EMA and 200 EMA for a given stock data"""
        try:
            if data.empty or len(data) < 200:
                return {"ema50": None, "ema200": None}
            
            # Calculate EMAs - get the last value
            ema50_series = data['Close'].ewm(span=50, adjust=False).mean()
            ema200_series = data['Close'].ewm(span=200, adjust=False).mean()
            
            ema50 = ema50_series.iloc[-1]
            ema200 = ema200_series.iloc[-1]
            
            return {
                "ema50": round(float(ema50), 2) if pd.notna(ema50) else None,
                "ema200": round(float(ema200), 2) if pd.notna(ema200) else None
            }
        except Exception as e:
            logger.error(f"Error calculating EMAs: {e}")
            return {"ema50": None, "ema200": None}
    
    def detect_trendline(self, price_data: pd.DataFrame, timeframe: str) -> Optional[Dict]:
        """Detect ascending trendline from price data
        
        Args:
            price_data: DataFrame with OHLC data
            timeframe: 'Weekly' or 'Monthly'
            
        Returns:
            Dictionary with trendline data or None if no valid trendline found
        """
        try:
            if len(price_data) < 12:  # Need minimum data
                return None
            
            lows = price_data['Low'].values
            dates = price_data.index
            current_price = price_data['Close'].iloc[-1]
            
            # Use longer analysis period for better trendline detection
            analysis_period = min(len(price_data), 104 if timeframe == 'Weekly' else 36)  # 2 years
            analysis_data = price_data.tail(analysis_period)
            
            # Find significant lows (local minima)
            window = 3 if timeframe == 'Weekly' else 2
            significant_lows = []
            
            for i in range(window, len(analysis_data) - window):
                current_low = analysis_data['Low'].iloc[i]
                current_date = analysis_data.index[i]
                
                # Check if this is a local minimum
                surrounding_lows = analysis_data['Low'].iloc[i-window:i+window+1]
                if current_low == surrounding_lows.min():
                    # Must be significant (at least 5% below recent highs)
                    recent_high = analysis_data['High'].iloc[max(0, i-8):i+8].max()
                    if current_low <= recent_high * 0.95:
                        significant_lows.append({
                            'price': current_low,
                            'date': current_date,
                            'index': i
                        })
            
            if len(significant_lows) < 3:
                return None
            
            # Sort by date
            significant_lows.sort(key=lambda x: x['date'])
            
            # Try different combinations to find best ascending trendline
            best_trendline = None
            best_score = 0
            
            for i in range(len(significant_lows) - 2):
                for j in range(i + 2, len(significant_lows)):
                    low1 = significant_lows[i]
                    low2 = significant_lows[j]
                    
                    # Calculate slope
                    time_diff_days = (low2['date'] - low1['date']).days
                    if time_diff_days < (56 if timeframe == 'Weekly' else 180):  # Min 8 weeks or 6 months
                        continue
                    
                    price_diff = low2['price'] - low1['price']
                    slope = price_diff / time_diff_days  # Price change per day
                    
                    if slope <= 0:  # Must be ascending
                        continue
                    
                    # Project to current date
                    current_days_from_low1 = (dates[-1] - low1['date']).days
                    current_trendline_price = slope * current_days_from_low1 + low1['price']
                    
                    # Check if current price is within ±5% of trendline
                    distance_percent = ((current_price - current_trendline_price) / current_trendline_price) * 100
                    
                    if not (-5.0 <= distance_percent <= 5.0):
                        continue
                    
                    # Score based on touches and consistency
                    touches = 0
                    total_deviation = 0
                    
                    for low in significant_lows:
                        days_from_low1 = (low['date'] - low1['date']).days
                        expected_price = slope * days_from_low1 + low1['price']
                        deviation = abs(low['price'] - expected_price) / expected_price
                        
                        if deviation <= 0.03:  # Within 3%
                            touches += 1
                        
                        total_deviation += deviation
                    
                    # Calculate score
                    avg_deviation = total_deviation / len(significant_lows)
                    proximity_score = max(0, 5 - abs(distance_percent))
                    touch_score = touches * 2
                    consistency_score = max(0, 1 - avg_deviation) * 10
                    
                    total_score = proximity_score + touch_score + consistency_score
                    
                    if total_score > best_score and touches >= 3:
                        best_score = total_score
                        best_trendline = {
                            'low1': low1,
                            'low2': low2,
                            'slope': slope,
                            'current_trendline_price': current_trendline_price,
                            'distance_percent': distance_percent,
                            'touches': touches,
                            'avg_deviation': avg_deviation,
                            'score': total_score,
                            'timeframe_days': current_days_from_low1
                        }
            
            if not best_trendline:
                return None
            
            # Build result
            trendline_strength = min(100, (best_trendline['touches'] * 20) + (best_trendline['score'] * 5))
            
            return {
                'trendline_price': round(best_trendline['current_trendline_price'], 2),
                'distance_to_trendline_percent': round(best_trendline['distance_percent'], 2),
                'trendline_slope_daily': round(best_trendline['slope'], 6),
                'trendline_start_price': round(best_trendline['low1']['price'], 2),
                'trendline_start_date': best_trendline['low1']['date'].strftime('%Y-%m-%d'),
                'trendline_end_price': round(best_trendline['low2']['price'], 2),
                'trendline_end_date': best_trendline['low2']['date'].strftime('%Y-%m-%d'),
                'timeframe_days': round(best_trendline['timeframe_days'], 1),
                'timeframe_months': round(best_trendline['timeframe_days'] / 30.44, 1),
                'trendline_touches': best_trendline['touches'],
                'trendline_strength': round(trendline_strength, 1)
            }
            
        except Exception as e:
            logger.error(f"Error detecting {timeframe} trendline: {e}")
            return None
    
    def detect_golden_stocks_combined(self, data: pd.DataFrame, weekly_data: pd.DataFrame) -> Dict:
        """Combined Golden Stocks analysis - Trendline + Fibonacci + Vertical Line analysis
        
        Analyzes both weekly and monthly timeframes for trendline detection
        """
        try:
            if len(weekly_data) < 52:  # Need at least 1 year of weekly data
                return {'is_golden_stock': False, 'error': 'Insufficient weekly data'}
            
            closes = weekly_data['Close'].values
            lows = weekly_data['Low'].values
            highs = weekly_data['High'].values
            dates = weekly_data.index
            current_price = closes[-1]
            
            # Calculate 52-week high and low
            week_52_high = max(highs[-52:]) if len(highs) >= 52 else max(highs)
            week_52_low = min(lows[-52:]) if len(lows) >= 52 else min(lows)
            
            # Calculate 200 EMA on weekly data
            ema_200 = None
            if len(weekly_data) >= 200:
                ema_200 = weekly_data['Close'].ewm(span=200, adjust=False).mean().iloc[-1]
            
            # First check Fibonacci levels from daily data
            fib_result = self.calculate_fibonacci_levels(data)
            
            # Detect trendlines on both weekly and monthly timeframes
            weekly_trendline = self.detect_trendline(weekly_data, 'Weekly')
            
            # Create monthly data from weekly
            monthly_data = weekly_data.resample('ME').agg({
                'Open': 'first',
                'High': 'max',
                'Low': 'min',
                'Close': 'last',
                'Volume': 'sum'
            }).dropna()
            
            monthly_trendline = None
            if len(monthly_data) >= 24:  # Need at least 2 years of monthly data
                monthly_trendline = self.detect_trendline(monthly_data, 'Monthly')
            
            
            # Determine which trendline to use (prefer the one closer to current price)
            has_trendline = False
            trendline_data = {}
            
            if weekly_trendline and monthly_trendline:
                # Both available - prioritize monthly timeframe
                has_trendline = True
                trendline_data = monthly_trendline
                trendline_data['primary_timeframe'] = 'Monthly'
                trendline_data['secondary_trendline_price'] = weekly_trendline['current_trendline_price']
                trendline_data['secondary_timeframe'] = 'Weekly'
            elif monthly_trendline:
                has_trendline = True
                trendline_data = monthly_trendline
                trendline_data['primary_timeframe'] = 'Monthly'
            elif weekly_trendline:
                has_trendline = True
                trendline_data = weekly_trendline
                trendline_data['primary_timeframe'] = 'Weekly'
            
            # Initialize has_fibonacci
            has_fibonacci = fib_result.get('is_near_fibonacci', False)
            
            # Must have Trendline (Fibonacci is optional)
            if not has_trendline:
                return {'is_golden_stock': False, 'error': 'Requires Trendline signal'}
            
            # Determine overall entry quality
            if has_fibonacci:
                if (abs(trendline_data.get('distance_to_trendline_percent', 100)) <= 2.0 and 
                    abs(fib_result.get('distance_percent', 100)) <= 1.0):
                    entry_quality = 'Excellent - Trendline + Fibonacci Confluence'
                else:
                    entry_quality = 'Good - Trendline + Fibonacci'
            else:
                if abs(trendline_data.get('distance_to_trendline_percent', 100)) <= 2.0:
                    entry_quality = 'Good - Trendline Only'
                else:
                    entry_quality = 'Fair - Trendline Only'
            
            # Calculate potential upside to recent high
            potential_upside = ((week_52_high - current_price) / current_price) * 100
            
            # Build result
            result = {
                'is_golden_stock': True,
                'current_price': round(current_price, 2),
                'week_52_high': round(week_52_high, 2),
                'week_52_low': round(week_52_low, 2),
                'ema_200': round(ema_200, 2) if ema_200 else None,
                'potential_upside_percent': round(potential_upside, 2),
                'entry_quality': entry_quality,
                'has_fibonacci': has_fibonacci,
                'has_trendline': has_trendline,
                'analysis_timeframe': 'Weekly + Monthly + Daily',
                'pattern_type': 'Golden Stock Analysis'
            }
            
            # Add Fibonacci data if present
            if has_fibonacci:
                result.update({
                    'fibonacci_level': fib_result['level'],
                    'fibonacci_level_price': fib_result['level_price'],
                    'fibonacci_distance_percent': fib_result['distance_percent'],
                    'fibonacci_high_5y': fib_result['high_5y'],
                    'fibonacci_low_5y': fib_result['low_5y']
                })
            
            # Add trendline data if present
            if has_trendline:
                result.update(trendline_data)
                # Add both weekly and monthly trendline prices if available
                if 'secondary_trendline_price' in trendline_data:
                    if trendline_data['primary_timeframe'] == 'Weekly':
                        result['weekly_trendline_price'] = trendline_data['trendline_price']
                        result['monthly_trendline_price'] = trendline_data['secondary_trendline_price']
                    else:
                        result['monthly_trendline_price'] = trendline_data['trendline_price']
                        result['weekly_trendline_price'] = trendline_data['secondary_trendline_price']
                else:
                    # Only one timeframe available
                    if trendline_data.get('primary_timeframe') == 'Weekly':
                        result['weekly_trendline_price'] = trendline_data['trendline_price']
                        result['monthly_trendline_price'] = None
                    else:
                        result['monthly_trendline_price'] = trendline_data['trendline_price']
                        result['weekly_trendline_price'] = None
            
            # Add Vertical Line analysis to Golden Stocks (OPTIONAL - just for entry price info)
            try:
                vertical_result = self.detect_vertical_line_pattern(weekly_data)
                if vertical_result.get('is_vertical_line', False):
                    result['has_vertical_line'] = True
                    result['vertical_line_price'] = vertical_result['vertical_line_price']
                    result['vertical_line_touch_count'] = vertical_result['touch_count']
                    result['vertical_line_signal'] = vertical_result['signal_strength']
                    result['vertical_line_entry_trigger'] = vertical_result['entry_trigger_price']
                    result['vertical_line_distance_percent'] = vertical_result['distance_to_trigger_abs_percent']
                    result['vertical_line_alert_status'] = vertical_result['alert_status']
                    result['vertical_line_position'] = vertical_result['position_vs_trigger']
                    result['vertical_line_target_price'] = vertical_result['target_price_20_percent']
                else:
                    result['has_vertical_line'] = False
                    result['vertical_line_price'] = None
            except Exception as e:
                logger.warning(f"Vertical line analysis failed in Golden Stocks: {e}")
                result['has_vertical_line'] = False
                result['vertical_line_price'] = None
            
            return result
            
        except Exception as e:
            logger.error(f"Error detecting Golden Stocks combined: {e}")
            return {'is_golden_stock': False, 'error': str(e)}
    
    def detect_vertical_line_pattern(self, weekly_data: pd.DataFrame) -> Dict:
        """Detect Vertical Line Pattern - Horizontal support/resistance with multiple touches
        
        This detects horizontal price levels that have been tested multiple times (like the 
        screenshots show - Lupin at 601, BEML at 1200-1300, etc.). These levels act as 
        entry trigger points when price returns to touch them.
        
        Alert Threshold: Within 10% of the vertical line touch point price
        """
        try:
            if len(weekly_data) < 52:  # Need at least 1 year of weekly data
                return {'is_vertical_line': False, 'error': 'Insufficient weekly data'}
            
            closes = weekly_data['Close'].values
            lows = weekly_data['Low'].values
            highs = weekly_data['High'].values
            dates = weekly_data.index
            current_price = closes[-1]
            
            # Calculate 52-week high and low
            week_52_high = max(highs[-52:]) if len(highs) >= 52 else max(highs)
            week_52_low = min(lows[-52:]) if len(lows) >= 52 else min(lows)
            
            # Look for vertical line pattern (significant support/resistance levels)
            # Analyze longer period for better pattern detection (3-5 years if available)
            analysis_period = min(260, len(weekly_data))  # Up to 5 years of weekly data
            analysis_data = weekly_data.tail(analysis_period)
            
            # Find significant price levels (horizontal support/resistance)
            price_levels = []
            tolerance = 0.03  # 3% tolerance for level matching (increased for better grouping)
            
            # Collect all significant highs and lows (local extrema)
            window = 5  # Look at 5 weeks on each side
            for i in range(window, len(analysis_data) - window):
                current_high = analysis_data['High'].iloc[i]
                current_low = analysis_data['Low'].iloc[i]
                current_date = analysis_data.index[i]
                
                # Check if this is a significant high or low
                surrounding_highs = analysis_data['High'].iloc[i-window:i+window+1]
                surrounding_lows = analysis_data['Low'].iloc[i-window:i+window+1]
                
                # Local maximum (resistance)
                if current_high == surrounding_highs.max():
                    price_levels.append({
                        'price': current_high,
                        'type': 'resistance',
                        'date': current_date,
                        'touches': 1
                    })
                
                # Local minimum (support)
                if current_low == surrounding_lows.min():
                    price_levels.append({
                        'price': current_low,
                        'type': 'support',
                        'date': current_date,
                        'touches': 1
                    })
            
            # Group similar price levels and count touches
            consolidated_levels = []
            for level in price_levels:
                found_similar = False
                for existing in consolidated_levels:
                    if abs(level['price'] - existing['price']) / existing['price'] <= tolerance:
                        existing['touches'] += 1
                        existing['dates'].append(level['date'])
                        # Update average price for the level
                        existing['price'] = (existing['price'] * (existing['touches'] - 1) + level['price']) / existing['touches']
                        found_similar = True
                        break
                
                if not found_similar:
                    consolidated_levels.append({
                        'price': level['price'],
                        'type': level['type'],
                        'touches': 1,
                        'dates': [level['date']],
                        'first_touch': level['date']
                    })
            
            # Find levels with multiple touches (Touch 2 or more) - this is the key pattern
            significant_levels = [level for level in consolidated_levels if level['touches'] >= 2]
            
            if not significant_levels:
                return {'is_vertical_line': False, 'error': 'No significant vertical line levels found'}
            
            # Find the most relevant level for current price - ALERT WITHIN 10%
            best_level = None
            min_distance = float('inf')
            alert_threshold = 0.10  # 10% alert threshold
            
            for level in significant_levels:
                distance = abs(current_price - level['price']) / level['price']
                
                # Check if current price is within 10% of the level (ALERT ZONE)
                if distance <= alert_threshold and distance < min_distance:
                    min_distance = distance
                    best_level = level
            
            if not best_level:
                return {'is_vertical_line': False, 'error': 'No relevant vertical line level within 10% of current price'}
            
            # Calculate entry trigger price (the vertical line touch point)
            entry_trigger_price = best_level['price']
            
            # Calculate 20% upside target from entry trigger
            target_price = entry_trigger_price * 1.20
            upside_potential = ((target_price - current_price) / current_price) * 100
            
            # Determine touch count and trigger status
            touch_number = best_level['touches']
            is_touch_2_or_more = touch_number >= 2
            
            # Calculate distance to entry trigger (vertical line touch point)
            distance_percent = ((current_price - entry_trigger_price) / entry_trigger_price) * 100
            distance_abs_percent = abs(distance_percent)
            
            # Determine signal strength based on proximity to entry trigger
            if distance_abs_percent <= 2.0:
                signal_strength = 'EXCELLENT - At Entry Trigger'
                alert_status = '🔥 IMMEDIATE ENTRY ZONE'
            elif distance_abs_percent <= 5.0:
                signal_strength = 'VERY GOOD - Near Entry Trigger'
                alert_status = '⚡ CLOSE TO ENTRY'
            elif distance_abs_percent <= 10.0:
                signal_strength = 'GOOD - Approaching Entry Trigger'
                alert_status = '📍 WATCH ZONE'
            else:
                signal_strength = 'MONITORING'
                alert_status = '👀 MONITORING'
            
            # Determine if price is above or below trigger
            position_vs_trigger = 'ABOVE' if current_price > entry_trigger_price else 'BELOW'
            
            return {
                'is_vertical_line': True,
                'current_price': round(current_price, 2),
                'vertical_line_price': round(entry_trigger_price, 2),  # This is the ENTRY TRIGGER
                'entry_trigger_price': round(entry_trigger_price, 2),  # Explicit entry trigger field
                'level_type': best_level['type'],
                'touch_count': touch_number,
                'is_touch_2_trigger': is_touch_2_or_more,
                'distance_to_trigger_percent': round(distance_percent, 2),
                'distance_to_trigger_abs_percent': round(distance_abs_percent, 2),
                'position_vs_trigger': position_vs_trigger,
                'target_price_20_percent': round(target_price, 2),
                'upside_potential_percent': round(upside_potential, 2),
                'first_touch_date': best_level['first_touch'].strftime('%Y-%m-%d'),
                'last_touch_date': best_level['dates'][-1].strftime('%Y-%m-%d'),
                'signal_strength': signal_strength,
                'alert_status': alert_status,
                'week_52_high': round(week_52_high, 2),
                'week_52_low': round(week_52_low, 2),
                'analysis_timeframe': 'Weekly',
                'pattern_type': 'Vertical Line Entry Trigger',
                'all_touch_dates': [d.strftime('%Y-%m-%d') for d in best_level['dates']]
            }
            
        except Exception as e:
            logger.error(f"Error detecting Vertical Line pattern: {e}")
            return {'is_vertical_line': False, 'error': str(e)}
    
    
    def screen_stock(self, symbol: str, company_name: str, industry: str) -> None:
        """Screen a single stock for all conditions"""
        try:
            self.results['diagnostics']['total_stocks_processed'] += 1
            
            # Download daily stock data with timeout
            data = self.get_stock_data(symbol)
            if data is None or data.empty:
                self.results['diagnostics']['failed_downloads'] += 1
                return
            
            self.results['diagnostics']['successful_downloads'] += 1
            
            # Get weekly data once for all analyses that need it
            weekly_data = self.get_weekly_data(symbol)
            
            # Get vertical line price for all patterns (if weekly data available)
            vertical_line_price = None
            if weekly_data is not None and not weekly_data.empty:
                try:
                    vertical_result = self.detect_vertical_line_pattern(weekly_data)
                    if vertical_result.get('is_vertical_line', False):
                        vertical_line_price = vertical_result.get('vertical_line_price')
                except Exception as e:
                    logger.warning(f"Vertical line detection failed for {symbol}: {e}")
            
            # Note: Fibonacci analysis is now combined with Golden Stocks
            # Check volume breakout
            try:
                volume_result = self.check_volume_breakout(data)
                if volume_result.get('is_volume_breakout', False):
                    # Calculate EMAs for volume breakout stocks
                    emas = self.calculate_emas(data)
                    
                    stock_info = {
                        'symbol': symbol,
                        'company_name': company_name,
                        'industry': industry,
                        'vertical_line_price': vertical_line_price,  # Add vertical line price
                        'ema50': emas.get('ema50'),
                        'ema200': emas.get('ema200'),
                        **volume_result
                    }
                    self.results['volume_breakout_stocks'].append(stock_info)
                    self.results['diagnostics']['volume_breakout_matches'] += 1
                    logger.info(f"Volume breakout: {symbol} with {volume_result.get('breakout_volume_ratio', 'N/A')}x volume")
            except Exception as e:
                logger.warning(f"Volume breakout analysis failed for {symbol}: {e}")
            
            # Check Golden Stocks - Separate Weekly and Monthly
            try:
                # Use weekly data for combined analysis
                if weekly_data is not None and not weekly_data.empty:
                    golden_result = self.detect_golden_stocks_combined(data, weekly_data)
                    if golden_result.get('is_golden_stock', False):
                        stock_info = {
                            'symbol': symbol,
                            'company_name': company_name,
                            'industry': industry,
                            **golden_result
                        }
                        
                        # Add to unified golden_stocks array
                        self.results['golden_stocks'].append(stock_info)
                        self.results['diagnostics']['golden_matches'] += 1
                        
                        # Get trendline touch point and distance
                        trendline_price = golden_result.get('trendline_price', 0)
                        current_price = golden_result.get('current_price', 0)
                        distance_to_trendline = golden_result.get('distance_to_trendline_percent', 0)
                        timeframe = golden_result.get('primary_timeframe', 'Weekly')
                        
                        # Determine alert status based on distance to trendline
                        if abs(distance_to_trendline) <= 2.0:
                            alert = "🔥 AT ENTRY"
                        elif abs(distance_to_trendline) <= 5.0:
                            alert = "⚡ NEAR ENTRY"
                        elif abs(distance_to_trendline) <= 10.0:
                            alert = "📍 WATCH"
                        else:
                            alert = "👀 MONITOR"
                        
                        logger.info(f"Golden Stock ({timeframe}) match: {symbol} | Entry: ₹{trendline_price:.2f} | Current: ₹{current_price:.2f} | Distance: {distance_to_trendline:+.1f}% | {alert}")
            except Exception as e:
                logger.warning(f"Golden Stocks analysis failed for {symbol}: {e}")
            
            # Rate limiting to avoid overwhelming the API - increased delay
            time.sleep(0.5)  # Increased from 0.1 to 0.5 seconds
            
        except Exception as e:
            logger.error(f"Error screening {symbol}: {e}")
            self.results['diagnostics']['errors'].append(f"Error screening {symbol}: {e}")
            self.results['diagnostics']['failed_downloads'] += 1
    
    def run_screening(self) -> None:
        """Run the complete screening process"""
        logger.info("Starting stock screening process...")
        
        # Load stock universe
        stocks_df = self.load_stock_universe()
        if stocks_df.empty:
            logger.error("No stocks to process")
            return
        
        # Process each stock - revert to original working version
        total_stocks = len(stocks_df)
        logger.info(f"Processing {total_stocks} stocks")
        
        for idx, row in stocks_df.iterrows():
            symbol = row['Symbol']
            company_name = row['Company Name']
            industry = row['Industry']
            
            logger.info(f"Processing {idx + 1}/{total_stocks}: {symbol}")
            self.screen_stock(symbol, company_name, industry)
            
            # Progress update every 50 stocks
            if (idx + 1) % 50 == 0:
                logger.info(f"Progress: {idx + 1}/{total_stocks} stocks processed")
        
        # Sort results by priority after screening
        self.sort_results()
        
        logger.info("Screening process completed")
        self.log_summary()
    
    def sort_results(self) -> None:
        """Sort all results by priority - most relevant opportunities first"""
        try:
            # Note: Fibonacci is now combined with Golden Stocks, so no separate sorting needed
            
            # Sort Volume Breakout stocks: Radar Active first, then by proximity to breakout low
            self.results['volume_breakout_stocks'].sort(key=lambda x: (
                0 if x.get('radar_status') == 'Active' else 1,  # Radar Active first
                abs(x.get('current_price', 0) - x.get('radar_trigger_price', 0))  # Closer to trigger price
            ))
            
            # Sort Golden Stocks: Double signals first, then by entry quality, then by proximity
            self.results['golden_stocks'].sort(key=lambda x: (
                0 if 'Double Signal' in x.get('entry_quality', '') else 1,  # Double signals first
                0 if x.get('entry_quality', '').startswith('Excellent') else 1 if x.get('entry_quality', '').startswith('Good') else 2,  # Quality priority
                abs(x.get('fibonacci_distance_percent', x.get('distance_to_trendline_percent', 100))),  # Closer to signal
                -x.get('trendline_strength', 0)  # Stronger trendlines first (negative for descending sort)
            ))
            
            logger.info("Results sorted by priority")
            
        except Exception as e:
            logger.error(f"Error sorting results: {e}")
            # Continue without sorting if there's an error
    
    def log_summary(self) -> None:
        """Log screening summary"""
        diag = self.results['diagnostics']
        logger.info(f"""
        Screening Summary:
        - Total stocks processed: {diag['total_stocks_processed']}
        - Successful downloads: {diag['successful_downloads']}
        - Failed downloads: {diag['failed_downloads']}
        - Golden Stocks matches: {diag['golden_matches']} (Fibonacci + Trendline + Vertical Line)
        - Volume breakout matches: {diag['volume_breakout_matches']}
        - Errors: {len(diag['errors'])}
        """)
    
    def save_results(self) -> None:
        """Save results to JSON file"""
        try:
            # Convert NaN values to None for JSON serialization
            import json
            import numpy as np
            
            def convert_nan(obj):
                if isinstance(obj, dict):
                    return {k: convert_nan(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_nan(item) for item in obj]
                elif isinstance(obj, float) and np.isnan(obj):
                    return None
                elif isinstance(obj, np.bool_):
                    return bool(obj)
                else:
                    return obj
            
            clean_results = convert_nan(self.results)
            
            with open('data.json', 'w') as f:
                json.dump(clean_results, f, indent=2)
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
            golden_count = len(self.results['golden_stocks'])
            vol_count = len(self.results['volume_breakout_stocks'])
            
            # Count radar alerts
            vol_radar_active = sum(1 for stock in self.results['volume_breakout_stocks'] 
                                 if stock.get('radar_status') == 'Active')
            
            total_processed = self.results['diagnostics']['total_stocks_processed']
            
            message = f"""🔍 *Stock Yard Daily Screening Report*
📅 {datetime.now().strftime('%Y-%m-%d %H:%M IST')}

📊 *Results Summary:*
• Total Stocks Screened: {total_processed}
• Golden Stocks: {golden_count} matches
• Volume Breakout: {vol_count} matches

🚨 *RADAR ALERTS:*
• Volume Stocks in Radar: {vol_radar_active}
• W-Pattern Stocks in Radar: {w_radar_active}

📱 *View Full Report:*
https://anuragsin17-sketch.github.io/Stock-Yard-Public/

_Automated screening completed successfully_"""
            
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
    
    try:
        # Check if stock universe file exists
        import os
        available_files = [f for f in os.listdir('.') if 'nifty' in f.lower() and f.endswith('.csv')]
        logger.info(f"Available NIFTY files: {available_files}")
        
        if not available_files:
            logger.error("No NIFTY CSV files found in current directory")
            logger.info("Current directory contents:")
            for item in os.listdir('.'):
                logger.info(f"  - {item}")
            # Don't return here, let the screener try to create test data
        
        screener = StockScreener()
        screener.run_screening()
        screener.save_results()
        screener.send_telegram_notification()
        
        logger.info("Stock Yard Screener Completed!")
        
    except Exception as e:
        logger.error(f"Critical error in main execution: {e}")
        # Create minimal fallback data
        fallback_data = {
            'timestamp': datetime.now().isoformat(),
            'golden_stocks': [],
            'volume_breakout_stocks': [],
            'diagnostics': {
                'total_stocks_processed': 0,
                'successful_downloads': 0,
                'failed_downloads': 0,
                'golden_matches': 0,
                'volume_breakout_matches': 0,
                'errors': [f"Critical error: {e}"]
            }
        }
        
        try:
            with open('data.json', 'w') as f:
                json.dump(fallback_data, f, indent=2)
            logger.info("Fallback data.json created")
        except Exception as save_error:
            logger.error(f"Failed to save fallback data: {save_error}")
        
        # Don't raise the exception, let the workflow continue

if __name__ == "__main__":
    try:
        # Run the main screener
        main()
        
        logger.info("✅ Stock Yard Screener Completed!")
        
    except Exception as e:
        logger.error(f"Error in main execution: {e}")
        # Create minimal fallback data instead of raising
        try:
            fallback_data = {
                'timestamp': datetime.now().isoformat(),
                'golden_stocks': [],
                'volume_breakout_stocks': [],
                'diagnostics': {
                    'total_stocks_processed': 0,
                    'successful_downloads': 0,
                    'failed_downloads': 0,
                    'golden_matches': 0,
                    'volume_breakout_matches': 0,
                    'errors': [f"Main execution error: {e}"]
                }
            }
            
            with open('data.json', 'w') as f:
                json.dump(fallback_data, f, indent=2)
            logger.info("Fallback data.json created due to main execution error")
            
            # Also create empty positions.json
            with open('positions.json', 'w') as f:
                json.dump({'open_positions': [], 'closed_positions': []}, f, indent=2)
            logger.info("Created empty positions.json")
            
        except Exception as save_error:
            logger.error(f"Failed to save fallback data: {save_error}")
        
        # Don't raise - let workflow continue with fallback data