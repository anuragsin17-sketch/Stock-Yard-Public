import json

# Read the data
with open('data.json', 'r') as f:
    data = json.load(f)

# Check all pattern types to see which have both Fibonacci and Trendline
golden_candidates = []

# Check volume_breakout_stocks
for stock in data.get('volume_breakout_stocks', []):
    if 'fibonacci_level' in stock and 'trendline_price' in stock:
        golden_candidates.append({
            'symbol': stock['symbol'],
            'company': stock['company_name'],
            'pattern': 'volume_breakout',
            'fib_level': stock.get('fibonacci_level'),
            'trendline': stock.get('trendline_price'),
            'vertical_line': stock.get('vertical_line_price'),
            'current_price': stock.get('current_price')
        })

# Check w_pattern_stocks
for stock in data.get('w_pattern_stocks', []):
    if 'fibonacci_level' in stock and 'trendline_price' in stock:
        golden_candidates.append({
            'symbol': stock['symbol'],
            'company': stock['company_name'],
            'pattern': 'w_pattern',
            'fib_level': stock.get('fibonacci_level'),
            'trendline': stock.get('trendline_price'),
            'vertical_line': stock.get('vertical_line_price'),
            'current_price': stock.get('current_price')
        })

# Check elliott_wave_stocks
for stock in data.get('elliott_wave_stocks', []):
    if 'fibonacci_level' in stock and 'trendline_price' in stock:
        golden_candidates.append({
            'symbol': stock['symbol'],
            'company': stock['company_name'],
            'pattern': 'elliott_wave',
            'fib_level': stock.get('fibonacci_level'),
            'trendline': stock.get('trendline_price'),
            'vertical_line': stock.get('vertical_line_price'),
            'current_price': stock.get('current_price')
        })

print(f'Total stocks with Fibonacci + Trendline: {len(golden_candidates)}')
print()
print(f"{'Symbol':<15} {'Company':<40} {'Fib Level':<10} {'Trendline':<12} {'VLine':<12} {'Price':<10}")
print("="*110)
for stock in golden_candidates:
    vline = str(stock['vertical_line']) if stock['vertical_line'] else 'None'
    print(f"{stock['symbol']:<15} {stock['company'][:40]:<40} {str(stock['fib_level']):<10} {str(stock['trendline']):<12} {vline:<12} {str(stock['current_price']):<10}")
