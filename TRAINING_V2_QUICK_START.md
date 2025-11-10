# Training v2 Quick Start Guide

## Current Training Status (as of Nov 7, 2025)

**Training v2 is RUNNING with optimal configuration:**
- Started: November 7, 2025 at 06:31 AM
- Expected completion: November 8, 2025 afternoon (~32 hours)
- Process: PID varies (check with `ps aux | grep train-commander`)
- Log file: `training_v2.log`
- VRAM usage: **15.2GB / 16GB (93% utilization - PERFECT)**

## Critical Information

### Hardware Setup
- **GPU**: Intel Arc B50 16GB VRAM (Battlemage)
- **CPU**: Intel i7-11700K
- **RAM**: 128GB
- **OS**: Linux (Ubuntu/Debian-based)

### Virtualenv Setup
**CRITICAL**: PyTorch XPU is ONLY available in virtualenv:
```bash
source ~/.virtualenvs/magicapp/bin/activate
```

Without this, you'll get: `ModuleNotFoundError: No module named 'torch'`

## Training Configuration (OPTIMAL)

### v2 Configuration (Current - Nov 7, 2025)
```bash
BATCH_SIZE=4                      # Conservative for 16GB VRAM
GRADIENT_ACCUMULATION_STEPS=8     # Effective batch size = 32
MAX_SEQ_LENGTH=675                # Fits full 100-card decks (510-793 tokens)
```

**Why these numbers:**
- BATCH_SIZE=4: Uses ~15.2GB VRAM (93% utilization, safe margin)
- BATCH_SIZE=6: Would use ~15.8GB, OOM risk
- BATCH_SIZE=8: Would use ~14.1GB, OOM during backward pass
- MAX_SEQ_LENGTH=675: Fits all Commander decks (avg 637 tokens, max 793)
- MAX_SEQ_LENGTH=384: Truncates 25-52% of deck content (BAD!)

### Dataset (v2)
- **File**: `data/training/combined_training_v2_50k.jsonl`
- **Total examples**: 43,631
  - Cards: 31,131 (71.4%) - prevents hallucinations
  - Decks: 12,500 (28.6%) - teaches deck patterns
- **Sources**:
  - MTGGoldfish: 12,314 decks (best quality)
  - Archidekt: 4,144 decks
  - Moxfield: 3,754 decks
  - Total available: 22,197 validated decks

## How to Start Training (if not running)

### 1. Activate Virtualenv
```bash
source ~/.virtualenvs/magicapp/bin/activate
```

### 2. Start Training
```bash
cd /home/social/magicapp

BATCH_SIZE=4 GRADIENT_ACCUMULATION_STEPS=8 MAX_SEQ_LENGTH=675 \
  nohup python3 scripts/train-commander-model-optimized.py > training_v2.log 2>&1 &
```

### 3. Monitor Progress
```bash
# Watch log file
tail -f training_v2.log

# Check GPU VRAM (both integrated + Arc B50)
nvtop

# Check process
ps aux | grep train-commander-model-optimized
```

## Monitoring Commands

### GPU Monitoring
```bash
# Best option: Interactive interface with VRAM bars
nvtop

# Alternative: Python monitor script
python3 scripts/monitor-combined.py

# Menu script
./monitor-gpu.sh
```

### Training Progress
```bash
# Live log tail (Ctrl+C to exit)
tail -f training_v2.log

# Last 50 lines
tail -50 training_v2.log

# Search for specific epoch
grep "Epoch" training_v2.log | tail -20
```

### Process Management
```bash
# Check if running
ps aux | grep train-commander-model-optimized

# Stop training (if needed)
pkill -f train-commander-model-optimized

# Check VRAM usage
ps aux | grep train-commander | awk '{print $6/1024 " MB"}'
```

## Training Timeline

### Expected Progress
- **Total steps**: 3,886 per epoch × 3 epochs = 11,658 steps
- **Step time**: ~3.3 seconds/step
- **Time per epoch**: ~3.6 hours
- **Total time**: ~32 hours (~1.3 days)
- **Checkpoints**: Every 100 steps (~5.5 minutes)

### Loss Trajectory (Expected)
- **Epoch 1**: Loss 3.5 → 2.0
- **Epoch 2**: Loss 1.8 → 1.3
- **Epoch 3**: Loss 1.2 → 0.9

