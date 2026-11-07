# Commander AI Model Training Guide

## Overview
This guide covers training a custom Llama 3.1 8B model for Commander/EDH deck building using LoRA fine-tuning on Intel Arc B50 Pro.

## Prerequisites ✓
- [x] Base model downloaded: `models/llama-3.1-8b/` (16GB)
- [x] Training data prepared: `data/training/combined_training.jsonl` (65,480 examples, 23.94 MB)
- [x] Dependencies installed: PyTorch, transformers, PEFT, datasets, accelerate
- [x] Training script ready: `scripts/train-commander-model.py`

## Training Configuration

### Model Architecture
- **Base Model**: Llama 3.1 8B Instruct
- **Fine-tuning Method**: LoRA (Low-Rank Adaptation)
- **LoRA Rank**: 16
- **LoRA Alpha**: 32
- **Target Modules**: q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj
- **Trainable Parameters**: ~1-2% of total (efficient training)

### Training Hyperparameters
- **Epochs**: 3
- **Batch Size**: 2 per device
- **Gradient Accumulation Steps**: 8 (effective batch size = 16)
- **Learning Rate**: 2e-4
- **Mixed Precision**: FP16 (for GPU acceleration)
- **Max Sequence Length**: 2048 tokens
- **Warmup Steps**: 100
- **Checkpoints**: Saved every 500 steps

### Training Data
- **Total Examples**: 65,480
  - 65,379 card knowledge examples (card descriptions, mechanics, power levels)
  - 101 real Commander decks from TappedOut (authentic deck patterns)
- **Format**: Instruction-output pairs for instruction-following fine-tuning
- **File Size**: 23.94 MB

### Hardware Requirements
- **GPU**: Intel Arc B50 Pro (16GB VRAM)
- **VRAM Usage**: ~12GB during training
- **Expected Training Time**: 12-18 hours
- **Storage**: ~1GB for checkpoints, ~200MB for final LoRA adapter

## Starting Training

### Command
```bash
C:\Users\fuckthisshit\openvino_env\Scripts\python scripts/train-commander-model.py
```

### What to Expect
1. **Initialization** (2-3 minutes):
   - Loading tokenizer
   - Loading base model (8B parameters)
   - Applying LoRA configuration
   - Preparing dataset

2. **Training Progress**:
   - Logs every 10 steps
   - Checkpoints saved every 500 steps
   - Total steps: ~12,000 (3 epochs × 4,092 steps/epoch)
   - Progress bar shows current step, loss, and ETA

3. **Output**:
   - Checkpoints: `models/commander-llama-lora/checkpoints/checkpoint-{step}/`
   - Final model: `models/commander-llama-lora/`
   - Training config: `models/commander-llama-lora/training_config.json`
   - Completion log: `models/commander-llama-lora/training_complete.json`

### Monitoring Training
- **GPU Usage**: Open Task Manager → Performance → GPU to monitor VRAM usage
- **Training Logs**: Terminal shows loss, learning rate, and progress every 10 steps
- **Checkpoints**: Resume training from any checkpoint if interrupted

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
