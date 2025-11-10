#!/usr/bin/env python3
"""
Test deck building WITHOUT collection restriction (all cards mode)
"""

import json
import sys
import os

# Simulate the structure WITHOUT collection
test_structure = {
    "commander": "Hope Estheim",
    "strategy": "mill",
    "bracket": 3,
    "power_level": 3,
    "priority_cards": [
        "Brainstorm", "Rhystic Study", "Smothering Tithe"
    ],
    "color_restrictions": ["W", "U"],
    "card_selection": {
        "lands": {
            "count": 35,
            "filters": [{"types": ["Land"]}]
        },
        "staples": {
            "count": 3,
            "filters": [{"names": ["Sol Ring", "Arcane Signet", "Command Tower"]}]
        },
        "ramp": {
            "count": 9,
            "filters": [{"tags": ["ramp"], "types_exclude": ["Land"]}]
        },
        "mill_effects": {
            "count": 15,
            "filters": [{"oracle_text_includes": ["mill", "library into", "graveyard from their library"]}]
        },
        "creatures": {
            "count": 15,
            "filters": [{"types": ["Creature"]}]
        },
        "card_draw": {
            "count": 8,
            "filters": [{"tags": ["card_draw"]}]
        }
    }
    # NOTE: NO "collection" field - should allow all cards
}

# Save to temp file
output_file = "generated_decks/temp/test-all-cards.json"
os.makedirs("generated_decks/temp", exist_ok=True)

with open(output_file, 'w') as f:
    json.dump(test_structure, f, indent=2)

print(f"✅ Test structure created: {output_file}")
print(f"\n🔍 Testing ALL CARDS mode (no collection restriction):")
print(f"   Commander: {test_structure['commander']}")
print(f"   Color restrictions: {test_structure['color_restrictions']}")
print(f"   Collection: NOT PROVIDED (should use all available cards)")
print(f"\n🚀 Running deck builder...\n")

# Run the deck builder
os.system(f"python3 scripts/build-deck-from-structure.py {output_file}")
