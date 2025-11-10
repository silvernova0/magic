# JankBuild - MTG Commander Deck Builder AI Instructions

## Project Architecture

**Hybrid AI System**: Combines Google Gemini API (primary) with local fine-tuned LLM (LoRA-adapted Qwen 2.5 3B) for Commander/EDH deck generation. The fine-tuned model is now trained **only on structured deck-building data**—all factual card knowledge lives in the local Prisma/SQLite databases and is fetched during inference instead of being memorized.

### Core Components
- **Frontend**: Next.js 15 + React 19, TailwindCSS, Shadcn/UI components in `src/components/`
- **Backend**: Next.js API routes (`src/app/api/`) + Server Actions
- **Database**: Prisma + SQLite with 31,000+ MTG cards (`prisma/schema.prisma`)
- **AI Deck Builder**: 
  - Primary: Gemini 2.5 Flash (`src/lib/gemini.ts`)
  - Local: Fine-tuned Qwen 2.5 3B model (`models/commander-llama-lora/`)
- **Data Pipeline**: Web scrapers → Training data → LoRA fine-tuning → Inference

### Key Directories
```
scripts/          # Python scrapers, training scripts, data preparation
data/training/    # Deck-only datasets (v3_structured_training.jsonl, deck_building_rules.json)
models/           # Base models (qwen2.5-3b, llama-3.1-8b) + LoRA adapters
src/app/api/      # REST endpoints for deck building, cards, admin
src/lib/          # Utilities (auth.ts, gemini.ts, ollama.ts, email.ts)
prisma/           # Database schema and migrations
```

## Critical Workflows

### Training the Local AI Model

**Purpose**: Fine-tune a local LLM to **learn deck-building logic only** (ratios, brackets, strategy filters, combo thresholds). We no longer try to force the model to memorize the 31k-card MTG catalog—that comes from the local database at inference time.

**Key Constraint**: Intel Arc B50 16GB VRAM. Stick with Qwen 2.5 3B (6.5GB base). Everything larger (Llama 8B) thrashes VRAM and is now retired.

**Before running ANY training script**:
```bash
source ~/.virtualenvs/magicapp/bin/activate

# Force Accelerate/Trainer to see the Arc GPU
export ACCELERATE_USE_XPU=1
export USE_XPU=1
export ONEAPI_DEVICE_SELECTOR=level_zero:*
export SYCL_PI_LEVEL_ZERO_USE_IMMEDIATE_COMMANDLISTS=1
export PYTORCH_XPU_ALLOC_CONF="expandable_segments:True,max_split_size_mb:512"
```

Without the virtualenv you get `ModuleNotFoundError: No module named 'torch'`. Without the env vars Accelerate silently picks CPU, even though `torch.xpu.is_available()` returns True.

**Training Commands (v3 - CURRENT)**:
```bash
# Dataset is already built: data/training/v3_structured_training.jsonl

# Structured deck-only training (Arc B50)
BATCH_SIZE=4 GRADIENT_ACCUMULATION_STEPS=8 MAX_SEQ_LENGTH=600 \
  nohup python3 scripts/train-v3-structured.py > training_v3.log 2>&1 &

# Monitor run + confirm GPU usage
tail -f training_v3.log
watch -n 2 "ps -o pid,%cpu,%mem,cmd -p $(pgrep -f train-v3-structured.py)"
sudo intel_gpu_top -J -s 200 | head -40
```

**Training Commands (v2 - DEPRECATED)**:
Kept only for archaeology. v2 mixed decks + card descriptions and failed validation (hallucinated cards, wrong counts).

