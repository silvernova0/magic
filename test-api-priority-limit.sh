#!/bin/bash
# Test API with priority_cards hard limit

echo "Testing API priority_cards hard limit..."
echo ""

curl -X POST http://localhost:8000/api/deck/generate \
  -H "Content-Type: application/json" \
  -d '{
    "commander": "Atraxa, Praetors'\'' Voice",
    "theme": "counters",
    "colors": ["W", "U", "B", "G"],
    "powerLevel": "4",
    "useCollectionOnly": false
  }' | python3 -c "
import sys
import json

data = json.load(sys.stdin)
priority_cards = data.get('priority_cards', [])

print(f'✅ API Response received')
print(f'Commander: {data.get(\"commander\")}')
print(f'Strategy: {data.get(\"strategy\")}')
print(f'Power Level: {data.get(\"power_level\")}')
print(f'Bracket: {data.get(\"bracket\")}')
print(f'')
print(f'Priority Cards Count: {len(priority_cards)}')
print(f'')
print('First 10 priority cards:')
for i, card in enumerate(priority_cards[:10], 1):
    print(f'  {i}. {card}')

if len(priority_cards) > 10:
    print(f'  ... and {len(priority_cards) - 10} more')

# Verify limit
if len(priority_cards) <= 30:
    print(f'')
    print(f'✅ PASS: Priority cards limited to {len(priority_cards)} (max 30)')
else:
    print(f'')
    print(f'❌ FAIL: Priority cards exceeded limit: {len(priority_cards)} > 30')
"
