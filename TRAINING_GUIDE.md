# Commander AI Model Training Guide (v2)

## Overview
This guide covers training a custom Qwen 2.5 3B model for Commander/EDH deck building using LoRA fine-tuning on Intel Arc B50 16GB.

## Prerequisites ✓
- [x] Base model downloaded: `models/qwen2.5-3b/` (6.5GB)
- [x] Training data prepared: `data/training/combined_training_v2_50k.jsonl` (43,631 examples)
- [x] Dependencies installed: PyTorch 2.8.0+xpu, transformers, PEFT, datasets, trl
- [x] Virtualenv activated: `source ~/.virtualenvs/magicapp/bin/activate`
- [x] Training script ready: `scripts/train-commander-model-optimized.py`

## Training Configuration (v2 - Optimized)

### Model Architecture
- **Base Model**: Qwen 2.5 3B
- **Fine-tuning Method**: LoRA (Low-Rank Adaptation)
- **LoRA Rank**: 16
- **LoRA Alpha**: 32
- **LoRA Dropout**: 0.05
- **Target Modules**: q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj
- **Trainable Parameters**: 29.9M (~0.96% of total 3.1B params)

### Training Hyperparameters
- **Epochs**: 3
- **Batch Size**: 4 per device (optimal for 16GB VRAM)
- **Gradient Accumulation Steps**: 8 (effective batch size = 32)
- **Learning Rate**: 2e-4 with linear warmup
- **Warmup Steps**: 100
- **Mixed Precision**: BF16 (bfloat16 for stability)
- **Max Sequence Length**: 675 tokens (fits full Commander decks)
- **Gradient Checkpointing**: Enabled (reduces VRAM usage)
- **VRAM Usage**: ~15.2GB / 16GB (93% utilization - optimal)
- **Checkpoints**: Saved every 100 steps

### Training Data (v2)
- **Total Examples**: 43,631
  - 31,131 card knowledge examples (71.4%) - prevents hallucinations
  - 12,500 Commander decks (28.6%) - teaches deck patterns
- **Sources**:
  - MTGGoldfish: 12,314 decks (commander-specific search, highest quality)
  - Archidekt: 4,144 decks (popular commanders)
  - Moxfield: 3,754 decks (theme + power bracket filtered)
- **Format**: Instruction-output pairs for instruction-following fine-tuning
- **File**: `data/training/combined_training_v2_50k.jsonl`

### Hardware Requirements
- **GPU**: Intel Arc B50 16GB VRAM (Battlemage architecture)
- **VRAM Usage**: ~15.2GB during training (93% utilization)
- **Expected Training Time**: ~32 hours (~1.3 days)
- **Storage**: ~500MB for checkpoints, ~200MB for final LoRA adapter

## Starting Training (v2)

### CRITICAL: Activate Virtualenv First
```bash
source ~/.virtualenvs/magicapp/bin/activate
# PyTorch 2.8.0+xpu is ONLY available in virtualenv
```

### Command (Optimal Configuration)
```bash
BATCH_SIZE=4 GRADIENT_ACCUMULATION_STEPS=8 MAX_SEQ_LENGTH=675 \
  nohup python3 scripts/train-commander-model-optimized.py > training_v2.log 2>&1 &
```

### Monitor Training
```bash
# Watch training progress
tail -f training_v2.log

# Monitor GPU VRAM usage (both integrated + Arc B50)
nvtop

# Check process status
ps aux | grep train-commander-model-optimized
```

### What to Expect
1. **Initialization** (~2-3 minutes):
   - Loading tokenizer (Qwen 2.5 3B)
   - Loading 43,631 training examples
   - Tokenizing datasets (41,449 train, 2,182 validation)
   - Loading base model (3.1B parameters)
   - Applying LoRA configuration (29.9M trainable params)
   - Total steps: 3,886 per epoch × 3 epochs

2. **Training Progress**:
   - Logs every 20 steps with validation
   - Checkpoints saved every 100 steps
   - Step time: ~3.3 seconds per step
   - Loss trajectory: Epoch 1 (3.5→2.0), Epoch 2 (1.8→1.3), Epoch 3 (1.2→0.9)
   - Progress bar shows current step, loss, and speed

3. **VRAM Usage**:
   - Initial model load: ~6.5GB
   - During training: ~15.2GB (93% of 16GB)
   - Backward pass uses MORE than forward pass
   - Monitor with: `nvtop` (shows real-time VRAM bars)

4. **Output**:
   - Checkpoints: `models/commander-llama-lora/checkpoint-{step}/`
   - Final model: `models/commander-llama-lora/final/`
   - Training log: `training_v2.log`
   - Model config: `models/commander-llama-lora/final/adapter_config.json`

