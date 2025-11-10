# Commander AI Model Training v2

## Dataset Summary
- **Total examples**: 85,939 (10.5x larger than v1)
- **Card knowledge**: 65,379 examples (76.1%)
- **Deck examples**: 20,560 examples (23.9%)
- **Sources**: Archidekt (4,144), Moxfield (3,754), MTGGoldfish (12,662)

## Training Configuration
- **Model**: Qwen 2.5 3B (6.5GB base)
- **Batch size**: 24 (aggressive optimization)
- **Gradient accumulation**: 1
- **Effective batch size**: 24
- **Max sequence length**: 384 tokens
- **Epochs**: 3
- **LoRA rank**: 16

## Resource Usage
- **VRAM**: ~11.3GB / 16GB (4.7GB headroom)
- **Training time**: ~74 hours (~3.1 days)
- **Dataset file**: `data/training/combined_training_balanced_v2.jsonl`

## Start Training

```bash
# Recommended configuration (BATCH_SIZE=24)
BATCH_SIZE=24 GRADIENT_ACCUMULATION_STEPS=1 \
  nohup python3 scripts/train-commander-model-optimized.py > training_v2.log 2>&1 &

# Get the process ID
ps aux | grep train-commander-model-optimized

# Monitor progress
tail -f training_v2.log

# Or watch live updates
watch -n 5 'tail -20 training_v2.log'
```

## Fallback Configuration

If you get OOM (Out of Memory) errors with BATCH_SIZE=24:

```bash
# Kill the training process
pkill -f train-commander-model-optimized

# Restart with conservative batch size (BATCH_SIZE=16)
BATCH_SIZE=16 GRADIENT_ACCUMULATION_STEPS=2 \
  nohup python3 scripts/train-commander-model-optimized.py > training_v2.log 2>&1 &
```

This will take ~4 days instead of 3.1, but uses only ~9.7GB VRAM.

## Monitor GPU Usage

```bash
# Check GPU memory usage
intel_gpu_top

# Or with JSON output
watch -n 1 'intel_gpu_top -J | grep -A 5 memory'
```

## What to Expect

### Training Progress
- **Step 0-100**: Warmup period, loss may be erratic
- **Step 100-1000**: Loss should decrease steadily
- **Every 100 steps**: Checkpoint saved to `models/commander-llama-lora/checkpoints/`
- **Every 300 steps**: Test generation to verify quality

### Expected Results
With 10.5x more training data and 76% card knowledge:
- ✅ No hallucinated cards
- ✅ Proper 100-card decklists
- ✅ Valid commanders (legendary creatures/planeswalkers)
- ✅ Correct color identity enforcement
- ✅ No duplicates (except basic lands)
- ✅ Strategic deck composition

## After Training

Test the model:
```bash
python3 scripts/test-model-with-validation.py
```

This will generate 5 test decks and validate them against the card database.

## Estimated Completion

If started now (Nov 7, 2025), training should complete around **Nov 10, 2025 (~11am)**.
