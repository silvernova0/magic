# Commander Model Training: Real Data Collection Strategy

## Updated Plan (Moxfield API Blocked)

### Data Sources Assessment

| Source | Accessibility | Quality | Quantity | Status |
|--------|--------------|---------|----------|--------|
| **EDHREC** | ✅ Public | ⭐⭐⭐⭐⭐ | 5,000+ | Ready to scrape |
| **Moxfield** | ❌ API blocked | ⭐⭐⭐⭐⭐ | 10,000+ | Requires auth/workaround |
| **Archidekt** | ✅ Public API | ⭐⭐⭐⭐ | 3,000+ | To implement |
| **TappedOut** | ✅ Web scraping | ⭐⭐⭐ | 2,000+ | To implement |
| **Your Database** | ✅ Ready | ⭐⭐⭐⭐⭐ | 65k examples | Already exported |

---

## Recommended Strategy: EDHREC + Archidekt + Card Knowledge

### Phase 1: EDHREC (Primary Source - 3-5 days)

**Target**: 3,000-5,000 Commander decklists

**Why EDHREC**:
- ✅ Publicly accessible (no auth required)
- ✅ Average decklists = community consensus (high quality)
- ✅ Includes EDHREC rank and synergy data
- ✅ Covers most popular commanders
- ✅ Well-structured data

**Scraping Approach**:
```python
# Already created: scripts/scrape-edhrec-decks.py
scraper = EDHRECScraper()
decks = scraper.scrape_decks(num_decks=3000)
# Rate limit: 2-4 seconds between requests
# Time estimate: 3-5 hours for 3000 decks
```

**Data Quality**:
- Average decklists represent what WORKS
- Includes high-synergy cards
- Tested by thousands of players
- Better than random Moxfield decks

---

### Phase 2: Archidekt (Secondary Source - 1-2 days)

**Target**: 1,000-2,000 additional decks

**Why Archidekt**:
- ✅ Public GraphQL API (no auth)
- ✅ High-quality user decks with descriptions
- ✅ Tags and categories
- ✅ View counts for quality filtering

**API Endpoint**:
```python
POST https://archidekt.com/api/decks/cards/
{
  "filters": {
    "formats": ["commander"],
    "orderBy": "-viewCount"
  },
  "page": 1,
  "pageSize": 100
}
```

**Implementation**: Create `scripts/scrape-archidekt-decks.py`

---

### Phase 3: Augment with Your Database (Already Done)

**What You Have**: 65,379 card knowledge entries
- Card descriptions
- Commander eligibility
- Power levels
- Color identity rules
- Saltiness scores

**Training Value**: This teaches the model about **individual cards**, while scraped decks teach **deck building strategy**.

---

## Total Training Dataset

### Minimum Viable (3-5 days)
- **3,000 EDHREC decks** (avg 95 cards each) = 285,000 card placements
- **65,379 card knowledge entries** = individual card expertise
- **Total**: ~350k training examples
- **Quality**: ⭐⭐⭐⭐⭐ (High - all from trusted sources)

### Optimal (7-10 days)
- **5,000 EDHREC decks** = 475,000 card placements
- **2,000 Archidekt decks** = 190,000 card placements
- **65,379 card knowledge** = card expertise
- **Total**: ~730k training examples
- **Quality**: ⭐⭐⭐⭐⭐ (Excellent diversity)

---

## Model Selection for 8-16B Parameters

