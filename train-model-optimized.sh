#!/usr/bin/env bash

set -euo pipefail

echo "============================================================"
echo "Commander AI Model Training - OPTIMIZED (10-15% faster)"
echo "============================================================"
echo
echo "Optimizations:"
echo "  - Batch size: 4 (4x larger, fewer gradient accumulation loops)"
echo "  - Gradient accumulation: 4 steps (down from 16)"
echo "  - Validation frequency: Every 20 steps (down from 10)"
echo "  - Expected speedup: ~2.5 hours saved on 21-hour training"
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

# Training feature toggles
USE_IPEX="${USE_IPEX:-0}"
GRADIENT_CHECKPOINTING="${GRADIENT_CHECKPOINTING:-1}"
export USE_IPEX
export GRADIENT_CHECKPOINTING

# Force Level Zero to use system memory for overflow (like Windows behavior)
export SYCL_PI_LEVEL_ZERO_USE_IMMEDIATE_COMMANDLISTS=1
export ZE_FLAT_DEVICE_HIERARCHY=COMPOSITE
export PYTORCH_XPU_ALLOC_CONF="expandable_segments:True,max_split_size_mb:512"

# Hugging Face datasets cache directory
export HF_DATASETS_CACHE="${HF_DATASETS_CACHE:-$(pwd)/data/.hf_cache}"

echo "Training options:"
if [[ "${USE_IPEX}" != "1" ]]; then
  echo "  USE_IPEX=${USE_IPEX} (default off; set USE_IPEX=1 to force Intel IPEX optimize)"
else
  echo "  USE_IPEX=${USE_IPEX}"
fi
echo "  GRADIENT_CHECKPOINTING=${GRADIENT_CHECKPOINTING}"
echo "  HF_DATASETS_CACHE=${HF_DATASETS_CACHE}"
echo

# Activate virtualenv if not already active
if [[ -z "${VIRTUAL_ENV:-}" ]]; then
  if [[ -f "${HOME}/.virtualenvs/magicapp/bin/activate" ]]; then
    echo "Activating virtualenv..."
    source "${HOME}/.virtualenvs/magicapp/bin/activate"
  fi
fi

# Ensure the virtualenv's shared libs take precedence so the XPU wheels
# can find the correct libur_loader shipped with the pip packages.
if [[ -n "${VIRTUAL_ENV:-}" ]]; then
  export LD_LIBRARY_PATH="${VIRTUAL_ENV}/lib:${LD_LIBRARY_PATH:-}"
fi

# Optional pre-processing step
RUN_PREP="${RUN_PREP:-0}"
INVENTORY_FILE="${INVENTORY_FILE:-data/training/inventory.json}"
RECENT_FILE="${RECENT_FILE:-data/training/recent_decks.jsonl}"

if [[ "${RUN_PREP}" == "1" ]]; then
  echo "Preparing training data with inventory/recent context..."
  python3 -u scripts/prepare-training-data.py \
    --inventory "${INVENTORY_FILE}" \
    --recent "${RECENT_FILE}"
  echo
fi

echo "Memory Management:"
echo "- Manual PyTorch training loop (no Trainer class)"
echo "- Direct XPU device control"
echo "- Checkpoints every 100 steps"
echo "- Aggressive garbage collection enabled"
echo "- OPTIMIZED: Batch size 4, validation every 20 steps"
echo

echo "Starting optimized training..."
echo "Expected time: ~18.5 hours on Intel Arc B50 Pro (2.5 hours faster than standard)"
echo "The script will save checkpoints every 100 steps"
echo "You can safely interrupt with Ctrl+C and resume later"
echo

echo "TIP: Run './scripts/monitor-memory.py' in another window to watch RAM usage"
echo

python3 -u scripts/train-commander-model-optimized.py

echo
echo "============================================================"
echo "Training session ended"
echo "============================================================"
