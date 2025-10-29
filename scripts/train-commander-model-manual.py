"""
Fine-tune Llama 3.1 8B for Commander/EDH deck building using LoRA.
MANUAL TRAINING LOOP - Direct XPU control without Transformers Trainer.

This script uses a manual PyTorch training loop for full XPU compatibility.
"""

import os
import sys
import json
import torch
import gc
from pathlib import Path
from datetime import datetime
from tqdm import tqdm
import math

from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    get_cosine_schedule_with_warmup
)
from peft import LoraConfig, get_peft_model, TaskType
from datasets import Dataset
from torch.utils.data import DataLoader
import logging

# Set memory limit
MAX_MEMORY_GB = 100
os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'max_split_size_mb:512'

# Paths
BASE_MODEL_PATH = "models/llama-3.1-8b"
TRAINING_DATA_PATH = "data/training/combined_training.jsonl"
OUTPUT_DIR = "models/commander-llama-lora"
CHECKPOINT_DIR = "models/commander-llama-lora/checkpoints"

# Training hyperparameters
LORA_RANK = 16
LORA_ALPHA = 32
LORA_DROPOUT = 0.05
LEARNING_RATE = 2e-4
NUM_EPOCHS = 3
BATCH_SIZE = 2  # Compromise: 2 instead of 1 or 4
GRADIENT_ACCUMULATION_STEPS = 8  # Keep effective batch size at 16 (2*8=16)
MAX_SEQ_LENGTH = 1024  # Reduced from 2048 to ease GPU memory pressure
WARMUP_STEPS = 100
SAVE_STEPS = 100
LOGGING_STEPS = 10

