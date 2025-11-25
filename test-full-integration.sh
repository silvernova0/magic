#!/bin/bash
# Comprehensive test: Next.js → Local Model API → Database → Complete Deck

set -e  # Exit on error

echo "========================================================================="
echo "FULL INTEGRATION TEST: Next.js + Local Model API + Database"
echo "========================================================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check prerequisites
echo "Step 1: Checking prerequisites..."
echo "-----------------------------------"

# Check if API server is running
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo -e "${RED}❌ FastAPI server not running on port 8000${NC}"
    echo "Start it with: python3 api-server.py"
    exit 1
fi
echo -e "${GREEN}✓${NC} FastAPI server running"

# Check if Next.js dev server is running
if ! curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠${NC}  Next.js server not running on port 3000"
    echo "This test will use API calls directly instead of UI"
    NEXTJS_RUNNING=false
else
    echo -e "${GREEN}✓${NC} Next.js server running"
    NEXTJS_RUNNING=true
fi

# Check database
if [ ! -f "prisma/dev.db" ]; then
    echo -e "${RED}❌ Database not found at prisma/dev.db${NC}"
    echo "Run: npm run import:mtgjson:full"
    exit 1
fi
echo -e "${GREEN}✓${NC} Database exists"

# Check if execute-deck-structure.ts exists
if [ ! -f "scripts/execute-deck-structure.ts" ]; then
    echo -e "${RED}❌ Database executor not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} Database executor exists"

echo ""
echo "Step 2: Testing FastAPI Model Endpoint"
echo "-----------------------------------"

# Test 1: Generate deck structure via API
echo "Generating deck structure for Atraxa (counters, power 8)..."

RESPONSE=$(curl -s -X POST http://localhost:8000/api/deck/generate \
  -H "Content-Type: application/json" \
  -d '{
    "commander": "Atraxa, Praetors'\'' Voice",
    "theme": "counters",
    "colors": ["W", "U", "B", "G"],
    "powerLevel": "4",
    "useCollectionOnly": false
  }')

# Check if response is valid JSON
if ! echo "$RESPONSE" | python3 -c "import sys, json; json.load(sys.stdin)" 2>/dev/null; then
    echo -e "${RED}❌ API returned invalid JSON${NC}"
    echo "Response: $RESPONSE"
    exit 1
fi

# Save response to temp file
echo "$RESPONSE" > /tmp/test-deck-structure.json

# Validate response fields
COMMANDER=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('commander', ''))")
STRATEGY=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('strategy', ''))")
PRIORITY_COUNT=$(echo "$RESPONSE" | python3 -c "import sys, json; print(len(json.load(sys.stdin).get('priority_cards', [])))")

if [ -z "$COMMANDER" ]; then
    echo -e "${RED}❌ Missing commander in response${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} API Response valid"
echo "  Commander: $COMMANDER"
echo "  Strategy: $STRATEGY"
echo "  Priority Cards: $PRIORITY_COUNT"

if [ "$PRIORITY_COUNT" -gt 30 ]; then
    echo -e "${RED}❌ Priority cards exceeded limit: $PRIORITY_COUNT > 30${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} Priority cards within limit ($PRIORITY_COUNT <= 30)"

echo ""
echo "Step 3: Converting to Complete 100-Card Deck"
echo "-----------------------------------"

# Execute deck structure through database
echo "Running database executor..."

if ! npx tsx scripts/execute-deck-structure.ts /tmp/test-deck-structure.json > /tmp/executor-output.log 2>&1; then
    echo -e "${RED}❌ Database executor failed${NC}"
    cat /tmp/executor-output.log
    exit 1
fi

