"""Quick script to inspect a single Archidekt deck's structure"""
import requests
import json

# Get one specific deck to see structure
deck_id = 7031486  # "Buffs by Hans" from our test

url = f'https://archidekt.com/api/decks/{deck_id}/'

response = requests.get(url)
print(f"Status: {response.status_code}\n")

if response.status_code == 200:
    data = response.json()
    
    # Save full JSON to inspect
    with open('data/training/sample_deck.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    
    print("Full deck JSON saved to data/training/sample_deck.json")
    print("\n=== DECK STRUCTURE ===")
    print(f"Keys: {list(data.keys())}")
    
    if 'cards' in data:
        print(f"\nCards type: {type(data['cards'])}")
        if isinstance(data['cards'], dict):
            print(f"Cards keys: {list(data['cards'].keys())}")
        elif isinstance(data['cards'], list):
            print(f"Cards is a list with {len(data['cards'])} items")
            if data['cards']:
                print(f"First card item keys: {list(data['cards'][0].keys())}")
else:
    print(f"Error: {response.text}")
