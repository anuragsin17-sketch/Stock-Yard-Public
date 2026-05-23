# Requirements Document

## Introduction

The Macro Monthly Trendline Entry Scanner is a stock screening system that identifies high-probability entry opportunities in Nifty 500 stocks by detecting when prices approach long-term monthly trendline support levels within institutional buying zones (Fibonacci retracement levels). The system provides traders with actionable entry signals, risk management parameters, and target exit prices through an auto-refreshing HTML dashboard with optional Telegram alerts.

## Glossary

- **Scanner**: The complete trendline screening system including backend analysis and frontend display
- **GeometricTrendlineEngine**: Existing Python class that performs trendline detection and pattern analysis
- **Trendline**: A geometric line connecting historical support anchor troughs on monthly timeframe
- **Fibonacci_Grid**: Five horizontal price levels (23.6%, 38.2%, 50.0%, 61.8%, and 100%) mapped from touchback base to maximum peak
- **Institutional_Buying_Zone**: Price regions defined by Fibonacci retracement levels where institutional accumulation typically occurs
- **Trigger_Price**: The calculated price level where the trendline intersects with current time period
- **CRITICAL_TOUCH**: Status indicating price is within 1% of trendline trigger price
- **WATCHLIST**: Status indicating price is within 10% but beyond 1% of trendline trigger price
- **Backend_Scanner**: Python function that analyzes Nifty 500 stocks and generates JSON output
- **Frontend_Dashboard**: HTML/JavaScript interface that displays screening results
- **Nifty_500**: The universe of 500 stocks to be scanned
- **Position_Size**: Fixed investment amount of ₹50,000 per trade
- **Stop_Loss**: Risk management exit at 8% below entry price
- **Target_Exit**: Profit-taking exit at the identified pivot peak price
- **Alert_System**: Telegram notification mechanism for critical entry signals

## Requirements

### Requirement 1: Trendline Detection and Analysis

**User Story:** As a trader, I want the system to detect long-term monthly trendlines using historical support points, so that I can identify stocks with established geometric support patterns.

#### Acceptance Criteria

1. WHEN the Backend_Scanner analyzes a stock, THE GeometricTrendlineEngine SHALL identify ascending trendlines using monthly low prices from at least 24 months of historical data
2. THE GeometricTrendlineEngine SHALL locate significant support anchor troughs by identifying local minima within a 2-month rolling window
3. WHEN calculating trendline validity, THE GeometricTrendlineEngine SHALL require at least 3 touch points within 2% tolerance of the trendline
4. THE GeometricTrendlineEngine SHALL calculate the current Trigger_Price by projecting the trendline to the present time period
5. WHEN multiple potential trendlines exist, THE GeometricTrendlineEngine SHALL select the trendline with the highest strength score based on touch count, timeframe duration, and slope consistency

### Requirement 2: Fibonacci Grid Mapping

**User Story:** As a trader, I want the system to map Fibonacci retracement levels from the last major touchback to the peak, so that I can identify institutional buying zones.

#### Acceptance Criteria

1. THE Scanner SHALL identify the last major touchback base as the starting point for Fibonacci_Grid calculation
2. THE Scanner SHALL identify the maximum peak following the touchback base as the ending point for Fibonacci_Grid calculation
3. THE Scanner SHALL calculate five Fibonacci retracement levels at 23.6%, 38.2%, 50.0%, 61.8%, and 100% between the base and peak
4. THE Scanner SHALL determine whether the Trigger_Price intersects within any of the five Fibonacci retracement zones
5. WHEN the Trigger_Price falls outside all Fibonacci zones, THE Scanner SHALL exclude the stock from screening results

### Requirement 3: Entry Point Identification and Filtering

**User Story:** As a trader, I want the system to identify stocks where the trendline touch point intersects inside institutional buying pockets, so that I can focus on high-probability setups.

#### Acceptance Criteria

1. WHEN the Backend_Scanner evaluates a stock, THE Scanner SHALL calculate the distance percentage between current price and Trigger_Price
2. IF the distance percentage is greater than 10%, THEN THE Scanner SHALL exclude the stock from results
3. IF the distance percentage is less than or equal to 1%, THEN THE Scanner SHALL assign status CRITICAL_TOUCH
4. IF the distance percentage is greater than 1% and less than or equal to 10%, THEN THE Scanner SHALL assign status WATCHLIST
5. THE Scanner SHALL include only stocks where Trigger_Price intersects within Institutional_Buying_Zone boundaries

### Requirement 4: Risk Management Parameter Calculation

**User Story:** As a trader, I want the system to calculate position sizing and risk parameters automatically, so that I can maintain consistent risk management across all trades.

#### Acceptance Criteria

1. THE Scanner SHALL use a fixed Position_Size of ₹50,000 for all trade calculations
2. THE Scanner SHALL calculate Stop_Loss as 8% below the Trigger_Price
3. THE Scanner SHALL calculate Target_Exit as 20% above the Trigger_Price
4. THE Scanner SHALL include Trigger_Price, Stop_Loss, and Target_Exit in the output data for each stock
5. THE Scanner SHALL express distance to Trigger_Price as a percentage value rounded to 2 decimal places

### Requirement 5: Backend Data Generation and JSON Output

