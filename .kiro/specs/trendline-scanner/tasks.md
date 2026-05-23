# Implementation Plan: Trendline Scanner

## Overview

This implementation plan creates a comprehensive trendline scanning system that identifies high-probability entry opportunities in Nifty 500 stocks by detecting when prices approach long-term monthly trendline support levels within institutional buying zones. The system builds upon the existing `MacroInstitutionalEngine` and `EditableTriggerEngine` classes while introducing a new `GeometricTrendlineEngine` interface to meet the specific requirements for trendline detection and pattern analysis.

The implementation follows a modular approach with clear separation between the analysis engine, backend scanner, frontend dashboard, and alert system components.

## Tasks

- [ ] 1. Create GeometricTrendlineEngine interface and adapter
  - Create `geometric_trendline_engine.py` with the `GeometricTrendlineEngine` class
  - Implement adapter pattern to wrap existing `MacroInstitutionalEngine` functionality
  - Add `extract_pattern_metrics` method that returns simplified data structure for scanner
  - Configure buffer_percentage (10.0) and critical_trigger_percentage (1.0) parameters
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 7.1, 7.2_

  - [ ]* 1.1 Write property test for minimum data requirement
    - **Property 1: Trendline Detection Requires Minimum Data**
    - **Validates: Requirements 1.1, 9.1**

  - [ ]* 1.2 Write property test for trendline validation
    - **Property 2: Trendline Validation Requires Minimum Touch Points**
    - **Validates: Requirements 1.3**

  - [ ]* 1.3 Write property test for trigger price projection
    - **Property 3: Trigger Price Projection Accuracy**
    - **Validates: Requirements 1.4**

- [ ] 2. Implement Fibonacci grid mapping and analysis
  - [ ] 2.1 Create `fibonacci_analyzer.py` with FibonacciGrid and FibonacciAnalysis classes
    - Implement touchback base and peak identification logic
    - Calculate five Fibonacci retracement levels (23.6%, 38.2%, 50.0%, 61.8%, 100%)
    - Add intersection detection between trendline and Fibonacci zones
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [ ]* 2.2 Write property test for Fibonacci level calculations
    - **Property 4: Fibonacci Level Calculation Accuracy**
    - **Validates: Requirements 2.3**

  - [ ]* 2.3 Write property test for Fibonacci zone filtering
    - **Property 12: Fibonacci Zone Filtering**
    - **Validates: Requirements 2.5, 3.5**

- [ ] 3. Create main backend scanner with entry point identification
  - [ ] 3.1 Create `trendline_scanner.py` with TrendlineScanner class
    - Implement Nifty 500 stock universe iteration
    - Add distance percentage calculation and status assignment logic
    - Implement filtering for stocks within 10% of trendline trigger price
    - Add CRITICAL_TOUCH (≤1%) and WATCHLIST (1-10%) status assignment
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

  - [ ]* 3.2 Write property test for distance percentage calculation
    - **Property 5: Distance Percentage Calculation**
    - **Validates: Requirements 3.1, 4.5**

  - [ ]* 3.3 Write property test for status assignment
    - **Property 6: Status Assignment Based on Distance**
    - **Validates: Requirements 3.2, 3.3, 3.4**

- [ ] 4. Implement risk management and position sizing
  - [ ] 4.1 Add risk parameter calculation methods to TrendlineScanner
    - Implement fixed ₹50,000 position sizing
    - Calculate 8% stop loss below trigger price
    - Calculate 20% target exit above trigger price
    - Add share quantity calculation based on position size
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [ ]* 4.2 Write property test for risk parameter calculations
    - **Property 7: Risk Parameter Calculations**
    - **Validates: Requirements 4.2, 4.3**

  - [ ]* 4.3 Write property test for position sizing consistency
    - **Property 8: Position Sizing Consistency**
    - **Validates: Requirements 4.1**

- [ ] 5. Create JSON output generation and data formatting
  - [ ] 5.1 Implement JSON output generator in TrendlineScanner
    - Create `generate_json_output` method that writes to `trendline_screen.json`
    - Implement ticker symbol cleaning (remove ".NS" suffix)
    - Add price rounding to 2 decimal places
    - Implement result sorting by distance percentage (ascending)
    - Add stock filtering to exclude non-qualifying stocks
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7_

  - [ ]* 5.2 Write property test for JSON output structure
    - **Property 9: JSON Output Structure Validation**
    - **Validates: Requirements 5.3, 5.4**

  - [ ]* 5.3 Write property test for numerical precision
    - **Property 10: Numerical Precision in Output**
    - **Validates: Requirements 5.5**

  - [ ]* 5.4 Write property test for result sorting
    - **Property 11: Result Sorting Consistency**
    - **Validates: Requirements 5.6, 6.6**

