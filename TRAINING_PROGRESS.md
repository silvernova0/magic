# Commander Model Training - Progress Report

## Current Status: Data Collection Complete ✅

### What We Have

**Card Knowledge Dataset** 
- **65,379 training examples** from your 31,131-card database
- **File**: `data/training/card_knowledge.jsonl` (22.88 MB)
- **Coverage**: All cards with oracle text, metadata, EDHREC rankings

**Training Example Types:**
1. **Card Descriptions** (~31k) - Full card details with rules text
2. **Commander Eligibility** (~3k) - Which cards can be commanders
3. **Power Level Assessments** (~15k) - Power ratings 0-10 
4. **Color Identity** (~31k) - Commander format color rules
5. **Saltiness Scores** (~5k) - Community perception data

**Example Training Entry:**
```json
{
  "instruction": "Describe the Magic: The Gathering card 'Meren of Clan Nel Toth'.",
  "output": "Meren of Clan Nel Toth is a Legendary Creature — Human Shaman with mana cost {2}{B}{G}. Whenever another creature you control dies, you get an experience counter. At the beginning of your end step, choose target creature card in your graveyard. If that card's converted mana cost is less than or equal to the number of experience counters you have, return it to the battlefield. Otherwise, put it into your hand. Its color identity is B, G.",
  "type": "card_description",
  "metadata": {
    "cardName": "Meren of Clan Nel Toth",
    "powerLevel": 8.5,
    "edhrecRank": 1250
  }
}
```

---

## Next Steps: Choose Your Training Path

### Option A: Synthetic Deck Generation (Fast Start - 1-2 days)
Generate 1,000-5,000 complete Commander decks using Gemini, then fine-tune.

**Pros:**
- Start training immediately
- Scalable (generate overnight)
- Quality control via validation

**Cons:**
- May inherit Gemini's biases
- Not "real" player data

**Script Ready**: `scripts/generate-synthetic-decks.py` (needs creation)

---

### Option B: Real Deck Scraping (High Quality - 1 week)
Scrape 5,000-50,000 real Commander decklists from EDHREC, Moxfield, MTGTop8.

**Pros:**
- Learns from real player choices
- Higher quality synergies
- Better meta knowledge

**Cons:**
- Takes longer to collect
- Needs robust scrapers
- Rate limiting concerns

**Scripts Needed:**
- `scripts/scrape-edhrec-decks.py` (enhance existing)
- `scripts/scrape-moxfield-decks.py` (new)
- `scripts/validate-decklists.py` (new)

---

### Option C: Hybrid Approach (Recommended - 3-5 days)
1. **Day 1**: Generate 500 synthetic decks with Gemini
2. **Day 2**: Fine-tune Phi-3.5 Mini on cards + 500 decks (v0.1)
3. **Day 3-4**: Scrape 2,000 real EDHREC decks
4. **Day 5**: Re-train with real data (v0.2) and compare quality

---

## Training Resources Required

### Hardware (You Have This)
- ✅ Intel Arc B50 Pro Graphics (16GB VRAM)
- ✅ OpenVINO 2025.3.0 installed
- ✅ Python environment ready

### Software Dependencies Needed
```bash
pip install transformers
pip install datasets
pip install peft  # For LoRA
pip install accelerate
pip install torch
pip install huggingface-hub
```

### Model Download (~7GB)
```bash
python scripts/download-openvino-model.py
# Select: Phi-3.5 Mini (Option 2)
```

### Training Time Estimates
- **Phi-3.5 Mini (3.8B)**: 8-12 hours on Intel Arc
- **Epochs**: 3-5
- **Batch size**: 2-4 (with gradient accumulation)
- **Total**: ~500-1000 examples/hour

---

## Quality Metrics to Track

### Automatic Validation (Must Pass)
1. **Color Identity Accuracy**: 99%+ (critical for Commander)
2. **Format Compliance**: 100-card singleton, no duplicates
3. **Card Validity**: All cards exist in database (no hallucinations)
4. **Banned List**: No banned cards included

### Human Evaluation (Sample 10 decks)
1. **Synergy Score**: Do cards work together? (1-10)
2. **Strategy Clarity**: Clear game plan? (1-10)
3. **Playability**: Would you play this? (Yes/No)
4. **vs. Gemini**: Better/Same/Worse

### Performance Benchmarks
- **Generation Speed**: Target <60 seconds/deck
- **VRAM Usage**: Target <12GB (leave room for other apps)
- **Load Time**: Target <20 seconds (first call)

---

## Training Data Breakdown

### Current Assets
| Dataset | Examples | Size | Status |
|---------|----------|------|--------|
| Card Knowledge | 65,379 | 22.88 MB | ✅ Complete |
| Synthetic Decks | 0 | 0 MB | ⏳ Pending |
| EDHREC Decks | 0 | 0 MB | ⏳ Pending |
| Moxfield Decks | 0 | 0 MB | ⏳ Pending |
| User Decks | 0 | 0 MB | ⏳ Future |

