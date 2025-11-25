# cEDH Tournament Data Scraping Guide

Complete guide for collecting cEDH tournament decklists for training data.

## Overview

Two-scraper architecture collects comprehensive tournament data:
1. **EDHTop16 Scraper** - Collects tournament metadata and TopDeck.gg URLs
2. **TopDeck Scraper** - Fetches full 100-card decklists from URLs

## Step 1: Scrape EDHTop16 Tournaments

**Purpose**: Collect tournament metadata (player names, commanders, standings, decklist URLs)

### Running the Scraper

```bash
# Scrape ALL tournaments with cursor-based pagination
python3 scripts/scrape-edhtop16.py

# Limit to specific number of tournaments
# Edit main() to set: tournaments = scraper.scrape_tournaments(max_tournaments=200)
```

### What It Does

- **Pagination**: Automatically follows cursor-based pagination to load all tournaments
- **Filtering**: Skips tournaments with no entries or no decklist URLs
- **Output**: `data/training/edhtop16_tournaments.json`

### Expected Output

```
=== PAGE 1 ===
Found 100 new tournaments on this page
  Next cursor available: 104;8;2025-11-06T01:30:00.000Z

=== PAGE 2 ===
Found 100 new tournaments on this page
...

Total unique tournament links collected: 500+

[1/500] ✓ Better Plays $5k Invitational (36 players, 2025-11-09)
   Winner: Nick Novak with Krark/Sakashima
   Decklists available: 36/36

[2/500] ⊘ Commander League 2 week 12 - No decklists available, skipping
```

### Key Features

✅ **Cursor-based pagination** - Loads all tournaments (500+), not just first 100
✅ **Smart filtering** - Skips tournaments with no decklists
✅ **Rate limiting** - 1 second between pages, 0.5 seconds between tournaments
✅ **Resumable** - Tracks scraped tournaments to avoid duplicates

## Step 2: Scrape TopDeck.gg Decklists

**Purpose**: Fetch full 100-card decklists for each tournament entry

### Running the Scraper

```bash
# Scrape ALL decklists from EDHTop16 data
python3 scripts/scrape-topdeck-decklists.py

# Or run in background
nohup python3 scripts/scrape-topdeck-decklists.py > topdeck_scrape.log 2>&1 &

# Monitor progress
tail -f topdeck_scrape.log
```

### What It Does

- **Reads**: `data/training/edhtop16_tournaments.json`
- **Fetches**: Full decklists from TopDeck.gg URLs
- **Parses**: Commanders (from sideboard section) and mainboard separately
- **Enriches**: Adds tournament metadata (tournament name, player, position, W-L-D record)
- **Outputs**: `data/training/topdeck_decklists.json`

### Expected Output

```
📊 Found 2018 unique decklists to scrape
📁 Loaded 116 previously scraped decklists

[1/2018] 🎴 Nick Novak - Krark/Sakashima
    📍 Better Plays $5k Invitational (#1, 4-0-0)
    🔗 https://topdeck.gg/deck/...
    ✅ 100 total cards
       Commander(s): Krark, the Thumbless, Sakashima of a Thousand Faces (2 cards)
       Mainboard: 98 cards (94 unique)

[2/2018] 🎴 Tim - Unknown Commander
    📍 Commander Bracket 3 (#1, 3-0-0)
    🔗 https://topdeck.gg/deck/...
    ⚠️  Deck not available on TopDeck.gg
    ❌ Failed to parse decklist
```

### Key Features

✅ **Processes ALL decks** - Including those marked "Unknown Commander" in EDHTop16
✅ **Separate commander parsing** - Commanders stored in TopDeck.gg's "Sideboard" section
✅ **Smart skipping** - Handles unavailable decklists gracefully
✅ **Resumable** - Loads existing data and only scrapes new decks
✅ **Rate limiting** - 1 second between requests to avoid overload
✅ **Rich metadata** - Tournament, player, position, W-L-D record attached to each deck

## Data Structure

### EDHTop16 Output (`edhtop16_tournaments.json`)

```json
[
  {
    "name": "Better Plays $5k Invitational",
    "url": "/tournament/better-plays-5k-invitational",
    "date": "2025-11-09",
    "size": 36,
    "source": "edhtop16",
    "entries": [
      {
        "player": "Nick Novak",
        "commander": "Krark, the Thumbless / Sakashima of a Thousand Faces",
        "position": 1,
        "wins": 4,
        "losses": 0,
        "draws": 0,
        "decklist_url": "https://topdeck.gg/deck/..."
      }
    ]
  }
]
```

