#!/bin/bash
# Monitor EDHTop16 tournament scraper progress

echo "=== EDHTop16 Tournament Scraper Monitor ==="
echo ""

# Check if scraper is running
if pgrep -f "scrape-edhtop16-topdeck.py" > /dev/null; then
    echo "Status: ✓ RUNNING"
else
    echo "Status: ✗ NOT RUNNING"
fi

echo ""

# Count collected decks
if [ -f "data/training/edhtop16_tournament_decks.jsonl" ]; then
    DECK_COUNT=$(wc -l < data/training/edhtop16_tournament_decks.jsonl)
    echo "Decks collected: $DECK_COUNT"
else
    echo "Decks collected: 0 (file not created yet)"
fi

echo ""
echo "=== Recent Log Output ==="
tail -30 edhtop16_tournament.log

echo ""
echo "=== Tournament Progress ==="
grep -E "^\[[0-9]+/[0-9]+\]" edhtop16_tournament.log | tail -5
