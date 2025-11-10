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
from datasets import load_dataset
from torch.utils.data import DataLoader
import logging

# Set memory limit
MAX_MEMORY_GB = 100
os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'max_split_size_mb:512'
os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')

# Paths
BASE_MODEL_PATH = "models/qwen2.5-3b"  # Qwen2.5-3B-Instruct (3B params, ~6GB VRAM)
TRAINING_DATA_PATH = "data/training/combined_training.jsonl"
HF_CACHE_DIR = "data/.hf_cache"
OUTPUT_DIR = "models/commander-llama-lora"
CHECKPOINT_DIR = "models/commander-llama-lora/checkpoints"

# Training hyperparameters (environment overrides allowed for quick tuning)
LORA_RANK = 16
LORA_ALPHA = 32
LORA_DROPOUT = 0.05
LEARNING_RATE = 2e-4
NUM_EPOCHS = 3

_DEFAULT_BATCH_SIZE = 1  # Keep micro-batch tiny for Arc VRAM stability
_DEFAULT_GRAD_ACCUM_STEPS = 16  # Effective batch size ~16 (1*16)
_DEFAULT_MAX_SEQ_LEN = 384  # Further trimmed to lower activation memory budget

BATCH_SIZE = int(os.getenv("BATCH_SIZE", _DEFAULT_BATCH_SIZE))
GRADIENT_ACCUMULATION_STEPS = int(os.getenv("GRADIENT_ACCUMULATION_STEPS", _DEFAULT_GRAD_ACCUM_STEPS))
MAX_SEQ_LENGTH = int(os.getenv("MAX_SEQ_LENGTH", _DEFAULT_MAX_SEQ_LEN))

WARMUP_STEPS = int(os.getenv("WARMUP_STEPS", "100"))
SAVE_STEPS = int(os.getenv("SAVE_STEPS", "100"))
LOGGING_STEPS = int(os.getenv("LOGGING_STEPS", "10"))
EVAL_GENERATE_INTERVAL_STEPS = int(os.getenv("EVAL_GENERATE_INTERVAL_STEPS", "300"))  # Lightweight generation check cadence

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


