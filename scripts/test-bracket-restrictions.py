
import sys
import os
import json
import sqlite3
from pathlib import Path

# Add scripts directory to path
sys.path.append(os.path.join(os.getcwd(), 'scripts'))

# Import DeckBuilder (we'll need to make sure it's importable or mock it)
# Since build-deck-from-structure.py is a script, we might need to import it carefully
# or just use the logic directly if it's not easily importable.
# Ideally, we should refactor build-deck-from-structure.py to be a module, but for now 
# we can try to import the class if it's in the global scope or use exec.

# Actually, let's just use the DeckBuilder class from the file. 
# We can import it if we rename the file or add it to python path.
# It is in scripts/build-deck-from-structure.py.

import importlib.util
spec = importlib.util.spec_from_file_location("DeckBuilderModule", "scripts/build-deck-from-structure.py")
deck_builder_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deck_builder_module)
DeckBuilder = deck_builder_module.DeckBuilder

def test_bracket_restrictions():
    print("🧪 Testing Bracket Restrictions...")
    
    db_path = "prisma/dev.db"
    builder = DeckBuilder(db_path=db_path)
    # Set colors to WUBRG to allow all cards for testing
    builder.commander_colors = {'W', 'U', 'B', 'R', 'G'}
    
    # Test Case 1: Bracket 2 (Casual) - Should exclude expensive cards and staples
    print("\n📋 Test Case 1: Bracket 2 (Casual)")
    
    # Mock structure for a simple deck
    structure_b2 = {
        "commander": "Lavinia, Azorius Renegade",
        "strategy": "control",
        "power_level": 5,
        "bracket": 2,
        "card_selection": {
            "ramp": {"count": 10, "filters": [{"tags": ["ramp"]}]},
            "draw": {"count": 10, "filters": [{"tags": ["draw"]}]}
        }
    }
    
    # We want to check if query_cards filters out expensive stuff
    # We can call query_cards directly with the bracket context if we modify the class
    # For now, let's just check if we can find "Mana Crypt" or "Cyclonic Rift" with bracket 2 settings
    
    # NOTE: The current implementation doesn't take bracket in __init__, it takes it in build_deck
    # But query_cards doesn't take bracket. We need to modify query_cards to take bracket or 
    # set it on the instance.
    
    # Let's simulate what we WANT to happen.
    # We will modify DeckBuilder to accept 'bracket' in query_cards or set it on the instance.
    
    # For this test to be useful BEFORE implementation, we can just check if high power cards exist in DB
    # and if the current builder would include them.
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    high_power_cards = ["Mana Crypt", "Cyclonic Rift", "Rhystic Study", "Dockside Extortionist"]
    print(f"Checking for high power cards in DB: {high_power_cards}")
    
    for card in high_power_cards:
        cursor.execute("SELECT name, prices FROM Card WHERE name = ?", (card,))
        row = cursor.fetchone()
        if row:
            prices = json.loads(row['prices']) if row['prices'] else {}
            usd = float(prices.get('usd', 0) or 0)
            print(f"  - {card}: ${usd:.2f}")
        else:
            print(f"  - {card}: Not found in DB")
            
    # Now let's try to query for them using the builder's logic with Bracket 2
    print("\nQuerying for 'ramp' with Bracket 2 (expecting Mana Crypt to be EXCLUDED)...")
    # We need to pass bracket=2 to query_cards
    results = builder.query_cards([{"names": ["Mana Crypt"]}], limit=1, bracket=2)
    if results:
        print(f"  ❌ Found Mana Crypt in results! (FAILED: Should be banned)")
    else:
        print(f"  ✅ Mana Crypt not found (PASSED: Banned/Excluded)")

    print("\nQuerying for 'Cyclonic Rift' with Bracket 2 (expecting EXCLUDED due to price/banlist)...")
    results = builder.query_cards([{"names": ["Cyclonic Rift"]}], limit=1, bracket=2)
    if results:
         print(f"  ❌ Found Cyclonic Rift in results! (FAILED: Should be excluded)")
    else:
         print(f"  ✅ Cyclonic Rift not found (PASSED: Excluded)")

    print("\nQuerying for 'Rhystic Study' with Bracket 2 (expecting EXCLUDED due to price/banlist)...")
    results = builder.query_cards([{"names": ["Rhystic Study"]}], limit=1, bracket=2)
    if results:
         print(f"  ❌ Found Rhystic Study in results! (FAILED: Should be excluded)")
    else:
         print(f"  ✅ Rhystic Study not found (PASSED: Excluded)")

    # Test Bracket 5 (Should allow everything)
    print("\n📋 Test Case 2: Bracket 5 (cEDH)")
    print("Querying for 'Mana Crypt' with Bracket 5 (expecting INCLUDED)...")
    results = builder.query_cards([{"names": ["Mana Crypt"]}], limit=1, bracket=5)
    if results:
        print(f"  ✅ Found Mana Crypt in results! (PASSED)")
    else:
        print(f"  ⚠️  Mana Crypt not found (Maybe banned in DB data?)")

    print("Querying for 'Cyclonic Rift' with Bracket 5 (expecting INCLUDED)...")
    results = builder.query_cards([{"names": ["Cyclonic Rift"]}], limit=1, bracket=5)
    if results:
        print(f"  ✅ Found Cyclonic Rift in results! (PASSED)")
    else:
        print(f"  ❌ Cyclonic Rift not found (FAILED)")


if __name__ == "__main__":
    test_bracket_restrictions()