- [ ] 6. Checkpoint - Ensure backend scanner functionality
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 7. Create frontend HTML dashboard
  - [ ] 7.1 Create `trendline_screen.html` with responsive table layout
    - Implement sortable table with columns: Ticker, Current Price, Expected Entry Trigger, Distance Remaining, Expected Target Exit, System Status
    - Add Indian Rupee (₹) currency formatting for all price displays
    - Implement status badge system with red animated "🎯 CRITICAL ENTRY" and yellow "👀 WATCHLIST" badges
    - Add auto-refresh functionality with 5-minute intervals
    - Display last refresh timestamp in header area
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 6.9_

  - [ ]* 7.2 Write property test for currency formatting
    - **Property 15: Currency Formatting Consistency**
    - **Validates: Requirements 6.3**

- [ ] 8. Implement JavaScript data loading and table rendering
  - [ ] 8.1 Create JavaScript modules for data management
    - Implement `TrendlineDataLoader` class for JSON data fetching
    - Create `TrendlineTableRenderer` class for table display and formatting
    - Add error handling for failed JSON loads with user-friendly error messages
    - Implement automatic data refresh every 5 minutes
    - Add sorting functionality for table columns
    - _Requirements: 6.1, 6.2, 6.6, 6.7, 6.8, 6.9_

- [ ] 9. Integrate alert system with Telegram notifications
  - [ ] 9.1 Create `alert_system.py` with TrendlineAlertSystem class
    - Implement Telegram bot integration using existing infrastructure
    - Add critical entry notification for CRITICAL_TOUCH status stocks
    - Include ticker symbol and entry message in notifications
    - Add non-blocking alert sending with error logging
    - Implement graceful degradation when alert system fails
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

  - [ ]* 9.2 Write property test for alert triggering logic
    - **Property 14: Alert Triggering Logic**
    - **Validates: Requirements 8.1, 8.2**

- [ ] 10. Add comprehensive error handling and data quality validation
  - [ ] 10.1 Enhance error handling throughout the system
    - Add insufficient data handling (< 24 months) with warning logs
    - Implement empty yfinance data handling with stock skipping
    - Add GeometricTrendlineEngine None result handling
    - Implement error logging with ticker identification
    - Add execution completion success messages
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

  - [ ]* 10.2 Write property test for error handling continuity
    - **Property 13: Error Handling Continuity**
    - **Validates: Requirements 7.5, 8.4, 9.2, 9.3**

- [ ] 11. Create main execution script and Nifty 500 integration
  - [ ] 11.1 Create `run_trendline_scanner.py` main execution script
    - Implement Nifty 500 stock list loading or hardcoded list
    - Add main execution loop that processes all 500 stocks
    - Integrate GeometricTrendlineEngine instantiation with correct parameters
    - Add progress logging and execution timing
    - Implement standalone script execution and importable function capability
    - _Requirements: 5.1, 7.3, 7.4, 10.1, 10.2, 10.5_

- [ ] 12. Performance optimization and scalability enhancements
  - [ ] 12.1 Optimize scanner performance for 500-stock processing
    - Add appropriate delays between API calls to respect rate limits
    - Implement retry logic with exponential backoff for failed requests
    - Add timeout handling for long-running data fetches
    - Optimize data processing algorithms for faster execution
    - Add progress indicators and estimated completion time
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

- [ ] 13. Integration testing and system validation
  - [ ] 13.1 Create integration test suite
    - Test complete workflow from data fetching to JSON generation
    - Validate frontend dashboard loading and display functionality
    - Test alert system integration with mock Telegram service
    - Verify error handling with various data quality scenarios
    - Test performance with subset of Nifty 500 stocks
    - _Requirements: All requirements validation_

  - [ ]* 13.2 Write integration tests for complete workflow
    - Test end-to-end scanning process with sample stocks
    - Validate JSON output format and frontend compatibility
    - Test alert system integration and error handling

- [ ] 14. Final system integration and wiring
  - [ ] 14.1 Wire all components together and create deployment package
    - Ensure all modules import correctly and dependencies are satisfied
    - Create configuration file for system parameters (position size, tolerances, etc.)
    - Add command-line interface for running scanner with different options
    - Create documentation for system setup and execution
    - Test complete system with live data and verify all functionality
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [ ] 15. Final checkpoint - Complete system validation
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at key milestones
- Property tests validate universal correctness properties from the design document
- Integration tests validate complete system behavior and user interface functionality
- The system builds upon existing `MacroInstitutionalEngine` and `EditableTriggerEngine` classes
- All price calculations use 2 decimal precision and Indian Rupee formatting
- The scanner processes all Nifty 500 stocks with appropriate error handling and performance optimization