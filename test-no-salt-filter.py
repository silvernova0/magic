#!/usr/bin/env python3
"""
Test WITHOUT salt avoidance - might include high-salt cards
"""

import json
import os

test_structure = {
    "commander": "Grand Arbiter Augustin IV",
    "strategy": "control",
    "bracket": 3,
    "power_level": 6,
    # NO avoid_salt_cards field - should allow salty cards
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

output_file = "generated_decks/temp/test-no-salt-filter.json"
os.makedirs("generated_decks/temp", exist_ok=True)

with open(output_file, 'w') as f:
    json.dump(test_structure, f, indent=2)

print(f"✅ NO salt filtering test: {test_structure['commander']}")
print(f"   Expected: Might include Rhystic Study, Thassa's Oracle, etc.\n")

os.system(f"python3 scripts/build-deck-from-structure.py {output_file} 2>&1 | tail -100 | grep -E 'Rhystic Study|Thassa|Oracle|The One Ring|Total:' | head -10")
