# Validation & Extended Scraping - Quick Reference

## 1. Card Validation Tools

### Validate Generated Decks Against Database

**Tool**: `scripts/validate_generated_deck.py`

Validates AI-generated decks against your MTGJson SQLite database (31,000+ cards).

**Checks**:
- ✅ All card names exist in database (no hallucinations)
- ✅ Exactly 100 cards total
- ✅ No invalid duplicates (allows Relentless Rats, basic lands, etc.)
- ✅ Color identity matches commander
- ✅ All cards are Commander-legal
- ✅ Commander is legendary

**Usage**:
```bash
# Validate a single deck file
python3 scripts/validate_generated_deck.py generated_decks/my_deck.txt

# Use in Python
from scripts.validate_generated_deck import DeckValidator

validator = DeckValidator()
result = validator.validate_deck(deck_text)

if result['valid']:
    print("✅ Deck is valid!")
else:
    print(f"❌ Errors: {result['errors']}")
```

---

### Automated Testing with Validation

**Tool**: `scripts/test-model-with-validation.py`

Runs complete test suite with automatic validation.

**Features**:
- Generates 5 test decks with diverse strategies
- Validates each deck against database
- Provides detailed error reports
- Saves results to `generated_decks/validated/`
- Summary report with pass/fail rates

**Usage**:
```bash
# Run full test suite
python3 scripts/test-model-with-validation.py

# Output shows validation results:
# ✅ VALID - ur-dragon-tribal
#   Cards: 100
#   Hallucinated: 0
#   Illegal: 0
#   Color violations: 0
```

**Test Cases**:
1. The Ur-Dragon - Tribal Dragons
2. Atraxa - +1/+1 counters and proliferate
3. Krenko - Budget goblins under $100
4. Tymna/Thrasios - cEDH control combo
5. Muldrotha - Graveyard value self-mill

---

## 2. Extended MTGGoldfish Scraping

### Unlimited Commander Decks via Date Range Batching!

MTGGoldfish advanced search provides access to massive Commander deck database.

**Scraper**: `scripts/scrape-mtggoldfish-advanced.py`

**Key Stats (Updated):**
- **Decks per page**: 32 decks (not 20)
- **Pages per search**: 313 pages maximum
- **Decks per search**: ~10,000 decks maximum per date range
- **Search limit workaround**: Batch by date ranges!
- **Total available**: **UNLIMITED** (470k+ decks from 2018-2025)

**Date Range Strategy:**
- Each 2-month batch = ~10,000 decks
- 2025 (11 months) = 6 batches × 10k = **60,000 decks**
- 2024-2025 (22 months) = 11 batches × 10k = **110,000 decks**
- 2018-2025 (94 months) = 47 batches × 10k = **470,000 decks**

---

### Usage Examples

**Single 2-Month Range** (~10k decks):
```bash
python3 scripts/scrape-mtggoldfish-advanced.py \
  --date-start "09/13/2025" \
  --date-end "11/06/2025"
```

**Auto-Batch Full Year** (~60k decks):
```bash
python3 scripts/scrape-mtggoldfish-advanced.py \
  --date-start "01/01/2025" \
  --date-end "11/06/2025" \
  --batch-months 2
```

**Auto-Batch 2024-2025** (~110k decks):
```bash
python3 scripts/scrape-mtggoldfish-advanced.py \
  --date-start "01/01/2024" \
  --date-end "11/06/2025" \
  --batch-months 2
```

**Historical Archive 2018-2025** (~470k decks):
```bash
python3 scripts/scrape-mtggoldfish-advanced.py \
  --date-start "01/01/2018" \
  --date-end "11/06/2025" \
  --batch-months 2
```

**Resume from Specific Page**:
```bash
# If scraper stopped at page 100, resume from there
python3 scripts/scrape-mtggoldfish-advanced.py \
  --date-start "09/13/2025" \
  --date-end "11/06/2025" \
  --start-page 100
```

**Run in Background**:
```bash
nohup python3 scripts/scrape-mtggoldfish-advanced.py \
  --date-start "01/01/2024" \
  --date-end "11/06/2025" \
  --batch-months 2 \
  > mtggoldfish_batch.log 2>&1 &

# Monitor
tail -f mtggoldfish_batch.log
```

**See `MTGGOLDFISH_BATCH_SCRAPING.md` for complete guide with all plans and strategies.**

---

### Why Use Extended Scraping?

