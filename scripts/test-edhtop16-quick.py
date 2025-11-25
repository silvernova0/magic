#!/usr/bin/env python3
"""Quick test of EDHTop16 JSON parsing"""

import requests
import json

url = "https://edhtop16.com/tournament/better-plays-5k-invitational"

print(f"Fetching {url}...")
response = requests.get(url, timeout=15)
html = response.text

# Find script tag
start_marker = 'window.__router_ops = '
end_marker = ';</script>'

start_idx = html.find(start_marker)
if start_idx == -1:
    print("Could not find window.__router_ops")
    exit(1)

start_idx += len(start_marker)
end_idx = html.find(end_marker, start_idx)

if end_idx == -1:
    end_idx = html.find(';', start_idx)

if end_idx == -1:
    print("Could not find end of JSON")
    exit(1)

json_str = html[start_idx:end_idx]

# Fix JavaScript-specific values that aren't valid JSON
json_str = json_str.replace(':undefined', ':null')
json_str = json_str.replace(',undefined', ',null')

print(f"\nJSON length: {len(json_str)} characters")

try:
    data = json.loads(json_str)
    print(f"✓ JSON parsed successfully")
    print(f"Data type: {type(data)}")
    print(f"Length: {len(data) if isinstance(data, list) else 'N/A'}")
    
    # Navigate to tournament
    if isinstance(data, list) and len(data) >= 2:
        for item in data:
            if isinstance(item, list) and len(item) >= 2:
                response_data = item[1]
                if isinstance(response_data, dict) and 'tournament' in response_data:
                    tournament = response_data['tournament']
                    print(f"\n✓ Found tournament data:")
                    print(f"  Name: {tournament.get('name')}")
                    print(f"  Size: {tournament.get('size')}")
                    print(f"  Date: {tournament.get('tournamentDate')}")
                    print(f"  Entries: {len(tournament.get('entries', []))}")
                    
                    # Show first entry
                    entries = tournament.get('entries', [])
                    if entries:
                        first = entries[0]
                        print(f"\n  First entry:")
                        print(f"    Player: {first.get('player', {}).get('name')}")
                        print(f"    Commander: {first.get('commander', {}).get('name')}")
                        print(f"    Standing: {first.get('standing')}")
                        print(f"    Record: {first.get('wins')}-{first.get('losses')}-{first.get('draws')}")
                    break
                    
except json.JSONDecodeError as e:
    print(f"✗ JSON parse error: {e}")
    print(f"  Position: {e.pos}")
    print(f"  Context: ...{json_str[max(0, e.pos-50):e.pos+50]}...")
