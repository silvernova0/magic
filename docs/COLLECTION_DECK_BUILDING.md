# Collection-Based Deck Building

The app now supports building Commander decks from your personal card collection using the v3 deck builder with quality scoring and smart synergies.

## Features

✅ **Build from Your Collection** - Only use cards you actually own
✅ **Quality Card Scoring** - Prioritizes best cards using EDHREC rank
✅ **Smart Land Synergy** - Automatically includes Tron/Cloudpost packages when appropriate
✅ **Color Identity Enforcement** - Only legal cards for your commander
✅ **Optimal Land Ratios** - Balanced mana base with proper basic land counts

## How to Use

### 1. Import Your Collection

First, add cards to your collection:

**Option A: Manual Entry**
- Go to `/collection`
- Add cards one by one with quantities

**Option B: Bulk Import**
- Go to `/import`
- Paste your collection export (from MTGA, Moxfield, Archidekt, etc.)
- Format: `quantity cardname` per line

Example:
```
1 Sol Ring
1 Command Tower
4 Forest
1 Llanowar Elves
```

### 2. Build a Deck from Collection

1. Go to `/deckbuilder`
2. Enter your commander name
3. Select theme/strategy
4. Choose power level (1-5)
5. **Enable "Use Collection Only"** checkbox
6. Click "Build Deck"

The v3 deck builder will:
- Only select cards from your collection
- Prioritize high-quality cards (EDHREC rank)
- Include smart land packages (Tron/Cloudpost for colorless)
- Enforce color identity
- Create a legal 100-card deck

### 3. View Your Deck

After generation, you'll be redirected to the deck view where you can:
- See the complete decklist
- Export to various formats
- Save or edit the deck

## API Endpoints

### Build Deck from Collection
```http
POST /api/commander/build-from-collection
Content-Type: application/json

{
  "commander": "Ulamog, the Ceaseless Hunger",
  "strategy": "colorless ramp",
  "powerLevel": 8,
  "bracket": 4,
  "useCollectionOnly": true
}
```

**Response**:
```json
{
  "success": true,
  "deck": {
    "id": "...",
    "name": "Ulamog, the Ceaseless Hunger - colorless ramp",
    "decklist": { ... }
  },
  "message": "Deck built from your collection"
}
```

### Get Collection
```http
GET /api/collection
```

**Response**:
```json
{
  "success": true,
  "stats": {
    "totalCards": 250,
    "uniqueCards": 180
  },
  "cards": [
    {
      "name": "Sol Ring",
      "quantity": 1,
      "rarity": "uncommon",
      ...
    }
  ]
}
```

## Python Deck Builder Integration

The app uses `scripts/build-deck-from-structure.py` which now supports collection filtering:

**Input JSON (with collection)**:
```json
{
  "commander": "Krenko, Mob Boss",
  "strategy": "tribal",
  "bracket": 3,
  "power_level": 7,
  "collection": ["Mountain", "Sol Ring", "Krenko, Mob Boss", ...],
  "card_selection": {
    "lands": { "count": 37, "filters": [{"types": ["Land"]}] },
    "creatures": { "count": 30, "filters": [{"subtypes": ["Goblin"]}] },
    ...
  }
}
```

The deck builder will:
1. Load your collection
2. Query only cards from your collection
3. Apply quality scoring (EDHREC rank)
4. Build optimal 100-card deck

## Quality Improvements

**Compared to Random Selection**:
- Average EDHREC rank: ~885 (vs ~14,888)
- Includes format staples automatically (Sol Ring, etc.)
- Better mana curves and synergies
- Legal and optimized land bases

**Smart Features**:
- Excludes Arcane Signet from colorless decks (doesn't work)
- Includes Tron lands as package for colorless ramp
- Weighted basic land distribution based on mana symbols
- Filters conditional lands without support

## Troubleshooting

**"Your collection is empty"**
- Import cards first at `/import` or `/collection`

**"Failed to build deck"**
- Check if you have enough cards in your collection
- Ensure commander is in your collection (or manually add)
- Try a lower power level if collection is limited

**Deck has too few cards**
- You may not have enough cards in collection matching the filters
- Try broader strategies or import more cards
- Lower power level requirements

## Future Enhancements

- [ ] Multiple deck iterations from same collection
- [ ] Budget mode (use only cards under $X)
- [ ] Collection value tracking
- [ ] Trade suggestions to complete decks
- [ ] Deck optimization recommendations