**Problem**: Model hallucinates cards because it doesn't see enough card examples.

**Solution**: More decks = more unique cards = less hallucination.

**Dataset Size Comparison**:

| Dataset | Card Examples | Deck Examples | Total | Card/Deck Ratio |
|---------|--------------|---------------|-------|-----------------|
| **Current (Conservative)** | 6,515 | 15,311 | 21,826 | 30/70 |
| **Extended (2025 only)** | 27,990 | 65,311 | 93,301 | 30/70 |
| **Massive (2024-2025)** | 47,419 | 125,311 | 172,730 | 30/70 |
| **Archive (2018-2025)** | 201,133 | 485,311 | 686,444 | 30/70 |

**Recommendation**:
1. Start with **conservative** dataset (~15k decks)
2. Train model v2 and validate
3. If still seeing hallucinations, add **extended MTGGoldfish** data
4. Retrain with more card knowledge

---

## 3. Training Pipeline with Validation

### Complete Workflow

**Step 1**: Complete current scraping (~3-4 hours)
```bash
# Monitor progress
watch -n 60 'wc -l data/training/{archidekt,moxfield,mtggoldfish}_decks.jsonl'

# Expected: ~15,311 decks
```

**Step 2**: Prepare balanced dataset
```bash
python3 scripts/prepare-balanced-dataset-v2.py
# Output: 21,826 examples (30/70 card/deck ratio)
```

**Step 3**: Train model v2 (~12-16 hours)
```bash
BATCH_SIZE=2 GRADIENT_ACCUMULATION_STEPS=8 MAX_SEQ_LENGTH=675 \
  nohup python3 scripts/train-commander-model-optimized.py > training_v2.log 2>&1 &
```

**Step 4**: Validate model quality
```bash
python3 scripts/test-model-with-validation.py
```

**Step 5**: Assess results
- ✅ All decks valid? → Proceed to Phase 2 (constraint fine-tuning)
- ❌ Still hallucinating? → Add extended MTGGoldfish data, retrain

**Step 6** (if needed): Extended dataset
```bash
# Scrape 50k more decks
python3 scripts/scrape-mtggoldfish-advanced.py --max-decks 50000

# Prepare extended dataset (93k examples)
python3 scripts/prepare-balanced-dataset-v2.py --extended

# Retrain with more data (~18-24 hours)
nohup python3 scripts/train-commander-model-optimized.py > training_v2_extended.log 2>&1 &
```

---

## 4. Validation in Production

### Real-Time Validation

When deploying model, add validation layer:

```python
from scripts.validate_generated_deck import DeckValidator

validator = DeckValidator()

# Generate deck
deck = model.generate(prompt)

# Validate before returning to user
result = validator.validate_deck(deck)

if not result['valid']:
    # Regenerate or fix errors
    print(f"Validation failed: {result['errors']}")
    # Option 1: Retry generation
    # Option 2: Use card database to fix hallucinations
    # Option 3: Return error to user
```

### Integration with Ollama Inference

```python
# src/lib/ollama.ts equivalent in Python
def generate_validated_deck(commander, strategy, max_retries=3):
    for attempt in range(max_retries):
        deck = generate_deck(commander, strategy)
        validation = validator.validate_deck(deck)
        
        if validation['valid']:
            return deck
        
        print(f"Attempt {attempt+1} failed: {validation['errors']}")
    
    raise Exception("Could not generate valid deck after {max_retries} attempts")
```

---

## 5. Summary

**New Capabilities**:
1. ✅ **Database validation** - Checks all cards exist, prevents hallucinations
2. ✅ **Automated testing** - Validates model quality with test suite
3. ✅ **Extended scraping** - Access to 100k+ MTGGoldfish decks
4. ✅ **Quality assurance** - Ensures 100 cards, legal cards, color identity

**Recommended Approach**:
1. Complete current scraping (conservative ~15k decks)
2. Train model v2 with validation
3. If quality issues persist, add extended MTGGoldfish data
4. Retrain with more card examples
5. Deploy with real-time validation layer

**Files Created**:
- `scripts/validate_generated_deck.py` - Card database validator
- `scripts/test-model-with-validation.py` - Automated testing with validation
- `scripts/scrape-mtggoldfish-advanced.py` - Extended scraping (100k+ decks)
- Updated `INVENTORY_DECK_BUILDER_ROADMAP.md` - Includes validation steps
