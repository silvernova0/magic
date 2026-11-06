"""
Manual LoRA fine-tuning with on-disk HF datasets (memory-mapped Arrow).

Optimized for Intel Arc (XPU) and CUDA:
- Loads JSONL with datasets.load_dataset (no full in-RAM load)
- Batched tokenization cached to disk
- Dynamic padding in collate_fn with tokenizer.pad_token_id
- Autocast (bf16 on XPU, fp16 on CUDA) to reduce memory
- Conservative defaults to avoid system lockups
"""

import os
import json
import torch
import gc
from datetime import datetime
from tqdm import tqdm

from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    get_cosine_schedule_with_warmup,
)
from peft import LoraConfig, get_peft_model, TaskType
from datasets import load_dataset
from torch.utils.data import DataLoader
import logging

# Environment and caching
os.environ.setdefault('PYTORCH_CUDA_ALLOC_CONF', 'max_split_size_mb:512')
os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')

# Paths
BASE_MODEL_PATH = "models/llama-3.1-8b"
TRAINING_DATA_PATH = "data/training/combined_training.jsonl"
OUTPUT_DIR = "models/commander-llama-lora"
CHECKPOINT_DIR = "models/commander-llama-lora/checkpoints"
HF_CACHE_DIR = "data/.hf_cache"

# Training hyperparameters (start conservative; increase after stability)
LORA_RANK = 16
LORA_ALPHA = 32
LORA_DROPOUT = 0.05
LEARNING_RATE = 2e-4
NUM_EPOCHS = 3
BATCH_SIZE = 1  # Start at 1 to avoid lockups; try 2 later
GRADIENT_ACCUMULATION_STEPS = 16  # Effective batch = 16
MAX_SEQ_LENGTH = 1024  # Lower than 2048 to reduce memory
WARMUP_STEPS = 100
SAVE_STEPS = 100
LOGGING_STEPS = 10

# Logging
os.makedirs(OUTPUT_DIR, exist_ok=True)
log_file = f"{OUTPUT_DIR}/training_manual_mmap_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)
logger.info(f"Logging to file: {log_file}")


def format_prompt(instruction, output=""):
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
    """Pad to max length in batch using provided pad_token_id."""
    def collate_fn(batch):
        # Items may be lists of ints; convert to tensors
        def to_tensor(x):
            return x if torch.is_tensor(x) else torch.tensor(x, dtype=torch.long)

        batch = [{k: to_tensor(v) for k, v in item.items()} for item in batch]
        max_len = max(item['input_ids'].size(0) for item in batch)

        input_ids, attention_mask, labels = [], [], []
        for item in batch:
            seq = item['input_ids']
            mask = item.get('attention_mask', torch.ones_like(seq))
            lab = item.get('labels', seq.clone())
            pad = max_len - seq.size(0)
            input_ids.append(torch.nn.functional.pad(seq, (0, pad), value=pad_token_id))
            attention_mask.append(torch.nn.functional.pad(mask, (0, pad), value=0))
            labels.append(torch.nn.functional.pad(lab, (0, pad), value=-100))
        return {
            'input_ids': torch.stack(input_ids),
            'attention_mask': torch.stack(attention_mask),
            'labels': torch.stack(labels),
        }

    return collate_fn


def save_checkpoint(model, optimizer, scheduler, step, epoch, output_dir):
    path = os.path.join(output_dir, f"checkpoint-{step}")
    os.makedirs(path, exist_ok=True)
    model.save_pretrained(path)
    torch.save({
        'optimizer_state_dict': optimizer.state_dict(),
        'scheduler_state_dict': scheduler.state_dict(),
        'step': step,
        'epoch': epoch,
    }, os.path.join(path, 'training_state.pt'))
    logger.info(f"✓ Checkpoint saved: {path}")


def update_progress(step, max_steps, loss, lr, output_dir):
    progress_file = f"{output_dir}/training_progress.json"
    progress = {
        "global_step": step,
        "max_steps": max_steps,
        "epoch": step / (max_steps / NUM_EPOCHS) if max_steps else 0,
        "loss": float(loss),
        "learning_rate": float(lr),
        "last_update": datetime.now().isoformat(),
        "progress_percent": round(100 * step / max_steps, 2) if max_steps else 0,
    }
    with open(progress_file, 'w') as f:
        json.dump(progress, f, indent=2)