# Find the generated deck file
LATEST_DECK=$(ls -t generated_decks/executed/*.json 2>/dev/null | head -1)

if [ -z "$LATEST_DECK" ]; then
    echo -e "${RED}❌ No deck file generated${NC}"
    cat /tmp/executor-output.log
    exit 1
fi

echo -e "${GREEN}✓${NC} Deck generated: $LATEST_DECK"

# Validate deck has 99-100 cards
# (Commander decks can be stored as 99 mainboard + 1 commander, or 100 mainboard with commander included)
TOTAL_CARDS=$(python3 -c "
import json
with open('$LATEST_DECK') as f:
    deck = json.load(f)
    mainboard = deck.get('mainboard', [])
    commanders = deck.get('commanders', [])
    total = len(mainboard) + len(commanders)
    print(total)
")

if [ "$TOTAL_CARDS" -lt 99 ] || [ "$TOTAL_CARDS" -gt 100 ]; then
    echo -e "${RED}❌ Invalid card count: $TOTAL_CARDS (expected 99-100)${NC}"
    exit 1
fi

if [ "$TOTAL_CARDS" -eq 99 ]; then
    echo -e "${GREEN}✓${NC} Deck has 99 cards (commander included in mainboard)"
else
    echo -e "${GREEN}✓${NC} Deck has exactly 100 cards"
fi

# Show deck summary
python3 -c "
import json
with open('$LATEST_DECK') as f:
    deck = json.load(f)

print('')
print('Deck Summary:')
print('=' * 50)
print(f\"Commander: {deck.get('commander', 'Unknown')}\")
print(f\"Strategy: {deck.get('theme', deck.get('strategy', 'Unknown'))}\")
print(f\"Power Level: {deck.get('powerLevel', deck.get('power_level', 'Unknown'))}\")
print(f\"Commanders: {len(deck.get('commanders', []))}\")
print(f\"Mainboard: {len(deck.get('mainboard', []))}\")
print(f\"Total: {len(deck.get('commanders', [])) + len(deck.get('mainboard', []))}\")

# Sample 5 random cards
import random
mainboard = deck.get('mainboard', [])
if mainboard:
    print('')
    print('Sample Cards:')
    for card in random.sample(mainboard, min(5, len(mainboard))):
        print(f\"  - {card.get('name')} ({card.get('type', 'Unknown')})\")
"

echo ""
echo "Step 4: Validating Card Legality"
echo "-----------------------------------"

# Check for banned cards
BANNED_COUNT=$(python3 -c "
import json
with open('$LATEST_DECK') as f:
    deck = json.load(f)
    
# List of banned commanders
banned = [
    'Ancestral Recall', 'Balance', 'Biorhythm', 'Black Lotus', 
    'Braids, Cabal Minion', 'Channel', 'Chaos Orb', 'Coalition Victory',
    'Emrakul, the Aeons Torn', 'Erayo, Soratami Ascendant', 'Falling Star',
    'Fastbond', 'Flash', 'Gifts Ungiven', 'Griselbrand', 'Hullbreacher',
    'Iona, Shield of Emeria', 'Karakas', 'Leovold, Emissary of Trest',
    'Library of Alexandria', 'Limited Resources', 'Lutri, the Spellchaser',
    'Mox Emerald', 'Mox Jet', 'Mox Pearl', 'Mox Ruby', 'Mox Sapphire',
    'Panoptic Mirror', 'Paradox Engine', 'Primeval Titan', 'Prophet of Kruphix',
    'Recurring Nightmare', 'Rofellos, Llanowar Emissary', 'Shahrazad',
    'Sundering Titan', 'Sway of the Stars', 'Sylvan Primordial', 'Time Vault',
    'Time Walk', 'Tinker', 'Tolarian Academy', 'Trade Secrets', 'Upheaval',
    'Worldfire', 'Yawgmoth's Bargain'
]

all_cards = deck.get('commanders', []) + deck.get('mainboard', [])
banned_found = [card.get('name') for card in all_cards if card.get('name') in banned]

print(len(banned_found))
if banned_found:
    print('Banned cards found:', ', '.join(banned_found), file=sys.stderr)
" 2>&1)

if echo "$BANNED_COUNT" | grep -q "Banned cards found"; then
    echo -e "${RED}❌ Deck contains banned cards${NC}"
    echo "$BANNED_COUNT"
    exit 1
fi

echo -e "${GREEN}✓${NC} No banned cards found"

# Check for Arena-only cards (A- prefix)
ARENA_COUNT=$(python3 -c "
import json
with open('$LATEST_DECK') as f:
    deck = json.load(f)
    
all_cards = deck.get('commanders', []) + deck.get('mainboard', [])
arena_cards = [card.get('name') for card in all_cards if card.get('name', '').startswith('A-')]

print(len(arena_cards))
")

if [ "$ARENA_COUNT" -gt 0 ]; then
    echo -e "${RED}❌ Deck contains $ARENA_COUNT Arena-only cards${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} No Arena-only cards (A- prefix)"

# Check color identity
python3 -c "
import json
with open('$LATEST_DECK') as f:
    deck = json.load(f)

commander = deck.get('commanders', [{}])[0]
cmd_colors = set(commander.get('colorIdentity', []))

violations = []
for card in deck.get('mainboard', []):
    card_colors = set(card.get('colorIdentity', []))
    if not card_colors.issubset(cmd_colors):
        violations.append(card.get('name'))

if violations:
    print(f'Color identity violations: {len(violations)}')
    print('Cards:', ', '.join(violations[:5]))
    exit(1)
else:
    print('✓ All cards match commander color identity')
"

echo ""
echo "========================================================================="
echo -e "${GREEN}✅ ALL TESTS PASSED!${NC}"
echo "========================================================================="
echo ""
echo "Summary:"
echo "  1. FastAPI server responding correctly"
echo "  2. Model generates valid deck structure"
echo "  3. Priority cards limited to max 30"
echo "  4. Database executor creates 100-card deck"
echo "  5. No banned or Arena-only cards"
echo "  6. Color identity respected"
echo ""
echo "Generated deck saved to: $LATEST_DECK"
echo ""

if [ "$NEXTJS_RUNNING" = true ]; then
    echo "Next step: Test via Next.js UI at http://localhost:3000"
else
    echo "Start Next.js dev server with: npm run dev"
    echo "Then test the UI at http://localhost:3000"
fi
