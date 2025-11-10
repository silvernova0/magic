#!/usr/bin/env python3
"""
Optimized Commander AI Model Training - Manual Loop (XPU Compatible)
Optimizations:
- Batch size 4 (75% fewer gradient accumulation loops)
- Validation every 20 steps (50% fewer validation calls)
- Expected speedup: 10-15% (~2.5 hours saved on 21-hour training)
"""

import os
import sys
import json
import logging
import gc
from datetime import datetime
from typing import Dict, Any
from pathlib import Path

import torch
from torch.utils.data import DataLoader
from datasets import load_dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    get_linear_schedule_with_warmup,
)
from peft import (
    get_peft_model,
    LoraConfig,
    TaskType,
    PeftModel,
)
from tqdm import tqdm

os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'max_split_size_mb:512'
os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')

# Paths
BASE_MODEL_PATH = "models/qwen2.5-3b"  # Qwen2.5-3B-Instruct (3B params, fits in VRAM)
TRAINING_DATA_PATH = "data/training/combined_training_v2_50k.jsonl"  # V2 DATASET: 43,631 examples (reduced for memory)
HF_CACHE_DIR = "data/.hf_cache"
OUTPUT_DIR = "models/commander-llama-lora"
CHECKPOINT_DIR = "models/commander-llama-lora/checkpoints"

# Training hyperparameters (OPTIMIZED for faster training)
LORA_RANK = 16
LORA_ALPHA = 32
LORA_DROPOUT = 0.05
LEARNING_RATE = 2e-4
NUM_EPOCHS = 3

# OPTIMIZED DEFAULTS - 10-15% faster training
_DEFAULT_BATCH_SIZE = 4  # Quadrupled from 1 (fewer gradient accumulation loops)
_DEFAULT_GRAD_ACCUM_STEPS = 4  # Reduced from 16 (same effective batch = 16)
_DEFAULT_MAX_SEQ_LEN = 384  # Unchanged, proven stable

BATCH_SIZE = int(os.getenv("BATCH_SIZE", _DEFAULT_BATCH_SIZE))
GRADIENT_ACCUMULATION_STEPS = int(os.getenv("GRADIENT_ACCUMULATION_STEPS", _DEFAULT_GRAD_ACCUM_STEPS))
MAX_SEQ_LENGTH = int(os.getenv("MAX_SEQ_LENGTH", _DEFAULT_MAX_SEQ_LEN))

WARMUP_STEPS = int(os.getenv("WARMUP_STEPS", "100"))
SAVE_STEPS = int(os.getenv("SAVE_STEPS", "100"))
LOGGING_STEPS = int(os.getenv("LOGGING_STEPS", "20"))  # Halved from 10 (fewer validation calls)
EVAL_GENERATE_INTERVAL_STEPS = int(os.getenv("EVAL_GENERATE_INTERVAL_STEPS", "300"))

# Configure logging
log_file = f"models/commander-llama-lora/training_optimized_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
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
            data.append(json.loads(line))
    logger.info(f"Loaded {len(data)} training examples")
    return data


def format_prompt(example: Dict[str, Any]) -> str:
    """Format example into instruction prompt."""
    instruction = example.get('instruction', '')
    output = example.get('output', '')
    return f"{instruction}\n\n{output}"


def tokenize_function(examples, tokenizer):
    """Tokenize examples with proper truncation."""
    texts = [format_prompt(ex) for ex in examples]
    return tokenizer(
        texts,
        truncation=True,
        max_length=MAX_SEQ_LENGTH,
        padding='max_length',
        return_tensors='pt'
    )


def collate_fn(batch):
    """Collate batch for DataLoader."""
    input_ids = torch.stack([torch.tensor(item['input_ids']) for item in batch])
    attention_mask = torch.stack([torch.tensor(item['attention_mask']) for item in batch])
    return {
        'input_ids': input_ids,
        'attention_mask': attention_mask,
        'labels': input_ids.clone()
    }