**Quick health checks before/after launching v3**:
```bash
# Verify the Arc GPU is visible to PyTorch
python - <<'PY'
import torch
print("xpu available:", torch.xpu.is_available())
print("device count:", torch.xpu.device_count())
PY

# Confirm Trainer kept the model on XPU after wrapping LoRA
python - <<'PY'
from peft import LoraConfig, get_peft_model
from transformers import AutoModelForCausalLM
import torch, intel_extension_for_pytorch as ipex
model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen2.5-3B-Instruct",
    torch_dtype=torch.bfloat16, device_map="xpu", trust_remote_code=True)
model = ipex.optimize(model, dtype=torch.bfloat16)
model = get_peft_model(model, LoraConfig(r=16,lora_alpha=32,target_modules=["q_proj"]))
print("sample parameter device:", next(model.parameters()).device)
PY
```

If any of those print `cpu`, stop—the Trainer run will never hit the Arc GPU.

**Why v3 works**:
- Dataset is 100% deck-derived JSON rules—no card descriptions.
- Model outputs structured filters/counts (`card_selection`, `mana_curve`, `combo_plan`).
- Database queries (Prisma + deck rules) fill the actual cards, guaranteeing legality and eliminating hallucinations.
- Shorter sequences (≤600 tokens) mean faster training and less VRAM churn.


**Training Configuration** (`scripts/train-v3-structured.py` - v3 CURRENT):
- **Model**: Qwen 2.5 3B Instruct (3.09B parameters)
- **LoRA**: rank=16, alpha=32, dropout=0.05 (29.9M trainable params = 0.96%)
- **Optimizer**: AdamW (lr=2e-4, weight_decay=0.01)
- **Schedule**: Linear warmup (100 steps) + decay
- **Memory**: BF16 mixed precision, gradient checkpointing
- **Target modules**: q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj
- **Sequence length**: 600 tokens (fits all v3 examples: 452-581 token range)
- **Batch size**: 4 with gradient accumulation 8 (effective batch 32)
- **Expected VRAM**: ~15GB / 16GB on Arc B50
- **Expected duration**: 4-6 hours (if GPU actually used, currently unknown)
- **GPU Issue**: Despite XPU config, training showing CPU usage patterns

**Training Configuration** (`scripts/train-commander-model-optimized.py` - v2 DEPRECATED):
- **LoRA**: rank=16, alpha=32, dropout=0.05
- **Optimizer**: AdamW (lr=2e-4, weight_decay=0.01)
- **Schedule**: Linear warmup (100 steps) + decay
- **Memory**: BF16 mixed precision, gradient checkpointing
- **Target modules**: q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj
- **Sequence length**: 675 tokens (fits 510-793 token decks, avg 637)
- **VRAM usage**: ~15.2GB / 16GB (93% utilization - optimal)
- **Result**: Completed successfully but failed validation (hallucinations)

**Data Requirements (v3 - CURRENT)**:
- **Dataset**: 23,405 structured examples from 6 sources
- **Format**: Instruction → Structured JSON output (not text decks)
- **Sources**:
  * 2,557 EDHREC average decks (commander-specific patterns)
  * 12,334 MTGGoldfish commander decks
  * 3,759 Moxfield theme decks
  * 4,289 Archidekt popular decks
  * 466 MTGGoldfish archetype decks
- **Output Structure**:
  ```json
  {
    "commander": "The Ur-Dragon",
    "strategy": "tribal",
    "bracket": 3,
    "power_level": 7,
    "card_selection": {
      "lands": {"count": 37, "filters": [{"types": ["Land"]}]},
      "creatures": {"count": 23, "filters": [{"subtypes": ["Dragon"]}]},
      "ramp": {"count": 13, "filters": [{"tags": ["ramp"], "cmc_max": 3}]}
  }
}
```
- **Key Insight**: Model learns deck-building patterns (land ratios, strategy coherence, power levels) but doesn't memorize card names. Database queries ensure valid cards only.
- **Card knowledge lives elsewhere**: `data/training/deck_building_rules.json`, Prisma card tags, combo datasets. **Do not** add `card_knowledge.jsonl` back into v3 training; it undermines the "database handles facts" plan.
- **Token Analysis**: All examples fit in 600 tokens (range 452-581, median 510)

