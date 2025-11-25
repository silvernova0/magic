# New Commander Deck Strategies Added

## Date: November 11, 2025

Added **9 new deck strategies** to the deck builder and training pipeline.

## New Strategies

### 1. **Self Mill**
- **Description**: Mill yourself to fuel graveyard strategies
- **Adjustments**:
  - +10 to +15 self_mill_effects
  - +8 to +12 graveyard_payoffs
  - -5 to -8 creatures
- **Reasoning**: Fill graveyard quickly, leverage it as second hand
- **Examples**: Muldrotha, Gitrog Monster, Sidisi Brood Tyrant

### 2. **Discard**
- **Description**: Make opponents discard, benefit from discard triggers
- **Adjustments**:
  - +12 to +18 discard_effects
  - +5 to +8 card_draw
  - -8 to -12 creatures
- **Reasoning**: Strip opponent's hands, generate value from discard
- **Examples**: Tinybones, Kroxa, Nath of the Gilt-Leaf

### 3. **Cycling**
- **Description**: Cycle cards for value, cycling payoffs
- **Adjustments**:
  - +15 to +20 cycling_cards
  - +8 to +12 cycling_payoffs
  - +2 to +4 lands
  - -5 to -8 creatures
- **Reasoning**: Many cycling cards, payoffs trigger on each cycle
- **Examples**: Gavi, Nest Warden; Zur the Enchanter (Astral Slide build)

### 4. **Go Wide / Overrun**
- **Description**: Many creatures, overrun effects, go wide strategy
- **Adjustments**:
  - +10 to +15 creatures
  - +5 to +8 anthems
  - +5 to +8 overrun_effects
  - -5 to -8 removal
- **Reasoning**: Flood board with creatures, pump team and swing
- **Examples**: Jetmir, Adeline, Heliod God of the Sun
- **Note**: Similar to "Tokens" but focuses on actual creature cards, not token generators

### 5. **Pillowfort**
- **Description**: Prevent attacks, taxing effects, defensive strategy
- **Adjustments**:
  - +12 to +18 pillowfort_effects
  - +5 to +8 card_draw
  - -10 to -15 creatures
- **Reasoning**: Prevent combat damage, control with taxes, win slowly
- **Examples**: Karona False God, Oloro, Queen Marchesa

### 6. **Turbo Fog**
- **Description**: Fog effects every turn, prevent all combat damage
- **Adjustments**:
  - +15 to +20 fog_effects
  - +8 to +12 card_draw
  - -15 to -20 creatures
- **Reasoning**: Prevent all damage, draw cards, win with alternate wincon
- **Examples**: Angus Mackenzie, Isperia Supreme Judge

### 7. **Hate Bears**
- **Description**: Small creatures that disrupt opponents (Death & Taxes strategy)
- **Adjustments**:
  - +10 to +15 creatures
  - +12 to +18 hatebears
  - +3 to +5 protection
  - -5 to -8 removal
- **Reasoning**: Many small disruptive creatures, taxing effects
- **Examples**: Thalia Guardian of Thraben, Aven Mindcensor, Drannith Magistrate
- **Key Cards**: Thalia, Spirit of the Labyrinth, Collector Ouphe, Grand Abolisher

### 8. **Infect**
- **Description**: Win with poison counters (10 = death), proliferate
- **Adjustments**:
  - +8 to +12 creatures
  - +8 to +12 pump_spells
  - +5 to +8 proliferate
  - -5 to -8 removal
- **Reasoning**: Infect creatures, pump them, 10 poison kills
- **Examples**: Skithiryx, Atraxa (infect build), Fynn the Fangbearer

### 9. **Wheels**
- **Description**: Wheel effects (discard hand, draw 7), hand/graveyard synergies
- **Adjustments**:
  - +10 to +15 wheel_effects
  - +8 to +12 wheel_payoffs
  - +5 to +8 card_draw
  - -8 to -12 creatures
- **Reasoning**: Wheel to refill hands, trigger Nekusar/waste-not effects
- **Examples**: Nekusar, Xyris, Locust God
- **Key Cards**: Wheel of Fortune, Windfall, Notion Thief, Narset

## Total Strategy Count

- **Before**: 21 strategies
- **After**: 30 strategies

## Files Modified

### 1. `/data/training/deck_building_rules.json`
**Purpose**: Define card ratios and adjustments for each strategy

**Changes**: Added 9 new strategy definitions with adjustments for:
- Card type counts (creatures, lands, etc.)
- Strategy-specific card types (fog_effects, hatebears, cycling_cards, etc.)
- Reasoning for each adjustment

### 2. `/scripts/scrape-moxfield-themes.py`
**Purpose**: Scrape decks from Moxfield by theme

**Changes**: Added to `PRIORITY_THEMES` list:
- 'Turbo' (for Turbo Fog)
- 'Hatebears'
- 'Discard'

**Note**: Cycling, Infect, Mill, Pillowfort, Wheels already existed in the scraper

