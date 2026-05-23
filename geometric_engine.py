import yfinance as yf
import pandas as pd
import numpy as np
from scipy.signal import argrelextrema

class MacroInstitutionalEngine:
    def __init__(self, position_size=50000.0, sl_pct=8.0, watchlist_buffer=10.0):
        """
        Initializes your precise pattern scanning and risk allocation matrices.
        """
        self.capital_per_trade = float(position_size)
        self.sl_multiplier = 1.0 - (float(sl_pct) / 100.0)
        self.buffer = float(watchlist_buffer)

    def process_ticker_geometry(self, ticker: str):
        """
        Analyzes multi-year candle structures, matches forward-looking vector projections,
        calculates full-grid Fibonacci layers, and outputs exact position parameters.
        """
        try:
            # 1. Fetch long-term monthly historical candle data
            # auto_adjust=True guarantees proper adjustment for corporate splits/demergers
            df = yf.download(ticker, period="15y", interval="1mo", auto_adjust=True, progress=False)
            if df.empty or len(df) < 36: 
                return None
                
            df = df.dropna()
            df['Price_Idx'] = np.arange(len(df))
            low_prices = df['Low'].values.flatten()
            
            # 2. Extract major multi-year visual bottoms (using a 12-month cyclical radius)
            touchbacks = argrelextrema(low_prices, np.less, order=12)
            if len(touchbacks[0]) < 2: 
                return None
                
            # 3. Fit your straight geometrical trendline across the true visual anchors (y = mx + c)
            x_anchors = df['Price_Idx'].iloc[touchbacks[0][-3:]].values # Capture latest 2-3 major touches
            y_anchors = low_prices[touchbacks[0][-3:]]
            slope, intercept = np.polyfit(x_anchors, y_anchors, 1)
            
            # 4. Project the trendline value onto the current active monthly index bar
            current_bar_idx = df['Price_Idx'].iloc[-1]
            current_close = df['Close'].iloc[-1].item()
            expected_trendline_trigger = (slope * current_bar_idx) + intercept
            
            # 5. Formulate the absolute Fibonacci impulse limits from your true last touch to peak
            wave_base_origin = low_prices[touchbacks[0][-1]].item() # Your verified last touch floor
            wave_peak_ceiling = df['High'].max().item() # The absolute historical distribution peak
            total_wave_range = wave_peak_ceiling - wave_base_origin
            
            if total_wave_range <= 0: 
                return None
                
            # Compute the exact price matrix positions for all 5 core levels
            fib_236 = wave_peak_ceiling - (total_wave_range * 0.236)
            fib_382 = wave_peak_ceiling - (total_wave_range * 0.382)
            fib_500 = wave_peak_ceiling - (total_wave_range * 0.500)
            fib_618 = wave_peak_ceiling - (total_wave_range * 0.618)
            
            # Determine where the future line intersection sits as a pure Fibonacci ratio
            upcoming_line_fib_pct = ((wave_peak_ceiling - expected_trendline_trigger) / total_wave_range) * 100
            
            # 6. Apply your structural filters (Only pass if the line sits within mathematical boundaries)
            if upcoming_line_fib_pct <= 25.0:
                zone_tag = "23.6% (Shallow Momentum)"
            elif 25.0 < upcoming_line_fib_pct <= 45.0:
                zone_tag = "38.2% (Institutional Pocket)"
            elif 45.0 < upcoming_line_fib_pct <= 55.0:
                zone_tag = "50.0% (Equilibrium Baseline)"
            elif 55.0 < upcoming_line_fib_pct <= 75.0:
                zone_tag = "61.8% (Golden Ratio Floor)"
            else:
                zone_tag = "100.0% (Full Capitulation Reset)"
                
            # Measure proximity distance remaining until the live candle lands on the line
            pct_distance_to_line = ((current_close - expected_trendline_trigger) / expected_trendline_trigger) * 100
            
            # SCREEN FILTER: Keep only if the stock falls within your requested nearby buffer
            if 0.0 <= pct_distance_to_line <= self.buffer:
                
                # 7. Generate strict position and risk management values
                calculated_stop_loss = expected_trendline_trigger * self.sl_multiplier
                risk_per_share = expected_trendline_trigger - calculated_stop_loss
                total_shares_to_buy = int(self.capital_per_trade // expected_trendline_trigger)
                
                # Instant alert trigger condition if current price is within 1% of the trendline
                is_alert_active = pct_distance_to_line <= 1.0
                
                return {
                    "ticker": ticker.replace(".NS", ""),
                    "currentPrice": round(current_close, 2),
                    "triggerPrice": round(expected_trendline_trigger, 2),
                    "distanceRemaining": round(pct_distance_to_line, 2),
                    "fibLevelMatch": f"{round(upcoming_line_fib_pct, 2)}%",
                    "patternZone": zone_tag,
                    "positionSizing": {
                        "allocatedAmount": float(self.capital_per_trade),
                        "sharesToBuy": int(total_shares_to_buy),
                        "strictStopLoss": round(calculated_stop_loss, 2),
                        "pivotTargetExit": round(wave_peak_ceiling, 2)
                    },
                    "fullFibGridPrices": {
                        "level_236": round(fib_236, 2),
                        "level_382": round(fib_382, 2),
                        "level_500": round(fib_500, 2),
                        "level_618": round(fib_618, 2),
                        "level_1000": round(wave_base_origin, 2)
                    },
                    "notificationTrigger": bool(is_alert_active)
                }
        except Exception as e:
            pass
        return None