**Data Requirements (v2 - DEPRECATED)**:
- **70/30 ratio**: 71% card knowledge (prevents hallucinations), 29% decks (teaches patterns)
- **Dataset size**: 43,631 examples (31,131 cards + 12,500 decks)
- **Deck validation**: Must be exactly 100 cards (99 mainboard + 1 commander OR 98 mainboard + 2 commanders)
- **Sources**: MTGGoldfish (12,314 decks - best quality), Archidekt (4,144), Moxfield (3,754)
- **Total available**: 22,197 validated decks collected
- **Result**: Failed - model couldn't memorize 31k cards AND learn patterns simultaneously

### Scraping Training Data

**v3 Data Sources** (CURRENT - 23,405 total examples):

**EDHREC Average Decks** (`scripts/scrape-edhrec-average-decks.py`):
```bash
nohup python3 scripts/scrape-edhrec-average-decks.py > edhrec_average.log 2>&1 &
# Result: 2,557 of 2,938 commanders scraped (87% success rate)
# These provide real deck patterns for each commander
```

**Best Source - MTGGoldfish Commander Scraper** (`scripts/scrape-mtggoldfish-by-commander.py`):
```bash
# Scrapes decks by searching each commander (highest quality)
nohup python3 scripts/scrape-mtggoldfish-by-commander.py > mtggoldfish_commander.log 2>&1 &
# Result: 12,314 decks from 2,059 commanders (69% success rate)
```

**Other Scrapers**:
```bash
# Moxfield (30 themes × 5 brackets)
python3 scripts/scrape-moxfield-themes.py  # 3,754 decks

# Archidekt (popular commanders)
python3 scripts/scrape-archidekt-commanders.py  # 4,144 decks

# MTGGoldfish archetypes
python3 scripts/scrape-mtggoldfish.py  # 466 decks
```

**EDHREC Combo Scraper** (`scripts/scrape-edhrec-combos.py` - NEEDS FIXING):
```bash
python3 scripts/scrape-edhrec-combos.py
# Result: 0 combos (HTML selectors don't match current EDHREC structure)
# Status: Low priority, can add to v3.1 later
```

**v3 Data Conversion** (`scripts/convert-to-v3-training.py`):
```bash
# Converts all deck sources to v3 structured format
python3 scripts/convert-to-v3-training.py
# Analyzes card distributions, detects strategy, estimates power levels
# Generates structured JSON outputs instead of text decks
# Output: data/training/v3_structured_training.jsonl (23,405 examples)
```

**Validation Rules**:
- Total cards = 100 (mainboard + commanders)
- 1 commander: 99 mainboard + 1 commander
- 2 commanders: 98 mainboard + 2 commanders
- Commander section required
- Validates by quantity sum (handles "27 Swamp" format)
- Skip decks that don't meet criteria

**Output Format** (v2 scrapers - text decks):
```json
{
  "instruction": "Build a Commander deck with X focused on Y.",
  "output": "Commander: X\nDeck Name: ...\n\nCommanders:\n1x CardName\n\nCreatures:\n1x CardName\n..."
}
```

**Output Format** (v3 scrapers - structured JSON):
```json
{
  "instruction": "Build a Commander deck with The Ur-Dragon focused on tribal dragons at power level 7",
  "output": {
    "commander": "The Ur-Dragon",
    "strategy": "tribal",
    "bracket": 3,
    "power_level": 7,
    "card_selection": {
      "lands": {"count": 37, "filters": [{"types": ["Land"], "colors_within": ["W","U","B","R","G"]}]},
      "ramp": {"count": 13, "filters": [{"tags": ["ramp"], "cmc_max": 3}]},
      "creatures": {"count": 23, "filters": [{"subtypes": ["Dragon"]}]}
    }
  }
}
```

