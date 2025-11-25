# v3 Training Data - READY FOR WINDOWS TRANSFER

## Dataset Summary

**Total Examples**: 29,152 structured training examples
**File Size**: 41 MB
**Format**: v3 structured JSON (no card name generation)

## Data Sources

| Source | Decks | Purpose |
|--------|-------|---------|
| EDHREC Average Decks | 2,557 | Commander-specific patterns |
| MTGGoldfish Commander | 21,854 | Meta decks across all power levels |
| Moxfield Themes | 4,063 | Theme/bracket filtered builds |
| TappedOut | 101 | Community decks |
| Vehicle Commanders | 179 | Legendary vehicle commanders |
| MTGGoldfish Advanced | 60 | High-level competitive |
| Precons | 2 | Official preconstructed decks |
| **EDHTop16 Tournaments** | **336** | **cEDH tournament winners** |

## Strategy Distribution

- **Midrange**: 24,297 (83.3%) - Dominant strategy
- **Combo**: 1,630 (5.6%) - Competitive combos
- **Tribal**: 1,194 (4.1%) - Creature type synergies
- **Aggro**: 470 (1.6%)
- **Voltron**: 283 (1.0%)
- Other strategies: <1% each

## Power Level Distribution

### By Bracket
- **Bracket 2** (Casual): 56.0%
- **Bracket 3** (Optimized): 32.1%
- **Bracket 4** (High-Power): 3.9%
- **Bracket 5** (cEDH): 8.0% ← Boosted from 7.3% with tournament data

### By Power Level (1-10 scale)
- Level 5: 57.4% (sweet spot for most players)
- Level 4: 16.7%
- Level 6: 10.3%
- Level 10: 6.4% (cEDH)
- Level 7: 4.5%
- Level 8: 2.2%
- Level 9: 1.5%
- Level 3: 0.9%

## Commander Synergy Capture

**Priority Cards per Deck**: 20 (improved from 6)

Sampling Strategy:
- First 10 cards (early game staples, ramp, removal)
- Every 5th card from position 10-60 (mid-game synergies, combos)

**Verified Synergies**:
- ✅ Vivi Ornitier → Quicksilver Elemental (pos 55)
- ✅ Edgar Markov → Vampire tribal + Anointed Procession
- ✅ Ur-Dragon → Scion of Ur-Dragon
- ✅ Kinnan (tournament) → Fast combo patterns

## Token Length Analysis

- **Range**: 310-405 tokens per example
- **Median**: 355 tokens
- **Max allowed**: 600 tokens
- **Status**: ✅ All examples fit comfortably

## v3 Format Highlights

### Zero Hallucinations
- Model generates **filters/queries**, not card names
- Database executes queries to get actual cards
- All cards guaranteed to exist and be legal

### Structure Example
```json
{
  "commander": "Kinnan, Bonder Prodigy",
  "strategy": "combo",
  "bracket": 5,
  "power_level": 10,
  "card_selection": {
    "lands": {"count": 30, "filters": [...]},
    "ramp": {"count": 20, "filters": [{"tags": ["ramp"], "cmc_max": 2}]},
    "creatures": {"count": 15, "filters": [{"tags": ["combo"]}]},
    "interaction": {"count": 25, "filters": [{"tags": ["counterspell", "removal"]}]}
  },
  "priority_cards": [
    "Kinnan, Bonder Prodigy",
    "Basalt Monolith",
    "Mana Crypt",
    "Force of Will",
    ...
  ]
}
```

## Next Steps

### 1. Package for Windows Transfer
```bash
# Create transfer package
tar -czf v3_training_data.tar.gz \
  data/training/v3_structured_training.jsonl \
  data/training/deck_building_rules.json

# Transfer to Windows training machine
# SMB: //192.168.0.151/aitrainingv4/
```

### 2. Train on Windows RTX 5070 Ti
- Model: Mistral 7B or Llama 3.1 8B
- Method: LoRA fine-tuning
- VRAM: 16GB available
- Duration: 10-12 hours overnight
- Guide: WINDOWS_RTX_TRAINING_GUIDE.md

### 3. Test & Deploy
- Test structured output generation
- Verify card selection filters work
- Deploy to production deck builder

## Tournament Data Impact

**Added**: 336 cEDH/high-power tournament decks
**Benefit**: Teaches competitive deck patterns
**Impact**: 
- Bracket 5 boosted from 7.3% → 8.0%
- Total dataset: +1.2% size
- Combo strategy: +7% examples (1,521 → 1,630)

**Top Tournament Commanders**:
- Kinnan, Bonder Prodigy (39 decks)
- Etali, Primal Conqueror (24 decks)
- Sisay, Weatherlight Captain (15 decks)
- Kefka, Court Mage (11 decks)
- Tivit, Seller of Secrets (10 decks)

## File Versions

- `v3_structured_training.jsonl` (41 MB) ← **USE THIS**
- `v3_structured_training_no_tournaments.jsonl` (41 MB) - Backup without tournaments
- `v3_structured_training_old.jsonl` (33 MB) - Old version with 6 priority cards

---

**Status**: ✅ READY FOR TRAINING
**Date**: November 11, 2025
**Total Time**: ~6 hours (scraping + conversion + improvements)
