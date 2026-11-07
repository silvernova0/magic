# MTGTop8 Scraper Enhancement - Complete

## What Was Built

### 1. Enhanced Scraper (`src/lib/scrapers/mtgtop8.ts`)
- **Added `scrapeDeckDetails()` function** - Scrapes individual deck pages to get complete 100-card decklists
- **Multiple parsing strategies** - Handles different HTML structures on MTGTop8
- **Rate limiting** - 1-second delay between requests to be respectful
- **Mainboard + Sideboard support** - Separates main deck from sideboard cards

### 2. Import Script (`scripts/import-mtgtop8-decks.ts`)
- **Batch processing** - Processes decks in batches of 10 with pauses
- **Database storage** - Stores full decklists in `CommanderDeck` model
- **Smart inferencing**:
  - Power level (1-5) based on event type and deck name
  - Theme extraction from deck names
  - Popularity scoring based on tournament placement
- **Commander linking** - Connects decks to Card records when possible
- **Error handling** - Continues import even if individual decks fail

### 3. Test Script (`scripts/test-mtgtop8-scraper.ts`)
- Validates scraper functionality
- Shows sample output for debugging
- Tests both deck list and detail scraping

## Test Results ✅

Successfully tested on MTGTop8:
- **Found 26 recent Commander decks**
- **Scraped complete 100-card decklist** from test deck
- **Mainboard parsing works** - All cards extracted correctly
- **URL construction works** - Properly builds full URLs

## Database Schema

Decks are stored in the `CommanderDeck` model with:
```prisma
model CommanderDeck {
  id           String   @id         // "mtgtop8-{event_id}"
  name         String                // Deck name
  commander    String                // Commander name
  commanderId  String?               // Link to Card table
  colors       String                // JSON array
  theme        String?               // Inferred theme
  powerLevel   Int?                  // 1-5 bracket
  source       String                // "mtgtop8"
  sourceUrl    String?               // Original deck URL
  decklist     String                // JSON: {mainboard, sideboard, event, placement, date}
  popularity   Int?                  // Score based on placement
  scrapedAt    DateTime
  updatedAt    DateTime
}
```

## How to Use

### Run Import
```bash
npm run import:mtgtop8
```

### Test Scraper
```bash
npx tsx scripts/test-mtgtop8-scraper.ts
```

## What Data You Get

For each deck:
- **Complete decklist** - All 100 cards (99 + commander)
- **Tournament info** - Event name, placement, date
- **Commander details** - Name and link to card database
- **Power level** - Estimated 1-5 bracket
- **Theme** - Inferred from deck name (cEDH, Stax, Combo, etc.)
- **Color identity** - Extracted from commander
- **Popularity score** - Based on tournament placement

## Expected Import Results

When you run the full import:
- **~20-30 recent Commander decks**
- **~2,000-3,000 unique cards** across all decks
- **Tournament-tested decklists** from competitive events
- **Placement data** for meta analysis
- **Import duration**: ~30-60 seconds (with rate limiting)

## Power Level Inference Logic

- **Level 5** - cEDH decks or events
- **Level 4** - Tournament/Championship events, or Turbo/Stax/Combo decks
- **Level 3** - Default for other competitive decks

## Theme Inference Logic

Detects themes from deck names:
- cEDH, Stax, Combo, Aggro, Voltron
- Control, Midrange, Tribal, Tokens
- Aristocrats, Lands Matter, Graveyard
- Spellslinger, and more...

## Next Steps

1. ✅ **MTGTop8 scraper enhanced** - Full decklist scraping works
2. 🔄 **Ready to import** - Run `npm run import:mtgtop8` when you want to populate the database
3. 📊 **Use the data** - Tournament decks can now be used by the AI deck builder for suggestions
4. ⏭️ **Next task**: Enhance Moxfield scraper for bracket-specific data

## Integration with Deck Builder

The imported MTGTop8 data will be useful for:
- **Competitive meta analysis** - See what's winning tournaments
- **Deck suggestions** - "Show me top 8 decks with [commander]"
- **Card recommendations** - "These cards appear in tournament-winning decks"
- **Power level reference** - Compare user decks against tournament data

## Notes

- MTGTop8 focuses on **Duel Commander** (1v1 format), not traditional multiplayer EDH
- Some deck names may be in different languages (French, Czech, etc.)
- The scraper handles various page structures to maximize compatibility
- Rate limiting ensures we don't overload MTGTop8's servers
