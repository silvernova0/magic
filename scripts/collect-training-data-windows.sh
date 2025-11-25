#!/bin/bash
#
# Training Data Collection for Windows RTX Training
# Run this on Linux machine to collect comprehensive dataset
#
# Usage: bash scripts/collect-training-data-windows.sh
#

set -e  # Exit on error

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  COMMANDER DECK TRAINING DATA COLLECTION                   ║"
echo "║  Target: 75,000-100,000 examples for 7B model training     ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Check we're in the right directory
if [ ! -f "package.json" ]; then
    echo "❌ Error: Run this from /home/social/magicapp directory"
    exit 1
fi

# Create data directory if needed
mkdir -p data/training

# Phase 1: MTGGoldfish by Commander (BIGGEST DATA SOURCE)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 PHASE 1: MTGGoldfish Commander Scraping"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Target: 25 decks × 2,500 commanders = 62,500 new examples"
echo "Estimated time: 15-20 hours"
echo ""
read -p "Start MTGGoldfish scraper? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🚀 Starting MTGGoldfish commander scraper..."
    echo "   Output: data/training/mtggoldfish_by_commander_decks.jsonl"
    echo "   Log: mtggoldfish_commander.log"
    echo ""
    
    nohup python3 scripts/scrape-mtggoldfish-by-commander.py \
        --decks-per-commander 25 \
        --max-commanders 2500 \
        > mtggoldfish_commander.log 2>&1 &
    
    GOLDFISH_PID=$!
    echo "✅ Scraper started (PID: $GOLDFISH_PID)"
    echo "   Monitor: tail -f mtggoldfish_commander.log"
    echo ""
    
    # Wait a few seconds to check if it started properly
    sleep 3
    if ps -p $GOLDFISH_PID > /dev/null; then
        echo "✅ Process running successfully"
    else
        echo "❌ Process may have failed - check log"
        cat mtggoldfish_commander.log | tail -20
        exit 1
    fi
else
    echo "⏭️  Skipping MTGGoldfish scraper"
fi

echo ""

# Phase 2: Re-scrape Moxfield (optional)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 PHASE 2: Moxfield Themes (Optional)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Target: 30 themes × 5 brackets × ~50 decks = ~7,500 examples"
echo "Estimated time: 3-5 hours"
echo ""
read -p "Start Moxfield scraper? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🚀 Starting Moxfield themes scraper..."
    
    nohup python3 scripts/scrape-moxfield-themes.py \
        > moxfield_themes.log 2>&1 &
    
    MOXFIELD_PID=$!
    echo "✅ Scraper started (PID: $MOXFIELD_PID)"
    echo "   Monitor: tail -f moxfield_themes.log"
else
    echo "⏭️  Skipping Moxfield scraper"
fi

echo ""

# Phase 3: Re-scrape Archidekt (optional)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 PHASE 3: Archidekt Popular (Optional)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Target: ~5,000 examples"
echo "Estimated time: 2-3 hours"
echo ""
read -p "Start Archidekt scraper? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🚀 Starting Archidekt scraper..."
    
    nohup python3 scripts/scrape-archidekt-commanders.py \
        > archidekt.log 2>&1 &
    
    ARCHIDEKT_PID=$!
    echo "✅ Scraper started (PID: $ARCHIDEKT_PID)"
    echo "   Monitor: tail -f archidekt.log"
else
    echo "⏭️  Skipping Archidekt scraper"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ SCRAPING JOBS STARTED"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 Monitor progress:"
echo "   watch -n 60 'tail -3 mtggoldfish_commander.log moxfield_themes.log archidekt.log'"
echo ""
echo "📁 Check data files:"
echo "   ls -lh data/training/*.jsonl"
echo ""
echo "🔍 Count examples:"
echo "   wc -l data/training/*.jsonl"
echo ""
echo "⏰ Estimated completion:"
echo "   MTGGoldfish: 15-20 hours"
echo "   Moxfield: 3-5 hours"
echo "   Archidekt: 2-3 hours"
echo ""
echo "💡 TIP: These can run in parallel overnight!"
echo "    When done, run: bash scripts/package-training-data.sh"
echo ""
