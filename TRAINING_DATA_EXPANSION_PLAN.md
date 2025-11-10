# Training Data Expansion Plan

## Current Status (November 6, 2025)

### Existing Data
- **Moxfield decks**: 4,161 (81.2% are valid 100-card decks)
- **Moxfield diverse**: 1,457
- **TappedOut**: 25
- **EDHREC**: 0
- **Archidekt**: 0
- **cEDH Database**: 0
- **MTGGoldfish**: 0
- **Total**: 5,643 decks

### Problem with First Training Run
- **Data ratio**: 80% card knowledge / 20% decks (16,744 card examples vs 4,186 deck examples)
- **Result**: Model learned to explain individual cards, not build complete decklists
- **Validation loss**: Good (0.17), but output quality is poor - hallucinations, wrong format, incomplete decks

### Target for Quality Training
- **Minimum**: 10,000-15,000 complete decklists
- **Ideal**: 20,000-30,000 complete decklists
- **Ratio**: 50/50 or 60/40 (decks/cards) instead of 20/80

## Expansion Strategy

### Phase 1: Moxfield Deep Scrape (Target: +5,000 decks)

**Current scraper settings:**
- max_pages: 50 per theme+bracket combo
- 39 themes × 5 brackets = 195 combinations
- Current yield: ~30 decks per combination average

**Expansion plan:**
1. Increase max_pages: 50 → 100 per combo (+50%)
2. Add more sorting options (views, updated, created) to get different decks
3. Add date filters to get historical decks
4. Expected yield: +2,500-3,000 decks

**Commands:**
```bash
# Update scraper to use max_pages=100
python scripts/scrape-moxfield-themes.py  # Will take 4-6 hours
```

### Phase 2: EDHREC Scraping (Target: +3,000 decks)

**Source**: https://edhrec.com/commanders
- 1,000+ popular commanders with sample decklists
- Average 5-10 decklists per commander
- High-quality, community-vetted builds

**Create new scraper:**
```python
# scripts/scrape-edhrec-commanders.py
# Target: Top 500 commanders × 6 decks = 3,000 decks
```

### Phase 3: Archidekt Scraping (Target: +2,000 decks)

**Source**: https://archidekt.com/search/decks
- Public Commander decks with similar filtering to Moxfield
- API available: https://archidekt.com/api/decks/cards/

**Create new scraper:**
```python
# scripts/scrape-archidekt.py
# Target: 2,000-3,000 validated Commander decks
```

### Phase 4: cEDH Database (Target: +500 decks)

**Source**: https://cedh-decklist-database.com/
- Curated competitive EDH decklists
- High-quality, tournament-proven builds
- JSON API available

**Create new scraper:**
```python
# scripts/scrape-cedh-database.py
# Target: All available cEDH decks (~500-800)
```

### Phase 5: TappedOut Expansion (Target: +1,000 decks)

**Current**: Only 25 decks scraped
**Available**: 50,000+ Commander decks

**Update existing scraper:**
```bash
# Increase from 500 to 2,000 decks
python scripts/scrape-tappedout.py  # max_pages=200
```

### Phase 6: MTGGoldfish Commander (Target: +500 decks)

**Source**: https://www.mtggoldfish.com/metagame/commander
- Meta decklists
- Budget builds
- Paper + MTGO decks

**Create new scraper:**
```python
# scripts/scrape-mtggoldfish-commander.py
# Target: 500-1,000 decks
```

## Data Quality Requirements

### Validation Rules (CRITICAL)
All scraped decks must pass:
1. **Exactly 100 cards** (99 mainboard + 1 commander OR 98 mainboard + 2 commanders)
2. **Color identity validation** - Every card's color identity ⊆ commander's color identity
3. **No hallucinated cards** - All cards exist in MTGJson database (32,735 valid cards)
4. **Proper structure** - Commander, Creatures, Instants, Sorceries, Artifacts, Enchantments, Planeswalkers, Lands sections
5. **No duplicates** - Track deck IDs to avoid re-scraping

### Deduplication Strategy
- Track Moxfield IDs, EDHREC URLs, Archidekt IDs
- Store in `data/training/scraped_deck_ids.json`
- Skip decks already in training set

## New Training Dataset Preparation

### Balanced Dataset v2 (Target Ratio: 60/40 Decks/Cards)

**With 15,000 decks:**
- 15,000 deck examples (60%)
- 10,000 card knowledge examples (40%)
- Total: 25,000 training examples

**With 20,000 decks:**
- 20,000 deck examples (67%)
- 10,000 card knowledge examples (33%)
- Total: 30,000 training examples

**Preparation script:**
```bash
python scripts/prepare-balanced-dataset-v2.py --deck-ratio 0.6 --min-decks 15000
```

## Retrieval-Augmented Generation (RAG) Alternative