def compute_validation_loss(model, val_dataloader, device, max_batches=10):
    """Compute validation loss on a sample of validation data."""
    model.eval()
    total_loss = 0
    num_batches = 0
    
    with torch.no_grad():
        for batch in val_dataloader:
            if num_batches >= max_batches:
                break
            
            input_ids = batch['input_ids'].to(device)
            attention_mask = batch['attention_mask'].to(device)
            labels = batch['labels'].to(device)
            
            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                labels=labels
            )
            
            total_loss += outputs.loss.item()
            num_batches += 1
    
    model.train()
    return total_loss / num_batches if num_batches > 0 else 0


def save_checkpoint(model, optimizer, scheduler, global_step, epoch, output_dir):
    """Save training checkpoint."""
    checkpoint_path = os.path.join(output_dir, f"checkpoint-{global_step}")
    os.makedirs(checkpoint_path, exist_ok=True)
    
    # Save LoRA adapters
    model.save_pretrained(checkpoint_path)
    
    # Save optimizer and scheduler states
    torch.save({
        'optimizer_state_dict': optimizer.state_dict(),
        'scheduler_state_dict': scheduler.state_dict(),
        'global_step': global_step,
        'epoch': epoch,
    }, os.path.join(checkpoint_path, 'training_state.pt'))
    
    logger.info(f"✓ Checkpoint saved: {checkpoint_path}")


def check_generated_structure(text: str) -> Dict[str, Any]:
    """Quick structural check on generated text."""
    has_commander = "Commander:" in text or "COMMANDER:" in text
    has_decklist = "Decklist:" in text or "DECKLIST:" in text or "Deck:" in text
    
    lines = text.split('\n')
    card_lines = [l for l in lines if l.strip() and any(c.isdigit() for c in l[:5])]
    approx_cards = len(card_lines)
    
    total_qty = 0
    for line in card_lines:
        parts = line.strip().split(None, 1)
        if parts and parts[0].isdigit():
            total_qty += int(parts[0])
    
    return {
        'has_commander_section': has_commander,
        'has_decklist_section': has_decklist,
        'approx_card_lines': approx_cards,
        'approx_total_qty': total_qty,
    }


