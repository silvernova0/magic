# Deck Scraping Strategy - Progress Report

## Sources Tested

### ✅ Working Sources
1. **MTGGoldfish** - Currently running
   - 45 Commander archetypes found
   - Scraping 3 decks per archetype
   - Status: In progress (detecting some duplicates in results)
   - Estimated: 50-100 unique decks

2. **TappedOut** - Needs fixing
   - Search functionality not returning correct results
   - Only found 1 deck link per page
   - Needs different search approach

3. **cEDH Database** - Blocked
   - Found 211 Moxfield deck links
   - Moxfield API returns 403 Forbidden
   - Cannot scrape without browser automation

### ❌ Blocked Sources
- Moxfield (403 Forbidden)
- MTGDecks.net (403 Forbidden)  
- AetherHub (403 Forbidden)
- Archidekt (Rate limited too aggressively)

## Current Data Collection Status

### Completed
- ✅ Card knowledge: 65,379 examples (22.88 MB)

### In Progress
- 🔄 MTGGoldfish: ~50-100 decks (running now)

### Need to Fix
- ⚠️ TappedOut: Search not working correctly
- ⚠️ EDHREC: HTML parsing issues

## Recommended Next Steps

### Option 1: Focus on What Works
- Let MTGGoldfish finish (~100 decks)
- Fix TappedOut search (could get 500+ decks)
- Total: ~600 decks + 65k card examples = ~660k training examples

### Option 2: Manual Deck Collection
- Download popular precon decklists (official WotC decks)
- Scrape from Reddit threads (r/EDH, r/cEDH)
- Use public deck databases on GitHub

### Option 3: Synthetic Deck Generation
- Use Gemini to generate example decks based on:
  - Card database (31k cards with power levels, tags)
  - EDHREC commander popularity
  - Color identity rules
- Generate 2000-3000 synthetic decks
- Higher volume but lower quality than real decks

## Data Quality Assessment

### High Quality (Real Player Decks)
- MTGGoldfish: ⭐⭐⭐⭐⭐ (Popular archetypes)
- TappedOut: ⭐⭐⭐⭐ (Top-rated user decks)
- cEDH Database: ⭐⭐⭐⭐⭐ (Competitive validated lists)

### Medium Quality
- EDHREC: ⭐⭐⭐⭐⭐ (Community average decks - if we can fix scraper)

### Lower Quality
- Synthetic generation: ⭐⭐⭐ (Rules-compliant but not play-tested)

## Training Data Requirements

### Minimum Viable
- 1,000-2,000 decks
- Each deck = ~95 cards
- Total: 95k-190k card placements
- + 65k card knowledge
- **Total: 160k-255k examples**

### Optimal
- 3,000-5,000 decks  
- Each deck = ~95 cards
- Total: 285k-475k card placements
- + 65k card knowledge
- **Total: 350k-540k examples**

## Current Projection

With current working sources:
- MTGGoldfish: ~100 decks
- TappedOut (if fixed): ~500 decks
- **Total: ~600 decks = ~57k card placements + 65k card knowledge = 122k examples**

This is **below minimum viable** for quality training.

## Recommendation

**Combine real + synthetic approach:**
1. Finish MTGGoldfish scraping (~100 decks)
2. Fix TappedOut search (~500 decks)
3. Generate 1,500 synthetic decks using Gemini
4. **Total: 2,100 decks = ~340k training examples** ✅

This gives us:
- Real deck patterns (600 decks)
- Synthetic volume (1,500 decks)
- Card knowledge foundation (65k examples)
- Adequate training data for 8B model