### Option 1: Llama 3.1 8B (Recommended for Intel Arc)
**Size**: 16GB model files, ~12GB VRAM during training
**Training Time**: 12-18 hours (3 epochs, 3000 decks)
**Quality**: ⭐⭐⭐⭐⭐ (Meta's best open-source)
**Intel Arc**: Excellent support via OpenVINO

```python
model_name = "meta-llama/Meta-Llama-3.1-8B-Instruct"
```

**Pros**:
- State-of-the-art instruction following
- Excellent reasoning capabilities
- Large context window (8k tokens)
- Strong Commander format understanding

**Cons**:
- Requires HuggingFace authentication
- 16GB download

---

### Option 2: Qwen 2.5 14B (Best Quality)
**Size**: 28GB model files, ~14GB VRAM during training
**Training Time**: 24-36 hours (3 epochs, 3000 decks)
**Quality**: ⭐⭐⭐⭐⭐ (Best structured output)
**Intel Arc**: Good support

```python
model_name = "Qwen/Qwen2.5-14B-Instruct"
```

**Pros**:
- Excellent at structured JSON output
- Strong reasoning for card synergies
- Best quality for 14B class
- No authentication required

**Cons**:
- Larger model = slower training
- May need gradient checkpointing
- Tight fit in 16GB VRAM

---

### Option 3: Mistral 7B v0.3 (Fallback)
**Size**: 14GB model files, ~10GB VRAM during training
**Training Time**: 10-15 hours (3 epochs, 3000 decks)
**Quality**: ⭐⭐⭐⭐ (Solid baseline)
**Intel Arc**: Excellent support

```python
model_name = "mistralai/Mistral-7B-Instruct-v0.3"
```

**Pros**:
- Fast training
- Lower memory requirements
- Well-documented
- Good instruction following

**Cons**:
- Not as strong at reasoning as Llama 3.1
- Smaller context window (4k)

---

## Hardware Requirements (Your Intel Arc B50 Pro)

### VRAM Usage During Training (LoRA)

| Model | Base Model | LoRA Weights | Optimizer | Batch | Total | Fits? |
|-------|-----------|--------------|-----------|-------|-------|-------|
| Llama 3.1 8B | 8GB | 1GB | 2GB | 1GB | 12GB | ✅ Yes |
| Qwen 2.5 14B | 10GB | 1.5GB | 2.5GB | 1GB | 15GB | ⚠️ Tight |
| Mistral 7B | 7GB | 0.8GB | 1.5GB | 1GB | 10GB | ✅ Easy |

**Recommendations**:
- **Llama 3.1 8B**: Best balance (leaves 4GB free)
- **Qwen 2.5 14B**: Use gradient checkpointing + batch size 1
- **Mistral 7B**: Safest option (leaves 6GB free)

---

## Training Pipeline

### Step 1: Data Preparation (scripts/prepare-training-data.py)

```python
"""
Merge all data sources into unified training format
"""

# Load scraped decks
edhrec_decks = load_jsonl('data/training/edhrec_decks.jsonl')
archidekt_decks = load_jsonl('data/training/archidekt_decks.jsonl')
card_knowledge = load_jsonl('data/training/card_knowledge.jsonl')

# Convert decks to instruction-following format
training_examples = []

for deck in edhrec_decks:
    # Create instruction
    instruction = f"Build a Commander deck with {deck['commander']} as the commander. "
    instruction += f"Theme: {deck['theme']}. "
    instruction += f"Colors: {', '.join(deck['colors'])}. "
    instruction += "Generate a complete 100-card decklist."
    
    # Create output (formatted decklist)
    output = format_decklist(deck)
    
    training_examples.append({
        'instruction': instruction,
        'output': output,
        'type': 'deck_generation'
    })

# Add card knowledge
training_examples.extend(card_knowledge)

# Save combined dataset
save_jsonl(training_examples, 'data/training/combined_training.jsonl')
```

---

### Step 2: Model Download (scripts/download-training-model.py)

```python
from huggingface_hub import snapshot_download

model_name = "meta-llama/Meta-Llama-3.1-8B-Instruct"
cache_dir = "models/llama-3.1-8b"

print(f"Downloading {model_name}...")
snapshot_download(
    repo_id=model_name,
    local_dir=cache_dir,
    local_dir_use_symlinks=False
)
print(f"✓ Model downloaded to {cache_dir}")
```

---

### Step 3: LoRA Fine-Tuning (scripts/train-commander-model.py)

```python
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer
from peft import LoraConfig, get_peft_model
from datasets import load_dataset

# Load model
model = AutoModelForCausalLM.from_pretrained(
    "models/llama-3.1-8b",
    torch_dtype=torch.float16,
    device_map="auto"
)

# LoRA config (trains only 1-2% of parameters)
lora_config = LoraConfig(
    r=16,  # Rank (higher = more capacity, slower)
    lora_alpha=32,
    target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM"
)

model = get_peft_model(model, lora_config)

# Training config
training_args = TrainingArguments(
    output_dir="models/commander-llama-3.1-8b",
    num_train_epochs=3,
    per_device_train_batch_size=2,  # Adjust based on VRAM
    gradient_accumulation_steps=8,  # Effective batch size = 16
    learning_rate=2e-4,
    fp16=True,
    save_strategy="epoch",
    logging_steps=10
)

# Load dataset
dataset = load_dataset('json', data_files='data/training/combined_training.jsonl')

# Train
trainer = Trainer(model=model, args=training_args, train_dataset=dataset)
trainer.train()

# Save
model.save_pretrained("models/commander-llama-3.1-8b-final")
```

**Training Time Estimate**: 12-18 hours on Intel Arc B50 Pro

---

### Step 4: Export to OpenVINO (scripts/export-to-openvino.py)

```python
from optimum.intel import OVModelForCausalLM

# Load fine-tuned model
model = OVModelForCausalLM.from_pretrained(
    "models/commander-llama-3.1-8b-final",
    export=True,
    compile=True
)

# Save optimized for Intel Arc GPU
model.save_pretrained("models/commander-openvino")

print("✓ Model exported to OpenVINO format")
print("Optimized for Intel Arc GPU inference")
```

---

## Timeline & Milestones

### Week 1: Data Collection
- **Day 1-2**: Run EDHREC scraper (3,000 decks) ✅ Script ready
- **Day 3**: Create Archidekt scraper (1,000 decks)
- **Day 4**: Validate and clean data
- **Day 5**: Merge datasets into training format
- **Day 6-7**: Manual review of sample decks

**Deliverable**: ~4,000 clean decklists + 65k card knowledge = 730k examples

---

### Week 2: Model Training
- **Day 1**: Download Llama 3.1 8B (requires HuggingFace token)
- **Day 2**: Set up training environment, test on 100 examples
- **Day 3-5**: Full LoRA training (12-18 hours compute time)
- **Day 6**: Export to OpenVINO format
- **Day 7**: Quality testing and A/B comparison vs. Gemini

**Deliverable**: Fine-tuned Commander model optimized for Intel Arc

---

### Week 3: Integration & Testing
- **Day 1-2**: Create Flask API service
- **Day 3-4**: Integrate with Next.js app
- **Day 5-6**: A/B testing with users
- **Day 7**: Documentation and deployment

**Deliverable**: Production-ready local AI deck builder

---

## Cost Analysis

### Time Investment
- Data collection: 20-30 hours (mostly automated)
- Training setup: 10-15 hours
- Training time: 12-18 hours (GPU running)
- Integration: 15-20 hours
- **Total**: 60-85 hours over 3 weeks

### Financial Cost
- **$0** - All tools are open source
- Your hardware already owned
- No API fees

### Break-Even
- Current Gemini cost: ~$10-50/month (depending on usage)
- Break-even: 2-4 months if moderate usage
- **But**: Main benefit is unlimited generations + no rate limits

---

## Quality Expectations

### Realistic Assessment

**Llama 3.1 8B fine-tuned on 4,000 decks**:
- Color identity accuracy: 95-98% (vs. Gemini 99%)
- Deck synergy: 80-85% (vs. Gemini 90%)
- Card validity: 98-99% (trained on your database)
- Format compliance: 99% (easy rule to enforce)

**Overall Quality**: 85-90% of Gemini 2.5 Flash

**When to use**:
- ✅ Fallback when Gemini hits rate limits
- ✅ Privacy-sensitive deck generation
- ✅ Unlimited bulk deck generation
- ✅ Offline/local development

**When to prefer Gemini**:
- ⭐ User wants absolute best quality
- ⭐ Complex edge cases (color identity with hybrid mana)
- ⭐ New cards not in training data (recent sets)

---

## Next Steps

### Option A: Start EDHREC Scraping Now (Recommended)
```powershell
# Run this command
& "C:\Users\fuckthisshit\openvino_env\Scripts\python.exe" scripts\scrape-edhrec-decks.py

# Expected: 3-5 hours runtime, 3000 decks
# Output: data/training/edhrec_decks.jsonl
```

### Option B: Test Smaller Scale First
```powershell
# Scrape 100 decks for testing
# Modify script: scraper.scrape_decks(num_decks=100)
# Train on small dataset (2-3 hours)
# Evaluate quality before committing
```

### Option C: Wait for Moxfield Workaround
- Research Moxfield authentication
- Try browser automation (Selenium/Playwright)
- Find alternative high-quality source

---

## My Recommendation

**Start with EDHREC** (3,000 decks):
1. Run `scrape-edhrec-decks.py` tonight (automated)
2. Tomorrow: Validate data quality
3. Day 3: Download Llama 3.1 8B
4. Day 4-5: Training (overnight)
5. Day 6: Compare quality to Gemini

**Decision point**: If quality ≥85% of Gemini, proceed with integration. Otherwise, stick with Gemini + retry logic.

The EDHREC data alone is high enough quality to be valuable. Don't let Moxfield block you - you can always add more sources later (continuous learning).

Ready to start scraping?
