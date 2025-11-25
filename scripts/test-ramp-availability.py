
import sys
import os
import json
import sqlite3
from pathlib import Path

# Add scripts directory to path
sys.path.append(os.path.join(os.getcwd(), 'scripts'))

import importlib.util
spec = importlib.util.spec_from_file_location("DeckBuilderModule", "scripts/build-deck-from-structure.py")
deck_builder_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deck_builder_module)
DeckBuilder = deck_builder_module.DeckBuilder

def test_ramp_availability():
    print("🧪 Testing Ramp Availability in Bracket 1...")
    
    db_path = "prisma/dev.db"
    builder = DeckBuilder(db_path=db_path)
    # Set colors to WUBRG to allow all cards for testing
    builder.commander_colors = {'W', 'U', 'B', 'R', 'G'}
    
    ramp_staples = ["Sol Ring", "Arcane Signet", "Fellwar Stone"]
    
    for card in ramp_staples:
        print(f"\nChecking {card}...")
        # Query with Bracket 1 (strict $5 cap)
        results = builder.query_cards([{"names": [card]}], limit=1, bracket=1)
        
        if results:
            print(f"  ✅ {card} is AVAILABLE in Bracket 1")
            # Check price just to be sure
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT prices FROM Card WHERE name = ?", (card,))
            row = cursor.fetchone()
            if row and row['prices']:
                prices = json.loads(row['prices'])
                print(f"     Price: ${prices.get('usd', 'N/A')}")
            conn.close()
        else:
            print(f"  ❌ {card} is NOT available in Bracket 1 (Price too high?)")
            # Check price to see why
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT prices FROM Card WHERE name = ?", (card,))
            row = cursor.fetchone()
            if row and row['prices']:
                prices = json.loads(row['prices'])
                print(f"     Price: ${prices.get('usd', 'N/A')} (Limit: $5.00)")
            conn.close()

if __name__ == "__main__":
    test_ramp_availability()