### TopDeck Output (`topdeck_decklists.json`)

```json
[
  {
    "url": "https://topdeck.gg/deck/...",
    "scraped_at": "2025-11-10T...",
    "commander": [
      "Krark, the Thumbless",
      "Sakashima of a Thousand Faces"
    ],
    "mainboard": [
      {"name": "Sol Ring", "quantity": 1},
      {"name": "Island", "quantity": 12}
    ],
    "total_cards": 100,
    "metadata": {
      "tournament": "Better Plays $5k Invitational",
      "player": "Nick Novak",
      "commander_from_edhtop16": "Krark/Sakashima",
      "position": 1,
      "record": "4-0-0"
    }
  }
]
```

## Common Scenarios

### Scenario 1: "Unknown Commander" in EDHTop16

**Example**: Commander League X tournament shows "Unknown Commander" for all entries

**What Happens**:
- EDHTop16 scraper: Still collects the entry with decklist URL
- TopDeck scraper: Fetches the actual decklist from TopDeck.gg
- Result: Real commander names extracted from TopDeck.gg page

**Why**: EDHTop16 sometimes doesn't have commander data, but TopDeck.gg does.

### Scenario 2: Tournament Has No Decklists

**Example**: Some weekly events don't require players to upload decklists

**What Happens**:
- EDHTop16 scraper: Checks if any entries have `decklist_url`
- If zero decklists: Skips entire tournament with message "No decklists available, skipping"
- Result: Tournament not included in output

**Why**: No point scraping tournaments with no actual decklist data.

### Scenario 3: Decklist URL Exists But Deck Not Uploaded

**Example**: Player registered but didn't upload their deck to TopDeck.gg

**What Happens**:
- TopDeck scraper: Tries to fetch URL
- Detects "Unable to Display Deck" message
- Logs: "⚠️ Deck not available on TopDeck.gg"
- Result: Skips to next deck

**Why**: Some players register but don't upload their decklists.

## Data Quality

### Current Status (as of Nov 10, 2025)

From 10 tournaments in initial test:
- Total entries: 190
- Entries with decklists: 116 (61%)
- "Unknown Commander": 74 (39%)

After running full scrape with pagination:
- Expected: 500+ tournaments
- Expected: 5,000+ decklists
- Expected success rate: ~60-70% (based on upload patterns)

### Why Not 100% Success?

1. **Players don't upload** - Some tournaments don't require decklist uploads
2. **Casual events** - Not all events are competitive cEDH
3. **Tournament organizers** - Different quality standards across venues

## Training Data Pipeline

1. **Scrape EDHTop16** → `edhtop16_tournaments.json` (500+ tournaments)
2. **Scrape TopDeck** → `topdeck_decklists.json` (3,000+ full decklists)
3. **Convert to v3 format** → `scripts/convert-to-v3-training.py`
4. **Train model** → `scripts/train-v3-structured.py`

## Troubleshooting

### "Unterminated string" error during pagination

**Symptom**: Cursor parsing fails but still collects 100 tournaments per page

**Impact**: Low - pagination continues, just can't detect next page automatically

**Fix**: Pagination logic gracefully handles this and stops when no more tournaments found

### Scraper seems stuck

**Likely Cause**: Rate limiting (1 second delays are normal)

**Check**: 
```bash
tail -f topdeck_scrape.log  # Watch progress in real-time
```

### Many "Deck not available" messages

**Expected**: 30-40% of decks may not be uploaded to TopDeck.gg

**Action**: No action needed - scraper handles this automatically

## Rate Limiting

⚠️ **Respect the sites!**

- EDHTop16: 0.5 seconds between tournaments, 1 second between pages
- TopDeck.gg: 1 second between decklist requests

Do NOT reduce these delays - both sites are community resources.

## Next Steps

After collecting ~3,000+ decklists:

1. Run `scripts/convert-to-v3-training.py` to convert to structured format
2. Train v3 model with deck-building patterns
3. Use trained model for generating legal, high-quality Commander decks

## Files Modified

- `scripts/scrape-edhtop16.py` - ✅ Enhanced with cursor-based pagination
- `scripts/scrape-topdeck-decklists.py` - ✅ Removed "Unknown Commander" filter
- `data/training/edhtop16_tournaments.json` - Output from step 1
- `data/training/topdeck_decklists.json` - Output from step 2
