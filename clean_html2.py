#!/usr/bin/env python3
"""Clean up duplicate radar tab code from index.html"""

with open('index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the second occurrence of the empty radar check (the old duplicate)
marker = "                    <div class=\"mobile-card rounded-xl p-8 text-center\">\n                        <div class=\"text-4xl mb-4\">📡</div>"
first = content.find(marker)
second = content.find(marker, first + 1)

if second == -1:
    print("No duplicate found")
else:
    # Find the end of the old duplicate block - ends before updateTradeStatus
    end_marker = "\n        // Update trade status in radar"
    end_idx = content.find(end_marker, second)
    
    if end_idx == -1:
        print("End marker not found")
    else:
        # Remove from second occurrence start (go back to find the if statement)
        # Find the 'if (!trades' before the second marker
        if_marker = "            if (!trades || trades.length === 0) {"
        if_idx = content.rfind(if_marker, 0, second)
        
        print(f"Removing old code from pos {if_idx} to {end_idx}")
        content = content[:if_idx] + content[end_idx:]
        print(f"Removed {end_idx - if_idx} chars")

# Also fix the stray old code after removeTrade
old_stray = """        alert(`✅ ${trade.ticker} added to Radar!`);
            switchTab('performance');
        };
                
                if (currentStock) {
                    const currentPrice = currentStock.current_price;
                    const entryPrice = position.entry_price;
                    const priceChange = ((currentPrice - entryPrice) / entryPrice) * 100;
                    
                    position.current_price = currentPrice;
                    position.price_change = priceChange;
                    position.last_updated = new Date().toISOString();
                    
                    // Check if target hit (+20%)
                    if (priceChange >= 20) {
                        position.status = 'closed_target';
                        position.exit_price = currentPrice;
                        position.exit_date = new Date().toISOString();
                        position.final_return = priceChange;"""

if old_stray in content:
    content = content.replace(old_stray, "")
    print("Removed stray old code")

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print(f"Final file size: {len(content)} chars")

# Verify
checks = ['updateTradeStatus', 'removeTrade', 'renderRadarTab', 'mergeRadarTrades']
for c in checks:
    count = content.count(c)
    print(f"{c}: {count} occurrences")
