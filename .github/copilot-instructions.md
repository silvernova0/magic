# JankBuild - MTG Commander Deck Builder AI Instructions

## Project Status (Updated Nov 18, 2025)

**Current Training**: Qwen 2.5 3B v3 model in progress (~12-13 hours, completes ~7-8 PM)
- **Major improvements**: Strategy-specific card types (spellslinger→instants/sorceries, artifacts→artifacts, enchantments→enchantments, superfriends→planeswalkers)
- **Better strategy detection**: Commander-aware (Hope Estheim→mill, Talrand→spellslinger) + card composition analysis
- **Dataset**: 29,152 examples with improved distribution (tokens: 1,701, aristocrats: 1,419, spellslinger: 382, artifacts: 304, superfriends: 264)
- **Previous issue**: Old model generated 45 creatures for spellslinger decks instead of 35 instants/sorceries

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
- **Batch size**: 1 with gradient accumulation 32 (effective batch 32)
- **Actual VRAM**: ~14-15GB / 16GB on Arc B50 (batch 1 stable, batch 2+ OOM)
- **Actual duration**: ~12-13 hours (3 epochs × ~4.5 hours each)
- **Training speed**: 1.75 it/s (slower than batch 4 but stable)
- **CRITICAL**: Batch 2+ fails OOM with 600 token sequences. Batch 4 worked with previous 4B model (675 tokens) but not 3B (600 tokens). Cause unknown. Always use batch 1 for safety.

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
- **Dataset**: 29,152 structured examples from 6 sources
- **Format**: Instruction → Structured JSON output (not text decks)
- **Sources**:
  * 2,557 EDHREC average decks (commander-specific patterns)
  * 21,854 MTGGoldfish commander decks (highest quality source)
  * 4,063 Moxfield theme decks
  * 101 TappedOut decks
  * 179 Vehicles decks
  * 60 Advanced decks
  * 336 EDHTop16 decks
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
- **Strategy Distribution** (IMPROVED):
  - midrange: 20,269 (69.5%) - Still dominant but much better
  - tokens: 1,701 (5.8%) - 8.7x increase from v2
  - aristocrats: 1,419 (4.9%) - 8.6x increase
  - spellslinger: 382 (1.3%) - 3.6x increase
  - artifacts: 304 (1.0%) - 4.8x increase
  - superfriends: 264 (0.9%) - 24x increase
  - enchantments: 134 (0.5%) - 33x increase
  - Previous had 83.3% midrange due to weak detection
- **Card Type Allocations** (CRITICAL FIX):
  - **Spellslinger**: 20 instants + 15 sorceries + 12-16 creatures (was 0/0/45 - BUG)
  - **Artifacts**: 25 artifacts + 15 creatures (was 0/35)
  - **Enchantments**: 25 enchantments + 15 creatures (was 0/38)
  - **Superfriends**: 15 planeswalkers + 18-27 creatures (was 0/42)
  - Previous training had ALL non-functional cards as creatures - conversion script never created type-specific categories
  - This caused spellslinger decks to generate 48 creatures + 10 spells instead of the reverse

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
# Output: data/training/v3_structured_training.jsonl (29,152 examples)
```

**Enhanced Strategy Detection** (CRITICAL IMPROVEMENT):
```python
# Lines 131-266: Multi-signal strategy detection
# 1. Commander-specific matching (20 points)
#    - Hope Estheim → mill/lifegain
#    - Talrand/Niv-Mizzet → spellslinger
#    - Urza/Breya → artifacts
#    - Atraxa → superfriends
# 2. Card type composition (10 points)
#    - 25+ instants/sorceries → spellslinger
#    - 20+ artifacts → artifacts
#    - 15+ enchantments → enchantments
# 3. Indicator cards (10 points)
#    - Blood Artist/Zulaport Cutthroat → aristocrats
#    - Doubling Season/Parallel Lives → tokens
#    - Thassa's Oracle/Consultation → combo
# 4. Theme text matching (15 points)
#    - "spellslinger" in theme → spellslinger
#
# Previous: Only checked theme text (weak, 83.3% mislabeled as midrange)
# Current: Multi-signal scoring (better, 69.5% midrange with variety)
```

**Strategy-Specific Card Type Allocations** (CRITICAL FIX):
```python
# Lines 415-520: Strategy determines card types
if strategy == 'spellslinger':
    card_selection['instants'] = {'count': 20, 'filters': [...]}
    card_selection['sorceries'] = {'count': 15, 'filters': [...]}
    card_selection['creatures'] = {'count': 12, 'filters': [...]}
elif strategy == 'artifacts':
    card_selection['artifacts'] = {'count': 25, 'filters': [...]}
    card_selection['creatures'] = {'count': 15, 'filters': [...]}
