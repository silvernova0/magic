# Gemini AI Deck Builder - Enhanced Features

## Overview

Your Magic: The Gathering deck builder now features an advanced AI-powered deck building system using Google's Gemini AI with context from:
- **EDHREC.com** - Commander statistics and popularity data
- **MTGTop8.com** - Tournament results and competitive meta
- **Moxfield.com** - Power level brackets (1-5 scale)

## Features

### 🎯 Deck Building Options

#### 1. **Commander Selection**
- Specify a commander OR let AI suggest the best one
- AI references popular commanders from EDHREC for your theme

#### 2. **Theme/Archetype**
Choose from 20+ deck archetypes:
- **Aggro** - Fast, aggressive creature strategies
- **Tempo** - Efficient threats with disruption
- **Control** - Counter spells, removal, late-game wins
- **Stax** - Tax effects and resource denial
- **Combo** - Multi-card instant-win combinations
- **Midrange** - Value engines and resilient threats
- **Tribal** - Creature type synergies
- **Voltron** - Commander damage with equipment/auras
- **Tokens** - Go-wide strategies
- **Aristocrats** - Sacrifice and death triggers
- **Reanimator** - Graveyard recursion
- And more...

#### 3. **Color Identity**
- Select specific colors (W/U/B/R/G/Colorless)
- Leave empty for any color combination
- Commander must match selected colors

#### 4. **Power Level (Moxfield Brackets)**

**Bracket 1 - Precon Level**
- Unmodified preconstructed decks
- Basic lands, simple synergies
- No fast mana or tutors

**Bracket 2 - Casual**
- Upgraded precons
- Some ramp and basic tutors
- Tribal synergies

**Bracket 3 - Focused**
- Tuned with good synergies
- Efficient ramp and card draw
- Some combos and tutors

**Bracket 4 - Optimized**
- Highly optimized strategies
- Fast mana (Sol Ring, Mana Crypt)
- Powerful tutors and strong combos

**Bracket 5 - Competitive (cEDH)**
- Aims to win turns 1-4
- Best-in-slot cards
- Instant-win combos
- Minimal interaction

#### 5. **Collection Options**

**Use Collection Only** ✓
- AI builds from YOUR cards only
- Perfect for budget builds
- Uses cards you actually own

**Use Any Cards** ✗
- AI selects from entire MTG card pool
- References popular cards from EDHREC/MTGTop8
- Includes staples for the power level

## How to Use

### Step 1: Access Deck Builder
Navigate to **Deck Builder** from the sidebar or go to `/deckbuilder`

### Step 2: Configure Your Deck

1. **Commander (Optional)**
   - Enter a specific commander name, OR
   - Leave empty for AI suggestion

2. **Theme**
   - Select from dropdown (Aggro, Control, Stax, etc.)

3. **Colors**
   - Click color symbols to select
   - Leave empty for any colors

4. **Power Level**
   - Choose Bracket 1-5 from dropdown
   - Read descriptions to match your playgroup

5. **Collection**
   - Check "Build from my collection only" if desired
   - Paste your card list (one per line)

### Step 3: Build
Click **"Build My Commander Deck"** and wait for AI to generate your deck!

## Example Builds

### Example 1: Budget Tribal Deck
```
Commander: (leave empty)
Theme: Tribal
Colors: Green, White
Power Level: Bracket 2
Use Collection Only: ✓
Collection: (paste your cards)
```
**Result**: AI suggests best tribal commander for your G/W cards and builds around them

### Example 2: Competitive Stax
```
Commander: Grand Arbiter Augustin IV
Theme: Stax
Colors: White, Blue
Power Level: Bracket 4
Use Collection Only: ✗
```
**Result**: Optimized stax deck with tax effects and resource denial

### Example 3: Combo Deck
```
Commander: (leave empty)
Theme: Combo
Colors: Blue, Black
Power Level: Bracket 3
Use Collection Only: ✗
```
**Result**: AI suggests best U/B combo commander and includes popular combos

## AI Context Sources

### EDHREC.com Integration
The AI is trained on:
- Most popular commanders by theme
- Top played cards for each commander
- Synergy scores and card relationships
- Budget alternatives

### MTGTop8.com Integration
The AI references:
- Tournament-winning decklists
- Competitive meta trends
- Proven card combinations
- Sideboard strategies (adapted for EDH)

### Moxfield.com Integration
The AI uses:
- Power level bracket definitions
- Deck categorization system
- Community standards for power levels

## Deck Analysis Features

### After Building
Your generated deck includes:
- **Description** - Overview of the strategy
- **Key Cards** - Most important cards for the strategy
- **Strategy Guide** - How to pilot the deck
- **Card Categories** - Organized by type (creatures, instants, etc.)

### Deck Stats
- Total cards: 100 (singleton format)
- Commander: 1-2 legendary creatures
- Lands: ~35-40 (adjusts by power level)
- Ramp: 8-12 sources
- Card Draw: 8-10 sources
- Removal: 8-10 pieces

## Advanced Tips

### 1. **Power Level Matching**
- Choose bracket based on your playgroup
- Bracket 3 is most common for casual commander
- Bracket 4-5 requires expensive cards and fast combos

### 2. **Color Selection**
- Fewer colors = more consistent mana base
- More colors = more options but risky mana
- 2-3 colors recommended for most builds

### 3. **Collection Building**
- Start with "Use Any Cards" to see ideal list
- Switch to "Collection Only" for budget version
- Import your collection from Moxfield/Archidekt

### 4. **Theme Synergy**
- Tribal works best in G/W/R colors
- Control excels in U/W/B
- Aggro prefers R/G/W
- Combo loves U/B/R

## Troubleshooting

**"Failed to generate deck"**
- Check your internet connection
- Try simpler theme or fewer restrictions
- Ensure collection has enough cards (if using collection only)

**"Deck has wrong number of cards"**
- AI may need retry
- Click "Build" again for new generation
- Report consistent issues

**"Missing commander"**
- Specify a commander manually
- Try different color combination
- Ensure colors are valid for theme

## API Endpoints

### Build Deck
```
POST /api/commander/build
Body: {
  commander?: string,
  theme: string,
  colors: string[],
  powerLevel: string,
  useCollectionOnly: boolean,
  collection?: string
}
```

### Get Commander Suggestions
```
POST /api/commander/suggest
Body: {
  colors: string[],
  theme: string,
  powerLevel: string
}
```

## Future Enhancements

Coming soon:
- Deck analysis and improvement suggestions
- Card upgrade recommendations
- Sideboard suggestions
- Meta analysis
- Budget alternatives
- Deck comparison tools

## Credits

- **Gemini AI** by Google - Core AI engine
- **EDHREC.com** - Commander statistics
- **MTGTop8.com** - Tournament data
- **Moxfield.com** - Power level standards
- **Scryfall** - Card database and images

## Support

For issues or questions:
1. Check this documentation
2. Review error messages in console
3. Try rebuilding with different parameters
4. Contact support with detailed description

---

**Happy Deck Building! 🎴✨**