### Target Training Size
- **Minimum viable**: 1,000 complete decks + card knowledge
- **Good quality**: 5,000 complete decks + card knowledge  
- **Excellent**: 10,000+ complete decks + card knowledge

### Data Augmentation Ideas
1. **Commander variations**: Same deck, different commanders
2. **Power level shifts**: Upgrade/downgrade card choices
3. **Budget constraints**: Replace expensive cards
4. **Theme variations**: Slight theme tweaks (Aggro → Voltron)

---

## Cost Analysis

### Cloud API (Current - Gemini)
- **Cost per deck**: $0.01-0.05 (varies by length)
- **Monthly estimate** (1000 decks): $10-50
- **Issues**: Rate limits, 503 errors, dependency

### Local Training (Proposed)
- **Initial setup**: $0 (hardware owned)
- **Training cost**: $0 (local GPU)
- **Inference cost**: $0 (unlimited generations)
- **Total**: Free after initial time investment

### Break-even Analysis
- **Training time investment**: 40-60 hours (data + training + integration)
- **API cost saved**: $10-50/month
- **Break-even**: 2-4 months if high usage
- **Bonus**: No rate limits, better privacy

---

## Risk Assessment

### Technical Risks
1. **Quality lower than Gemini** (70% chance)
   - Mitigation: A/B test, use as fallback only
   - Smaller models may struggle with complex synergies

2. **Training takes longer than expected** (40% chance)
   - Mitigation: Start with small model, iterate
   - Phi-3.5 Mini should fit in timeline

3. **Color identity violations persist** (30% chance)
   - Mitigation: Post-processing validation
   - Reject decks that fail rules check

### Business Risks
1. **User complaints about quality** (50% chance if primary)
   - Mitigation: Keep Gemini as primary, local as fallback
   - Monitor user feedback closely

2. **Maintenance burden** (60% chance)
   - Mitigation: Automate re-training pipeline
   - Monthly model updates

---

## Recommended Next Action

**My suggestion**: Start with **Option C (Hybrid)** but validate quality early.

**Week 1 Plan:**
1. ✅ **Day 1** (Done): Export card knowledge (65k examples)
2. **Day 2**: Generate 500 synthetic decks with Gemini
3. **Day 3**: Download Phi-3.5 Mini and test training on 50 examples
4. **Day 4**: Full training run (v0.1 model)
5. **Day 5**: Generate 5 test decks, compare to Gemini
6. **Decision**: If quality ≥70% of Gemini → proceed with scraping
7. **Decision**: If quality <70% → stick with Gemini + retry logic

**Key Decision Point**: After Day 5, evaluate:
- Is the quality gap acceptable for a fallback?
- Is the speed improvement worth the quality trade-off?
- Do users have strong preferences?

---

## Resources & Scripts

### Ready to Use
- ✅ `scripts/export-card-knowledge.js` - Card database export
- ✅ `data/training/card_knowledge.jsonl` - 65k training examples
- ✅ `FINE_TUNING_PLAN.md` - Comprehensive guide
- ✅ `OPENVINO_SETUP.md` - Hardware setup guide

### To Create (if proceeding)
- ⏳ `scripts/generate-synthetic-decks.py` - Gemini deck generation
- ⏳ `scripts/train-commander-model.py` - LoRA fine-tuning
- ⏳ `scripts/validate-decks.py` - Quality checks
- ⏳ `scripts/test-model-quality.py` - A/B testing
- ⏳ `scripts/scrape-edhrec-bulk.py` - Real deck collection

---

## Questions to Answer Before Proceeding

1. **Priority**: Is unlimited local AI more valuable than maintaining Gemini quality?
2. **Timeline**: Do you have 40-60 hours over next 2-3 weeks?
3. **Expectations**: Are you okay with 70-85% of Gemini quality for fallback?
4. **Maintenance**: Will you commit to monthly re-training with new data?

If answers are **Yes**, proceed with training.
If **No** to any, stick with Gemini + retry logic (current solution works well).

---

## My Honest Assessment

**Gemini with retry logic (current)** is probably sufficient for most use cases:
- 503 errors are usually temporary (retry succeeds)
- Quality is excellent (understands Commander format)
- Cost is minimal at current usage
- No maintenance burden

**Local fine-tuned model** makes sense if:
- You expect high volume (>10,000 decks/month)
- You want to build this as a learning experience
- You plan to offer API access to other tools (revenue)
- Privacy is critical for your users
- You want complete independence from cloud APIs

**Recommendation**: Test quality with 500 synthetic decks before committing to full training pipeline. The gap between 3.8B local model and Gemini's massive model might be larger than expected for Commander's complex rules.

Ready to proceed? I can generate the synthetic deck creation script next.