### Monitoring Training
- **GPU Usage**: `nvtop` shows both integrated GPU and Arc B50 with VRAM bars
- **Training Logs**: `tail -f training_v2.log` shows loss, learning rate, progress
- **Process Status**: `ps aux | grep train-commander` confirms running
- **Resume from Checkpoint**: Training can resume from any checkpoint if interrupted

### Sample Output
```
============================================================
Commander Deck Builder - LoRA Fine-Tuning
============================================================
Start time: 2025-10-23 14:30:00
Base model: models/llama-3.1-8b
Training data: data/training/combined_training.jsonl
Output directory: models/commander-llama-lora

Device: cuda
GPU: Intel(R) Arc(TM) Pro B50 16GB
VRAM: 16.00 GB

✓ Tokenizer loaded
  Vocab size: 128,256
  Padding token: <|end_of_text|>

✓ Loaded 65,480 training examples

✓ Dataset tokenized

✓ Base model loaded
  Parameters: 8,030,261,248
  Trainable parameters: 8,030,261,248

✓ LoRA configured and applied
  LoRA rank: 16
  LoRA alpha: 32
  Total parameters: 8,030,261,248
  Trainable parameters: 167,772,160
  Trainable %: 2.09%

✓ Training configured
  Epochs: 3
  Effective batch size: 16
  Total training steps: 12,276
  Save every 500 steps

============================================================
STARTING TRAINING
============================================================
This will take approximately 12-18 hours on Intel Arc B50 Pro
Progress will be logged every 10 steps

Step 10/12276 | Loss: 2.345 | LR: 2.0e-05 | ETA: 14:23:15
Step 20/12276 | Loss: 2.156 | LR: 4.0e-05 | ETA: 14:15:22
...
```

## Pausing/Resuming Training

### To Pause
Press `Ctrl+C` in the terminal. The script will:
- Save current checkpoint
- Log interruption
- Exit gracefully

### To Resume
Run the same command again:
```bash
C:\Users\fuckthisshit\openvino_env\Scripts\python scripts/train-commander-model.py
```

The script will automatically resume from the latest checkpoint.

## After Training

### Files Created
```
models/commander-llama-lora/
├── adapter_config.json       # LoRA adapter configuration
├── adapter_model.safetensors # LoRA weights (~100-200 MB)
├── training_config.json      # Training hyperparameters
├── training_complete.json    # Completion timestamp and final loss
├── tokenizer.json            # Tokenizer (copied from base model)
├── tokenizer_config.json
├── special_tokens_map.json
└── checkpoints/
    ├── checkpoint-500/
    ├── checkpoint-1000/
    ├── checkpoint-1500/
    └── ... (up to checkpoint-12000)
```

### Next Steps
1. **Export to OpenVINO Format** (for optimized inference on Intel Arc GPU)
2. **Create Inference API** (Flask API for deck generation)
3. **Integrate with Next.js App** (replace Gemini with local model)

## Troubleshooting

### Out of Memory (OOM) Error
If you get CUDA OOM errors:
1. Reduce `BATCH_SIZE` to 1 in the script
2. Increase `GRADIENT_ACCUMULATION_STEPS` to 16 (keeps effective batch size)
3. Reduce `MAX_SEQ_LENGTH` to 1536

### Slow Training
- Ensure GPU is being used (check logs for "Device: cuda")
- Close other GPU-intensive applications
- Monitor VRAM usage (should be ~12GB)

### Training Loss Not Decreasing
- Normal for first 100-200 steps (warmup period)
- Should steadily decrease after warmup
- Final loss target: <1.0 (good), <0.5 (excellent)

### Checkpoint Corruption
If a checkpoint is corrupted:
1. Delete the corrupted checkpoint folder
2. Training will resume from the previous valid checkpoint

## Performance Tips

### Speed Optimization
- Keep training window in focus (Windows may throttle background processes)
- Disable Windows Game Bar (can interfere with GPU scheduling)
- Close other GPU applications (browsers, video players, etc.)

### Quality Optimization
- Current 3 epochs is good for initial training
- If underfitting (high loss), increase epochs to 5
- If overfitting (memorizing decks), reduce epochs to 2

## Expected Results

### Training Metrics
- **Initial Loss**: ~3.0-4.0 (expected for untrained model)
- **Final Loss**: ~0.5-1.0 (target for good performance)
- **Training Time**: 12-18 hours (depends on GPU load)

### Model Capabilities After Training
- Generate complete 99-card Commander decks
- Understand card synergies and combos
- Follow power level and theme constraints
- Produce authentic, playable decklists
- Answer Magic card questions

## Ready to Start?

Everything is prepared! Run this command when ready:

```bash
C:\Users\fuckthisshit\openvino_env\Scripts\python scripts/train-commander-model.py
```

The training will run for 12-18 hours. You can leave it running overnight. The script will automatically save checkpoints and handle interruptions gracefully.

Good luck with your training! 🎲⚡
