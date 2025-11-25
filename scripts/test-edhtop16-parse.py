#!/usr/bin/env python3
"""Test script to understand EDHTop16 JSON structure"""

import requests
import json
import re

url = "https://edhtop16.com/tournament/better-plays-5k-invitational"

print(f"Fetching {url}...")
response = requests.get(url)
html = response.text

# Find the window.__router_ops data
match = re.search(r'window\.__router_ops\s*=\s*({.*?});?\s*</script>', html, re.DOTALL)

if match:
    json_str = match.group(1)
    
    # Parse JSON
    try:
        data = json.loads(json_str)
        
        # Navigate to tournament data
        if 'data' in data:
            tournament_data = data['data']
            
            # Print structure
            print("\nTop-level keys:")
            print(json.dumps(list(tournament_data.keys()), indent=2))
            
            # Look for tournament info
            if 'tournament' in tournament_data:
                tournament = tournament_data['tournament']
                print("\nTournament keys:")
                print(json.dumps(list(tournament.keys()), indent=2))
                
                print(f"\nTournament name: {tournament.get('name', 'N/A')}")
                print(f"Size: {tournament.get('size', 'N/A')}")
                print(f"Date: {tournament.get('tournamentDate', 'N/A')}")
                
                if 'entries' in tournament:
                    entries = tournament['entries']
                    print(f"\nTotal entries: {len(entries)}")
                    
                    if entries:
                        print("\nFirst entry structure:")
                        print(json.dumps(entries[0], indent=2)[:1000])
                        
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        print(f"At position: {json_str[max(0, e.pos-50):e.pos+50]}")
else:
    print("Could not find window.__router_ops")
