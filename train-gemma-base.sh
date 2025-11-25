#!/bin/bash
# Train Gemma 3 4B BASE model for Commander deck building
# Expected duration: 4-6 hours on Intel Arc B50

cd /home/social/magicapp

# Activate virtualenv
source ~/.virtualenvs/magicapp/bin/activate

# Set Intel XPU environment variables
export ACCELERATE_USE_XPU=1
export USE_XPU=1
export ONEAPI_DEVICE_SELECTOR=level_zero:*
export SYCL_PI_LEVEL_ZERO_USE_IMMEDIATE_COMMANDLISTS=1
export PYTORCH_XPU_ALLOC_CONF="expandable_segments:True,max_split_size_mb:512"

# Training parameters
export BATCH_SIZE=4
export GRADIENT_ACCUMULATION_STEPS=8
export MAX_SEQ_LENGTH=600

echo "========================================================================"
echo "Starting Gemma 3 4B BASE Training"
echo "========================================================================"
echo "Model: google/gemma-3-4b (base, not instruction-tuned)"
echo "Dataset: data/training/v3_structured_training.jsonl (23,405 examples)"
echo "Output: ./gemma-3-4b-base-commander-lora/"
echo "Expected time: 4-6 hours"
echo "========================================================================"
echo ""

# Run training
nohup python3 scripts/train-gemma-4b-arc.py > training_gemma_base.log 2>&1 &

TRAIN_PID=$!
echo "Training started with PID: $TRAIN_PID"
echo "Monitor with: tail -f training_gemma_base.log"
echo "GPU usage: watch -n 2 'sudo intel_gpu_top -J -s 200 | head -40'"
echo ""
