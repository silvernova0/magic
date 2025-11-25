
import sys
import os
import sqlite3
from pathlib import Path

# Add scripts directory to path
sys.path.append(os.path.join(os.getcwd(), 'scripts'))

import importlib.util
spec = importlib.util.spec_from_file_location("DeckBuilderModule", "scripts/build-deck-from-structure.py")
deck_builder_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deck_builder_module)
DeckBuilder = deck_builder_module.DeckBuilder

def test_urborg_logic():
    print("🧪 Testing Urborg/Yavimaya Logic...")
    
    db_path = "prisma/dev.db"
    builder = DeckBuilder(db_path=db_path)
    
    # Case 1: Mono-White (Adeline) - Should NOT allow Urborg
    print("\n📋 Case 1: Mono-White (Adeline)")
    builder.commander_colors = {'W'}
    
    # Mock a card row for Urborg
    urborg = {
        'name': 'Urborg, Tomb of Yawgmoth',
        'typeLine': 'Legendary Land',
        'oracleText': 'Each land is a Swamp in addition to its other land types.',
        'colorIdentity': ''
    }
    
    is_usable = builder.is_land_usable(urborg)
    if is_usable:
        print("  ❌ Urborg is marked USABLE in Mono-White (Current Issue)")
    else:
        print("  ✅ Urborg is marked UNUSABLE in Mono-White (Fixed)")
        
    # Case 2: Black-White (Orzhov) - Should ALLOW Urborg
    print("\n📋 Case 2: Orzhov (Black/White)")
    builder.commander_colors = {'W', 'B'}
    is_usable = builder.is_land_usable(urborg)
    if is_usable:
        print("  ✅ Urborg is marked USABLE in Orzhov (Correct)")
    else:
        print("  ❌ Urborg is marked UNUSABLE in Orzhov (Incorrect)")

    # Case 3: Mono-Green (Yavimaya check)
    print("\n📋 Case 3: Mono-Red (No Green)")
    builder.commander_colors = {'R'}
    yavimaya = {
        'name': 'Yavimaya, Cradle of Growth',
        'typeLine': 'Legendary Land',
        'oracleText': 'Each land is a Forest in addition to its other land types.',
        'colorIdentity': ''
    }
    is_usable = builder.is_land_usable(yavimaya)
    if is_usable:
        print("  ❌ Yavimaya is marked USABLE in Mono-Red (Potential Issue)")
    else:
        print("  ✅ Yavimaya is marked UNUSABLE in Mono-Red (Fixed)")

if __name__ == "__main__":
    test_urborg_logic()
