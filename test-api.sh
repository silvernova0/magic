#!/bin/bash
# Quick test of the FastAPI server

echo "Testing Gemma API Server..."
echo ""

# Test health endpoint
echo "1. Health Check:"
curl -s http://localhost:8000/health | jq '.'
echo ""

# Test deck generation (this will take ~30 seconds)
echo "2. Generating test deck (this may take 30 seconds)..."
curl -s -X POST http://localhost:8000/api/deck/generate \
  -H "Content-Type: application/json" \
  -d '{
    "commander": "The Ur-Dragon",
    "theme": "Dragons",
    "colors": ["W", "U", "B", "R", "G"],
    "powerLevel": "3",
    "useCollectionOnly": false
  }' | jq '.' > /tmp/gemma-test-deck.json

if [ -s /tmp/gemma-test-deck.json ]; then
  echo "✅ Deck generated successfully!"
  echo ""
  echo "Commander:" 
  jq -r '.commander' /tmp/gemma-test-deck.json
  echo ""
  echo "Strategy:"
  jq -r '.strategy' /tmp/gemma-test-deck.json
  echo ""
  echo "Power Level:"
  jq -r '.power_level' /tmp/gemma-test-deck.json
  echo ""
  echo "Card Selection Categories:"
  jq -r '.card_selection | keys | .[]' /tmp/gemma-test-deck.json
  echo ""
  echo "Full output saved to: /tmp/gemma-test-deck.json"
else
  echo "❌ Deck generation failed"
  cat /tmp/gemma-test-deck.json
fi
