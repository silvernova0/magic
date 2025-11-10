#!/usr/bin/env bash

set -euo pipefail

echo "============================================================"
echo "Commander AI Model Training - Llama 3.1 8B"
echo "============================================================"
echo
echo "Configuration:"
echo "  - Base Model: Llama 3.1 8B (8 billion parameters)"
echo "  - Batch size: 2 (optimized for 8B VRAM efficiency)"
echo "  - Gradient accumulation: 8 steps (effective batch = 16)"
echo "  - LoRA rank: 16, alpha: 32"
echo "  - Expected training time: ~3-4 hours (2-2.5x slower than 3B)"
echo "  - Better understanding and card memorization"
echo

# Locate oneAPI setvars script if available
ONEAPI_SETVARS_SH="${ONEAPI_ROOT:-/opt/intel/oneapi}/setvars.sh"

if [[ -f "${ONEAPI_SETVARS_SH}" ]]; then
  echo "Configuring Intel oneAPI environment from ${ONEAPI_SETVARS_SH}..."
  set +u
  # shellcheck disable=SC1090
  source "${ONEAPI_SETVARS_SH}" --force >/dev/null 2>&1
  set -u
  echo "Environment configured."
else
  echo "WARNING: Intel oneAPI environment not detected at ${ONEAPI_SETVARS_SH}."
  echo "Install Intel oneAPI Base Toolkit and set ONEAPI_ROOT if you plan to train on the Arc GPU."
  echo
fi

# Activate Python virtual environment
if [[ -f "$HOME/.virtualenvs/magicapp/bin/activate" ]]; then
  echo "Activating Python virtual environment..."
  # shellcheck disable=SC1091
  source "$HOME/.virtualenvs/magicapp/bin/activate"
else
  echo "ERROR: Virtual environment not found at $HOME/.virtualenvs/magicapp"
  echo "Create it with: python -m venv ~/.virtualenvs/magicapp"
  exit 1
fi

# Check if training data exists
TRAINING_DATA="data/training/combined_training_balanced.jsonl"
if [[ ! -f "${TRAINING_DATA}" ]]; then
  echo "ERROR: Training data not found: ${TRAINING_DATA}"
  echo "Run: python scripts/prepare-balanced-dataset.py"
  exit 1
fi

echo
echo "Training data: ${TRAINING_DATA}"
wc -l "${TRAINING_DATA}"
echo

# Training hyperparameters (optimized for Llama 3.1 8B)
export BATCH_SIZE="${BATCH_SIZE:-2}"  # Reduced for 8B model
export GRADIENT_ACCUMULATION_STEPS="${GRADIENT_ACCUMULATION_STEPS:-8}"  # Increased to maintain effective batch=16
export MAX_SEQ_LENGTH="${MAX_SEQ_LENGTH:-675}"  # Default to 675 tokens (captures 75-80% of examples)
export WARMUP_STEPS="${WARMUP_STEPS:-100}"
export SAVE_STEPS="${SAVE_STEPS:-100}"
export LOGGING_STEPS="${LOGGING_STEPS:-20}"
export EVAL_GENERATE_INTERVAL_STEPS="${EVAL_GENERATE_INTERVAL_STEPS:-300}"

echo "Training Configuration:"
echo "  Base Model: models/llama-3.1-8b"
echo "  Batch Size: ${BATCH_SIZE}"
echo "  Gradient Accumulation Steps: ${GRADIENT_ACCUMULATION_STEPS}"
echo "  Effective Batch Size: $((BATCH_SIZE * GRADIENT_ACCUMULATION_STEPS))"
echo "  Max Sequence Length: ${MAX_SEQ_LENGTH} tokens"
echo "  Warmup Steps: ${WARMUP_STEPS}"
echo "  Save Every: ${SAVE_STEPS} steps"
echo "  Validation Every: ${LOGGING_STEPS} steps"
echo "  Generate Test Decks Every: ${EVAL_GENERATE_INTERVAL_STEPS} steps"
echo

# Create output directory
mkdir -p models/commander-llama-lora/checkpoints

# Print Intel GPU info if available
if command -v xpu-smi >/dev/null 2>&1; then
  echo "Intel GPU Information:"
  xpu-smi discovery | grep -E "(Device|Name|Memory)" || true
  echo
fi

echo "Starting training at $(date)..."
echo "Logs will be saved to: models/commander-llama-lora/training_optimized_*.log"
echo

# Run training
python scripts/train-commander-model-optimized.py

echo
echo "Training completed at $(date)!"
echo
echo "Next steps:"
echo "  1. Test the model: python scripts/test-trained-model-validated.py"
echo "  2. Check training logs: tail -100 models/commander-llama-lora/training_optimized_*.log"
echo "  3. Model saved to: models/commander-llama-lora/final"
