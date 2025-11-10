#!/usr/bin/env python3
"""
Quick test to verify EDHREC integration + color restrictions work
"""

import json
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Simulate the structure that would be created by the API
test_structure = {
    "commander": "Hope Estheim",
    "strategy": "mill",
    "bracket": 3,
    "power_level": 3,
    "priority_cards": [
        "Absorb", "Adarkar Wastes", "Aetherflux Reservoir",
        "Ajani, Strength of the Pride", "Alhammarret's Archive",
        "An Offer You Can't Refuse", "Angel of Vitality", "Arcane Denial",
        "Archivist of Oghma", "Austere Command", "Authority of the Consuls",
        "Aven Mindcensor", "Blessed Respite", "Blossoming Calm", 
        "Boon Reflection", "Brago, King Eternal", "Brainstorm",
        "Celestine, the Living Saint", "Clever Concealment", "Cloudblazer"
    ],
    "color_restrictions": ["W", "U"],  # Only white and blue
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
        "lifegain": {
            "count": 12,
            "filters": [{"oracle_text_includes": ["you gain", "gain life", "life equal"]}]
        },
        "creatures": {
            "count": 15,
            "filters": [{"types": ["Creature"]}]
        },
        "card_draw": {
            "count": 8,
            "filters": [{"tags": ["card_draw"]}]
        },
        "protection": {
            "count": 2,
            "filters": [{"tags": ["protection"]}]
        }
    }
}

# Save to temp file
output_file = "generated_decks/temp/hope-estheim-test.json"
os.makedirs("generated_decks/temp", exist_ok=True)

with open(output_file, 'w') as f:
    json.dump(test_structure, f, indent=2)

print(f"✅ Test structure created: {output_file}")
print(f"\n🔍 Testing EDHREC integration + color restrictions:")
print(f"   Commander: {test_structure['commander']}")
print(f"   Priority cards: {len(test_structure['priority_cards'])} from EDHREC")
print(f"   Color restrictions: {test_structure['color_restrictions']}")
print(f"   Expected: Only W/U cards, no B/G despite commander having W/U/B/G identity")
print(f"\n🚀 Running deck builder...\n")

# Run the deck builder
os.system(f"python3 scripts/build-deck-from-structure.py {output_file}")