def main():
    # Check for Intel IPEX optimization (optional)
    use_ipex = os.getenv("USE_IPEX", "0") == "1"
    
    try:
        import intel_extension_for_pytorch as ipex
        ipex_available = True
        logger.info(f"Intel Extension for PyTorch version: {ipex.__version__}")
    except ImportError:
        ipex_available = False
        logger.info("Intel Extension for PyTorch not available")
    
    # Device setup
    if torch.xpu.is_available():
        device = torch.device("xpu")
        logger.info(f"Using Intel XPU device: {torch.xpu.get_device_name(0)}")
        logger.info(f"XPU device count: {torch.xpu.device_count()}")
    else:
        device = torch.device("cpu")
        logger.warning("XPU not available, falling back to CPU")
    
    logger.info(f"Using device: {device}")
    logger.info(f"Base model: {BASE_MODEL_PATH}")
    logger.info(f"Training data: {TRAINING_DATA_PATH}")
    logger.info(f"Output directory: {OUTPUT_DIR}")
    logger.info("")
    logger.info("=" * 60)
    logger.info("OPTIMIZED TRAINING CONFIGURATION")
    logger.info("=" * 60)
    logger.info(f"Batch size: {BATCH_SIZE} (4x larger than standard)")
    logger.info(f"Gradient accumulation steps: {GRADIENT_ACCUMULATION_STEPS}")
    logger.info(f"Effective batch size: {BATCH_SIZE * GRADIENT_ACCUMULATION_STEPS}")
    logger.info(f"Max sequence length: {MAX_SEQ_LENGTH}")
    logger.info(f"Learning rate: {LEARNING_RATE}")
    logger.info(f"LoRA rank: {LORA_RANK}, alpha: {LORA_ALPHA}, dropout: {LORA_DROPOUT}")
    logger.info(f"Number of epochs: {NUM_EPOCHS}")
    logger.info(f"Logging steps: {LOGGING_STEPS} (validation every 20 steps)")
    logger.info(f"Save steps: {SAVE_STEPS}")
    logger.info(f"IPEX optimization: {'ENABLED' if use_ipex and ipex_available else 'DISABLED'}")
    logger.info("=" * 60)
    logger.info("")
    logger.info("Expected speedup: 10-15% faster (~2.5 hours saved)")
    logger.info("")
    
    # Load tokenizer
    logger.info("Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(
        BASE_MODEL_PATH,
        trust_remote_code=True,
        cache_dir=HF_CACHE_DIR
    )
    
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
        logger.info("Set pad_token to eos_token")
    
    # Load and prepare dataset
    logger.info("Loading dataset...")
    raw_data = load_training_data(TRAINING_DATA_PATH)
    
    # Split into train/validation (95/5)
    split_idx = int(len(raw_data) * 0.95)
    train_data = raw_data[:split_idx]
    val_data = raw_data[split_idx:]
    
    logger.info(f"Training examples: {len(train_data)}")
    logger.info(f"Validation examples: {len(val_data)}")
    
    # Tokenize datasets
    logger.info("Tokenizing datasets...")
    
    def tokenize_batch(batch):
        texts = [format_prompt(ex) for ex in batch]
        return tokenizer(
            texts,
            truncation=True,
            max_length=MAX_SEQ_LENGTH,
            padding='max_length',
            return_tensors=None  # Return lists
        )
    
    # Create tokenized datasets
    train_dataset = []
    for example in tqdm(train_data, desc="Tokenizing training data"):
        tokens = tokenizer(
            format_prompt(example),
            truncation=True,
            max_length=MAX_SEQ_LENGTH,
            padding='max_length',
            return_tensors=None
        )
        train_dataset.append(tokens)
    
    val_dataset = []
    for example in tqdm(val_data, desc="Tokenizing validation data"):
        tokens = tokenizer(
            format_prompt(example),
            truncation=True,
            max_length=MAX_SEQ_LENGTH,
            padding='max_length',
            return_tensors=None
        )
        val_dataset.append(tokens)
    
    # Create DataLoaders
    train_dataloader = DataLoader(
        train_dataset,
        batch_size=BATCH_SIZE,
        shuffle=True,
        collate_fn=collate_fn,
        num_workers=0  # Keep 0 for XPU stability
    )
    
    val_dataloader = DataLoader(
        val_dataset,
        batch_size=BATCH_SIZE,
        shuffle=False,
        collate_fn=collate_fn,
        num_workers=0
    )
    
    # Load base model
    logger.info("Loading base model...")
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL_PATH,
        trust_remote_code=True,
        torch_dtype=torch.bfloat16,
        cache_dir=HF_CACHE_DIR,
        low_cpu_mem_usage=True,
    )
    
    # Configure LoRA
    logger.info("Configuring LoRA...")
    peft_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        inference_mode=False,
        r=LORA_RANK,
        lora_alpha=LORA_ALPHA,
        lora_dropout=LORA_DROPOUT,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    )
    
    model = get_peft_model(model, peft_config)
    model.print_trainable_parameters()
    
    # Enable gradient checkpointing
    if os.getenv("GRADIENT_CHECKPOINTING", "1") == "1":
        model.enable_input_require_grads()
        model.gradient_checkpointing_enable()
        logger.info("Gradient checkpointing enabled")
    
    # Move model to device
    model = model.to(device)
    
    # Apply IPEX optimization if enabled
    if use_ipex and ipex_available:
        logger.info("Applying IPEX optimization...")
        model = ipex.optimize(model, dtype=torch.bfloat16)
    
    # Setup optimizer and scheduler
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=LEARNING_RATE,
        weight_decay=0.01
    )
    
    total_steps = len(train_dataloader) * NUM_EPOCHS // GRADIENT_ACCUMULATION_STEPS
    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=WARMUP_STEPS,
        num_training_steps=total_steps
    )
    
    logger.info(f"Total training steps: {total_steps}")
    logger.info(f"Warmup steps: {WARMUP_STEPS}")
    
    # Training loop
    logger.info("")
    logger.info("=" * 60)
    logger.info("STARTING TRAINING")
    logger.info("=" * 60)
    logger.info("Training will save checkpoints every 100 steps")
    logger.info(f"Log file: {log_file}")
    logger.info("")
    
    global_step = 0
    model.train()
    
    # Training progress tracking
    progress_file = os.path.join(OUTPUT_DIR, "training_progress.json")
    
    for epoch in range(NUM_EPOCHS):
        logger.info(f"Epoch {epoch + 1}/{NUM_EPOCHS}")
        epoch_loss = 0
        optimizer.zero_grad()
        
        progress_bar = tqdm(
            train_dataloader,
            desc=f"Epoch {epoch + 1}",
            total=len(train_dataloader)
        )
        
        for step, batch in enumerate(progress_bar):
            input_ids = batch['input_ids'].to(device)
            attention_mask = batch['attention_mask'].to(device)
            labels = batch['labels'].to(device)
            
            # Forward pass
            with torch.amp.autocast(device_type='xpu' if device.type == 'xpu' else 'cpu', dtype=torch.bfloat16):
                outputs = model(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    labels=labels
                )
                loss = outputs.loss / GRADIENT_ACCUMULATION_STEPS
            
            # Backward pass
            loss.backward()
            epoch_loss += loss.item()
            
            # Update weights after gradient accumulation
            if (step + 1) % GRADIENT_ACCUMULATION_STEPS == 0:
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()
                scheduler.step()
                optimizer.zero_grad()
                global_step += 1
                
                # Update progress bar
                progress_bar.set_postfix({
                    'loss': f"{loss.item() * GRADIENT_ACCUMULATION_STEPS:.4f}",
                    'lr': f"{scheduler.get_last_lr()[0]:.2e}",
                    'step': global_step
                })
                
                # Logging and validation
                if global_step % LOGGING_STEPS == 0:
                    current_loss = loss.item() * GRADIENT_ACCUMULATION_STEPS
                    current_lr = scheduler.get_last_lr()[0]
                    
                    logger.info(f"Step {global_step}/{total_steps} | Loss: {current_loss:.4f} | LR: {current_lr:.2e}")
                    
                    # Validation
                    val_loss = compute_validation_loss(model, val_dataloader, device)
                    logger.info(f"Validation loss (sampled): {val_loss:.4f}")
                    
                    # Save progress
                    progress_data = {
                        "global_step": global_step,
                        "max_steps": total_steps,
                        "epoch": epoch + (step + 1) / len(train_dataloader),
                        "loss": current_loss,
                        "learning_rate": current_lr,
                        "last_update": datetime.now().isoformat(),
                        "progress_percent": round(global_step / total_steps * 100, 2)
                    }
                    with open(progress_file, 'w') as f:
                        json.dump(progress_data, f, indent=2)
                
                # Save checkpoint
                if global_step % SAVE_STEPS == 0:
                    save_checkpoint(model, optimizer, scheduler, global_step, epoch, CHECKPOINT_DIR)
                
                # Periodic generation check (structural validation)
                if global_step % EVAL_GENERATE_INTERVAL_STEPS == 0:
                    model.eval()
                    with torch.no_grad():
                        test_prompt = "Build a Commander deck with Atraxa, Praetors' Voice as the commander."
                        inputs = tokenizer(test_prompt, return_tensors='pt').to(device)
                        outputs = model.generate(
                            **inputs,
                            max_new_tokens=512,
                            temperature=0.7,
                            do_sample=True,
                            pad_token_id=tokenizer.pad_token_id
                        )
                        generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
                        structure_check = check_generated_structure(generated_text)
                        logger.info(f"Structural check: {structure_check}")
                    model.train()
                
                # Memory cleanup
                if global_step % 50 == 0:
                    gc.collect()
                    if device.type == 'xpu':
                        torch.xpu.empty_cache()
        
        logger.info(f"Epoch {epoch + 1} completed. Average loss: {epoch_loss / len(train_dataloader):.4f}")
    
    # Save final model
    logger.info("Training complete! Saving final model...")
    final_model_path = os.path.join(OUTPUT_DIR, "final")
    model.save_pretrained(final_model_path)
    tokenizer.save_pretrained(final_model_path)
    logger.info(f"Final model saved to: {final_model_path}")
    
    logger.info("")
    logger.info("=" * 60)
    logger.info("TRAINING COMPLETED SUCCESSFULLY")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
