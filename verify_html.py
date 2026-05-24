content = open('index.html', encoding='utf-8').read()
checks = ['Take Trade', 'takeTrade', 'saveTrendlineOverride', 'vol_entry_', 'renderRadarTab', 'placeAngelOrder', 'mergeRadarTrades']
for c in checks:
    found = c in content
    print(f"{c}: {'FOUND' if found else 'MISSING'}")
print(f"File size: {len(content)}")
