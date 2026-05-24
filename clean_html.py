#!/usr/bin/env python3
"""Clean up old position tracking code from index.html"""

with open('index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the marker where old code starts (after removeTrade function)
old_start = '            });\n            \n            // Save updated positions\n            localStorage.setItem(\'stockPositions\''
old_end = '            localStorage.setItem(\'stockPositions\', JSON.stringify(positions));\n            \n            alert(`✅ ${trade.ticker} added to Radar!`);\n            switchTab(\'performance\');\n        };\n    </script>'

new_end = '    </script>'

if old_start in content and old_end in content:
    # Remove everything from old_start to old_end, replace with just closing
    idx_start = content.find(old_start)
    idx_end = content.find(old_end) + len(old_end)
    content = content[:idx_start] + new_end + '\n</body>\n</html>'
    print(f"Removed {idx_end - idx_start} chars of old code")
else:
    print("Pattern not found - checking...")
    if old_start in content:
        print("Start found")
    else:
        print("Start NOT found")
    if old_end in content:
        print("End found")
    else:
        print("End NOT found")

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print(f"Final file size: {len(content)} chars")
