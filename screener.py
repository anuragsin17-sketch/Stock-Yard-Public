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
            'golden_stocks': [],  # Combined Fibonacci + Trendline + Vertical Line
            'volume_breakout_stocks': [],
            'w_pattern_stocks': [],
            'elliott_wave_stocks': [],
            'darvas_box_stocks': [],  # Darvas Box analysis
            'diagnostics': {
                'total_stocks_processed': 0,
                'successful_downloads': 0,
                'failed_downloads': 0,
                'golden_matches': 0,
                'volume_breakout_matches': 0,
                'w_pattern_matches': 0,
                'elliott_wave_matches': 0,
                'darvas_box_matches': 0,
                'errors': []
            }
        }
    
    def load_stock_universe(self) -> pd.DataFrame:
        """Load the NIFTY stock list"""
        try:
            # Try different possible file names - prioritize NIFTY 500 list
            possible_files = ['ind_nifty500list.csv', 'ind_nifty200list.csv', 'ind_nifty50list.csv', 'ind_nifty500list.xlsx', 'nifty500.csv', 'nifty50.csv']
            
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
            
            # Check if current price is within 1.5% of key levels
            tolerance = 0.015  # 1.5%
            
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
    
    def detect_w_pattern(self, weekly_data: pd.DataFrame) -> Dict:
        """Detect Weekly W-Pattern (Double Bottom) formation"""
        try:
            if len(weekly_data) < 20:  # Need at least 20 weeks of data
                return {'is_w_pattern': False, 'error': 'Insufficient weekly data'}
            
            closes = weekly_data['Close'].values
            lows = weekly_data['Low'].values
            highs = weekly_data['High'].values
            
            # Calculate 52-week high and low
            week_52_high = max(highs) if len(highs) >= 52 else max(highs)
            week_52_low = min(lows) if len(lows) >= 52 else min(lows)
            
            # Find local minima and maxima using a rolling window approach
            window = 3  # Look for peaks/troughs over 3-week periods
            
            # Identify potential troughs (local minima)
            troughs = []
            for i in range(window, len(lows) - window):
                if lows[i] == min(lows[i-window:i+window+1]):
                    troughs.append((i, lows[i], weekly_data.index[i]))
            
            # Identify potential peaks (local maxima) 
            peaks = []
            for i in range(window, len(highs) - window):
                if highs[i] == max(highs[i-window:i+window+1]):
                    peaks.append((i, highs[i], weekly_data.index[i]))
            
            if len(troughs) < 2 or len(peaks) < 1:
                return {'is_w_pattern': False, 'error': 'Insufficient pivot points'}
            
            # Look for W-pattern in the most recent data (last 6 months)
            recent_weeks = min(26, len(weekly_data))  # 6 months or available data
            start_idx = len(weekly_data) - recent_weeks
            
            # Filter pivots to recent period
            recent_troughs = [(i, price, date) for i, price, date in troughs if i >= start_idx]
            recent_peaks = [(i, price, date) for i, price, date in peaks if i >= start_idx]
            
            if len(recent_troughs) < 2:
                return {'is_w_pattern': False, 'error': 'No recent double bottom pattern'}
            
            # Find the best W-pattern candidate
            current_price = closes[-1]
            
            for i in range(len(recent_troughs) - 1):
                t1_idx, t1_price, t1_date = recent_troughs[i]
                
                for j in range(i + 1, len(recent_troughs)):
                    t2_idx, t2_price, t2_date = recent_troughs[j]
                    
                    # Find peak between the two troughs
                    intermediate_peaks = [p for p in recent_peaks if t1_idx < p[0] < t2_idx]
                    if not intermediate_peaks:
                        continue
                    
                    # Get the highest peak between troughs
                    p1_idx, p1_price, p1_date = max(intermediate_peaks, key=lambda x: x[1])
                    
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
                    
                    # Determine which trough is lower for radar tracking
                    lower_trough_price = min(t1_price, t2_price)
                    lower_trough_date = t1_date if t1_price <= t2_price else t2_date
                    
                    # Check if current price is near the lower trough (radar condition)
                    near_trough_low = abs(current_price - lower_trough_price) / lower_trough_price <= 0.02  # Within 2%
                    
                    # Valid W-pattern found
                    return {
                        'is_w_pattern': True,
                        'left_trough_price': round(t1_price, 2),
                        'left_trough_date': t1_date.strftime('%Y-%m-%d'),
                        'right_trough_price': round(t2_price, 2),
                        'right_trough_date': t2_date.strftime('%Y-%m-%d'),
                        'neckline_peak_price': round(p1_price, 2),
                        'neckline_peak_date': p1_date.strftime('%Y-%m-%d'),
                        'current_price': round(current_price, 2),
                        'distance_to_neckline_percent': round(distance_to_neckline, 2),
                        't2_vs_t1_percent': round(t2_vs_t1_percent, 2),
                        'recovery_from_t2_percent': round(recovery_from_t2, 2),
                        'pattern_timeframe_weeks': t2_idx - t1_idx + 1,
                        'week_52_high': round(week_52_high, 2),
                        'week_52_low': round(week_52_low, 2),
                        'lower_trough_price': round(lower_trough_price, 2),
                        'lower_trough_date': lower_trough_date.strftime('%Y-%m-%d'),
                        'radar_trigger_price': round(lower_trough_price, 2),
                        'near_trough_low': near_trough_low,
                        'radar_status': 'Active' if near_trough_low else 'Monitoring'
                    }
            
            return {'is_w_pattern': False, 'error': 'No valid W-pattern found in recent data'}
            
        except Exception as e:
            logger.error(f"Error detecting W-pattern: {e}")
            return {'is_w_pattern': False, 'error': str(e)}
    
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
    
    def detect_elliott_wave_macro(self, macro_data: pd.DataFrame) -> Dict:
        """Detect Elliott Wave macro setup with Golden Pocket analysis"""
        try:
            if len(macro_data) < 200:  # Need at least 4 years of weekly data
                return {'is_elliott_wave': False, 'error': 'Insufficient macro data'}
            
            closes = macro_data['Close'].values
            highs = macro_data['High'].values
            lows = macro_data['Low'].values
            current_price = closes[-1]
            
            # Calculate 200-week SMA (4-year moving average)
            sma_200w = macro_data['Close'].rolling(window=200).mean()
            current_sma_200w = sma_200w.iloc[-1] if not sma_200w.empty else None
            
            # Find macro highs and lows over past 48 months (208 weeks)
            analysis_period = min(208, len(macro_data))
            recent_data = macro_data.tail(analysis_period)
            
            # Find absolute highest peak and lowest trough in the analysis period
            macro_high = recent_data['High'].max()
            macro_low = recent_data['Low'].min()
            macro_high_date = recent_data[recent_data['High'] == macro_high].index[0]
            macro_low_date = recent_data[recent_data['Low'] == macro_low].index[0]
            
            # Ensure we have a proper Wave 1 structure (low before high)
            if macro_low_date >= macro_high_date:
                return {'is_elliott_wave': False, 'error': 'Invalid Wave 1 structure'}
            
            # Calculate Fibonacci retracement levels from Wave 1 (macro_low to macro_high)
            wave1_range = macro_high - macro_low
            fib_618 = macro_high - (wave1_range * 0.618)  # Golden ratio
            fib_50 = macro_high - (wave1_range * 0.50)    # 50% retracement
            
            # Golden Pocket: 50% to 61.8% retracement zone
            golden_pocket_high = fib_50
            golden_pocket_low = fib_618
            
            # Check if current price is in the Golden Pocket
            in_golden_pocket = golden_pocket_low <= current_price <= golden_pocket_high
            
            if not in_golden_pocket:
                return {'is_elliott_wave': False, 'error': 'Not in Golden Pocket zone'}
            
            # Calculate weekly RSI
            weekly_rsi = self.calculate_rsi(macro_data['Close'], period=14)
            current_rsi = weekly_rsi.iloc[-1] if not weekly_rsi.empty else None
            
            # Check RSI conditions (oversold or beginning to curl up)
            rsi_condition = current_rsi is not None and (current_rsi < 40 or 
                           (len(weekly_rsi) > 5 and current_rsi > weekly_rsi.iloc[-5]))
            
            if not rsi_condition:
                return {'is_elliott_wave': False, 'error': 'RSI conditions not met'}
            
            # Check 200-week SMA alignment (should be near Golden Pocket)
            sma_alignment = (current_sma_200w is not None and 
                           abs(current_sma_200w - ((golden_pocket_high + golden_pocket_low) / 2)) / 
                           current_sma_200w <= 0.15)  # Within 15% of Golden Pocket center
            
            # Calculate time since macro high (Wave 2 duration)
            weeks_since_high = len(macro_data[macro_data.index > macro_high_date])
            months_since_high = weeks_since_high / 4.33  # Convert to months
            
            # Wave 2 should be 6-18 months duration
            wave2_duration_valid = 6 <= months_since_high <= 18
            
            # Calculate retracement percentage
            retracement_percent = ((macro_high - current_price) / (macro_high - macro_low)) * 100
            
            # Calculate distance to Golden Pocket boundaries
            distance_to_fib50 = abs(current_price - fib_50) / current_price * 100
            distance_to_fib618 = abs(current_price - fib_618) / current_price * 100
            
            # All conditions must be met for a valid Elliott Wave setup
            if in_golden_pocket and rsi_condition and sma_alignment and wave2_duration_valid:
                return {
                    'is_elliott_wave': True,
                    'wave1_low': round(macro_low, 2),
                    'wave1_low_date': macro_low_date.strftime('%Y-%m-%d'),
                    'wave1_high': round(macro_high, 2),
                    'wave1_high_date': macro_high_date.strftime('%Y-%m-%d'),
                    'current_price': round(current_price, 2),
                    'golden_pocket_high': round(golden_pocket_high, 2),  # 50% level
                    'golden_pocket_low': round(golden_pocket_low, 2),   # 61.8% level
                    'retracement_percent': round(retracement_percent, 2),
                    'weekly_rsi': round(current_rsi, 2),
                    'sma_200w': round(current_sma_200w, 2),
                    'months_since_high': round(months_since_high, 1),
                    'distance_to_fib50': round(distance_to_fib50, 2),
                    'distance_to_fib618': round(distance_to_fib618, 2),
                    'wave1_duration_months': round((macro_high_date - macro_low_date).days / 30.44, 1),
                    'sma_alignment': sma_alignment,
                    'setup_quality': 'Excellent' if (current_rsi < 35 and sma_alignment) else 'Good'
                }
            
            return {'is_elliott_wave': False, 'error': 'Elliott Wave conditions not fully met'}
            
        except Exception as e:
            logger.error(f"Error detecting Elliott Wave macro setup: {e}")
            return {'is_elliott_wave': False, 'error': str(e)}
    
    
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
            monthly_data = weekly_data.resample('M').agg({
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
                # Both available - choose the one closer to current price
                weekly_distance = abs(weekly_trendline['current_trendline_price'] - current_price) / current_price
                monthly_distance = abs(monthly_trendline['current_trendline_price'] - current_price) / current_price
                
                if weekly_distance < monthly_distance:
                    has_trendline = True
                    trendline_data = weekly_trendline
                    trendline_data['primary_timeframe'] = 'Weekly'
                    trendline_data['secondary_trendline_price'] = monthly_trendline['current_trendline_price']
                    trendline_data['secondary_timeframe'] = 'Monthly'
                else:
                    has_trendline = True
                    trendline_data = monthly_trendline
                    trendline_data['primary_timeframe'] = 'Monthly'
                    trendline_data['secondary_trendline_price'] = weekly_trendline['current_trendline_price']
                    trendline_data['secondary_timeframe'] = 'Weekly'
            elif weekly_trendline:
                has_trendline = True
                trendline_data = weekly_trendline
                trendline_data['primary_timeframe'] = 'Weekly'
            elif monthly_trendline:
                has_trendline = True
                trendline_data = monthly_trendline
                trendline_data['primary_timeframe'] = 'Monthly'
            
            # Initialize has_fibonacci
            has_fibonacci = fib_result.get('is_near_fibonacci', False)
            
            # Must have either Fibonacci OR Trendline (or both) to qualify as Golden Stock
            if not (has_fibonacci or has_trendline):
                return {'is_golden_stock': False, 'error': 'No Fibonacci or Trendline signals found'}
            
            # Determine overall entry quality
            if has_fibonacci and has_trendline:
                if (abs(trendline_data.get('distance_to_trendline_percent', 100)) <= 2.0 and 
                    abs(fib_result.get('distance_percent', 100)) <= 1.0):
                    entry_quality = 'Excellent - Double Signal'
                else:
                    entry_quality = 'Good - Double Signal'
            elif has_fibonacci:
                if abs(fib_result.get('distance_percent', 100)) <= 1.0:
                    entry_quality = 'Excellent - Fibonacci'
                else:
                    entry_quality = 'Good - Fibonacci'
            else:  # has_trendline only
                if abs(trendline_data.get('distance_to_trendline_percent', 100)) <= 2.0:
                    entry_quality = 'Excellent - Trendline'
                else:
                    entry_quality = 'Good - Trendline'
            
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
            
            # Add Vertical Line analysis to Golden Stocks
            try:
                vertical_result = self.detect_vertical_line_pattern(weekly_data)
                if vertical_result.get('is_vertical_line', False):
                    result['has_vertical_line'] = True
                    result['vertical_line_price'] = vertical_result['vertical_line_price']
                    result['vertical_line_touch_count'] = vertical_result['touch_count']
                    result['vertical_line_signal'] = vertical_result['signal_strength']
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
        """Detect Vertical Line Pattern - Touch 2 trigger with 20% upside target"""
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
            # Find major horizontal levels that have been tested multiple times
            analysis_period = min(104, len(weekly_data))  # 2 years or available data
            analysis_data = weekly_data.tail(analysis_period)
            
            # Find significant price levels (horizontal support/resistance)
            price_levels = []
            tolerance = 0.02  # 2% tolerance for level matching
            
            # Collect all significant highs and lows
            for i in range(4, len(analysis_data) - 4):
                current_high = analysis_data['High'].iloc[i]
                current_low = analysis_data['Low'].iloc[i]
                current_date = analysis_data.index[i]
                
                # Check if this is a significant high or low
                surrounding_highs = analysis_data['High'].iloc[i-4:i+5]
                surrounding_lows = analysis_data['Low'].iloc[i-4:i+5]
                
                if current_high == surrounding_highs.max():
                    price_levels.append({
                        'price': current_high,
                        'type': 'resistance',
                        'date': current_date,
                        'touches': 1
                    })
                
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
            
            # Find levels with multiple touches (Touch 2 or more)
            significant_levels = [level for level in consolidated_levels if level['touches'] >= 2]
            
            if not significant_levels:
                return {'is_vertical_line': False, 'error': 'No significant vertical line levels found'}
            
            # Find the most relevant level for current price
            best_level = None
            min_distance = float('inf')
            
            for level in significant_levels:
                distance = abs(current_price - level['price']) / level['price']
                
                # Check if current price is within 3% of the level
                if distance <= 0.03 and distance < min_distance:
                    min_distance = distance
                    best_level = level
            
            if not best_level:
                return {'is_vertical_line': False, 'error': 'No relevant vertical line level near current price'}
            
            # Calculate 20% upside target
            target_price = current_price * 1.20
            upside_potential = ((target_price - current_price) / current_price) * 100
            
            # Determine if this is Touch 2 (trigger condition)
            is_touch_2 = best_level['touches'] >= 2
            touch_number = best_level['touches']
            
            # Calculate distance to level
            distance_percent = ((current_price - best_level['price']) / best_level['price']) * 100
            
            # Determine signal strength
            if is_touch_2 and abs(distance_percent) <= 1.0:
                signal_strength = 'Excellent - Touch 2 Trigger'
            elif is_touch_2 and abs(distance_percent) <= 2.0:
                signal_strength = 'Good - Touch 2 Active'
            elif touch_number >= 3:
                signal_strength = 'Strong - Multiple Touches'
            else:
                signal_strength = 'Fair - Monitoring'
            
            return {
                'is_vertical_line': True,
                'current_price': round(current_price, 2),
                'vertical_line_price': round(best_level['price'], 2),
                'level_type': best_level['type'],
                'touch_count': touch_number,
                'is_touch_2_trigger': is_touch_2,
                'distance_to_level_percent': round(distance_percent, 2),
                'target_price_20_percent': round(target_price, 2),
                'upside_potential_percent': round(upside_potential, 2),
                'first_touch_date': best_level['first_touch'].strftime('%Y-%m-%d'),
                'last_touch_date': best_level['dates'][-1].strftime('%Y-%m-%d'),
                'signal_strength': signal_strength,
                'week_52_high': round(week_52_high, 2),
                'week_52_low': round(week_52_low, 2),
                'analysis_timeframe': 'Weekly',
                'pattern_type': 'Vertical Line Analysis'
            }
            
        except Exception as e:
            logger.error(f"Error detecting Vertical Line pattern: {e}")
            return {'is_vertical_line': False, 'error': str(e)}
    
    def detect_darvas_box_pattern(self, data: pd.DataFrame) -> Dict:
        """Detect Darvas Box Pattern - Multi-timeframe consolidation with progressive targets"""
        try:
            if len(data) < 252:  # Need at least 1 year of daily data
                return {'is_darvas_box': False, 'error': 'Insufficient daily data'}
            
            current_price = data['Close'].iloc[-1]
            
            # Test multiple timeframes (2-3, 2-4, 2-5 years) - minimum 2 years consolidation
            timeframes = [
                {'years': '2-3', 'min_days': 730, 'max_days': 1095, 'target_percent': 100},  # 2-3 years
                {'years': '2-4', 'min_days': 730, 'max_days': 1460, 'target_percent': 150},  # 2-4 years
                {'years': '2-5', 'min_days': 730, 'max_days': 1825, 'target_percent': 200}   # 2-5 years
            ]
            
            best_darvas_box = None
            
            for timeframe in timeframes:
                # Check if we have enough data for this timeframe
                if len(data) < timeframe['max_days']:
                    continue
                
                # Get data for this timeframe range
                period_data = data.tail(timeframe['max_days'])
                highs = period_data['High'].values
                lows = period_data['Low'].values
                
                # Find the consolidation range (Darvas Box)
                # Look for periods where price stayed within a range for extended time
                
                # Calculate rolling max and min over different windows
                window_sizes = [20, 40, 60, 80]  # Different consolidation periods
                
                for window in window_sizes:
                    if len(period_data) < window * 2:
                        continue
                    
                    # Calculate rolling ranges
                    rolling_high = period_data['High'].rolling(window=window).max()
                    rolling_low = period_data['Low'].rolling(window=window).min()
                    rolling_range = ((rolling_high - rolling_low) / rolling_low) * 100
                    
                    # Find periods with tight consolidation (range < 15%)
                    consolidation_periods = rolling_range[rolling_range < 15]
                    
                    if len(consolidation_periods) < window // 2:  # Need sustained consolidation
                        continue
                    
                    # Find the most recent significant consolidation
                    recent_consolidations = consolidation_periods.tail(window)
                    if len(recent_consolidations) < window // 3:
                        continue
                    
                    # Get the consolidation box boundaries
                    consolidation_start_idx = recent_consolidations.index[0]
                    consolidation_end_idx = recent_consolidations.index[-1]
                    
                    # Find box boundaries from the consolidation period
                    consolidation_data = period_data.loc[consolidation_start_idx:consolidation_end_idx]
                    box_high = consolidation_data['High'].max()
                    box_low = consolidation_data['Low'].min()
                    box_range_percent = ((box_high - box_low) / box_low) * 100
                    
                    # Validate box criteria
                    if box_range_percent > 20:  # Box too wide
                        continue
                    
                    # Check if current price is within or near the box
                    distance_to_box_high = ((current_price - box_high) / box_high) * 100
                    distance_to_box_low = ((current_price - box_low) / box_low) * 100
                    
                    # Check if price is in the box or recently broke out
                    in_box = box_low <= current_price <= box_high
                    near_breakout = -5 <= distance_to_box_high <= 10  # Within 5% below to 10% above
                    
                    if not (in_box or near_breakout):
                        continue
                    
                    # Calculate consolidation duration
                    consolidation_days = (consolidation_end_idx - consolidation_start_idx).days
                    consolidation_months = consolidation_days / 30.44
                    
                    # Must have consolidated for at least 24 months (2 years)
                    if consolidation_months < 24:
                        continue
                    
                    # Calculate target based on timeframe
                    target_percent = timeframe['target_percent']
                    if consolidation_months >= 12:  # 1+ year consolidation gets higher target
                        target_percent = min(target_percent * 1.5, 300)
                    
                    target_price = current_price * (1 + target_percent / 100)
                    
                    # Determine breakout status
                    if current_price > box_high * 1.02:  # 2% above box high
                        breakout_status = 'Confirmed Breakout'
                        signal_strength = 'Excellent'
                    elif current_price > box_high:
                        breakout_status = 'Initial Breakout'
                        signal_strength = 'Good'
                    elif current_price >= box_high * 0.98:  # Within 2% of breakout
                        breakout_status = 'Near Breakout'
                        signal_strength = 'Good'
                    else:
                        breakout_status = 'In Consolidation'
                        signal_strength = 'Fair'
                    
                    # Calculate box strength (longer consolidation = stronger)
                    box_strength = min(100, (consolidation_months / 12) * 50 + 50)
                    
                    darvas_box = {
                        'timeframe_years': timeframe['years'],
                        'box_high': round(box_high, 2),
                        'box_low': round(box_low, 2),
                        'box_range_percent': round(box_range_percent, 2),
                        'consolidation_months': round(consolidation_months, 1),
                        'target_price': round(target_price, 2),
                        'target_percent': target_percent,
                        'breakout_status': breakout_status,
                        'signal_strength': signal_strength,
                        'box_strength': round(box_strength, 1),
                        'distance_to_breakout': round(distance_to_box_high, 2),
                        'consolidation_start': consolidation_start_idx.strftime('%Y-%m-%d'),
                        'consolidation_end': consolidation_end_idx.strftime('%Y-%m-%d')
                    }
                    
                    # Prefer longer timeframes and stronger signals
                    if (best_darvas_box is None or 
                        timeframe['years'] > best_darvas_box['timeframe_years'] or
                        (timeframe['years'] == best_darvas_box['timeframe_years'] and 
                         box_strength > best_darvas_box['box_strength'])):
                        best_darvas_box = darvas_box
            
            if not best_darvas_box:
                return {'is_darvas_box': False, 'error': 'No valid Darvas Box pattern found'}
            
            # Calculate 52-week high and low
            week_52_high = data['High'].tail(252).max() if len(data) >= 252 else data['High'].max()
            week_52_low = data['Low'].tail(252).min() if len(data) >= 252 else data['Low'].min()
            
            return {
                'is_darvas_box': True,
                'current_price': round(current_price, 2),
                'week_52_high': round(week_52_high, 2),
                'week_52_low': round(week_52_low, 2),
                'analysis_timeframe': 'Daily Multi-Year',
                'pattern_type': 'Darvas Box Analysis',
                **best_darvas_box
            }
            
        except Exception as e:
            logger.error(f"Error detecting Darvas Box pattern: {e}")
            return {'is_darvas_box': False, 'error': str(e)}
    
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
                    stock_info = {
                        'symbol': symbol,
                        'company_name': company_name,
                        'industry': industry,
                        'vertical_line_price': vertical_line_price,  # Add vertical line price
                        **volume_result
                    }
                    self.results['volume_breakout_stocks'].append(stock_info)
                    self.results['diagnostics']['volume_breakout_matches'] += 1
                    logger.info(f"Volume breakout: {symbol} with {volume_result.get('breakout_volume_ratio', 'N/A')}x volume")
            except Exception as e:
                logger.warning(f"Volume breakout analysis failed for {symbol}: {e}")
            
            # Check W-Pattern (weekly data)
            try:
                if weekly_data is not None and not weekly_data.empty:
                    w_pattern_result = self.detect_w_pattern(weekly_data)
                    if w_pattern_result.get('is_w_pattern', False):
                        stock_info = {
                            'symbol': symbol,
                            'company_name': company_name,
                            'industry': industry,
                            'vertical_line_price': vertical_line_price,  # Add vertical line price
                            **w_pattern_result
                        }
                        self.results['w_pattern_stocks'].append(stock_info)
                        self.results['diagnostics']['w_pattern_matches'] += 1
                        logger.info(f"W-Pattern match: {symbol} with {w_pattern_result['distance_to_neckline_percent']:.1f}% to neckline")
            except Exception as e:
                logger.warning(f"W-Pattern analysis failed for {symbol}: {e}")
            
            # Check Elliott Wave macro setup
            try:
                macro_data = self.get_macro_data(symbol)
                if macro_data is not None and not macro_data.empty:
                    elliott_result = self.detect_elliott_wave_macro(macro_data)
                    if elliott_result.get('is_elliott_wave', False):
                        stock_info = {
                            'symbol': symbol,
                            'company_name': company_name,
                            'industry': industry,
                            'vertical_line_price': vertical_line_price,  # Add vertical line price
                            **elliott_result
                        }
                        self.results['elliott_wave_stocks'].append(stock_info)
                        self.results['diagnostics']['elliott_wave_matches'] += 1
                        logger.info(f"Elliott Wave match: {symbol} in Golden Pocket with {elliott_result['retracement_percent']:.1f}% retracement")
            except Exception as e:
                logger.warning(f"Elliott Wave analysis failed for {symbol}: {e}")
            
            # Check Golden Stocks (Combined Trendline + Fibonacci + Vertical Line)
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
                        self.results['golden_stocks'].append(stock_info)
                        self.results['diagnostics']['golden_matches'] += 1
                        logger.info(f"Golden Stock match: {symbol} - {golden_result['entry_quality']} | Upside: {golden_result.get('potential_upside_percent', 0):.1f}%")
            except Exception as e:
                logger.warning(f"Golden Stocks analysis failed for {symbol}: {e}")
            
            # Check Darvas Box Pattern
            try:
                darvas_result = self.detect_darvas_box_pattern(data)
                if darvas_result.get('is_darvas_box', False):
                    stock_info = {
                        'symbol': symbol,
                        'company_name': company_name,
                        'industry': industry,
                        'vertical_line_price': vertical_line_price,  # Add vertical line price
                        **darvas_result
                    }
                    self.results['darvas_box_stocks'].append(stock_info)
                    self.results['diagnostics']['darvas_box_matches'] += 1
                    logger.info(f"Darvas Box match: {symbol} - {darvas_result['timeframe_years']}Y box, {darvas_result['breakout_status']}")
            except Exception as e:
                logger.warning(f"Darvas Box analysis failed for {symbol}: {e}")
            
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
            
            # Sort W-Pattern stocks: Radar Active first, then by proximity to completing pattern
            self.results['w_pattern_stocks'].sort(key=lambda x: (
                0 if x.get('radar_status') == 'Active' else 1,  # Radar Active first
                x.get('distance_to_neckline_percent', 100)  # Closer to neckline breakout
            ))
            
            # Sort Elliott Wave stocks: Best setup quality first, then by RSI (most oversold first)
            self.results['elliott_wave_stocks'].sort(key=lambda x: (
                0 if x.get('setup_quality') == 'Excellent' else 1,  # Excellent setups first
                x.get('weekly_rsi', 100),  # Most oversold first (lower RSI)
                x.get('retracement_percent', 0)  # Deeper retracements first
            ))
            
            # Sort Golden Stocks: Double signals first, then by entry quality, then by proximity
            self.results['golden_stocks'].sort(key=lambda x: (
                0 if 'Double Signal' in x.get('entry_quality', '') else 1,  # Double signals first
                0 if x.get('entry_quality', '').startswith('Excellent') else 1 if x.get('entry_quality', '').startswith('Good') else 2,  # Quality priority
                abs(x.get('fibonacci_distance_percent', x.get('distance_to_trendline_percent', 100))),  # Closer to signal
                -x.get('trendline_strength', 0)  # Stronger trendlines first (negative for descending sort)
            ))
            
            # Sort Darvas Box stocks: Longer timeframes first, then by breakout status
            self.results['darvas_box_stocks'].sort(key=lambda x: (
                0 if x.get('breakout_status') == 'Confirmed Breakout' else 1 if x.get('breakout_status') == 'Initial Breakout' else 2,  # Breakout status
                -x.get('timeframe_years', 0),  # Longer timeframes first
                -x.get('box_strength', 0),  # Stronger boxes first
                abs(x.get('distance_to_breakout', 100))  # Closer to breakout
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
        - W-Pattern matches: {diag['w_pattern_matches']}
        - Elliott Wave matches: {diag['elliott_wave_matches']}
        - Darvas Box matches: {diag['darvas_box_matches']}
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
            w_pattern_count = len(self.results['w_pattern_stocks'])
            elliott_count = len(self.results['elliott_wave_stocks'])
            darvas_count = len(self.results['darvas_box_stocks'])
            
            # Count radar alerts
            vol_radar_active = sum(1 for stock in self.results['volume_breakout_stocks'] 
                                 if stock.get('radar_status') == 'Active')
            w_radar_active = sum(1 for stock in self.results['w_pattern_stocks'] 
                               if stock.get('radar_status') == 'Active')
            
            total_processed = self.results['diagnostics']['total_stocks_processed']
            
            message = f"""🔍 *Stock Yard Daily Screening Report*
📅 {datetime.now().strftime('%Y-%m-%d %H:%M IST')}

📊 *Results Summary:*
• Total Stocks Screened: {total_processed}
• Golden Stocks (Fib+Trendline+Vertical): {golden_count} matches
• Volume Breakout: {vol_count} matches
• W-Pattern: {w_pattern_count} matches
• Elliott Wave (Long-term): {elliott_count} matches
• Darvas Box (Multi-Year): {darvas_count} matches

🚨 *RADAR ALERTS:*
• Volume Stocks in Radar: {vol_radar_active}
• W-Pattern Stocks in Radar: {w_radar_active}

📱 *View Full Report:*
https://anuragsin17-sketch.github.io/Stock-Yard/

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
            'darvas_box_stocks': [],
            'volume_breakout_stocks': [],
            'w_pattern_stocks': [],
            'elliott_wave_stocks': [],
            'diagnostics': {
                'total_stocks_processed': 0,
                'successful_downloads': 0,
                'failed_downloads': 0,
                'golden_matches': 0,
                'darvas_box_matches': 0,
                'volume_breakout_matches': 0,
                'w_pattern_matches': 0,
                'elliott_wave_matches': 0,
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
    main()