### 3. `/scripts/convert-to-v3-training.py`
**Purpose**: Convert scraped decks to v3 structured training format

**Changes**: Updated `detect_strategy()` function to recognize:
- self_mill (from 'self mill', 'dredge' themes)
- discard
- cycling
- go_wide (from 'go wide', 'overrun')
- pillowfort
- turbo_fog (from 'turbo', 'fog')
- hate_bears (from 'hatebears', 'hate bears', 'death & taxes')
- infect (from 'infect', 'poison')
- wheels (from 'wheels', 'wheel')

### 4. `/src/lib/constants.ts`
**Purpose**: UI constants for deck builder dropdown

**Changes**: Added 9 new strategies to `DECK_THEMES` array:
- 'Self Mill'
- 'Discard'
- 'Cycling'
- 'Go Wide'
- 'Pillowfort'
- 'Turbo Fog'
- 'Hate Bears'
- 'Infect'
- 'Wheels'

### 5. `/src/app/api/commander/build-from-collection/route.ts`
**Purpose**: API endpoint for deck building

**Changes**: Enhanced strategy name normalization with mapping:
```typescript
const strategyMap: Record<string, string> = {
  'kindred': 'tribal',
  'self mill': 'self_mill',
  'go wide': 'go_wide',
  'turbo fog': 'turbo_fog',
  'hate bears': 'hate_bears',
  'group hug': 'group_hug',
  'group slug': 'group_slug',
  'lands matter': 'lands_matter',
  'superfriends': 'superfriends',
};
```

## Impact on Training

### Current Dataset
- **Before new strategies**: 23,405 examples
- **Moxfield scraper**: Will now collect decks for new themes
- **MTGGoldfish scraper**: Already collects by commander (captures all strategies)

### Expected Additional Data
- **Cycling**: ~500-1000 decks (popular with Gavi, Astral Slide)
- **Discard**: ~300-500 decks (Tinybones, Kroxa)
- **Wheels**: ~800-1200 decks (very popular - Nekusar, Xyris)
- **Infect**: ~200-400 decks (niche but dedicated playerbase)
- **Hate Bears**: ~300-500 decks (popular in higher brackets)
- **Pillowfort**: ~400-600 decks (Oloro, Queen Marchesa)
- **Turbo Fog**: ~100-200 decks (very niche)
- **Self Mill**: ~500-800 decks (Muldrotha, Gitrog, Sidisi)
- **Go Wide**: ~1000-1500 decks (very common - Jetmir, Adeline)

**Estimated Total**: 4,100-7,700 new training examples

### Training Impact
- Broader strategy coverage ensures model learns diverse deck-building patterns
- Self Mill and Go Wide are very common archetypes that were missing
- Wheels is particularly important (Nekusar is a top commander)
- Combined with existing 23,405 examples → **~27,500-31,000 total examples**

## Next Steps

1. ✅ **COMPLETE**: Updated all configuration files
2. ⏳ **IN PROGRESS**: Current scrapers running (MTGGoldfish at 246/2500 commanders)
3. 🔜 **TODO**: Restart Moxfield scraper to include new themes
4. 🔜 **TODO**: Re-run `convert-to-v3-training.py` after scraping completes
5. 🔜 **TODO**: Package data for Windows training
6. 🔜 **TODO**: Train 7B model with expanded dataset

## Testing the New Strategies

To test the new strategies work in the deck builder:

1. Navigate to `/deckbuilder`
2. Select one of the new strategies from dropdown:
   - Self Mill
   - Discard
   - Cycling
   - Go Wide
   - Pillowfort
   - Turbo Fog
   - Hate Bears
   - Infect
   - Wheels
3. Choose colors and bracket
4. Generate deck

Expected behavior:
- Commander selection should find appropriate commander for strategy
- Deck ratios should follow strategy adjustments from `deck_building_rules.json`
- Strategy name should normalize correctly (spaces → underscores)

## Strategy Name Normalization

**UI Display** → **Database/Training**:
- Self Mill → self_mill
- Go Wide → go_wide
- Turbo Fog → turbo_fog
- Hate Bears → hate_bears
- Group Hug → group_hug
- Group Slug → group_slug
- Lands Matter → lands_matter
- Superfriends → superfriends
- Kindred → tribal

All other strategies use lowercase without underscores (aggro, combo, control, etc.)

## Related Documentation

- `DECK_BUILDER_FIXES.md` - Recent fixes to card filtering and commander selection
- `WINDOWS_RTX_TRAINING_GUIDE.md` - Training workflow for 7B model
- `data/training/deck_building_rules.json` - Complete strategy definitions

## Status

✅ **COMPLETE** - All 9 strategies added to:
- Deck building rules (ratios and adjustments)
- UI constants (dropdown options)
- API normalization (name mapping)
- Data conversion (strategy detection)
- Scraping configuration (theme priorities)

🔄 **READY FOR SCRAPING** - Moxfield scraper can now collect new themes
🔄 **READY FOR TRAINING** - v3 conversion will recognize all 30 strategies
