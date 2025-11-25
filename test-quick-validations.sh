#!/bin/bash
# Quick test of execute-deck-structure.ts with new validations

echo "Testing deck executor with validation improvements..."
echo ""

# Check if we have a test JSON file
TEST_FILE=$(ls -1 generated_decks/api_response_*.json 2>/dev/null | head -1)

if [ -z "$TEST_FILE" ]; then
    echo "No test JSON file found. Need to generate one first."
    echo "Starting API server to generate test deck..."
    
    # Start API in background
    cd /home/social/magicapp
    source ~/.virtualenvs/magicapp/bin/activate
    python3 scripts/active/pipeline/api-server.py &
    API_PID=$!
    
    sleep 10
    
    # Generate deck
    curl -X POST http://localhost:8000/api/deck/generate \
      -H "Content-Type: application/json" \
      -d '{"commander":"The Ur-Dragon","strategy":"tribal","power_level":7}' \
      -o generated_decks/test_validation.json
    
    # Stop API
    kill $API_PID 2>/dev/null
    
    TEST_FILE="generated_decks/test_validation.json"
fi

echo "Using test file: $TEST_FILE"
echo ""

# Run executor
npx ts-node scripts/execute-deck-structure.ts "$TEST_FILE"

# Validate output
echo ""
echo "========================================="
echo "Validation Checks:"
echo "========================================="

python3 << 'PYEOF'
import json
from collections import Counter

with open('generated_decks/executed/deck.json') as f:
    deck = json.load(f)

all_cards = deck['commanders'] + deck['mainboard']

# Color identity check
commander_colors = set(deck['commanders'][0].get('colorIdentity', []))
print(f"✓ Commander: {deck['commanders'][0]['name']}")
print(f"✓ Commander Colors: {','.join(sorted(commander_colors)) if commander_colors else 'Colorless'}")

# Check for color violations
violations = []
for card in deck['mainboard']:
    card_colors = set(card.get('colorIdentity', []))
    if card_colors and not card_colors.issubset(commander_colors):
        violations.append(f"{card['name']} ({','.join(sorted(card_colors))})")

if violations:
    print(f"\n❌ COLOR VIOLATIONS ({len(violations)}):")
    for v in violations[:5]:
        print(f"  - {v}")
else:
    print("✓ All cards match commander color identity")

# Check for banned cards (sample from known banned list)
banned_samples = ['Black Lotus', 'Ancestral Recall', 'Mana Crypt', 'Jeweled Lotus', 
                  'Dockside Extortionist', 'Nadu, Winged Wisdom']
found_banned = [c['name'] for c in all_cards if c['name'] in banned_samples]

if found_banned:
    print(f"\n❌ BANNED CARDS FOUND: {found_banned}")
else:
    print("✓ No banned cards detected")

# Check duplicates
legal_dupes = {'Relentless Rats', 'Rat Colony', 'Persistent Petitioners', 
               'Shadowborn Apostle', "Dragon's Approach", 'Seven Dwarves',
               'Slime Against Humanity', 'Nazgûl', 'Hare Apparent',
               'Plains', 'Island', 'Swamp', 'Mountain', 'Forest', 'Wastes'}

card_names = [c['name'] for c in all_cards]
non_legal_dupes = [n for n in card_names if n not in legal_dupes]
dupes = {n: cnt for n, cnt in Counter(non_legal_dupes).items() if cnt > 1}

if dupes:
    print(f"\n❌ INVALID DUPLICATES: {dupes}")
else:
    print("✓ No invalid duplicates")

# Check deck size
if len(all_cards) == 100 and len(deck['commanders']) == 1 and len(deck['mainboard']) == 99:
    print(f"✓ Deck structure: 100 cards (1 commander + 99 mainboard)")
else:
    print(f"❌ Deck structure: {len(all_cards)} cards ({len(deck['commanders'])} commander + {len(deck['mainboard'])} mainboard)")

print("\n========================================")
if not violations and not found_banned and not dupes and len(all_cards) == 100:
    print("🎉 ALL VALIDATION CHECKS PASSED!")
else:
    print("⚠️  Some validation checks failed")
print("========================================")
PYEOF

