#!/bin/bash
# Monitor quality test progress

echo "Quality Test Progress Monitor"
echo "=============================="
echo ""

# Check if test is running
if pgrep -f "test-model-quality.py" > /dev/null; then
    echo "✓ Test is running"
else
    echo "✗ Test is not running"
fi

echo ""
echo "Generated decks so far:"
ls -1 generated_decks/quality_test/*.json 2>/dev/null | grep -v summary | wc -l | xargs echo -n
echo " / 10"

echo ""
echo "Latest results:"
ls -lt generated_decks/quality_test/*.json 2>/dev/null | grep -v summary | head -3 | awk '{print "  "$9}'

echo ""
echo "Tail of current log:"
tail -20 quality-test-output.log 2>/dev/null || echo "  (log not available yet)"

echo ""
echo "To view full log: tail -f quality-test-output.log"
