#!/usr/bin/env python3
"""
Quick test of the TopDeck.gg commander extraction fix
"""

import requests
from bs4 import BeautifulSoup
import json
import re

def test_commander_extraction(url):
    """Test extracting commanders from a TopDeck.gg URL"""
    print(f"Testing: {url}")
    
    response = requests.get(url)
    if response.status_code != 200:
        print(f"❌ Failed to fetch: {response.status_code}")
        return
    
    html = response.text
    
    # Extract commanders from JavaScript deckObj
    deck_obj_match = re.search(r'const deckObj = (\{.*?\});', html, re.DOTALL)
    if deck_obj_match:
        try:
            deck_obj_str = deck_obj_match.group(1)
            deck_obj = json.loads(deck_obj_str)
            
            commanders = []
            if 'Commanders' in deck_obj:
                for card in deck_obj['Commanders']:
                    card_name = card.get('name', '')
                    quantity = card.get('count', 1)
                    for _ in range(quantity):
                        commanders.append(card_name)
                
                print(f"✅ Found {len(commanders)} commanders:")
                for cmd in commanders:
                    print(f"   - {cmd}")
            else:
                print(f"⚠️  No Commanders section in deckObj")
                
            # Also show mainboard count
            if 'Mainboard' in deck_obj:
                mainboard_count = sum(card.get('count', 1) for card in deck_obj['Mainboard'])
                print(f"✅ Found {mainboard_count} mainboard cards")
                print(f"✅ Total deck: {mainboard_count + len(commanders)} cards")
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse deckObj: {e}")
    else:
        print(f"❌ No deckObj found in HTML")

if __name__ == "__main__":
    # Test with the Kraum/Tymna deck
    test_url = "https://topdeck.gg/deck/wcg-nov-9th-2025-cedh-event-30full-proxy/cZcc0EquVhT7usEWcK5BEo5XKhX2"
    test_commander_extraction(test_url)
