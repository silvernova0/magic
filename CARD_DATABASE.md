# Card Database Features

## 📥 Setup Instructions

### 1. Download MTGJson Data
Visit [https://mtgjson.com/downloads/all-files/](https://mtgjson.com/downloads/all-files/) and download:

- **AtomicCards.json** (Required - ~50MB)
  - Contains unique cards with comprehensive data
  - This is what we import for the database
  
- **AllPrintings.json** (Optional - ~500MB)
  - Contains all printings and variations
  - Not currently used but available for future features

### 2. Place Files in Project
```bash
mkdir -p data/mtgjson
# Move downloaded AtomicCards.json to data/mtgjson/
```

### 3. Import Cards
```bash
# Run the comprehensive importer
npm run import:mtgjson:full

# This will:
# - Import 31,483 unique cards
# - Add EDHREC rankings and saltiness scores
# - Generate 20+ tag types
# - Calculate power levels (0-10)
# - Skip 1,252 "funny" cards (silver-bordered, etc.)
# - Takes approximately 2-3 minutes
```

**Note**: The JSON files are not tracked in Git due to their size. Each developer needs to download them locally.

## 🎴 Database Statistics
- **Total Cards**: 31,483 unique cards
- **Legal Commanders**: 23
- **High Saltiness Cards (>1.0)**: 775
- **Top 1000 EDHREC**: 1,001

## 🏷️ Auto-Generated Tags

Cards are automatically tagged for easy filtering:

### Mechanical Tags
- `card-draw` - Cards that draw cards
- `tutor` - Search library effects
- `removal` - Destroy effects
- `exile` - Exile effects
- `counterspell` - Counter spells/abilities
- `token` - Creates tokens
- `graveyard` - Graveyard interactions
- `sacrifice` - Sacrifice mechanics
- `extra-turns` - Extra turn effects
- `copy` - Copy effects
- `storm`, `cascade` - Mechanic-specific tags

### Power Level Tags
- `game-changer` - EDHREC rank < 500 or game-ending effects
- `top-100` - EDHREC rank < 100
- `high-salt` - Saltiness > 1.0
- `very-high-salt` - Saltiness > 2.0

### Leadership Tags
- `commander` - Legal as Commander
- `brawl-commander` - Legal as Brawl Commander
- `oathbreaker` - Legal as Oathbreaker

### Type Tags
- `creature`, `instant`, `sorcery`, `enchantment`, `artifact`, `planeswalker`, `land`

## 🔍 Search API Examples

### Basic Search
```
GET /api/cards/search?q=lightning bolt
```

### Commander Search (Red color identity)
```
GET /api/cards/search?isCommander=true&colorIdentity=R
```

### High-Salt Cards
```
GET /api/cards/search?minSaltiness=2.0&sortBy=edhrecSaltiness&sortOrder=desc
```

### Top EDHREC Cards
```
GET /api/cards/search?maxEdhrecRank=100&sortBy=edhrecRank&sortOrder=asc
```

### Tutors in Black
```
GET /api/cards/search?q=tutor&colorIdentity=B&sortBy=edhrecRank
```

### Low CMC Creatures
```
GET /api/cards/search?types=Creature&maxCmc=2&sortBy=cmc
```

### Game Changers
```
GET /api/cards/search?maxEdhrecRank=500&sortBy=edhrecRank
```

## 📊 Card Data Fields

Each card includes:

### Core Data
- `id` - Unique identifier
- `name` - Card name
- `manaCost` - Mana cost (e.g., "{2}{U}{U}")
- `cmc` - Converted mana cost
- `colors` - Array of colors ["U", "B"]
- `colorIdentity` - Commander color identity
- `typeLine` - Full type line
- `oracleText` - Rules text
- `power`, `toughness`, `loyalty` - P/T/Loyalty values
- `keywords` - Array of keywords

### Metadata
- `rarity` - common, uncommon, rare, mythic
- `setCode`, `setName` - Set information
- `artist` - Card artist
- `flavorText` - Flavor text

### EDHREC Data
- `edhrecRank` - Popularity ranking (lower = more popular)
- `edhrecSaltiness` - Community saltiness score
- `isCommander` - Can be used as commander

### Enhanced Data
- `tags` - Array of auto-generated tags
- `powerLevel` - Calculated 0-10 power score
- `legalities` - Format legality object
- `imageUris` - Card image URLs
- `prices` - Price data from multiple sources

## 🎯 Use Cases

### Deck Building
1. **Find Commanders**: `isCommander=true&colorIdentity=UG`
2. **Card Draw**: `q=draw&colorIdentity=U`
3. **Removal**: Tag-based search for removal spells
4. **Budget Options**: Filter by price data

### Collection Management
1. **High-Value Cards**: Sort by edhrecRank
2. **Format Legalities**: Filter by format
3. **Reserved List**: Query for reserved list cards

### Meta Analysis
1. **Popular Cards**: maxEdhrecRank=1000
2. **Salty Cards**: minSaltiness=1.5
3. **Game-Changing Effects**: Power level filtering

## 🚀 Integration

Use the card database in your deck builder to:
- **Validate card legality** in Commander
- **Display saltiness warnings** for high-salt cards
- **Suggest replacements** based on tags and power level
- **Calculate deck power level** from individual card scores
- **Show EDHREC popularity** for meta analysis
- **Auto-tag decks** based on card tags (aggro, control, combo, etc.)

## 📈 Power Level Calculation

Power levels are auto-calculated (0-10):
- **10**: EDHREC rank < 100 (Reserved list, staples)
- **9**: EDHREC rank < 500 (Very strong cards)
- **8**: EDHREC rank < 1000 (Strong cards)
- **7**: EDHREC rank < 5000 (Good cards)
- **6**: EDHREC rank < 10000 (Playable cards)
- **5**: Default for cards without rankings

Game-changer cards get +1 to their power level.
