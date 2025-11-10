# MTGGoldfish Batch Scraping Guide

## Key Discovery

**MTGGoldfish Search Limits:**
- **32 decks per page** (not 20 as originally thought)
- **313 pages maximum** per search
- **~10,000 decks maximum** per single date range search
- **Solution**: Batch by date ranges to get unlimited decks!

## Strategy: 2-Month Batches

**Each 2-month period yields ~10,000 decks**

Example batches for 2025:
- 09/13/2025 - 11/06/2025 = ~10,000 decks
- 07/13/2025 - 09/12/2025 = ~10,000 decks
- 05/13/2025 - 07/12/2025 = ~10,000 decks
- 03/13/2025 - 05/12/2025 = ~10,000 decks
- 01/13/2025 - 03/12/2025 = ~10,000 decks

**Result**: ~50,000 decks from just 2025!

---

## Usage Examples

### 1. Single 2-Month Range (~10k decks)

```bash
python3 scripts/scrape-mtggoldfish-advanced.py \
  --date-start "09/13/2025" \
  --date-end "11/06/2025"
```

### 2. Auto-Batch Entire Year (~60k decks)

```bash
python3 scripts/scrape-mtggoldfish-advanced.py \
  --date-start "01/01/2025" \
  --date-end "11/06/2025" \
  --batch-months 2
```

This automatically splits into 6 batches of 2 months each.

### 3. Scrape All of 2024-2025 (~110k decks!)

```bash
python3 scripts/scrape-mtggoldfish-advanced.py \
  --date-start "01/01/2024" \
  --date-end "11/06/2025" \
  --batch-months 2
```

**Result**: 22 months = 11 batches × 10k decks = **~110,000 decks!**

### 4. Custom Batch Size (3-month chunks)

```bash
python3 scripts/scrape-mtggoldfish-advanced.py \
  --date-start "01/01/2024" \
  --date-end "11/06/2025" \
  --batch-months 3
```

### 5. Limit Decks Per Range (Faster Testing)

```bash
python3 scripts/scrape-mtggoldfish-advanced.py \
  --date-start "09/13/2025" \
  --date-end "11/06/2025" \
  --max-per-range 5000
```

### 6. Resume from Specific Page

```bash
# If scraper stopped at page 100 in first range, resume:
python3 scripts/scrape-mtggoldfish-advanced.py \
  --date-start "09/13/2025" \
  --date-end "11/06/2025" \
  --start-page 100
```

### 7. Run in Background

```bash
nohup python3 scripts/scrape-mtggoldfish-advanced.py \
  --date-start "01/01/2024" \
  --date-end "11/06/2025" \
  --batch-months 2 \
  > mtggoldfish_batch.log 2>&1 &

# Monitor progress
tail -f mtggoldfish_batch.log
```

---

## Recommended Scraping Plans

### Plan A: Conservative (Current Strategy)

**Goal**: ~15k decks for v2 training

```bash
# Already running:
# - Archidekt: ~3,350 decks
# - Moxfield: ~8,961 decks  
# - MTGGoldfish archetype: ~3,000 decks
# Total: ~15,311 decks

# Current scrapers will complete in ~4 hours
# No additional scraping needed
```

### Plan B: Extended (~65k decks)

**Goal**: More card diversity if v2 hallucinates

```bash
# After v2 training, if model still hallucinates, add:
python3 scripts/scrape-mtggoldfish-advanced.py \
  --date-start "01/01/2025" \
  --date-end "11/06/2025" \
  --batch-months 2

# Result: ~50,000 additional decks
# New total: 15,311 + 50,000 = ~65,311 decks
# Training time: ~18-24 hours (vs 12-16 for v2)
```

### Plan C: Massive (~125k decks)

**Goal**: Maximum card knowledge diversity

```bash
# Scrape all of 2024-2025:
python3 scripts/scrape-mtggoldfish-advanced.py \
  --date-start "01/01/2024" \
  --date-end "11/06/2025" \
  --batch-months 2

# Result: ~110,000 additional decks
# New total: 15,311 + 110,000 = ~125,311 decks!
# Training time: ~36-48 hours
```

### Plan D: Historical Archive (2018-2025)

**Goal**: Complete historical coverage

