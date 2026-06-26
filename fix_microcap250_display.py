#!/usr/bin/env python3
"""
Script to replace the simplified displayMicrocap250Screen function
with a complete copy of displayTrendlineScreen logic
"""

import re

# Read the index.html file
with open('index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the displayTrendlineScreen function
trendline_pattern = r'(async function displayTrendlineScreen\(\) \{.*?\n        \})\s*\n\s*\n\s*// ─── PAST PERFORMANCE TAB'
match = re.search(trendline_pattern, content, re.DOTALL)

if not match:
    print("ERROR: Could not find displayTrendlineScreen function")
    exit(1)

trendline_function = match.group(1)
print(f"✅ Found displayTrendlineScreen function ({len(trendline_function)} chars)")

# Create microcap250 version by replacing key terms
microcap250_function = trendline_function

replacements = [
    ('displayTrendlineScreen', 'displayMicrocap250Screen'),
    ('TRENDLINE', 'MICROCAP250'),
    ('trendline', 'microcap250'),
    ('Trendline', 'Microcap250'),
    ("'trendline'", "'microcap250'"),
    ('trendlineStocks', 'microcap250Stocks'),
    ('trendline_screen.json', 'microcap250_screen.json'),
    ('trendShowAll', 'microcap250ShowAll'),
    ('trendPage', 'microcap250Page'),
    ('trendSearch', 'microcap250Search'),
    ('TL', 'MC250'),  # For variable names like tl52w
    ('filteredTrendStocks', 'filteredMicrocap250Stocks'),
    ('pagedTrendStocks', 'pagedMicrocap250Stocks'),
    ('trendTotalPages', 'microcap250TotalPages'),
    ('updateTrendlineDist', 'updateMicrocap250Dist'),
    ('saveTrendlineOverride', 'saveMicrocap250Override'),
    ('dismissTrendlineStock', 'dismissMicrocap250Stock'),
    ('toggleTrendSearch', 'toggleMicrocap250Search'),
    ('trendline52wCache', 'microcap250_52wCache'),
    ('trendline_dismissed', 'microcap250_dismissed'),
]

for old, new in replacements:
    microcap250_function = microcap250_function.replace(old, new)

print(f"✅ Created displayMicrocap250Screen function ({len(microcap250_function)} chars)")

# Find the current simplified displayMicrocap250Screen and replace it
simple_pattern = r'async function displayMicrocap250Screen\(\) \{.*?\n        \}\s*\n\s*\n\s*// ─── PAST PERFORMANCE TAB'
simple_match = re.search(simple_pattern, content, re.DOTALL)

if not simple_match:
    print("ERROR: Could not find existing displayMicrocap250Screen function")
    exit(1)

print(f"✅ Found existing simplified displayMicrocap250Screen ({len(simple_match.group(0))} chars)")

# Replace it
new_content = content.replace(simple_match.group(0), microcap250_function + '\n        \n        // ─── PAST PERFORMANCE TAB')

# Write back
with open('index.html', 'w', encoding='utf-8') as f:
    f.write(new_content)

print(f"✅ Updated index.html (size: {len(new_content)} chars)")
print("✅ Done! The displayMicrocap250Screen function now has all features from Trendline tab.")
