# EDHREC Scraping Progress

## Status (as of November 8, 2025 2:27 PM)

### Average Deck Scraper
- **Status:** Running in background (PID 1045120)
- **Progress:** 31 / 2,938 commanders (~1%)
- **Output:** `data/training/edhrec_average_decks.jsonl`
- **Success rate:** 100% so far (10/10 in test)
- **Estimated time:** ~73 minutes (2,938 × 1.5s rate limiting)
- **Expected completion:** ~3:40 PM

### Combo Scraper  
- **Status:** Completed
- **Result:** 0 combos found
- **Issue:** EDHREC likely changed their HTML structure for combo pages
- **Resolution:** Will need to manually inspect https://edhrec.com/combos and update selectors

## Next Steps

### While Scraping Continues:

1. **Check combo scraper failure** (5 minutes)
   - Visit https://edhrec.com/combos/wu manually
   - Inspect HTML structure
   - Update BeautifulSoup selectors in `scrape-edhrec-combos.py`
   - Re-run combo scraper

2. **Create deck building rules database** (30 minutes)
   - Codify Mythic Vault ratios into JSON
   - Create `data/training/deck_building_rules.json`
   - Structure by bracket (1-5) and strategy modifiers

3. **Prepare data conversion script** (1 hour)
   - Convert scraped average decks → v3 training format
   - Analyze card distributions in each deck
   - Map to bracket rules and strategies
   - Generate structured JSON outputs

### After Scraping Completes (~3:40 PM):

4. **Analyze scraped data** (15 minutes)
   - Check success rate
   - Verify data quality
   - Identify patterns in popular commanders

5. **Convert to training format** (2 hours)
   - Run conversion script on all scraped decks
   - Generate ~2,000-3,000 training examples
   - Split into train/validation sets

6. **Train v3 model** (4-6 hours)
   - Update training script for JSON output
   - Train on Arc B50 with Qwen 2.5 3B
   - Monitor for proper structure generation

## Monitoring Commands

```bash
# Check scraper progress
ps aux | grep scrape-edhrec
wc -l data/training/edhrec_*.jsonl

# View recent output
tail -f scrape_average_decks.log

# Check specific commander scraped
tail -5 data/training/edhrec_average_decks.jsonl | jq '.commander'

# Kill if needed
pkill -f scrape-edhrec
```

## Expected Outputs

### Average Decks (~2,000+ valid decks expected)
Each line in JSONL:
```json
{
  "commander": "The Ur-Dragon",
  "slug": "the-ur-dragon",
  "url": "https://edhrec.com/average-decks/the-ur-dragon",
  "all_cards": ["Sol Ring", "Command Tower", ...],
  "total_cards": 99,
  "themes": ["Dragons", "Tribal", "Ramp"],
  "categories": {
    "Creatures": {"count": 32, "cards": [...]},
    "Ramp": {"count": 12, "cards": [...]},
    ...
  }
}
```

### Combos (Need to fix scraper first)
```json
{
  "combo_id": "exquisite-blood-sanguine-bond",
  "name": "Exquisite Blood + Sanguine Bond",
  "cards": ["Exquisite Blood", "Sanguine Bond"],
  "colors": ["B"],
  "result": "Infinite lifegain/lifeloss loop",
  "tags": ["infinite", "lifegain", "win_con"],
  "popularity": 15234,
  "power_level": 8
}
```

## Timeline

- **2:30 PM** - Check combo scraper HTML issue
- **3:00 PM** - Create deck building rules
- **3:40 PM** - Average deck scraping completes
- **4:00 PM** - Fix and re-run combo scraper
- **5:00 PM** - Start data conversion
- **7:00 PM** - Begin v3 training
- **Next morning** - Validate trained model

## Success Metrics

- ✅ 2,000+ commander average decks scraped
- ⏳ 300+ combos scraped (after fixing selectors)
- ⏳ Deck building rules codified
- ⏳ Training data converted to v3 format
- ⏳ Model trained on structured patterns
- ⏳ Zero hallucinations in validation
- ⏳ Always generates exactly 100 cards
