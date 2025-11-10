#!/usr/bin/env python3
"""
Test colorless commander (should only get Sol Ring, not Arcane Signet or Command Tower)
"""

import json
import os

test_structure = {
    "commander": "Emrakul, the Promised End",
    "strategy": "ramp",
    "bracket": 4,
    "power_level": 8,
    "card_selection": {
        "lands": {
            "count": 35,
            "filters": [{"types": ["Land"]}]
        },
        "staples": {
            "count": 1,
            "filters": [{"names": ["Sol Ring"]}]  # Colorless = only Sol Ring
        },
        "ramp": {
            "count": 11,
            "filters": [{"tags": ["ramp"], "types_exclude": ["Land"]}]
        },
        "creatures": {
            "count": 20,
            "filters": [{"types": ["Creature"]}]
        },
        "card_draw": {
            "count": 8,
            "filters": [{"tags": ["card_draw"]}]
        }
    }
}

output_file = "generated_decks/temp/test-colorless.json"
os.makedirs("generated_decks/temp", exist_ok=True)

with open(output_file, 'w') as f:
    json.dump(test_structure, f, indent=2)

print(f"✅ Colorless commander test: {test_structure['commander']}")
print(f"   Expected: Only Sol Ring (no Arcane Signet or Command Tower)\n")

os.system(f"python3 scripts/build-deck-from-structure.py {output_file} 2>&1 | grep -E 'staples:|Sol Ring|Arcane Signet|Command Tower|Total:'")
