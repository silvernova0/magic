# Memory Management Configuration

## System Specifications
- **Total RAM**: 127.77 GB
- **Target Max Usage**: 100 GB (78% of total)
- **Safety Buffer**: ~28 GB for OS and other processes

## Memory Optimizations Applied

### 1. Training Script Settings
```python
# Batch configuration
BATCH_SIZE = 1                    # Minimal per-device batch
GRADIENT_ACCUMULATION_STEPS = 16  # Maintain effective batch=16

# Memory optimizations
gradient_checkpointing = True     # Trades compute for memory (30-40% savings)
optim = "adamw_torch"            # PyTorch native optimizer (more efficient)
dataloader_pin_memory = False    # Disable memory pinning
```

### 2. Automatic Memory Management
- **Garbage collection**: Every 50 steps
- **GPU cache clearing**: Every 50 steps (XPU/CUDA)
- **Dataset cleanup**: Explicit deletion after tokenization
- **Tokenization batching**: Reduced to 50 (from 100)

### 3. Model Loading
- `low_cpu_mem_usage=True` - Efficient model loading
- `gradient_checkpointing_enable()` - Activation checkpointing
- FP16 precision on GPU (half memory vs FP32)

### 4. Checkpoint Strategy
- Save every 100 steps (frequent saves)
- Keep last 10 checkpoints only
- Progress tracking every 10 steps

## Expected Memory Usage

### During Training
- **GPU VRAM**: 10-12 GB (Intel Arc B50 Pro)
- **System RAM Peak**: 60-80 GB
- **Typical RAM Usage**: 40-60 GB
- **Safety Margin**: ~30-50 GB available

### Memory Timeline
1. **Initial Load** (~20 GB): Tokenizer + Dataset
2. **Tokenization** (~30-40 GB): Processing 65,480 examples
3. **Model Load** (+15-20 GB): Loading 8B parameters
4. **Training Start** (~50-60 GB): LoRA + Optimizer states
5. **Steady State** (~40-60 GB): With periodic garbage collection

## Monitoring

### Real-time Memory Monitoring
```bash
# In separate terminal/SSH session
monitor-memory.bat
```

Shows:
- Total/Used/Available RAM
- Visual progress bar
- Python process memory usage
- Warnings at >80% usage

### Training Progress
```bash
# Check without interrupting training
check-progress.bat
```

Shows:
- Current step and percentage
- Training loss and learning rate
- Estimated time remaining
- Last checkpoint saved

## If Memory Issues Occur

### Warning Signs
- System RAM usage >90%
- Training slows significantly
- Windows "Low Memory" notifications

### Emergency Actions
1. Training will auto-save checkpoint before crash
2. Check last checkpoint: `models/commander-llama-lora/checkpoints/`
3. Resume from checkpoint by restarting training

### Further Optimizations (if needed)
```python
# Can reduce these if still hitting limits:
GRADIENT_ACCUMULATION_STEPS = 32  # Double from 16
MAX_SEQ_LENGTH = 1536             # Reduce from 2048
```

## Current Configuration Safety

✅ **Very Safe** - 128 GB RAM with 60-80 GB peak usage
✅ **50 GB buffer** minimum at all times
✅ **Automatic cleanup** prevents memory leaks
✅ **Frequent checkpoints** prevent data loss

## SSH Session Tips

Since you're running from SSH:
1. Training runs in foreground (normal)
2. Progress saves to file every 10 steps
3. Log file persists: `models/commander-llama-lora/training_*.log`
4. Can check status anytime with `check-progress.bat`
5. If SSH disconnects, training continues but you lose terminal view

### Recommended Setup
```bash
# Terminal 1 (SSH): Start training
train-model.bat

# Terminal 2 (SSH or local): Monitor memory
monitor-memory.bat

# Terminal 3 (SSH or local): Check progress periodically
check-progress.bat
```

## Resume from Checkpoint (if interrupted)

Training automatically resumes from last checkpoint when restarted:
1. Checkpoints saved every 100 steps
2. Located in: `models/commander-llama-lora/checkpoints/checkpoint-{step}/`
3. Simply run `train-model.bat` again
4. Trainer auto-detects and resumes

## Memory Limit Enforcement

The script sets a soft cap at 100 GB:
- Python garbage collection every 50 steps
- GPU cache clearing every 50 steps
- Explicit object deletion after use
- Windows relies on process monitoring (resource module N/A)

**Note**: Windows doesn't have hard memory limits like Linux `ulimit`. Instead:
- Aggressive garbage collection prevents leaks
- Monitoring alerts if usage >80%
- OS will page to disk if needed (training will slow but not crash)