### Checkpoints
- Location: `models/commander-llama-lora/checkpoint-{step}/`
- Final model: `models/commander-llama-lora/final/`
- Checkpoint frequency: Every 100 steps
- Total checkpoints: ~116 checkpoints across 3 epochs

## What Changed from v1 to v2

### Dataset Changes
| Metric | v1 | v2 |
|--------|----|----|
| Total examples | 8,142 | 43,631 |
| Card/Deck ratio | 50/50 | 71/29 |
| Deck sources | Moxfield only | MTGGoldfish, Archidekt, Moxfield |
| Best source | N/A | MTGGoldfish (12,314 decks) |
| Deck quality | Mixed | Validated, 100 cards exactly |

### Training Configuration Changes
| Metric | v1 | v2 |
|--------|----|----|
| Model | Qwen 2.5 3B | Qwen 2.5 3B |
| Batch size | Variable | 4 (optimal) |
| Sequence length | 384 | 675 (critical fix) |
| VRAM usage | Unknown | 15.2GB (93%) |
| Training time | Unknown | ~32 hours |
| Effective batch | 32 | 32 |

### Key Discoveries
1. **Sequence length critical**: 384 tokens truncated 25-52% of decks
   - Models would learn to generate 60-75 card decks (WRONG!)
   - 675 tokens fits full 100-card decks (510-793 token range)

2. **Backward pass uses MORE VRAM**: Not obvious from forward pass
   - BATCH_SIZE=24: OOM during forward pass
   - BATCH_SIZE=16/12: OOM during backward pass
   - BATCH_SIZE=4: Perfect (93% utilization)

3. **MTGGoldfish best quality**: Commander-specific search yields highest quality
   - 69% of commanders had decks in last 6 months
   - 12,314 decks collected (best source)
   - Validation rejection rate: 7.4%

4. **Token analysis saves time**: 30 minutes of analysis saved 32 hours of training
   - Identified truncation before committing to long run
   - Prevented deployment of broken model

## Troubleshooting

### Training Won't Start
```bash
# 1. Check virtualenv
source ~/.virtualenvs/magicapp/bin/activate
python3 -c "import torch; print(torch.__version__)"
# Should output: 2.8.0+xpu

# 2. Check if already running
ps aux | grep train-commander-model-optimized

# 3. Check log for errors
tail -100 training_v2.log
```

### Out of Memory (OOM)
```bash
# Reduce batch size
BATCH_SIZE=3 GRADIENT_ACCUMULATION_STEPS=11 MAX_SEQ_LENGTH=675 \
  nohup python3 scripts/train-commander-model-optimized.py > training_v2.log 2>&1 &

# Or reduce dataset size
python3 scripts/prepare-balanced-dataset-v2.py
# Edit to create 30k dataset instead of 43k
```

### Training Crashes
```bash
# Check last checkpoint
ls -lth models/commander-llama-lora/checkpoint-* | head -5

# Resume from last checkpoint
# Edit scripts/train-commander-model-optimized.py
# Set: resume_from_checkpoint="models/commander-llama-lora/checkpoint-XXXX"
```

### Slow Progress
```bash
# Check GPU usage (should be near 100%)
nvtop

# Check CPU bottleneck
htop

# Verify step time (should be ~3.3 seconds)
tail -f training_v2.log | grep "it/s"
```

## After Training Completes

### 1. Verify Model Saved
```bash
ls -lh models/commander-llama-lora/final/
# Should contain: adapter_config.json, adapter_model.safetensors
```

### 2. Test Model
```bash
source ~/.virtualenvs/magicapp/bin/activate
python3 scripts/test-trained-model-validated.py
```

### 3. Validate Against Database
```bash
python3 scripts/validate_generated_deck.py
# Tests: Ur-Dragon (tribal), Atraxa (counters), random commanders
```

### 4. Compare with v1
```bash
# Generate decks with both models
# Compare:
# - Hallucination rate (should be 0% for v2)
# - Card count accuracy (should be 100 cards)
# - Commander validity (should match color identity)
# - Deck playability (should be competitive)
```

## Key Files Reference

### Training Scripts
- `scripts/train-commander-model-optimized.py` - Main training script
- `scripts/prepare-balanced-dataset-v2.py` - Dataset preparation
- `scripts/test-trained-model-validated.py` - Model testing with validation