**Final Stats (v3 training - CURRENT)**:
- Total examples: 23,405 structured outputs
- Distribution: 81.8% midrange, 6.4% combo, 5% tribal
- Bracket distribution: 53.6% bracket 2, 32.9% bracket 3, 13.5% bracket 4-5
- Token lengths: 452-581 range (median 510, all fit in 600 tokens)

**Final Stats (v2 training - DEPRECATED)**:
- Total scraped: 22,197 validated decks
- Used in training: 12,500 decks (reduced for VRAM)
- Rejection rate: ~7.4% (invalid card counts or missing commanders)

### Database Operations

**Import MTGJson Cards** (31,000+ cards):
```bash
npm run import:mtgjson:full
# Adds EDHREC rankings, saltiness scores, power levels, tags
```

**Prisma Commands**:
```bash
npx prisma generate    # Generate client after schema changes
npx prisma db push     # Apply schema to database
npx prisma studio      # GUI for data inspection
```

**Card Search API** (`/api/cards/search`):
- Filters: colors, colorIdentity, types, keywords, CMC, EDHREC rank, saltiness
- Returns cards with tags (game-changer, removal, tutor, card-draw, high-salt)

## Project-Specific Conventions

### Color Identity Enforcement
Commander decks must respect color identity rules. Both AI systems enforce this:
```typescript
// src/lib/gemini.ts and src/lib/ollama.ts
// Prompts include explicit color identity constraints:
"EVERY card must have color identity ⊆ commander's identity"
"Example: Azorius (W/U) can ONLY use white, blue, and colorless cards"
```

### Deck Format
All generated decks follow this structure:
```
Commander: Card Name

Deck Name: ...
Theme: ...
Colors: ...

Decklist:

Commanders:
1x Card Name

Creatures:
1x Card Name
1x Another Card
...

[Instants, Sorceries, Enchantments, Artifacts, Planeswalkers, Lands sections]
```

### Training Data Balance
- **Legacy (v2)**: Needed 70-80% card descriptions to keep hallucinations down, but the 3B model still couldn't memorize 31k names + deck logic. Result: failed validation.
- **Current (v3)**: Dataset is 100% deck-derived JSON (commander requests + structured rules). Card knowledge is injected later from Prisma + `deck_building_rules.json` + combo datasets. Never mix raw card descriptions back into training.
- **Benefit**: Model capacity is spent on ratios, bracket shifts, combo timing, and commander patterns. All cards returned to the UI have already passed database validation.

**Sequence Length Discovery (v3)**:
- Structured examples tokenize to 452-581 tokens (median ≈510)
- `MAX_SEQ_LENGTH=600` keeps everything intact with minimal padding (tokenizer currently pads to 600 for simplicity)
- Earlier 384-token configs (v2) truncated 25-52% of decks and are permanently retired
- Keep `MAX_SEQ_LENGTH` <= 600 so the Arc B50 stays under ~15GB VRAM during backward pass

### Intel XPU (Arc GPU) Training
**CRITICAL**: Must use virtualenv with Intel PyTorch XPU:
```bash
source ~/.virtualenvs/magicapp/bin/activate
# PyTorch 2.8.0+xpu installed in virtualenv only
```

Use `device_map='xpu'` and Intel Extension for PyTorch (IPEX):
```python
import intel_extension_for_pytorch as ipex
model = AutoModelForCausalLM.from_pretrained(
    model_path,
    torch_dtype=torch.bfloat16,
    device_map='xpu'  # Not 'cuda'
)
# Apply IPEX optimization
model = ipex.optimize(model, dtype=torch.bfloat16)
```