def main():
    logger.info("=" * 60)
    logger.info("Commander Deck Builder - Manual Training (MMAP)")
    logger.info("=" * 60)
    logger.info(f"Base model: {BASE_MODEL_PATH}")
    logger.info(f"Training data: {TRAINING_DATA_PATH}")
    logger.info(f"Output directory: {OUTPUT_DIR}")
    logger.info("")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)

    # Detect device
    device = "cpu"
    device_name = "CPU"
    try:
        import intel_extension_for_pytorch as ipex  # noqa: F401
        if hasattr(torch, 'xpu') and torch.xpu.is_available():
            device = "xpu"
            device_name = torch.xpu.get_device_name(0)
            logger.info(f"✓ Intel XPU detected: {device_name}")
    except Exception:
        pass

    if device == "cpu" and torch.cuda.is_available():
        device = "cuda"
        device_name = torch.cuda.get_device_name(0)

    logger.info(f"Device: {device} ({device_name})")
    if device == "cuda":
        logger.info(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")
    logger.info("")

    # Tokenizer
    logger.info("Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_PATH)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
        tokenizer.pad_token_id = tokenizer.eos_token_id
    logger.info("✓ Tokenizer loaded")

    # Dataset (memory-mapped)
    logger.info("Loading dataset from JSONL (Arrow, memory-mapped)...")
    os.makedirs(HF_CACHE_DIR, exist_ok=True)
    try:
        from datasets import enable_caching  # type: ignore
        enable_caching()
    except Exception:
        pass
    raw_dataset = load_dataset(
        "json",
        data_files=TRAINING_DATA_PATH,
        split="train",
        cache_dir=HF_CACHE_DIR,
    )
    num_training_examples = len(raw_dataset)
    logger.info(f"✓ Dataset loaded with {num_training_examples:,} examples")

    # Batched tokenization with on-disk caching
    logger.info("Tokenizing dataset with on-disk caching (this may take a while)...")

    def batch_preprocess(examples):
        texts = [format_prompt(i, o) for i, o in zip(examples['instruction'], examples['output'])]
        enc = tokenizer(
            texts,
            truncation=True,
            max_length=MAX_SEQ_LENGTH,
            padding=False,
            return_attention_mask=True,
        )
        enc['labels'] = enc['input_ids'].copy()
        return enc

    tokenized_dataset = raw_dataset.map(
        batch_preprocess,
        batched=True,
        remove_columns=raw_dataset.column_names,
        desc="Tokenizing",
        num_proc=1,
        load_from_cache_file=True,
        keep_in_memory=False,
        writer_batch_size=1000,
    )
    del raw_dataset
    gc.collect()
    logger.info("✓ Tokenization complete")

    # DataLoader
    dataloader = DataLoader(
        tokenized_dataset,
        batch_size=BATCH_SIZE,
        shuffle=True,
        collate_fn=make_collate_fn(tokenizer.pad_token_id),
        num_workers=0,
        pin_memory=False,
    )

    # Model
    logger.info("Loading base model...")
    dtype = (
        torch.bfloat16 if device == "xpu" else
        (torch.float16 if device == "cuda" else torch.float32)
    )
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL_PATH,
        torch_dtype=dtype,
        device_map=None,
        low_cpu_mem_usage=True,
        trust_remote_code=True,
    )
    model.gradient_checkpointing_enable()
    model = model.to(device)
    logger.info("✓ Base model loaded and moved to device")

    # LoRA
    lora_config = LoraConfig(
        r=LORA_RANK,
        lora_alpha=LORA_ALPHA,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_dropout=LORA_DROPOUT,
        bias="none",
        task_type=TaskType.CAUSAL_LM,
    )
    model = get_peft_model(model, lora_config)
    model.train()
    logger.info("✓ LoRA configured and applied")

    # Optimizer & Scheduler
    optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE)
    total_steps = (len(dataloader) // GRADIENT_ACCUMULATION_STEPS) * NUM_EPOCHS
    scheduler = get_cosine_schedule_with_warmup(
        optimizer,
        num_warmup_steps=WARMUP_STEPS,
        num_training_steps=total_steps,
    )

    # Optional: IPEX optimize for XPU
    if device == "xpu":
        try:
            import intel_extension_for_pytorch as ipex
            logger.info("Applying IPEX optimization for XPU...")
            model, optimizer = ipex.optimize(
                model,
                dtype=dtype,
                optimizer=optimizer,
                inplace=True,
            )
            logger.info("✓ IPEX optimization applied")
        except Exception as e:
            logger.warning(f"IPEX optimization failed: {e}")

    # Train
    logger.info("=" * 60)
    logger.info("STARTING TRAINING (MMAP)")
    logger.info("=" * 60)
    logger.info(f"Epochs: {NUM_EPOCHS} | Batch size: {BATCH_SIZE} | Grad Accum: {GRADIENT_ACCUMULATION_STEPS}")
    logger.info(f"Total steps: {total_steps:,} | Dtype: {dtype} | Device: {device}")

    global_step = 0
    running_loss = 0.0

    try:
        for epoch in range(NUM_EPOCHS):
            logger.info(f"Epoch {epoch + 1}/{NUM_EPOCHS}")
            progress_bar = tqdm(dataloader, desc=f"Epoch {epoch+1}")

            for batch_idx, batch in enumerate(progress_bar):
                input_ids = batch['input_ids'].to(device, non_blocking=True)
                attention_mask = batch['attention_mask'].to(device, non_blocking=True)
                labels = batch['labels'].to(device, non_blocking=True)

                if device in ("xpu", "cuda"):
                    with torch.autocast(device_type=("xpu" if device == "xpu" else "cuda"), dtype=dtype):
                        outputs = model(
                            input_ids=input_ids,
                            attention_mask=attention_mask,
                            labels=labels,
                        )
                else:
                    outputs = model(
                        input_ids=input_ids,
                        attention_mask=attention_mask,
                        labels=labels,
                    )

                loss = outputs.loss / GRADIENT_ACCUMULATION_STEPS
                loss.backward()
                del outputs

                running_loss += loss.item()

                if (batch_idx + 1) % GRADIENT_ACCUMULATION_STEPS == 0:
                    optimizer.step()
                    scheduler.step()
                    optimizer.zero_grad(set_to_none=True)

                    global_step += 1
                    avg_loss = running_loss
                    running_loss = 0.0

                    progress_bar.set_postfix({
                        'loss': f'{avg_loss:.4f}',
                        'lr': f'{scheduler.get_last_lr()[0]:.2e}',
                        'step': global_step,
                    })

                    if global_step % LOGGING_STEPS == 0:
                        logger.info(f"Step {global_step}/{total_steps} | Loss: {avg_loss:.4f} | LR: {scheduler.get_last_lr()[0]:.2e}")
                        update_progress(global_step, total_steps, avg_loss, scheduler.get_last_lr()[0], OUTPUT_DIR)

                    if global_step % SAVE_STEPS == 0:
                        save_checkpoint(model, optimizer, scheduler, global_step, epoch, CHECKPOINT_DIR)
                        gc.collect()
                        if device == "xpu" and hasattr(torch.xpu, 'empty_cache'):
                            torch.xpu.empty_cache()
                            torch.xpu.synchronize()
                        elif device == "cuda":
                            torch.cuda.empty_cache()
                    elif global_step % 50 == 0:
                        gc.collect()
                        if device == "xpu" and hasattr(torch.xpu, 'empty_cache'):
                            torch.xpu.empty_cache()
                        elif device == "cuda":
                            torch.cuda.empty_cache()

            logger.info(f"✓ Epoch {epoch + 1} complete")

        # Save final model
        logger.info("Saving final model...")
        model.save_pretrained(OUTPUT_DIR)
        tokenizer.save_pretrained(OUTPUT_DIR)
        logger.info(f"✓ Model saved to {OUTPUT_DIR}")

    except KeyboardInterrupt:
        logger.warning("Training interrupted by user")
        logger.info(f"Last checkpoint step: {global_step}")
    except Exception as e:
        import traceback
        logger.error(f"Training failed: {e}")
        logger.error(traceback.format_exc())
        raise


if __name__ == "__main__":
    main()