def make_collate_fn(pad_token_id: int):
    """Create a collate_fn that pads sequences using tokenizer.pad_token_id."""
    def collate_fn(batch):
        # Ensure tensors
        def to_tensor(x):
            return x if torch.is_tensor(x) else torch.tensor(x, dtype=torch.long)

        batch = [{k: to_tensor(v) for k, v in item.items()} for item in batch]
        max_len = max(item['input_ids'].size(0) for item in batch)

        input_ids, attention_mask, labels = [], [], []
        for item in batch:
            seq = item['input_ids']
            mask = item.get('attention_mask', torch.ones_like(seq))
            lab = item.get('labels', seq.clone())
            padding_len = max_len - seq.size(0)

            input_ids.append(torch.nn.functional.pad(seq, (0, padding_len), value=pad_token_id))
            attention_mask.append(torch.nn.functional.pad(mask, (0, padding_len), value=0))
            labels.append(torch.nn.functional.pad(lab, (0, padding_len), value=-100))

        return {
            'input_ids': torch.stack(input_ids),
            'attention_mask': torch.stack(attention_mask),
            'labels': torch.stack(labels)
        }

    return collate_fn


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
    ipex = None
    
    try:
        import intel_extension_for_pytorch as ipex  # type: ignore
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
    use_ipex = os.getenv("USE_IPEX", "0") == "1"
    if device == "xpu":
        if use_ipex:
            logger.info("Intel IPEX optimizations requested (USE_IPEX=1)")
        else:
            logger.info("Intel IPEX optimizations disabled (USE_IPEX!=1)")
    logger.info("")
    
    # Load tokenizer
    logger.info("Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_PATH)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
        tokenizer.pad_token_id = tokenizer.eos_token_id
    logger.info("✓ Tokenizer loaded")
    logger.info("")
    
    # Load dataset from JSONL (Arrow, memory-mapped)
    logger.info("Loading dataset from JSONL (Arrow, memory-mapped)...")
    os.makedirs(HF_CACHE_DIR, exist_ok=True)
    try:
        # Prefer enabling caching when available; ignore if not supported on this version
        from datasets import enable_caching  # type: ignore
        enable_caching()
    except Exception:
        pass
    raw_dataset = load_dataset(
        "json",
        data_files=TRAINING_DATA_PATH,
        split="train",
        cache_dir=HF_CACHE_DIR
    )
    # Create a small validation split
    split = raw_dataset.train_test_split(test_size=0.02, seed=42)
    train_raw = split["train"]
    val_raw = split["test"]
    num_training_examples = len(train_raw)
    logger.info(f"✓ Dataset loaded with {len(raw_dataset):,} examples | train={len(train_raw):,} val={len(val_raw):,}")
    logger.info("")

    # Batched tokenization with on-disk caching
    logger.info("Tokenizing dataset with on-disk caching (this may take a while)...")
    def batch_preprocess(examples):
        texts = [format_prompt(i, o) for i, o in zip(examples['instruction'], examples['output'])]
        enc = tokenizer(
            texts,
            truncation=True,
            max_length=MAX_SEQ_LENGTH,
            padding=False,
            return_attention_mask=True
        )
        enc['labels'] = enc['input_ids'].copy()
        return enc

    tokenized_train = train_raw.map(
        batch_preprocess,
        batched=True,
        remove_columns=train_raw.column_names,
        desc="Tokenizing",
        num_proc=1,
        load_from_cache_file=True,
        keep_in_memory=False,
        writer_batch_size=1000
    )
    tokenized_val = val_raw.map(
        batch_preprocess,
        batched=True,
        remove_columns=val_raw.column_names,
        desc="Tokenizing (val)",
        num_proc=1,
        load_from_cache_file=True,
        keep_in_memory=False,
        writer_batch_size=1000
    )
    del raw_dataset, train_raw, val_raw
    gc.collect()
    logger.info("✓ Tokenization complete")
    logger.info("")

    # Create DataLoader with XPU-compatible settings
    dataloader = DataLoader(
        tokenized_train,
        batch_size=BATCH_SIZE,
        shuffle=True,
        collate_fn=make_collate_fn(tokenizer.pad_token_id),
        num_workers=0,
        pin_memory=False
    )
    val_dataloader = DataLoader(
        tokenized_val,
        batch_size=max(1, BATCH_SIZE),
        shuffle=False,
        collate_fn=make_collate_fn(tokenizer.pad_token_id),
        num_workers=0,
        pin_memory=False
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
    
    # Toggle gradient checkpointing via env (default on)
    if os.getenv("GRADIENT_CHECKPOINTING", "1") == "1":
        model.gradient_checkpointing_enable()
        try:
            if hasattr(model, 'config'):
                model.config.use_cache = False
        except Exception:
            pass
    else:
        try:
            model.gradient_checkpointing_disable()
        except Exception:
            pass
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
        if use_ipex:
            if ipex is None:
                logger.warning("⚠ USE_IPEX=1 but intel-extension-for-pytorch is not available; skipping optimization")
            else:
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
        else:
            logger.info("Skipping IPEX optimization (USE_IPEX!=1)")
    
    logger.info("")
    logger.info("Training configuration:")
    logger.info(f"  Epochs: {NUM_EPOCHS}")
    logger.info(f"  Batch size: {BATCH_SIZE}")
    logger.info(f"  Gradient accumulation: {GRADIENT_ACCUMULATION_STEPS}")
    logger.info(f"  Max sequence length: {MAX_SEQ_LENGTH}")
    logger.info(f"  Effective batch (approx): {BATCH_SIZE * GRADIENT_ACCUMULATION_STEPS}")
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
                
                # Forward pass with autocast for memory reduction
                if device in ("xpu", "cuda"):
                    with torch.autocast(device_type=("xpu" if device == "xpu" else "cuda"), dtype=dtype):
                        outputs = model(
                            input_ids=input_ids,
                            attention_mask=attention_mask,
                            labels=labels
                        )
                else:
                    outputs = model(
                        input_ids=input_ids,
                        attention_mask=attention_mask,
                        labels=labels
                    )
                
                loss = outputs.loss / GRADIENT_ACCUMULATION_STEPS
                # Optional gradient clipping for stability
                loss.backward()
                
                # Only synchronize after gradient accumulation, not every batch
                running_loss += loss.item()
                
                # Update weights
                if (batch_idx + 1) % GRADIENT_ACCUMULATION_STEPS == 0:
                    # Clip gradients to avoid spikes on XPU/CUDA
                    try:
                        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                    except Exception:
                        pass
                    optimizer.step()
                    scheduler.step()
                    optimizer.zero_grad(set_to_none=True)
                    
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
                        
                        # Quick validation loss on a few batches
                        model.eval()
                        with torch.no_grad():
                            val_losses = []
                            for vi, vbatch in enumerate(val_dataloader):
                                if vi >= 5:
                                    break
                                v_input_ids = vbatch['input_ids'].to(device, non_blocking=True)
                                v_attention_mask = vbatch['attention_mask'].to(device, non_blocking=True)
                                v_labels = vbatch['labels'].to(device, non_blocking=True)
                                if device in ("xpu", "cuda"):
                                    with torch.autocast(device_type=("xpu" if device == "xpu" else "cuda"), dtype=dtype):
                                        v_outputs = model(input_ids=v_input_ids, attention_mask=v_attention_mask, labels=v_labels)
                                else:
                                    v_outputs = model(input_ids=v_input_ids, attention_mask=v_attention_mask, labels=v_labels)
                                val_losses.append(v_outputs.loss.item())
                        if val_losses:
                            mean_vloss = sum(val_losses)/len(val_losses)
                            logger.info(f"Validation loss (sampled): {mean_vloss:.4f}")
                        model.train()
                    
                    # Save checkpoint
                    if global_step % SAVE_STEPS == 0:
                        save_checkpoint(model, optimizer, scheduler, global_step, epoch, CHECKPOINT_DIR)
                        # Clear GPU cache after checkpoint to prevent memory fragmentation
                        gc.collect()
                        if device == "xpu" and hasattr(torch.xpu, 'empty_cache'):
                            torch.xpu.empty_cache()
                            torch.xpu.synchronize()  # Wait for all operations to complete
                        # Optional lightweight generation + structural check
                        if global_step % EVAL_GENERATE_INTERVAL_STEPS == 0:
                            try:
                                model.eval()
                                from math import ceil
                                # Simple fixed instruction to probe output quality
                                probe_instruction = "Build a Commander/EDH deck with Atraxa, Praetors' Voice as the commander. Theme: midrange. Power level: 7/10."
                                prompt = format_prompt(probe_instruction, "")
                                enc = tokenizer(prompt, return_tensors="pt")
                                enc = {k: v.to(device) for k, v in enc.items()}
                                gen_kwargs = dict(
                                    max_new_tokens=300,
                                    temperature=0.7,
                                    top_p=0.9,
                                    do_sample=True,
                                    pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
                                )
                                if device in ("xpu", "cuda"):
                                    with torch.autocast(device_type=("xpu" if device == "xpu" else "cuda"), dtype=dtype):
                                        out = model.generate(**enc, **gen_kwargs)
                                else:
                                    out = model.generate(**enc, **gen_kwargs)
                                text = tokenizer.decode(out[0], skip_special_tokens=True)

                                # Structural checks
                                def check_deck_structure(t):
                                    metrics = {
                                        'has_commander_section': '## Commander' in t,
                                        'has_decklist_section': '## Decklist' in t,
                                        'approx_card_lines': 0,
                                        'approx_total_qty': 0,
                                    }
                                    total_qty = 0
                                    lines = [ln.strip() for ln in t.splitlines() if ln.strip()]
                                    for ln in lines:
                                        if 'x ' in ln:
                                            # crude parse like "2x Card Name (Category)"
                                            try:
                                                q = ln.split('x', 1)[0].strip()
                                                q = int(''.join(ch for ch in q if ch.isdigit()) or '0')
                                                if q > 0:
                                                    total_qty += q
                                                    metrics['approx_card_lines'] += 1
                                            except Exception:
                                                pass
                                    metrics['approx_total_qty'] = total_qty
                                    return metrics

                                metrics = check_deck_structure(text)
                                logger.info(f"Structural check: {metrics}")
                            except Exception as e:
                                logger.warning(f"Generation check failed: {e}")
                            finally:
                                model.train()
                    
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
        if "UR_RESULT_ERROR_DEVICE_LOST" in str(e) and device == "xpu":
            if use_ipex:
                logger.error("Detected Level Zero device loss while IPEX was enabled. Re-run with USE_IPEX=0 to disable IPEX optimizations.")
            else:
                logger.error("Detected Level Zero device loss. Consider lowering GRADIENT_ACCUMULATION_STEPS or MAX_SEQ_LENGTH.")
        raise


if __name__ == "__main__":
    main()