Instead of cramming all card data into training, use RAG:

### Architecture
1. **Training data**: Only decklists (no card knowledge examples)
2. **Card database**: SQLite with 32,735 cards (prisma/dev.db)
3. **Inference**: Model queries database for card details when generating

### Benefits
- Eliminates card hallucinations (always pulls from real DB)
- Smaller training dataset (20k decks vs 30k mixed)
- Faster training (~8-10 hours vs 14 hours)
- Always up-to-date with new cards (add to DB, no retraining)

### Implementation
```python
# src/lib/rag-deck-builder.ts
async function buildDeckWithRAG(commander: string, strategy: string) {
  // 1. Get commander details from database
  const commanderCard = await prisma.card.findFirst({ where: { name: commander }});
  
  // 2. Query cards matching strategy + color identity
  const candidateCards = await prisma.card.findMany({
    where: {
      colorIdentity: { hasSome: commanderCard.colorIdentity },
      tags: { hasSome: [strategy] }
    },
    orderBy: { edhrecRank: 'asc' },
    take: 200
  });
  
  // 3. Generate deck with LLM + card pool constraints
  const deck = await model.generate(prompt, { availableCards: candidateCards.map(c => c.name) });
  
  // 4. Validate every card exists in database
  return validateAndCorrectDeck(deck, candidateCards);
}
```

### Hybrid Approach (Recommended)
- **Training**: 15,000 decklists + 5,000 card knowledge (75/25 ratio)
- **Inference**: RAG for card validation and suggestions
- **Best of both worlds**: Model learns deck patterns, RAG prevents hallucinations

## Timeline

### Immediate (Week 1)
- [x] Analyze existing data quality
- [ ] Update Moxfield scraper (max_pages=100)
- [ ] Run expanded Moxfield scrape (4-6 hours)
- [ ] Create EDHREC scraper
- [ ] Run EDHREC scrape (2-3 hours)
- **Target**: +5,000 decks → 10,643 total

### Short-term (Week 2)
- [ ] Create Archidekt scraper
- [ ] Run Archidekt scrape (3-4 hours)
- [ ] Update TappedOut scraper settings
- [ ] Run TappedOut expansion (4-5 hours)
- **Target**: +3,000 decks → 13,643 total

### Medium-term (Week 3)
- [ ] Create cEDH Database scraper
- [ ] Create MTGGoldfish scraper
- [ ] Run final scrapes
- [ ] Prepare balanced dataset v2 (60/40 ratio)
- [ ] Test training on 5k sample
- **Target**: +1,500 decks → 15,143 total

### Long-term (Week 4)
- [ ] Full training run with 15k decks (~12-14 hours)
- [ ] Validate output quality
- [ ] Implement RAG validation layer
- [ ] Deploy to production

## Success Metrics

### Data Quality
- [ ] 15,000+ valid 100-card decklists
- [ ] <1% invalid cards after scraping
- [ ] 1,000+ unique commanders represented
- [ ] All 10 power brackets/strategies covered

### Model Quality
- [ ] 100% valid card names (no hallucinations)
- [ ] Exactly 100 cards per deck (±0)
- [ ] Correct color identity (100%)
- [ ] Proper deck structure (Commander, Creatures, etc.)
- [ ] Diverse strategies (not all aggro/combo)
- [ ] Reasonable power levels (not all cEDH)

### Training Metrics
- [ ] Validation loss < 0.15
- [ ] No repetitive text generation
- [ ] Completes 100-card decks in <1024 tokens
- [ ] <5% duplicate cards per deck

## Recommendations

1. **Priority 1**: Expand Moxfield scraping (easiest, high yield)
2. **Priority 2**: Add EDHREC scraping (high quality decks)
3. **Priority 3**: Implement RAG validation layer (prevents hallucinations)
4. **Priority 4**: Retrain with 60/40 deck/card ratio
5. **Priority 5**: Add remaining sources (Archidekt, cEDH, etc.)

## Commands to Run

```bash
# 1. Update Moxfield scraper max_pages
sed -i 's/max_pages=50/max_pages=100/g' scripts/scrape-moxfield-themes.py

# 2. Run expanded scrape
python scripts/scrape-moxfield-themes.py

# 3. Check new deck count
wc -l data/training/moxfield_decks.jsonl

# 4. Create EDHREC scraper (manual - needs implementation)
# See Phase 2 above

# 5. Prepare new balanced dataset
python scripts/prepare-balanced-dataset-v2.py --deck-ratio 0.6

# 6. Test sample training (optional)
python scripts/train-commander-model-optimized.py --max-steps 500

# 7. Full training run
BATCH_SIZE=2 GRADIENT_ACCUMULATION_STEPS=8 MAX_SEQ_LENGTH=675 \
  nohup python scripts/train-commander-model-optimized.py > training_v2.log 2>&1 &
```