elif strategy == 'enchantments':
    card_selection['enchantments'] = {'count': 25, 'filters': [...]}
elif strategy == 'superfriends':
    card_selection['planeswalkers'] = {'count': 15, 'filters': [...]}

# PREVIOUS BUG: Everything defaulted to creatures category
# This caused spellslinger decks to have 45 creatures + 0 instants/sorceries
# Now: Each strategy gets appropriate card types
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
- Total examples: 29,152 structured outputs
- Strategy distribution: 69.5% midrange, 5.8% tokens, 4.9% aristocrats, 1.3% spellslinger, 1.0% artifacts, 0.9% superfriends, 0.5% enchantments
- Bracket distribution: 53.6% bracket 2, 32.9% bracket 3, 13.5% bracket 4-5
- Token lengths: 452-581 range (median 510, all fit in 600 tokens)
- **Key improvements over v2**:
  - Strategy detection: 83.3% → 69.5% midrange (better variety)
  - Tokens: 195 → 1,701 examples (8.7x increase)
  - Aristocrats: 165 → 1,419 (8.6x increase)
  - Spellslinger: 106 → 382 (3.6x increase)
  - Superfriends: 11 → 264 (24x increase)
  - Enchantments: 4 → 134 (33x increase)

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

**VRAM CONSTRAINTS - CRITICAL**:
- Intel Arc B50: 16GB total VRAM
- API server uses 4.2GB when running (must stop during training)
- Training with 600-token sequences:
  - **Batch 1**: ~14-15GB VRAM ✅ STABLE
  - **Batch 2+**: OOM crashes (UR_RESULT_ERROR_OUT_OF_RESOURCES)
  - Previous 4B model with 675 tokens: Batch 4 worked (~15.2GB)
  - Mystery: Batch 2 worked before with API running, now fails without it
  - Cause: Likely VRAM fragmentation or backward pass memory growth
  - **ALWAYS USE BATCH 1** for safety with gradient accumulation 32

**Training Speed Comparison**:
- Batch 1: 1.75 it/s (current - stable but slow)
- Batch 4: ~7 it/s (previous model - 4x faster but OOMs now)
- Duration impact: 12-13h vs potential 3-4h (but OOM risk not worth it)

**GPU Monitoring**:
```bash
# Verify Arc GPU visible
python - <<'PY'
import torch
print("xpu available:", torch.xpu.is_available())
print("device count:", torch.xpu.device_count())
PY

# Monitor VRAM usage during training
sudo intel_gpu_top -J -s 200 | head -40
# Or use: watch -n 2 "ps -o pid,%cpu,%mem,cmd -p $(pgrep -f train-v3)"
```

**Common Training Failures**:
1. **OOM during backward pass**: Batch size too large, reduce to 1
2. **Training on CPU**: Virtualenv not activated or missing env vars:
   ```bash
   export ACCELERATE_USE_XPU=1
   export USE_XPU=1
   export ONEAPI_DEVICE_SELECTOR=level_zero:*
   export SYCL_PI_LEVEL_ZERO_USE_IMMEDIATE_COMMANDLISTS=1
   export PYTORCH_XPU_ALLOC_CONF="expandable_segments:True,max_split_size_mb:512"
   ```
3. **API server conflict**: Stop with `kill $(pgrep -f api-server.py)`
4. **GPU device lost**: Reset driver or reboot if persistent

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
   - ❌ Llama 8B won't fit (~17.5GB needed, 16GB available). Stick with Qwen 2.5 3B.
   - ❌ Batch 2+ with 600-token sequences: OOMs during backward pass
   - ❌ API server running during training: Uses 4.2GB VRAM, must stop it
   - ✅ Use batch 1 with gradient accumulation 32 (effective batch 32, stable)
   - Intel Arc B50 has ~14-15GB usable (1-2GB reserved by system)
   - Backward pass uses MORE VRAM than forward pass
   - Monitor with `intel_gpu_top` to see actual usage

2. **Dataset Imbalance**: 
   - ❌ v1 (50/50 cards/decks): Caused hallucinations and wrong counts
   - ❌ v2 (71/29 cards/decks): Model couldn't memorize 31k cards + patterns - FAILED
   - ✅ v3 (100% deck patterns): Model learns ratios/strategies, database provides cards - WORKS
   - **Never mix card knowledge into training** - it undermines the database-driven approach

3. **Strategy Detection Failures**:
   - ❌ Theme-only detection: 83.3% mislabeled as "midrange"
   - ✅ Multi-signal detection: Commander matching + card composition + indicators = 69.5% midrange
   - ❌ Generic creatures category: Spellslinger decks had 48 creatures, 10 spells
   - ✅ Strategy-specific types: Spellslinger gets 20 instants + 15 sorceries + 16 creatures

