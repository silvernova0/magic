# V3 Deck Builder - Future Improvements

This document tracks potential improvements to the v3 deck building system based on testing and user feedback.

## High Priority

### 1. ~~Smart Land Synergy Packages~~ ✅
**Status**: COMPLETED  
**Implementation**: Detects deck strategy and includes complete land packages when appropriate
- ✅ Tron lands (Urza's Mine/Tower/Power Plant) added as package for colorless/ramp strategies
- ✅ Cloudpost package (Cloudpost/Glimmerpost/Vesuva) added for colorless/ramp strategies
- ✅ Only includes full packages, never partial sets
- ✅ Individual synergy lands filtered out if package not appropriate
- ✅ Strategy keyword detection ('colorless', 'ramp', 'tron', 'post')

### 2. Mana Cost Validation for Multi-Color Decks
**Status**: Not implemented  
**Current**: Doomsday Excruciator ({B}{B}{B}{B}{B}{B}) can appear in 5-color decks  
**Needed**: Filter cards with high color devotion requirements that don't match deck's mana base
- [ ] Count color pips in mana cost (e.g., 6 black pips)
- [ ] Compare to deck's color distribution (from mana symbol analysis)
- [ ] Reject cards with >3 pips of a single color in 3+ color decks
- [ ] For 2-color decks, allow up to 4 pips if that color is >60% of symbols
- [ ] Mono-color decks: no restrictions

### 3. ~~Card Quality Scoring~~ ✅
**Status**: COMPLETED  
**Implementation**: Uses EDHREC rank to prioritize high-quality cards
- ✅ SQL queries order by EDHREC rank (lower = better, more popular)
- ✅ Priority card list for format staples (Sol Ring, etc.)
- ✅ Average deck quality improved from ~14,888 to ~885-1,480 rank
- ✅ Automatically includes top-tier cards (Moxen, The One Ring, fast mana)
- ✅ Works across all deck strategies and color identities
- ✅ Cards without rank data sorted to end (unranked cards less preferred)

### 4. Tribal Synergy Validation
**Status**: Minimal (filters subtypes)  
**Current**: Ally Encampment can appear in non-Ally decks (though rare now)  
**Needed**: Detect tribal lands and only include for matching tribes
- [ ] Map lands to their tribes (Ally Encampment → Ally, Cavern of Souls → any)
- [ ] Check if deck's creature types match the land's tribe
- [ ] Create whitelist of "universal" tribal lands (Unclaimed Territory, Path of Ancestry)

## Medium Priority

### 5. Enhanced Conditional Land Detection
**Status**: Basic implementation  
**Current**: Filters Serra's Sanctum, Gaea's Cradle by hardcoded list  
**Needed**: Smarter conditional land evaluation based on deck composition
- [ ] Count enchantments in deck before deciding on Serra's Sanctum
- [ ] If >15 enchantments, allow Serra's Sanctum
- [ ] If >25 creatures, allow Gaea's Cradle
- [ ] Cabal Coffers: allow if >20 Swamps in deck

### 6. Combo Detection
**Status**: Not implemented  
**Current**: No combo awareness  
**Needed**: Detect infinite combos and power level spikes
- [ ] Query EDHREC combos database
- [ ] If 2/3 combo pieces are in deck, suggest the 3rd
- [ ] Flag high-salt combos for power level adjustment
- [ ] Warn if adding card creates infinite combo (useful for bracket validation)

### 7. Mana Curve Optimization
**Status**: Not implemented  
**Current**: No curve validation  
**Needed**: Ensure balanced mana curve
- [ ] Count cards at each CMC (0-1, 2, 3, 4, 5, 6+)
- [ ] Target distribution: 10-15 @ CMC 1-2, 20-25 @ CMC 3-4, 15-20 @ CMC 5+
- [ ] Adjust queries to prefer cards filling gaps in curve
- [ ] For aggro: shift curve lower (more 1-3 CMC)
- [ ] For control: shift curve higher (more 4-6 CMC)

### 8. Basic Land Ratio Tuning
**Status**: Implemented (28 mono, 15 two-color, 8 three+)  
**Current**: Fixed ratios  
**Needed**: Adjust based on deck's average CMC
- [ ] High CMC decks (avg >4): +5 lands
- [ ] Low CMC decks (avg <3): -5 lands
- [ ] Heavy color requirements: +3 lands of that color
- [ ] Ramp-heavy decks: -5 lands

## Low Priority

### 9. Fetch Land Optimization
**Status**: Basic filtering (must fetch commander's land types)  
**Current**: May include suboptimal fetches  
**Needed**: Prioritize best fetches for color identity
- [ ] Rank fetches by how many relevant types they can find
- [ ] In 2-color: prefer fetches that get both types (e.g., Arid Mesa for W/R)
- [ ] In 5-color: prefer "any basic" fetches (Evolving Wilds, Terramorphic Expanse)

### 10. Budget Considerations
**Status**: Not implemented  
**Current**: May include Reserved List cards (e.g., The Tabernacle)  
**Needed**: Optional budget filtering
- [ ] Add price data to database (from Scryfall/TCGPlayer)
- [ ] Flag for budget mode (<$50, <$100, <$500 total)
- [ ] Replace expensive cards with budget alternatives
- [ ] Query EDHREC for budget replacements

### 11. Strategy-Specific Card Selection
**Status**: Basic (uses tags)  
**Current**: Generic card pools  
**Needed**: Strategy-aware selection
- [ ] For "voltron": prioritize equipment/auras, fewer creatures
- [ ] For "tokens": prioritize token generators and anthems
- [ ] For "aristocrats": prioritize sacrifice outlets and death triggers
- [ ] For "spellslinger": prioritize instants/sorceries, fewer creatures
- [ ] Map v3 strategies to EDHREC themes for better filtering

## Completed ✅

- ✅ **Smart Land Synergy Packages** - Tron and Cloudpost packages added for appropriate strategies
- ✅ **Card Quality Scoring** - EDHREC rank-based prioritization (avg rank 885-1,480)
- ✅ **Colorless Commander Filtering** - Excludes Arcane Signet and color-identity-dependent cards
- ✅ **Priority Ramp Cards** - Quality colorless ramp prioritized (Sol Ring, Basalt Monolith, etc.)
- ✅ **Improved Land Ratios** - Colorless decks use 18-22 basics instead of 30
- ✅ **Simplified Output Format** - Alphabetical list without categories for easy import
- ✅ Paper-only card filtering (no Arena/digital-only cards)
- ✅ Banned card filtering (Commander ban list)
- ✅ Color identity enforcement (priority cards validated)
- ✅ Commander exclusion from the 99
- ✅ Mana symbol analysis for weighted basic land distribution
- ✅ Conditional land filtering (Serra's Sanctum, Gaea's Cradle, etc.)
- ✅ Synergy dependency filtering (Tron lands, Cloudpost lands)
- ✅ Land usability validation (fetch lands must fetch commander's types)
- ✅ Cross-category deduplication (cards appear in only one category)
- ✅ Singleton format enforcement (except basics)

## Notes

### Testing Feedback Summary
From user validation sessions:
- **Ur-Dragon deck**: Playable but some suboptimal choices (King Darien, Doomsday Excruciator)
- **Krenko deck**: Good! 28 Mountains, proper tribal synergy, all legal cards
- **General**: System is ~80% there, needs fine-tuning on card quality and synergy edge cases

### Performance Considerations
- Current queries are fast (<1s per category)
- Adding combo detection may require caching
- Price data updates should be scheduled (not real-time)
- EDHREC synergy scores: consider caching top synergies per commander

### Data Sources Needed
- [ ] EDHREC combo database export
- [ ] Scryfall price API integration
- [ ] EDHREC synergy scores per commander
- [ ] Card quality ratings (community-driven or EDHREC-based)