# Configure logging
log_file = f"models/commander-llama-lora/training_manual_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
os.makedirs("models/commander-llama-lora", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
logger.info(f"Logging to file: {log_file}")


def load_training_data(file_path):
    """Load training data from JSONL file."""
    logger.info(f"Loading training data from {file_path}...")
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            example = json.loads(line)
            data.append(example)
    logger.info(f"✓ Loaded {len(data):,} training examples")
    return data


def format_prompt(instruction, output=""):
    """Format training examples as instruction-following prompts."""
    if output:
        return f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

You are a Magic: The Gathering Commander/EDH deck building expert. You have deep knowledge of all Magic cards, their synergies, power levels, and competitive rankings.<|eot_id|><|start_header_id|>user<|end_header_id|>

{instruction}<|eot_id|><|start_header_id|>assistant<|end_header_id|>

{output}<|eot_id|><|end_of_text|>"""
    else:
        return f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

You are a Magic: The Gathering Commander/EDH deck building expert. You have deep knowledge of all Magic cards, their synergies, power levels, and competitive rankings.<|eot_id|><|start_header_id|>user<|end_header_id|>

{instruction}<|eot_id|><|start_header_id|>assistant<|end_header_id|>

"""


def collate_fn(batch):
    """Custom collate function that pads sequences to same length within batch."""
    # Find max length in this batch
    max_len = max(item['input_ids'].size(0) for item in batch)
    
    # Pad each sequence to max length in batch
    input_ids = []
    attention_mask = []
    labels = []
    
    for item in batch:
        seq_len = item['input_ids'].size(0)
        padding_len = max_len - seq_len
        
        # Pad input_ids (pad with 0 - PAD token)
        padded_input = torch.nn.functional.pad(item['input_ids'], (0, padding_len), value=0)
        input_ids.append(padded_input)
        
        # Pad attention_mask (pad with 0 - don't attend)
        padded_mask = torch.nn.functional.pad(item['attention_mask'], (0, padding_len), value=0)
        attention_mask.append(padded_mask)
        
        # Pad labels (pad with -100 - ignore in loss)
        padded_labels = torch.nn.functional.pad(item['labels'], (0, padding_len), value=-100)
        labels.append(padded_labels)
    
    return {
        'input_ids': torch.stack(input_ids),
        'attention_mask': torch.stack(attention_mask),
        'labels': torch.stack(labels)
    }


def save_checkpoint(model, optimizer, scheduler, step, epoch, output_dir):
    """Save model checkpoint."""
    checkpoint_path = os.path.join(output_dir, f"checkpoint-{step}")
    os.makedirs(checkpoint_path, exist_ok=True)
    
    # Save LoRA model
    model.save_pretrained(checkpoint_path)
    
    # Save optimizer and scheduler states
    torch.save({
        'optimizer_state_dict': optimizer.state_dict(),
        'scheduler_state_dict': scheduler.state_dict(),
        'step': step,
        'epoch': epoch
    }, os.path.join(checkpoint_path, 'training_state.pt'))
    
    logger.info(f"✓ Checkpoint saved: {checkpoint_path}")


def update_progress(step, max_steps, loss, lr, output_dir):
    """Update progress file."""
    progress_file = f"{output_dir}/training_progress.json"
    progress = {
        "global_step": step,
        "max_steps": max_steps,
        "epoch": step / (max_steps / NUM_EPOCHS),
        "loss": float(loss),
        "learning_rate": float(lr),
        "last_update": datetime.now().isoformat(),
        "progress_percent": round(100 * step / max_steps, 2) if max_steps else 0
    }
    
    with open(progress_file, 'w') as f:
        json.dump(progress, f, indent=2)


def main():
    logger.info("=" * 60)
    logger.info("Commander Deck Builder - Manual Training Loop")
    logger.info("=" * 60)
    logger.info(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Base model: {BASE_MODEL_PATH}")
    logger.info(f"Training data: {TRAINING_DATA_PATH}")
    logger.info(f"Output directory: {OUTPUT_DIR}")
    logger.info("")
    
    # Create output directories
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    
    # Check device availability
    device = "cpu"
    device_name = "CPU"
    
    try:
        import intel_extension_for_pytorch as ipex
        if torch.xpu.is_available():
            device = "xpu"
            device_name = torch.xpu.get_device_name(0)
            logger.info(f"✓ Intel XPU (Arc GPU) detected: {device_name}")
    except (ImportError, AttributeError):
        pass
    
    if device == "cpu" and torch.cuda.is_available():
        device = "cuda"
        device_name = torch.cuda.get_device_name(0)
    
    logger.info(f"Device: {device}")
    logger.info(f"Hardware: {device_name}")
    logger.info("")
    
    # Load tokenizer
    logger.info("Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_PATH)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
        tokenizer.pad_token_id = tokenizer.eos_token_id
    logger.info("✓ Tokenizer loaded")
    logger.info("")
    
    # Load and tokenize data
    training_data = load_training_data(TRAINING_DATA_PATH)
    num_training_examples = len(training_data)
    
    logger.info("Tokenizing dataset...")
    tokenized_data = []
    for example in tqdm(training_data, desc="Tokenizing"):
        text = format_prompt(example['instruction'], example['output'])
        encoded = tokenizer(
            text,
            truncation=True,
            max_length=MAX_SEQ_LENGTH,
            padding=False,  # Don't pad yet - will pad dynamically in batches
            return_tensors="pt"
        )
        
        tokenized_data.append({
            'input_ids': encoded['input_ids'].squeeze(0),
            'attention_mask': encoded['attention_mask'].squeeze(0),
            'labels': encoded['input_ids'].squeeze(0)
        })
    
    logger.info(f"✓ Tokenized {len(tokenized_data):,} examples")
    del training_data
    gc.collect()
    logger.info("")
    
    # Create DataLoader with XPU-compatible settings
    # Note: XPU doesn't support pin_memory or multiple workers well yet
    dataloader = DataLoader(
        tokenized_data,
        batch_size=BATCH_SIZE,
        shuffle=True,  # Shuffle data for better model generalization
        collate_fn=collate_fn,
        num_workers=0,  # XPU works better with single worker for now
        pin_memory=False  # Not supported well with XPU
    )
    
    # Load model
    logger.info("Loading base model...")
    dtype = torch.bfloat16 if device == "xpu" else (torch.float16 if device == "cuda" else torch.float32)
    
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL_PATH,
        torch_dtype=dtype,
        device_map=None,
        low_cpu_mem_usage=True,
        trust_remote_code=True
    )
    
    model.gradient_checkpointing_enable()
    model = model.to(device)
    logger.info("✓ Base model loaded and moved to device")
    logger.info("")
    
    # Configure LoRA
    logger.info("Configuring LoRA...")
    lora_config = LoraConfig(
        r=LORA_RANK,
        lora_alpha=LORA_ALPHA,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_dropout=LORA_DROPOUT,
        bias="none",
        task_type=TaskType.CAUSAL_LM
    )
    
    model = get_peft_model(model, lora_config)
    model.train()  # Set to training mode before ipex.optimize
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total_params = sum(p.numel() for p in model.parameters())
    
    logger.info("✓ LoRA configured and applied")
    logger.info(f"  Trainable parameters: {trainable_params:,} ({100*trainable_params/total_params:.2f}%)")
    logger.info("")
    
    # Setup optimizer and scheduler
    optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE)
    
    total_steps = (len(dataloader) // GRADIENT_ACCUMULATION_STEPS) * NUM_EPOCHS
    scheduler = get_cosine_schedule_with_warmup(
        optimizer,
        num_warmup_steps=WARMUP_STEPS,
        num_training_steps=total_steps
    )
    
    # Apply IPEX optimization for XPU training (Intel recommendation)
    if device == "xpu":
        logger.info("Applying IPEX optimization for XPU training...")
        try:
            model, optimizer = ipex.optimize(
                model,
                dtype=dtype,
                optimizer=optimizer,
                inplace=True
            )
            logger.info("✓ IPEX optimization applied")
        except Exception as e:
            logger.warning(f"⚠ IPEX optimization failed: {e}")
            logger.warning("  Continuing without ipex.optimize()")
    
    logger.info("")
    logger.info("Training configuration:")
    logger.info(f"  Epochs: {NUM_EPOCHS}")
    logger.info(f"  Batch size: {BATCH_SIZE}")
    logger.info(f"  Gradient accumulation: {GRADIENT_ACCUMULATION_STEPS}")
    logger.info(f"  Total steps: {total_steps:,}")
    logger.info(f"  Device: {device} ({device_name})")
    logger.info(f"  Dtype: {dtype}")
    logger.info("")
    
    # Training loop
    logger.info("=" * 60)
    logger.info("STARTING TRAINING")
    logger.info("=" * 60)
    logger.info(f"Training will save checkpoints every {SAVE_STEPS} steps")
    logger.info(f"Log file: {log_file}")
    logger.info("")
    
    model.train()
    global_step = 0
    running_loss = 0.0
    
    try:
        for epoch in range(NUM_EPOCHS):
            logger.info(f"Epoch {epoch + 1}/{NUM_EPOCHS}")
            
            progress_bar = tqdm(dataloader, desc=f"Epoch {epoch+1}")
            
            for batch_idx, batch in enumerate(progress_bar):
                # Move batch to device (non_blocking for async transfer)
                input_ids = batch['input_ids'].to(device, non_blocking=True)
                attention_mask = batch['attention_mask'].to(device, non_blocking=True)
                labels = batch['labels'].to(device, non_blocking=True)
                
                # Forward pass
                print(f"Processing batch {batch_idx}")
                outputs = model(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    labels=labels
                )
                
                loss = outputs.loss / GRADIENT_ACCUMULATION_STEPS
                loss.backward()
                
                # Only synchronize after gradient accumulation, not every batch
                running_loss += loss.item()
                
                # Update weights
                if (batch_idx + 1) % GRADIENT_ACCUMULATION_STEPS == 0:
                    optimizer.step()
                    scheduler.step()
                    optimizer.zero_grad()
                    
                    global_step += 1
                    avg_loss = running_loss
                    running_loss = 0.0
                    
                    # Update progress bar
                    progress_bar.set_postfix({
                        'loss': f'{avg_loss:.4f}',
                        'lr': f'{scheduler.get_last_lr()[0]:.2e}',
                        'step': global_step
                    })
                    
                    # Log progress
                    if global_step % LOGGING_STEPS == 0:
                        logger.info(f"Step {global_step}/{total_steps} | Loss: {avg_loss:.4f} | LR: {scheduler.get_last_lr()[0]:.2e}")
                        update_progress(global_step, total_steps, avg_loss, scheduler.get_last_lr()[0], OUTPUT_DIR)
                    
                    # Save checkpoint
                    if global_step % SAVE_STEPS == 0:
                        save_checkpoint(model, optimizer, scheduler, global_step, epoch, CHECKPOINT_DIR)
                        # Clear GPU cache after checkpoint to prevent memory fragmentation
                        gc.collect()
                        if device == "xpu" and hasattr(torch.xpu, 'empty_cache'):
                            torch.xpu.empty_cache()
                            torch.xpu.synchronize()  # Wait for all operations to complete
                    
                    # Periodic garbage collection for XPU stability (reduced frequency for speed)
                    elif global_step % 50 == 0:  # Every 50 steps (not at checkpoint steps)
                        gc.collect()
                        if device == "xpu" and hasattr(torch.xpu, 'empty_cache'):
                            torch.xpu.empty_cache()
                        elif device == "cuda":
                            torch.cuda.empty_cache()
            
            logger.info(f"✓ Epoch {epoch + 1} complete")
            logger.info("")
        
        # Save final model
        logger.info("Saving final model...")
        model.save_pretrained(OUTPUT_DIR)
        tokenizer.save_pretrained(OUTPUT_DIR)
        logger.info(f"✓ Model saved to {OUTPUT_DIR}")
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("TRAINING COMPLETE!")
        logger.info("=" * 60)
        
    except KeyboardInterrupt:
        logger.warning("Training interrupted by user")
        logger.info(f"Last checkpoint saved at step {global_step}")
    except Exception as e:
        logger.error(f"Training failed with error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise


if __name__ == "__main__":
    main()
