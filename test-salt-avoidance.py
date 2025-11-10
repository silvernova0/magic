#!/usr/bin/env python3
"""
Test salt avoidance feature - should exclude high-salt cards like Stasis, Winter Orb, etc.
"""

import json
import os

test_structure = {
    "commander": "Grand Arbiter Augustin IV",  # Control commander
    "strategy": "control",
    "bracket": 3,
    "power_level": 6,
    "avoid_salt_cards": True,
    "salt_threshold": 2.0,
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
        "removal": {
            "count": 15,
            "filters": [{"tags": ["removal"]}]
        },
        "counterspells": {
            "count": 10,
            "filters": [{"oracle_text_includes": ["counter target", "counter spell"]}]
        },
        "card_draw": {
            "count": 12,
            "filters": [{"tags": ["card_draw"]}]
        },
        "creatures": {
            "count": 12,
            "filters": [{"types": ["Creature"]}]
        }
    }
}

output_file = "generated_decks/temp/test-salt-avoidance.json"
os.makedirs("generated_decks/temp", exist_ok=True)

with open(output_file, 'w') as f:
    json.dump(test_structure, f, indent=2)

print(f"✅ Salt avoidance test: {test_structure['commander']}")
print(f"   Expected: NO Stasis, Winter Orb, Armageddon, Thassa's Oracle, etc.\n")

os.system(f"python3 scripts/build-deck-from-structure.py {output_file} 2>&1 | grep -E '🧂|Avoiding|Stasis|Winter Orb|Armageddon|Total:'")
