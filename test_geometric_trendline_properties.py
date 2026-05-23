#!/usr/bin/env python3
"""
Property-based tests for GeometricTrendlineEngine

This module contains property-based tests that validate the correctness properties
of the GeometricTrendlineEngine class as specified in the design document.
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf
from unittest.mock import patch, MagicMock

from geometric_trendline_engine import GeometricTrendlineEngine


# Test data generation strategies
@st.composite
def stock_data_strategy(draw, months=None):
    """Generate synthetic stock data for testing."""
    if months is None:
        months = draw(st.integers(min_value=1, max_value=60))
    
    # Generate dates
    start_date = datetime.now() - timedelta(days=months * 30)
    dates = pd.date_range(start=start_date, periods=months, freq='M')
    
    # Generate price data with some realistic constraints
    base_price = draw(st.floats(min_value=10.0, max_value=5000.0))
    prices = []
    current_price = base_price
    
    for _ in range(months):
        # Random walk with some bounds
        change_pct = draw(st.floats(min_value=-0.3, max_value=0.3))
        current_price = max(1.0, current_price * (1 + change_pct))
        prices.append(current_price)
    
    # Create DataFrame similar to yfinance output
    df = pd.DataFrame({
        'Open': prices,
        'High': [p * draw(st.floats(min_value=1.0, max_value=1.1)) for p in prices],
        'Low': [p * draw(st.floats(min_value=0.9, max_value=1.0)) for p in prices],
        'Close': prices,
        'Volume': [draw(st.integers(min_value=1000, max_value=1000000)) for _ in prices]
    }, index=dates)
    
    return df


@st.composite
def trendline_parameters_strategy(draw):
    """Generate valid trendline parameters for testing."""
    slope = draw(st.floats(min_value=0.1, max_value=50.0))  # Positive slope for ascending trendline
    intercept = draw(st.floats(min_value=10.0, max_value=1000.0))
    time_index = draw(st.floats(min_value=0.0, max_value=100.0))
    
    return slope, intercept, time_index


class TestGeometricTrendlineProperties:
    """Property-based tests for GeometricTrendlineEngine correctness properties."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.engine = GeometricTrendlineEngine(
            buffer_percentage=10.0,
            critical_trigger_percentage=1.0
        )
    
    # Property 1: Trendline Detection Requires Minimum Data
    # **Validates: Requirements 1.1, 9.1**
    @given(historical_data=stock_data_strategy(months=st.integers(0, 23)))
    @settings(max_examples=50)
    def test_minimum_data_requirement_property(self, historical_data):
        """
        Feature: trendline-scanner, Property 1: Trendline Detection Requires Minimum Data
        
        For any stock analysis request, if the historical data contains fewer than 24 months 
        of price data, the GeometricTrendlineEngine should return None and the stock should 
        be excluded from results.
        """
        months_of_data = len(historical_data)
        
        # Mock yfinance to return our test data
        with patch('yfinance.download') as mock_download:
            mock_download.return_value = historical_data
            
            # Test the validation method directly
            has_sufficient_data = self.engine.validate_minimum_data_requirement("TEST.NS")
            
            # Property: If data has < 24 months, should return False
            if months_of_data < 24:
                assert has_sufficient_data is False, f"Expected False for {months_of_data} months of data"
            else:
                # This case shouldn't occur with our strategy, but handle it
                assert has_sufficient_data is True, f"Expected True for {months_of_data} months of data"
    
    # Property 2: Trendline Validation Requires Minimum Touch Points
    # **Validates: Requirements 1.3**
    @given(st.data())
    @settings(max_examples=30)
    def test_trendline_validation_touch_points_property(self, data):
        """
        Feature: trendline-scanner, Property 2: Trendline Validation Requires Minimum Touch Points
        
        For any detected trendline, it should only be considered valid if it has at least 
        3 touch points within 2% tolerance of the trendline equation.
        """
        # Generate test data with sufficient months
        historical_data = data.draw(stock_data_strategy(months=st.integers(24, 60)))
        
        with patch('yfinance.download') as mock_download:
            mock_download.return_value = historical_data
            
            # Test the touch point validation
            touch_count = self.engine.validate_trendline_touch_points("TEST.NS")
            
            # Property: If trendline is valid, it must have >= 3 touch points
            if touch_count is not None:
                assert touch_count >= 3, f"Valid trendline must have >= 3 touch points, got {touch_count}"
            # If touch_count is None, it means no valid trendline was found, which is acceptable
    
    # Property 3: Trigger Price Projection Accuracy
    # **Validates: Requirements 1.4**
    @given(trendline_params=trendline_parameters_strategy())
    @settings(max_examples=100)
    def test_trigger_price_projection_accuracy_property(self, trendline_params):
        """
        Feature: trendline-scanner, Property 3: Trigger Price Projection Accuracy
        
        For any valid trendline with known slope and intercept, projecting to the current 
        time period should produce a mathematically correct trigger price using linear 
        equation y = mx + b.
        """
        slope, intercept, time_index = trendline_params
        
        # Calculate expected result using the linear equation
        expected_trigger_price = (slope * time_index) + intercept
        
        # Test the engine's calculation
        calculated_trigger_price = self.engine.calculate_trigger_price_projection(
            slope, intercept, time_index
        )
        
        # Property: The calculated trigger price must match the linear equation y = mx + b
        # Allow for small floating-point precision errors
        assert abs(calculated_trigger_price - expected_trigger_price) < 1e-10, \
            f"Trigger price calculation incorrect: expected {expected_trigger_price}, got {calculated_trigger_price}"
    
    @given(
        current_price=st.floats(min_value=1.0, max_value=10000.0),
        trigger_price=st.floats(min_value=1.0, max_value=10000.0)
    )
    @settings(max_examples=100)
    def test_distance_percentage_calculation_property(self, current_price, trigger_price):
        """
        Property test for distance percentage calculation accuracy.
        
        For any current price and trigger price, the distance percentage should be 
        calculated as: ((current_price - trigger_price) / trigger_price) × 100
        """
        # Calculate expected distance percentage
        expected_distance = ((current_price - trigger_price) / trigger_price) * 100
        
        # Create a mock result from the underlying engine
        mock_result = {
            'ticker': 'TEST',
            'currentSignal': {
                'isActive': True,
                'currentPrice': current_price,
                'triggerPrice': trigger_price,
                'fibLevelMatch': '50.0%',
                'patternZone': 'Test Zone',
                'confluenceScore': 5,
                'notificationTrigger': False
            },
            'positionSizing': {
                'strictStopLoss': trigger_price * 0.92
            },
            'trendlineDetails': {
                'numTouches': 3
            }
        }
        
        # Mock the underlying engine to return our test data
        with patch.object(self.engine.macro_engine, 'process_ticker_geometry', return_value=mock_result):
            result = self.engine.extract_pattern_metrics("TEST.NS")
            
            if result is not None:
                calculated_distance = result['distance']
                
                # Property: Distance should match the mathematical formula
                # The result stores absolute distance, so compare with abs(expected)
                assert abs(calculated_distance - abs(expected_distance)) < 0.01, \
                    f"Distance calculation incorrect: expected {abs(expected_distance):.2f}, got {calculated_distance}"
    
    @given(
        distance_percentage=st.floats(min_value=0.0, max_value=15.0)
    )
    @settings(max_examples=50)
    def test_status_assignment_property(self, distance_percentage):
        """
        Property test for status assignment based on distance.
        
        For any stock with calculated distance percentage: 
        - if distance ≤ 1% then status = "CRITICAL_TOUCH"
        - if 1% < distance ≤ 10% then status = "WATCHLIST"  
        - if distance > 10% then stock is excluded (returns None)
        """
        # Create mock data with the specified distance
        trigger_price = 100.0
        current_price = trigger_price * (1 + distance_percentage / 100)
        
        mock_result = {
            'ticker': 'TEST',
            'currentSignal': {
                'isActive': True,
                'currentPrice': current_price,
                'triggerPrice': trigger_price,
                'fibLevelMatch': '50.0%',
                'patternZone': 'Test Zone',
                'confluenceScore': 5,
                'notificationTrigger': False
            },
            'positionSizing': {
                'strictStopLoss': trigger_price * 0.92
            },
            'trendlineDetails': {
                'numTouches': 3
            }
        }
        
        with patch.object(self.engine.macro_engine, 'process_ticker_geometry', return_value=mock_result):
            result = self.engine.extract_pattern_metrics("TEST.NS")
            
            # Property: Status assignment should follow the specified rules
            if distance_percentage <= 1.0:
                assert result is not None, f"Should not exclude stock with {distance_percentage}% distance"
                assert result['status'] == "CRITICAL_TOUCH", \
                    f"Expected CRITICAL_TOUCH for {distance_percentage}% distance, got {result['status']}"
            elif distance_percentage <= 10.0:
                assert result is not None, f"Should not exclude stock with {distance_percentage}% distance"
                assert result['status'] == "WATCHLIST", \
                    f"Expected WATCHLIST for {distance_percentage}% distance, got {result['status']}"
            else:
                assert result is None, f"Should exclude stock with {distance_percentage}% distance"
    
    @given(
        trigger_price=st.floats(min_value=10.0, max_value=5000.0)
    )
    @settings(max_examples=50)
    def test_risk_parameter_calculations_property(self, trigger_price):
        """
        Property test for risk parameter calculations.
        
        For any trigger price, the stop loss should equal trigger_price × 0.92 (8% below) 
        and target exit should equal trigger_price × 1.20 (20% above), both rounded to 2 decimal places.
        """
        expected_stop_loss = round(trigger_price * 0.92, 2)
        expected_target_exit = round(trigger_price * 1.20, 2)
        
        mock_result = {
            'ticker': 'TEST',
            'currentSignal': {
                'isActive': True,
                'currentPrice': trigger_price,  # At trigger price for simplicity
                'triggerPrice': trigger_price,
                'fibLevelMatch': '50.0%',
                'patternZone': 'Test Zone',
                'confluenceScore': 5,
                'notificationTrigger': True
            },
            'positionSizing': {
                'strictStopLoss': expected_stop_loss
            },
            'trendlineDetails': {
                'numTouches': 3
            }
        }
        
        with patch.object(self.engine.macro_engine, 'process_ticker_geometry', return_value=mock_result):
            result = self.engine.extract_pattern_metrics("TEST.NS")
            
            assert result is not None, "Should return result for valid data"
            
            # Property: Stop loss should be 8% below trigger price
            assert result['stopLoss'] == expected_stop_loss, \
                f"Stop loss calculation incorrect: expected {expected_stop_loss}, got {result['stopLoss']}"
            
            # Property: Target exit should be 20% above trigger price
            assert result['targetExit'] == expected_target_exit, \
                f"Target exit calculation incorrect: expected {expected_target_exit}, got {result['targetExit']}"
    
    def test_configuration_consistency(self):
        """Test that configuration values are consistent and accessible."""
        config = self.engine.get_configuration()
        
        assert config['buffer_percentage'] == 10.0
        assert config['critical_trigger_percentage'] == 1.0
        assert config['position_size'] == 50000.0
        assert config['stop_loss_percentage'] == 8.0
        assert config['target_exit_percentage'] == 20.0


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])