```bash
# Scrape all Commander decks since 2018:
python3 scripts/scrape-mtggoldfish-advanced.py \
  --date-start "01/01/2018" \
  --date-end "11/06/2025" \
  --batch-months 2

# Result: 94 months = 47 batches × ~10k = ~470,000 decks!!!
# Training time: 5-7 days (requires massive dataset handling)
# Storage: ~5-10GB of training data
```

---

## Performance Estimates

| Plan | Decks | Scraping Time | Training Time | Storage |
|------|-------|---------------|---------------|---------|
| **A: Conservative** | ~15k | 4 hours | 12-16 hours | ~150 MB |
| **B: Extended** | ~65k | 20-24 hours | 18-24 hours | ~650 MB |
| **C: Massive** | ~125k | 40-48 hours | 36-48 hours | ~1.2 GB |
| **D: Historical** | ~470k | 7-10 days | 5-7 days | ~4-5 GB |

**Recommended**: Start with **Plan A** (current), upgrade to **Plan B** if needed.

---

## Date Range Calculator

### Recent 2-Month Batches (2025)

```
11: 09/13/2025 - 11/06/2025 (current)
10: 07/13/2025 - 09/12/2025
 9: 05/13/2025 - 07/12/2025
 8: 03/13/2025 - 05/12/2025
 7: 01/13/2025 - 03/12/2025
```

### Full 2024 Batches

```
 6: 11/01/2024 - 12/31/2024
 5: 09/01/2024 - 10/31/2024
 4: 07/01/2024 - 08/31/2024
 3: 05/01/2024 - 06/30/2024
 2: 03/01/2024 - 04/30/2024
 1: 01/01/2024 - 02/29/2024
```

---

## Monitoring & Troubleshooting

### Check Progress

```bash
# Count decks collected
wc -l data/training/mtggoldfish_advanced_decks.jsonl

# Watch log
tail -f mtggoldfish_batch.log

# Check current date range being scraped
grep "DATE RANGE:" mtggoldfish_batch.log | tail -1
```

### Resume After Interruption

The scraper automatically:
- ✅ Loads existing deck IDs (skips duplicates)
- ✅ Saves incrementally (no data loss)
- ✅ Can resume from specific page with `--start-page`

### Rate Limiting

Built-in delays:
- 1.5-3 seconds between deck downloads
- 2-4 seconds between page requests
- 10 seconds between date ranges

**Safe**: Won't get IP banned from MTGGoldfish

---

## Integration with Training Pipeline

### After Batch Scraping

```bash
# 1. Check total decks
wc -l data/training/mtggoldfish_advanced_decks.jsonl
# Example output: 65000 data/training/mtggoldfish_advanced_decks.jsonl

# 2. Combine with other sources
# Update prepare-balanced-dataset-v2.py to include:
#   - archidekt_decks.jsonl
#   - moxfield_decks.jsonl
#   - mtggoldfish_decks.jsonl
#   - mtggoldfish_advanced_decks.jsonl

# 3. Calculate new ratio
# With 15k + 50k = 65k decks:
# 30/70 ratio: 27,990 card + 65,311 decks = 93,301 examples
# 40/60 ratio: 43,541 card + 65,311 decks = 108,852 examples

# 4. Prepare dataset
python3 scripts/prepare-balanced-dataset-v2.py --extended

# 5. Train model
BATCH_SIZE=2 GRADIENT_ACCUMULATION_STEPS=8 MAX_SEQ_LENGTH=675 \
  nohup python3 scripts/train-commander-model-optimized.py > training_v2_extended.log 2>&1 &
```

---

## Summary

**Key Takeaways:**
- ✅ MTGGoldfish has **unlimited decks** via date range batching
- ✅ Each 2-month batch = ~10,000 decks
- ✅ 2024-2025 (22 months) = **~110,000 decks**
- ✅ 2018-2025 (94 months) = **~470,000 decks**
- ✅ No IP banning risk (proper rate limiting built-in)
- ✅ Automatic duplicate detection and incremental saving

**Recommended Approach:**
1. Complete current scraping (~15k decks, 4 hours)
2. Train v2 model (12-16 hours)
3. Validate for hallucinations
4. **If needed**: Run Plan B batch scraping (~50k more decks, 24 hours)
5. Retrain with extended dataset (18-24 hours)
6. Should eliminate hallucinations!
