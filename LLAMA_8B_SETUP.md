# Llama 3.1 8B Training Setup

## Changes Made

### Updated Base Model
- **Previous:** Qwen 2.5 3B (`models/qwen2.5-3b`)
- **Current:** Llama 3.1 8B (`models/llama-3.1-8b`)

### Training Script Updates
- **File:** `scripts/train-commander-model-optimized.py`
- **Change:** Updated `BASE_MODEL_PATH` to use Llama 3.1 8B
- **Memory:** Optimized batch size for 8B parameters

### New Training Script
- **File:** `train-model-llama8b.sh`
- **Batch Size:** 2 (down from 4 for Qwen 3B)
- **Gradient Accumulation:** 8 steps (up from 4, maintains effective batch=16)
- **Max Sequence Length:** 675 tokens (default)

## Model Comparison

| Feature | Qwen 2.5 3B | Llama 3.1 8B |
|---------|-------------|--------------|
| Parameters | 3 billion | 8 billion |
| Context Window | 32K tokens | 128K tokens |
| Training Time | ~1.5-2 hours | ~3-4 hours |
| Memory Usage | ~6-8GB VRAM | ~14-18GB VRAM |
| Strengths | Fast, structured output | Better understanding, card memorization |
| Best For | Quick iterations | Final production model |

## Why Llama 3.1 8B?

✅ **More capacity** - 8B parameters vs 3B = better at:
  - Remembering real card names (less hallucination)
  - Understanding complex synergies
  - Following multi-constraint rules (color identity + strategy + power level)

✅ **Proven track record** - Meta's flagship open model, widely tested

✅ **128K context** - Can fit more training examples in context

✅ **Your hardware supports it** - Intel Arc A770 has sufficient VRAM

## Training Commands

### Option 1: Llama 3.1 8B (Recommended for final model)
```bash
# After scraping completes and dataset is prepared
source ~/.virtualenvs/magicapp/bin/activate
./train-model-llama8b.sh > training-llama8b.log 2>&1 &
```

### Option 2: Qwen 2.5 3B (Faster iterations)
```bash
# Update train-commander-model-optimized.py back to Qwen if needed
# BASE_MODEL_PATH = "models/qwen2.5-3b"
./train-model-optimized.sh > training-qwen3b.log 2>&1 &
```

## Next Steps

1. **Wait for scraper to finish** (~2-3 more hours)
   - Check progress: `tail -100 scrape-themes.log | grep PROGRESS`
   
2. **Prepare balanced dataset** with 80/20 card-to-deck ratio
   ```bash
   python scripts/prepare-balanced-dataset.py
   ```

3. **Train with Llama 3.1 8B**
   ```bash
   ./train-model-llama8b.sh > training-llama8b.log 2>&1 &
   ```

4. **Test comprehensively**
   - Test Ur-Dragon (dragon tribal)
   - Test Atraxa (casual counters, GWUB)
   - Test Krenko (goblin tribal, budget)
   - Verify: exactly 100 cards, no hallucinations, correct colors, strategy matches

## Expected Results

With Llama 3.1 8B + 80/20 card-heavy dataset + validated diverse decks:

✅ No hallucinated cards (80% card knowledge teaches real names)
✅ Correct card counts (100 cards every time)
✅ Color identity respect (more parameters = better rule following)
✅ Strategy matching (diverse training data from theme+bracket scraper)
✅ Power level awareness (Bracket 1-5 examples in training)

This should be the **final iteration** before production deployment.