### Data Files
- `data/training/combined_training_v2_50k.jsonl` - Current dataset (43k examples)
- `data/training/combined_training_balanced_v2.jsonl` - Full dataset (86k examples)
- `data/training/card_knowledge.jsonl` - Card descriptions (65k cards)
- `data/training/mtggoldfish_by_commander_decks.jsonl` - MTGGoldfish decks (12k)
- `data/training/archidekt_decks.jsonl` - Archidekt decks (4k)
- `data/training/moxfield_decks.jsonl` - Moxfield decks (4k)

### Scraper Scripts
- `scripts/scrape-mtggoldfish-by-commander.py` - Best source (12k decks)
- `scripts/scrape-archidekt-commanders.py` - Archidekt scraper (4k decks)
- `scripts/scrape-moxfield-themes.py` - Moxfield scraper (4k decks)

### Model Files
- `models/qwen2.5-3b/` - Base model (6.5GB)
- `models/commander-llama-lora/` - Training output directory
- `models/commander-llama-lora/checkpoint-*/` - Training checkpoints
- `models/commander-llama-lora/final/` - Final trained model

### Logs
- `training_v2.log` - Current training log
- `mtggoldfish_commander.log` - MTGGoldfish scraper log
- `archidekt.log` - Archidekt scraper log
- `moxfield.log` - Moxfield scraper log

## Contact & Documentation

### Documentation Files
- `.github/copilot-instructions.md` - AI assistant instructions (COMPREHENSIVE)
- `TRAINING_GUIDE.md` - Full training guide (updated for v2)
- `TRAINING_V2_QUICK_START.md` - This file
- `START_TRAINING_V2.md` - v2 training startup guide
- `TRAINING_PROGRESS.md` - Progress tracking

### Key Sections in copilot-instructions.md
- Training the Local AI Model (lines 28-66)
- Scraping Training Data (lines 68-108)
- Training Data Balance (lines 140-158)
- Intel XPU Training (lines 160-173)
- Common Pitfalls (lines 175-233)

## Quick Reference Commands

```bash
# === TRAINING ===
# Start training
source ~/.virtualenvs/magicapp/bin/activate && \
BATCH_SIZE=4 GRADIENT_ACCUMULATION_STEPS=8 MAX_SEQ_LENGTH=675 \
  nohup python3 scripts/train-commander-model-optimized.py > training_v2.log 2>&1 &

# Monitor training
tail -f training_v2.log

# Check GPU
nvtop

# Stop training
pkill -f train-commander-model-optimized

# === SCRAPING ===
# MTGGoldfish (best quality)
nohup python3 scripts/scrape-mtggoldfish-by-commander.py > mtggoldfish_commander.log 2>&1 &

# Archidekt
nohup python3 scripts/scrape-archidekt-commanders.py > archidekt.log 2>&1 &

# Moxfield
nohup python3 scripts/scrape-moxfield-themes.py > moxfield.log 2>&1 &

# === DATASET ===
# Prepare balanced dataset
python3 scripts/prepare-balanced-dataset-v2.py

# Analyze token lengths
source ~/.virtualenvs/magicapp/bin/activate && python3 scripts/analyze-token-lengths.py

# === VALIDATION ===
# Test trained model
source ~/.virtualenvs/magicapp/bin/activate && \
python3 scripts/test-trained-model-validated.py

# Validate generated deck
python3 scripts/validate_generated_deck.py
```

## Success Criteria

### Training Success
- ✅ Training completes 3 epochs
- ✅ Final loss < 1.0
- ✅ All checkpoints saved
- ✅ Model files present in `models/commander-llama-lora/final/`

### Model Quality
- ✅ No hallucinated cards (all cards exist in database)
- ✅ Exactly 100 cards per deck
- ✅ Valid commander (correct color identity)
- ✅ No duplicates except basic lands
- ✅ Deck strategy matches request
- ✅ Power level appropriate for request

### Performance Metrics (compare to v1)
- Hallucination rate: 0% (was >10% in v1)
- Card count accuracy: 100% (was ~80% in v1)
- Commander validity: 100% (was ~90% in v1)
- Strategy match: >90% (measure subjectively)

---

**Last Updated**: November 7, 2025
**Training Status**: RUNNING (started Nov 7 06:31, ETA Nov 8 afternoon)
**Configuration**: BATCH_SIZE=4, GRAD_ACCUM=8, SEQ_LEN=675 (93% VRAM - OPTIMAL)