**CURRENT ISSUE - GPU NOT BEING USED FOR TRAINING**:
- Arc B50 detected: ✅ `torch.xpu.is_available() = True`
- Model loads on XPU: ✅ `device_map='xpu'` works
- Inference on XPU: ✅ `model.generate()` works on xpu:0
- **If training suddenly goes CPU-only**:
  1. Stop the run immediately (no point waiting 30+ hours on CPU).
  2. Re-source the virtualenv and export the XPU env vars listed above.
  3. Confirm `ACCELERATE_USE_XPU=1` is set (`env | grep XPU`).
  4. Run the two Python health checks (torch.xpu + PeftModel) to ensure parameters stay on `xpu:0`.
  5. Restart training. Watch `intel_gpu_top` within the first minute—GPU utilization should spike >70% and VRAM should climb to ~15GB.
  6. If Trainer still refuses to use XPU, fall back to the manual training loop (see `scripts/train-commander-model-optimized.py`) or port the v3 dataset into that manual loop. The manual loop sidesteps Accelerate entirely and reliably holds the Arc device.

**VRAM Optimization Notes**:
- Backward pass always uses more VRAM than forward pass; never assume you're safe just because the model loads.
- v2 (675 tokens) pushed VRAM to ~15.2GB with batch 4—anything larger OOM'd.
- v3 (600 tokens padded) sits around 14.5GB with batch 4 / grad-acc 8. You still need the env vars from above so Level Zero can grow memory pools (`expandable_segments`).
- Monitor with `nvtop`, `intel_gpu_top`, or `scripts/monitor-combined.py` instead of assuming the Arc is busy.

### Authentication & Roles
- NextAuth.js with bcrypt for passwords
- Two roles: USER (default), ADMIN
- Admin promotion: `npm run create-admin` or via `/admin` panel
- Protected routes use `getServerSession()` server-side

## Key Integration Points

### Gemini AI Integration (`src/lib/gemini.ts`)
```typescript
buildCommanderDeckWithAI(request: DeckBuildRequest)
// Combines: EDHREC data, MTGTop8 meta, Moxfield brackets
// Returns: Formatted decklist with 100 cards
```

### Local Model Inference (`src/lib/ollama.ts`)
Currently uses Ollama server. To use fine-tuned model:
1. Load LoRA adapter: `PeftModel.from_pretrained(base_model, 'models/commander-llama-lora/final')`
2. Generate with constraints in prompt (color identity, strategy, power level)
3. Validate output with `scripts/card_validator.py` (checks against MTGJson database)

### Web Scrapers
- **Moxfield**: `scripts/scrape-moxfield-themes.py` - Theme+bracket filtered decks
- **EDHREC**: `scripts/scrape-edhrec-decks.py` - Popular commander decklists
- **MTGGoldfish**: `scripts/scrape-mtggoldfish.py` - Tournament meta decks

All scrapers output JSONL with standardized format for training.

## Critical Files

**Must understand before major changes**:
- `scripts/train-v3-structured.py` - v3 LoRA training pipeline with Intel XPU support and IPEX optimization
- `scripts/train-commander-model-optimized.py` - v2 LoRA training pipeline (DEPRECATED)
- `scripts/convert-to-v3-training.py` - Converts all deck sources to v3 structured JSON format
- `scripts/scrape-edhrec-average-decks.py` - Scrapes commander-specific deck patterns from EDHREC
- `scripts/prepare-balanced-dataset.py` - Creates 80/20 card/deck ratio dataset (v2 only)
- `scripts/scrape-moxfield-themes.py` - Primary v2 training data source with validation
- `src/lib/gemini.ts` - Primary AI deck builder with EDHREC context
- `prisma/schema.prisma` - Database schema (User, Card, Deck models)
- `data/training/v3_structured_training.jsonl` - 23,405 v3 training examples
- `data/training/deck_building_rules.json` - Codified deck construction wisdom (brackets + strategies)

## Testing & Validation

**Test v2 Trained Model** (DEPRECATED):
```bash
python scripts/test-trained-model-validated.py
# Tests: Ur-Dragon (tribal), Atraxa (counters), validates card counts/colors
# Result: Failed with hallucinations and wrong card counts
```