**User Story:** As a system administrator, I want the backend to scan all Nifty 500 stocks and generate a structured JSON file, so that the frontend can display current screening results.

#### Acceptance Criteria

1. THE Backend_Scanner SHALL iterate through all stocks in the Nifty_500 universe
2. WHEN the Backend_Scanner completes analysis, THE Backend_Scanner SHALL write results to a file named trendline_screen.json
3. THE trendline_screen.json file SHALL contain an array of stock objects with fields: ticker, currentPrice, triggerPrice, distance, targetExit, and status
4. THE Backend_Scanner SHALL remove the ".NS" suffix from ticker symbols in the JSON output
5. THE Backend_Scanner SHALL round all price values to 2 decimal places in the JSON output
6. THE Backend_Scanner SHALL sort results by distance percentage in ascending order before writing to JSON
7. WHEN a stock does not meet screening criteria, THE Backend_Scanner SHALL exclude it from the JSON output

### Requirement 6: Frontend Dashboard Display

**User Story:** As a trader, I want to view screening results in a sortable HTML table that auto-refreshes, so that I can monitor opportunities throughout the trading day.

#### Acceptance Criteria

1. THE Frontend_Dashboard SHALL load data from trendline_screen.json file
2. THE Frontend_Dashboard SHALL display results in a table with columns: Ticker, Current Price, Expected Entry Trigger, Distance Remaining, Expected Target Exit, and System Status
3. THE Frontend_Dashboard SHALL display prices in Indian Rupee format with ₹ symbol
4. WHEN status is CRITICAL_TOUCH, THE Frontend_Dashboard SHALL display a red animated badge with text "🎯 CRITICAL ENTRY"
5. WHEN status is WATCHLIST, THE Frontend_Dashboard SHALL display a yellow badge with text "👀 WATCHLIST"
6. THE Frontend_Dashboard SHALL sort displayed results by distance percentage in ascending order
7. THE Frontend_Dashboard SHALL refresh data automatically every 5 minutes
8. THE Frontend_Dashboard SHALL display the last refresh timestamp in the header area
9. WHEN the JSON file cannot be loaded, THE Frontend_Dashboard SHALL display an error message indicating data source failure

### Requirement 7: Integration with Existing Infrastructure

**User Story:** As a developer, I want the scanner to integrate seamlessly with existing codebase components, so that I can leverage proven functionality and maintain code consistency.

#### Acceptance Criteria

1. THE Backend_Scanner SHALL import and instantiate GeometricTrendlineEngine from geometric_engine.py
2. THE Backend_Scanner SHALL call the extract_pattern_metrics method for each stock in the scanning loop
3. THE Backend_Scanner SHALL initialize GeometricTrendlineEngine with buffer_percentage of 10.0 and critical_trigger_percentage of 1.0
4. THE Backend_Scanner SHALL use the existing yfinance library for fetching historical stock data
5. THE Backend_Scanner SHALL handle exceptions from GeometricTrendlineEngine gracefully and continue processing remaining stocks

### Requirement 8: Alert System Integration

**User Story:** As a trader, I want to receive Telegram notifications when stocks reach critical entry levels, so that I can act on time-sensitive opportunities immediately.

#### Acceptance Criteria

1. WHEN the Backend_Scanner identifies a stock with status CRITICAL_TOUCH, THE Alert_System SHALL trigger a Telegram notification
2. THE Telegram notification SHALL include the ticker symbol and a message indicating critical trendline entry target reached
3. THE Alert_System SHALL use the existing Telegram notification infrastructure in the codebase
4. THE Backend_Scanner SHALL provide a hook point for Alert_System integration without blocking the scanning process
5. IF the Alert_System fails to send a notification, THE Backend_Scanner SHALL log the error and continue processing

### Requirement 9: Data Quality and Error Handling

**User Story:** As a system administrator, I want the scanner to handle data quality issues gracefully, so that the system remains reliable even when individual stock data is unavailable or invalid.

#### Acceptance Criteria

1. WHEN a stock has insufficient historical data (less than 24 months), THE Backend_Scanner SHALL skip the stock and log a warning
2. WHEN yfinance returns empty data for a stock, THE Backend_Scanner SHALL skip the stock and continue processing
3. WHEN GeometricTrendlineEngine returns None for a stock, THE Backend_Scanner SHALL exclude the stock from results without raising an error
4. THE Backend_Scanner SHALL log all errors with stock ticker identification for debugging purposes
5. WHEN the Backend_Scanner completes execution, THE Backend_Scanner SHALL print a success message indicating JSON file update completion

### Requirement 10: Performance and Scalability

**User Story:** As a system administrator, I want the scanner to process all Nifty 500 stocks efficiently, so that results are available within a reasonable timeframe.

#### Acceptance Criteria

1. THE Backend_Scanner SHALL process the complete Nifty_500 universe in a single execution
2. THE Backend_Scanner SHALL complete execution within 15 minutes for 500 stocks under normal network conditions
3. THE Frontend_Dashboard SHALL load and render the JSON data within 2 seconds on standard web browsers
4. THE Frontend_Dashboard SHALL handle up to 100 stocks in the results table without performance degradation
5. THE Backend_Scanner SHALL be executable as a standalone script or importable function for scheduled automation
