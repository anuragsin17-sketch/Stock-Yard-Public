import json
c = json.load(open('trendline_cache.json'))
print(f"Cache built: {c['built_at']}")
print(f"Trendlines: {len(c['trendlines'])}")
keys = list(c['trendlines'].keys())
print(f"Sample keys: {keys[:5]}")