4. **Sequence Length Truncation**:
   - ❌ Default 384 tokens: Truncates 25-52% of deck content
   - ❌ 675 tokens: Fit previous dataset but OOM with batch 4 on 3B model
   - ✅ 600 tokens: Fits all v3 examples (452-581 range), works with batch 1
   - ALWAYS run token analysis before long training runs

5. **Missing Validation**: 
   - Scraper must check `total_cards == 100` and `total_mainboard == (100 - num_commanders)`
   - Validate by quantity sum, not line count (handles "27 Swamp")
   - Commander section required in output

6. **Virtualenv Not Activated**:
   - PyTorch XPU only in virtualenv: `source ~/.virtualenvs/magicapp/bin/activate`
   - System Python doesn't have torch module
   - Training fails immediately without virtualenv

7. **Batch Size Mysteries**:
   - ❌ BATCH_SIZE=24: OOM during forward pass (~14GB)
   - ❌ BATCH_SIZE=16: OOM during backward pass (~10.5GB)
   - ❌ BATCH_SIZE=12: OOM during backward pass (~9GB)
   - ❌ BATCH_SIZE=8 with seq 675: OOM (~14GB)
   - ❌ BATCH_SIZE=4 with seq 600 (3B model): OOM (mystery - worked on 4B model)
   - ❌ BATCH_SIZE=2 with seq 600: OOM (mystery - worked before with API running)
   - ✅ BATCH_SIZE=1 with seq 600: Stable at ~14-15GB (93% utilization)
   - Cause unknown: Possibly VRAM fragmentation or different memory patterns between models

8. **Remote Sessions**:
   - GNOME RDP sessions don't persist on disconnect
   - Use `nohup` for long-running training
   - VS Code Remote-SSH maintains connection better

9. **Duplicate Deck Prevention**: 
   - Scraper tracks `self.scraped_ids` to avoid re-scraping
   - "0/32 new decks" = all duplicates, already collected

## Things That Don't Work (DO NOT RETRY)

1. **V2 Mixed Dataset Approach**: Tried 70/30 card knowledge/deck patterns. Model couldn't memorize 31k cards AND learn patterns. Result: Hallucinations, wrong counts, failed validation. **Solution**: V3 pure deck patterns + database queries.

2. **Large Batch Sizes**: Batch 2-4 all OOM with 600-token sequences on Arc B50, even with API stopped. Previous 4B model handled batch 4 with 675 tokens, but 3B model can't. **Solution**: Always use batch 1 + gradient accumulation 32.

3. **API Server During Training**: Uses 4.2GB VRAM, causes OOM when training. **Solution**: Stop with `kill $(pgrep -f api-server.py)` before training.

4. **Generic Card Type Categories**: Everything defaulted to "creatures" category. Spellslinger decks had 48 creatures, 10 instants/sorceries. **Solution**: Strategy-specific allocations (spellslinger → instants/sorceries, artifacts → artifacts, etc.).

5. **Theme-Only Strategy Detection**: Checked only deck theme text, 83.3% labeled "midrange". **Solution**: Multi-signal detection with commander matching, card composition analysis, and indicator cards.

6. **Llama 8B Models**: Need ~17.5GB VRAM, Arc B50 only has 16GB. Even with quantization, OOMs. **Solution**: Stick with Qwen 2.5 3B (6.5GB base).

7. **Frontend 60s Timeout**: Model generation takes ~90s, browser timed out with "Unexpected token '<'" errors. **Solution**: Increased to 180s (3 minutes) in fetch call.

## What Actually Works

1. **V3 Dataset Structure**: Model outputs structured JSON filters, database fills actual cards. Zero hallucinations, all cards validated.

2. **Batch 1 + Gradient Accumulation 32**: Stable at ~14-15GB VRAM, effective batch 32, completes in 12-13 hours.

3. **Strategy-Specific Card Types**: Spellslinger gets instants/sorceries, artifacts get artifacts, superfriends get planeswalkers. Proper deck composition.

4. **Multi-Signal Strategy Detection**: Commander matching (20 pts) + card composition (10 pts) + indicator cards (10 pts) + theme text (15 pts). Better variety: 69.5% midrange vs 83.3%.

5. **600 Token Sequences**: Fits all v3 examples (452-581 range) without truncation, leaves VRAM headroom.

6. **Qwen 2.5 3B Base Model**: 3.09B params, 6.5GB base, leaves room for LoRA and training overhead.

7. **Frontend 180s Timeout**: Handles model generation time comfortably, good error messages on failures.

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
