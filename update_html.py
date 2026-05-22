import json
import re
import os

if os.path.exists("data.json"):
    print("Updating HTML with latest screening data...")
    
    # Read the latest data
    with open("data.json", "r", encoding="utf-8") as f:
        latest_data = json.load(f)

    # Read the HTML file
    with open("index.html", "r", encoding="utf-8") as f:
        html_content = f.read()

    # Update the embedded LIVE_DATA with a more robust pattern
    data_str = json.dumps(latest_data, indent=2)
    
    # Find the start and end of LIVE_DATA
    start_pattern = r"const LIVE_DATA = "
    end_pattern = r";\s*\n\s*// Global variables"
    
    # Use a more flexible regex that captures everything between the patterns
    pattern = r"(const LIVE_DATA = )(\{.*?\})(;\s*\n\s*// Global variables)"
    replacement = r"\1" + data_str + r"\3"
    
    # Replace the embedded data
    updated_html = re.sub(pattern, replacement, html_content, flags=re.DOTALL)

    # Write back to HTML
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(updated_html)

    print("HTML updated successfully via script!")
    print(f"Embedded {len(latest_data.get('golden_stocks', []))} Golden Stocks")
    print(f"Embedded {len(latest_data.get('volume_breakout_stocks', []))} Volume Breakout Stocks")
    print(f"Embedded {len(latest_data.get('w_pattern_stocks', []))} W-Pattern Stocks")
    print(f"Embedded {len(latest_data.get('elliott_wave_stocks', []))} Elliott Wave Stocks")
else:
    print("data.json not found, skipping HTML update.")