**Test v3 Trained Model** (CURRENT - NOT YET IMPLEMENTED):
```bash
python scripts/test-v3-model.py
# Will test structured JSON output format
# Validate all required fields present
# Check card_selection filters are valid
# NOT YET CREATED - needs to be built after training completes
```

**Structured Deck Executor (NEW)**:
```bash
# Convert structured JSON into a 100-card deck using Prisma SQLite
python3 scripts/build_deck_from_structure.py generated_decks/v3_test/ur-dragon-tribal.json
# Output deck written to generated_decks/v3_executed/*.json
# Script uses prisma/dev.db, so run `npm run import:mtgjson:full` first if empty
```

**Validation Checks** (v2):
- Exactly 100 cards (no 104, no 75)
- No color identity violations (e.g., red in W/U/B/G deck)
- No hallucinated cards (all cards exist in MTGJson)
- Strategy matches request (tribal for tribal, cEDH for cEDH)

**Validation Checks** (v3):
- Valid structured JSON output
- All required fields: commander, strategy, bracket, power_level, card_selection
- Filters are valid database queries
- Count totals = 100 cards
- No hallucinations possible (model doesn't generate card names)

## Common Pitfalls

1. **VRAM Exhaustion**: 
   - Llama 8B won't fit (~17.5GB needed, 16GB available). Stick with Qwen 2.5 3B.
   - Intel Arc B50 has ~14-15GB usable (1-2GB reserved by system)
   - Backward pass uses MORE VRAM than forward pass
   - Monitor with `nvtop` to see actual usage

2. **Dataset Imbalance**: 
   - 50/50 causes hallucinations. Always use 70-80% card-to-deck ratio.
   - v1 had 50/50: Generated fake cards and wrong counts
   - v2 has 71/29: Should eliminate hallucinations
   - **v2 Result**: FAILED - Model couldn't memorize 31k cards AND learn patterns
   - **v3 Solution**: Model learns patterns only, no card memorization needed

3. **Sequence Length Truncation**:
   - Default 384 tokens truncates 25-52% of deck content
   - Commander decks need 510-793 tokens (avg 637)
   - ALWAYS use MAX_SEQ_LENGTH=675 for full decks
   - Run token analysis before long training runs

4. **Missing Validation**: 
   - Scraper must check `total_cards == 100` and `total_mainboard == (100 - num_commanders)`
   - Validate by quantity sum, not line count (handles "27 Swamp")
   - Commander section required in output

5. **Virtualenv Not Activated**:
   - PyTorch XPU only in virtualenv: `source ~/.virtualenvs/magicapp/bin/activate`
   - System Python doesn't have torch module
   - Training fails immediately without virtualenv

6. **Batch Size Too Aggressive**:
   - BATCH_SIZE=24: OOM during forward pass (~14GB)
   - BATCH_SIZE=16: OOM during backward pass (~10.5GB)
   - BATCH_SIZE=12: OOM during backward pass (~9GB)
   - BATCH_SIZE=8 with seq 675: OOM (~14GB)
   - **Safe**: BATCH_SIZE=4 with seq 675 (~15.2GB = 93% utilization)

7. **Remote Sessions**:
   - GNOME RDP sessions don't persist on disconnect
   - Use `nohup` for long-running training
   - VS Code Remote-SSH maintains connection better

8. **Duplicate Deck Prevention**: 
   - Scraper tracks `self.scraped_ids` to avoid re-scraping
   - "0/32 new decks" = all duplicates, already collected

## Development Commands

```bash
# Frontend dev server
npm run dev

# Database
npx prisma studio

# Training pipeline
python scripts/prepare-balanced-dataset.py
BATCH_SIZE=2 GRADIENT_ACCUMULATION_STEPS=8 MAX_SEQ_LENGTH=675 \
  python scripts/train-commander-model-optimized.py

# Scrape training data
python scripts/scrape-moxfield-themes.py

# Test model
python scripts/test-trained-model-validated.py

# Import cards
npm run import:mtgjson:full
```
