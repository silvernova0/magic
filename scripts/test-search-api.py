import requests
import json
import sys

API_URL = "http://localhost:3000/api/cards/search"

def test_search(name):
    print(f"Testing search for: {name}...")
    try:
        response = requests.get(f"{API_URL}?name={name}&isCommander=true&limit=1")
        if response.status_code != 200:
            print(f"❌ FAILED: Status {response.status_code}")
            return False
            
        data = response.json()
        cards = data.get('cards', [])
        
        if not cards:
            print("❌ FAILED: No cards found")
            return False
            
        card = cards[0]
        print(f"Found card: {card.get('name')}")
        print(f"Color Identity: {card.get('colorIdentity')} (Type: {type(card.get('colorIdentity'))})")
        
        if 'colorIdentity' in card and isinstance(card['colorIdentity'], list):
            print("✅ PASSED: colorIdentity is a list")
            return True
        else:
            print("❌ FAILED: colorIdentity missing or not a list")
            return False
            
    except Exception as e:
        print(f"❌ FAILED: Error: {e}")
        return False

if __name__ == "__main__":
    if test_search("Thrasios"):
        sys.exit(0)
    else:
        sys.exit(1)
