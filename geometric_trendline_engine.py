"""
GeometricTrendlineEngine - Adapter for trendline analysis and pattern extraction.

This module provides a simplified interface to the MacroInstitutionalEngine
for the Trendline Scanner system. It extracts pattern metrics used by the
scanner for identifying high-probability entry opportunities based on
geometric trendline analysis.
"""

from typing import Optional, Dict, Any
from geometric_engine import MacroInstitutionalEngine


class GeometricTrendlineEngine:
    """
    Geometric trendline analysis engine for scanner integration.
    
    This class adapts the MacroInstitutionalEngine functionality to provide
    a simplified interface for trendline detection and pattern analysis.
    It extracts key pattern metrics that the scanner uses for entry point
    identification and risk management parameter calculation.
    
    Attributes:
        buffer_percentage (float): Maximum distance from trendline for WATCHLIST status (10%)
        critical_trigger_percentage (float): Maximum distance for CRITICAL_TOUCH status (1%)
        engine (MacroInstitutionalEngine): Underlying engine for trendline analysis
    """
    
    def __init__(self, 
                 buffer_percentage: float = 10.0, 
                 critical_trigger_percentage: float = 1.0,
                 position_size: float = 50000.0,
                 stop_loss_pct: float = 8.0):
        """
        Initialize the GeometricTrendlineEngine.
        
        Args:
            buffer_percentage: Maximum distance from trendline for WATCHLIST status.
                             Default: 10.0 (10%)
            critical_trigger_percentage: Maximum distance for CRITICAL_TOUCH status.
                                        Default: 1.0 (1%)
            position_size: Fixed capital allocated per trade in Indian Rupees.
                          Default: 50000.0 (₹50,000)
            stop_loss_pct: Stop loss percentage below trendline entry price.
                          Default: 8.0 (8%)
        """
        self.buffer_percentage = float(buffer_percentage)
        self.critical_trigger_percentage = float(critical_trigger_percentage)
        self.position_size = float(position_size)
        self.stop_loss_pct = float(stop_loss_pct)
        
        # Initialize underlying MacroInstitutionalEngine with position sizing and stop loss
        self.engine = MacroInstitutionalEngine(
            position_size=position_size,
            sl_pct=stop_loss_pct,
            touch_tolerance=buffer_percentage
        )
    
    def extract_pattern_metrics(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Extract trendline pattern metrics for a given stock ticker.
        
        This method analyzes a stock's historical price data to detect ascending
        trendlines and extract key geometric pattern metrics used by the scanner
        for entry point identification.
        
        Args:
            ticker: Stock symbol (e.g., "RELIANCE.NS" or "INFY.NS")
        
        Returns:
            Dictionary containing pattern metrics if a valid trendline is found:
                - ticker: Stock symbol (without .NS suffix)
                - current_price: Current market price (float, 2 decimals)
                - trigger_price: Trendline entry price (float, 2 decimals)
                - distance_percentage: Distance from current price to trigger (float, 2 decimals)
                - target_exit: 20% profit target above trigger price (float, 2 decimals)
                - stop_loss: 8% stop loss below trigger price (float, 2 decimals)
                - status: "CRITICAL_TOUCH" (≤1%) or "WATCHLIST" (1-10%) or None
                - confluence_score: Pattern quality score 1-10 (int)
                - trendline_strength: Overall pattern strength 0-100 (float)
                - wick_touches: Number of wick touches on trendline (int)
                - slope: Trendline slope (float)
                - num_anchors: Number of anchor points used (int)
                - fibonacci_levels: Dict of Fibonacci retracement levels (dict)
                
            Returns None if:
                - Historical data is insufficient (< 24 months)
                - No valid ascending trendline found
                - Insufficient touch points (< 3)
                - Price is > 10% away from trendline (outside buffer)
        """
        try:
            # Call underlying engine's analysis method
            result = self.engine.process_ticker_geometry(ticker)
            
            # Return None if engine couldn't find a valid pattern
            if result is None:
                return None
            
            # Extract and prepare metrics for scanner consumption
            current_signal = result.get("currentSignal", {})
            position_sizing = result.get("positionSizing", {})
            trendline_details = result.get("trendlineDetails", {})
            fib_grid = result.get("fibGrid", {})
            
            # Calculate distance percentage for filtering
            distance_pct = current_signal.get("distanceRemaining", 0.0)
            
            # Filter by buffer_percentage (10% default)
            if distance_pct > self.buffer_percentage:
                return None
            
            # Determine status based on distance thresholds
            if distance_pct <= self.critical_trigger_percentage:
                status = "CRITICAL_TOUCH"
            elif distance_pct <= self.buffer_percentage:
                status = "WATCHLIST"
            else:
                return None  # Outside thresholds, exclude from results
            
            # Extract clean ticker without .NS suffix
            clean_ticker = result.get("ticker", ticker).replace(".NS", "")
            
            # Build simplified metrics dictionary for scanner
            metrics = {
                "ticker": clean_ticker,
                "current_price": current_signal.get("currentPrice", 0.0),
                "trigger_price": position_sizing.get("entryPrice", 0.0),
                "distance_percentage": round(distance_pct, 2),
                "target_exit": position_sizing.get("targetExit", 0.0),
                "stop_loss": position_sizing.get("dynamicStopLoss", 0.0),
                "status": status,
                "confluence_score": current_signal.get("confluenceScore", 6),
                "trendline_strength": self._calculate_trendline_strength(
                    trendline_details.get("wickTouches", 0),
                    trendline_details.get("slope", 0.0)
                ),
                "wick_touches": trendline_details.get("wickTouches", 0),
                "slope": round(trendline_details.get("slope", 0.0), 4),
                "num_anchors": trendline_details.get("numAnchors", 0),
                "fibonacci_levels": fib_grid if fib_grid else {},
                "position_size": position_sizing.get("sharesToBuy", 0),
                "allocated_amount": position_sizing.get("allocatedAmount", self.position_size)
            }
            
            return metrics
            
        except Exception as e:
            # Log error but don't raise - allow scanner to continue
            # This implements graceful error handling per Requirements 7.5, 9.3
            return None
    
    def _calculate_trendline_strength(self, wick_touches: int, slope: float) -> float:
        """
        Calculate trendline strength score based on touch count and slope.
        
        Strength is determined by:
        - Number of wick touches (more touches = stronger pattern)
        - Slope consistency (steeper, consistent slope = stronger pattern)
        
        Args:
            wick_touches: Number of touch points on the trendline
            slope: Trendline slope value
        
        Returns:
            Strength score between 0-100
        """
        # Base score from touch count (3 touches = 40, +15 per additional touch)
        base_touch_score = min(40 + (max(0, wick_touches - 3) * 15), 80)
        
        # Slope component (higher slope = stronger uptrend)
        slope_score = min(abs(slope) * 5, 20)
        
        # Combined strength score
        strength = base_touch_score + slope_score
        
        return round(min(strength, 100), 1)
