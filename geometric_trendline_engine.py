#!/usr/bin/env python3
"""
GeometricTrendlineEngine - Adapter interface for trendline scanner

This module provides a simplified interface around the existing MacroInstitutionalEngine
for the trendline scanner system. It implements the adapter pattern to wrap the complex
functionality and provide a clean interface for pattern metrics extraction.
"""

from typing import Optional, Dict, Any
from geometric_engine import MacroInstitutionalEngine


class GeometricTrendlineEngine:
    """
    Adapter class that wraps MacroInstitutionalEngine functionality for trendline scanning.
    
    This class provides a simplified interface specifically designed for the trendline scanner,
    extracting only the essential pattern metrics needed for screening operations.
    """
    
    def __init__(self, buffer_percentage: float = 10.0, critical_trigger_percentage: float = 1.0):
        """
        Initialize the geometric trendline analysis engine.
        
        Args:
            buffer_percentage: Maximum distance from trendline for WATCHLIST status (default: 10%)
            critical_trigger_percentage: Maximum distance for CRITICAL_TOUCH status (default: 1%)
        """
        self.buffer_percentage = float(buffer_percentage)
        self.critical_trigger_percentage = float(critical_trigger_percentage)
        
        # Initialize the underlying MacroInstitutionalEngine with appropriate parameters
        # Using buffer_percentage as touch_tolerance for the underlying engine
        self.macro_engine = MacroInstitutionalEngine(
            position_size=50000.0,  # Fixed position size as per requirements
            sl_pct=8.0,             # 8% stop loss as per requirements
            touch_tolerance=buffer_percentage  # Use buffer_percentage as touch tolerance
        )
    
    def extract_pattern_metrics(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Extract trendline pattern metrics for a given stock ticker.
        
        This method wraps the MacroInstitutionalEngine's process_ticker_geometry method
        and returns a simplified data structure suitable for the scanner.
        
        Args:
            ticker: Stock symbol (e.g., "RELIANCE.NS")
            
        Returns:
            Dictionary containing simplified pattern analysis or None if no valid pattern found.
            
            The returned dictionary contains:
            - ticker: Clean ticker symbol (without .NS suffix)
            - currentPrice: Current stock price
            - triggerPrice: Calculated trendline trigger price
            - distance: Distance percentage from current price to trigger price
            - targetExit: Target exit price (20% above trigger price as per requirements)
            - stopLoss: Stop loss price (8% below trigger price as per requirements)
            - status: "CRITICAL_TOUCH" or "WATCHLIST" based on distance
            - fibonacciLevel: Which Fibonacci level the trigger intersects
            - patternZone: Description of the Fibonacci zone
            - confluenceScore: Numerical score indicating pattern strength
            - trendlineStrength: Strength score of the detected trendline
            - touchCount: Number of historical touch points
            - timeframeMonths: Duration of the trendline in months
        """
        try:
            # Call the underlying MacroInstitutionalEngine
            result = self.macro_engine.process_ticker_geometry(ticker)
            
            if result is None:
                return None
            
            # Extract the current signal data
            current_signal = result.get('currentSignal', {})
            position_sizing = result.get('positionSizing', {})
            trendline_details = result.get('trendlineDetails', {})
            
            if not current_signal.get('isActive', False):
                return None
            
            # Calculate distance percentage
            current_price = current_signal.get('currentPrice', 0)
            trigger_price = current_signal.get('triggerPrice', 0)
            
            if trigger_price <= 0:
                return None
            
            # Calculate distance percentage: ((current_price - trigger_price) / trigger_price) * 100
            distance_percentage = ((current_price - trigger_price) / trigger_price) * 100
            
            # Determine status based on distance
            if abs(distance_percentage) <= self.critical_trigger_percentage:
                status = "CRITICAL_TOUCH"
            elif abs(distance_percentage) <= self.buffer_percentage:
                status = "WATCHLIST"
            else:
                # Stock is outside the buffer range, should be excluded
                return None
            
            # Calculate target exit as 20% above trigger price (as per requirements)
            target_exit = trigger_price * 1.20
            
            # Extract trendline strength information
            confluence_score = current_signal.get('confluenceScore', 0)
            touch_count = trendline_details.get('numTouches', 0)
            
            # Estimate timeframe in months (rough calculation based on touch count)
            # Assuming average 12 months between touches for estimation
            timeframe_months = touch_count * 12.0 if touch_count > 0 else 24.0
            
            # Calculate trendline strength score (0-100 scale)
            # Based on confluence score, touch count, and other factors
            trendline_strength = min(100.0, confluence_score * 10 + touch_count * 5)
            
            return {
                'ticker': result.get('ticker', ticker.replace('.NS', '')),
                'currentPrice': round(current_price, 2),
                'triggerPrice': round(trigger_price, 2),
                'distance': round(abs(distance_percentage), 2),
                'targetExit': round(target_exit, 2),
                'stopLoss': round(position_sizing.get('strictStopLoss', trigger_price * 0.92), 2),
                'status': status,
                'fibonacciLevel': current_signal.get('fibLevelMatch', 'Unknown'),
                'patternZone': current_signal.get('patternZone', 'Unknown Zone'),
                'confluenceScore': confluence_score,
                'trendlineStrength': round(trendline_strength, 1),
                'touchCount': touch_count,
                'timeframeMonths': round(timeframe_months, 1)
            }
            
        except Exception as e:
            # Log the error but don't raise it - graceful degradation
            # In a production system, you might want to use proper logging
            print(f"Error processing {ticker}: {str(e)}")
            return None
    
    def get_configuration(self) -> Dict[str, float]:
        """
        Get the current configuration parameters.
        
        Returns:
            Dictionary containing current configuration values
        """
        return {
            'buffer_percentage': self.buffer_percentage,
            'critical_trigger_percentage': self.critical_trigger_percentage,
            'position_size': 50000.0,
            'stop_loss_percentage': 8.0,
            'target_exit_percentage': 20.0
        }
    
    def validate_minimum_data_requirement(self, ticker: str) -> bool:
        """
        Check if a ticker has sufficient historical data for analysis.
        
        This method validates that the stock has at least 24 months of historical data
        as required by the system specifications.
        
        Args:
            ticker: Stock symbol to validate
            
        Returns:
            True if sufficient data is available, False otherwise
        """
        try:
            import yfinance as yf
            
            # Fetch historical data to check availability
            df = yf.download(ticker, period="3y", interval="1mo", auto_adjust=True, progress=False)
            
            if df.empty:
                return False
            
            # Check if we have at least 24 months of data
            return len(df) >= 24
            
        except Exception:
            return False
    
    def validate_trendline_touch_points(self, ticker: str) -> Optional[int]:
        """
        Validate that a detected trendline has minimum required touch points.
        
        Args:
            ticker: Stock symbol to analyze
            
        Returns:
            Number of touch points if valid trendline found, None otherwise
        """
        try:
            # Use the underlying engine to get full analysis
            result = self.macro_engine.process_ticker_geometry(ticker)
            
            if result is None:
                return None
            
            trendline_details = result.get('trendlineDetails', {})
            touch_count = trendline_details.get('numTouches', 0)
            
            # Require minimum 3 touch points as per specifications
            if touch_count >= 3:
                return touch_count
            else:
                return None
                
        except Exception:
            return None
    
    def calculate_trigger_price_projection(self, slope: float, intercept: float, current_time_index: float) -> float:
        """
        Calculate trigger price using linear trendline projection.
        
        This method implements the mathematical formula for projecting a trendline
        to the current time period using the linear equation y = mx + b.
        
        Args:
            slope: Trendline slope (m)
            intercept: Trendline y-intercept (b)
            current_time_index: Current time index (x)
            
        Returns:
            Projected trigger price (y)
        """
        return (slope * current_time_index) + intercept


if __name__ == "__main__":
    # Example usage and testing
    engine = GeometricTrendlineEngine(buffer_percentage=10.0, critical_trigger_percentage=1.0)
    
    # Test with a sample ticker
    test_ticker = "RELIANCE.NS"
    result = engine.extract_pattern_metrics(test_ticker)
    
    if result:
        print(f"✅ Pattern found for {result['ticker']}:")
        print(f"   Current Price: ₹{result['currentPrice']}")
        print(f"   Trigger Price: ₹{result['triggerPrice']}")
        print(f"   Distance: {result['distance']}%")
        print(f"   Status: {result['status']}")
        print(f"   Target Exit: ₹{result['targetExit']}")
        print(f"   Stop Loss: ₹{result['stopLoss']}")
        print(f"   Fibonacci Level: {result['fibonacciLevel']}")
        print(f"   Pattern Zone: {result['patternZone']}")
        print(f"   Confluence Score: {result['confluenceScore']}")
        print(f"   Trendline Strength: {result['trendlineStrength']}")
    else:
        print(f"❌ No valid pattern found for {test_ticker}")
    
    # Test configuration
    config = engine.get_configuration()
    print(f"\n📋 Configuration: {config}")