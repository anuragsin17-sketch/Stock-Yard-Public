import json
import re
import os

if os.path.exists("data.json"):
    print("Updating HTML with latest screening data...")
    
    # Read the latest data
    with open("data.json", "r") as f:
        latest_data = json.load(f)

    # Read the HTML file
    with open("index.html", "r") as f:
        html_content = f.read()

    # Update the embedded LIVE_DATA
    data_str = json.dumps(latest_data, indent=2)
    pattern = r"const LIVE_DATA = \{[^}]+\};"
    replacement = f"const LIVE_DATA = {data_str};"

    # Replace the embedded data
    updated_html = re.sub(pattern, replacement, html_content, flags=re.DOTALL)

    # Write back to HTML
    with open("index.html", "w") as f:
        f.write(updated_html)

    print("HTML updated successfully via script!")
else:
    print("data.json not found, skipping HTML update.")
