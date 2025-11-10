#!/usr/bin/env python3
"""
Train v3 structured output model for Commander deck building.

Key differences from v2:
- Model learns to generate JSON structure with filters/queries
- No card name generation = zero hallucinations
- Database handles actual card lookup
- Shorter sequences (JSON vs full text decklist)
- Smaller dataset needed (23k examples vs 43k)

Training on Intel Arc B50 16GB with optimized settings.
"""

import os
import json
import torch
from pathlib import Path
from datasets import load_dataset
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    get_linear_schedule_with_warmup,
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
import intel_extension_for_pytorch as ipex
from torch.utils.data import DataLoader
from torch.optim import AdamW
from tqdm import tqdm

# Training configuration
# Prefer local cached model to avoid repeated HF downloads (override with MODEL_NAME env).
MODEL_NAME = os.getenv("MODEL_NAME", "models/qwen2.5-3b")
OUTPUT_DIR = "models/commander-qwen-3b-v3"
DATA_PATH = "data/training/v3_structured_training.jsonl"

# Hyperparameters optimized for Arc B50 16GB
BATCH_SIZE = int(os.getenv('BATCH_SIZE', '4'))
GRADIENT_ACCUMULATION_STEPS = int(os.getenv('GRADIENT_ACCUMULATION_STEPS', '8'))
MAX_SEQ_LENGTH = int(os.getenv('MAX_SEQ_LENGTH', '600'))  # Fits all v3 examples (max 581 tokens)
LEARNING_RATE = 2e-4
NUM_EPOCHS = 3
WARMUP_STEPS = 100
LOGGING_STEPS = int(os.getenv("LOGGING_STEPS", "50"))
SAVE_STEPS = int(os.getenv("SAVE_STEPS", "500"))
EVAL_STEPS = int(os.getenv("EVAL_STEPS", "500"))
LORA_RANK = 16
LORA_ALPHA = 32
LORA_DROPOUT = 0.05

print("=" * 70)
print("Commander Deck Builder v3 - Structured Output Training")
print("=" * 70)
print(f"Model: {MODEL_NAME}")
print(f"Device: Intel Arc B50 16GB (XPU)")
print(f"Training approach: Structured JSON generation")
print(f"Dataset: {DATA_PATH}")
print(f"Batch size: {BATCH_SIZE}")
print(f"Gradient accumulation: {GRADIENT_ACCUMULATION_STEPS}")
print(f"Effective batch size: {BATCH_SIZE * GRADIENT_ACCUMULATION_STEPS}")
print(f"Max sequence length: {MAX_SEQ_LENGTH}")
print(f"Learning rate: {LEARNING_RATE}")
print(f"Epochs: {NUM_EPOCHS}")
print(f"LoRA rank: {LORA_RANK}")
print("=" * 70)
print()

# Load tokenizer
print("Loading tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(
    MODEL_NAME,
    trust_remote_code=True,
    padding_side='right'
)

# Add padding token if needed
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.pad_token_id = tokenizer.eos_token_id

print(f"✅ Tokenizer loaded. Vocab size: {len(tokenizer)}")
print()

# Load and prepare dataset
print("Loading v3 structured training data...")
dataset = load_dataset('json', data_files=DATA_PATH, split='train')

print(f"Total examples: {len(dataset)}")
print(f"Columns: {dataset.column_names}")
print()

# Show example
print("Sample training example:")
print("-" * 70)
example = dataset[0]
print(f"Instruction: {example['instruction'][:100]}...")
print(f"Output (first 200 chars): {json.dumps(example['output'])[:200]}...")
print("-" * 70)
print()

# Tokenization function for v3 structured format
def tokenize_function(examples):
    """
    Convert instruction + structured output to training format.
    
    Format:
    <|im_start|>user
    Build a Commander deck with The Ur-Dragon focused on tribal dragons at power level 7<|im_end|>
    <|im_start|>assistant
    {
      "commander": "The Ur-Dragon",
      "strategy": "tribal",
      "bracket": 3,
      "card_selection": {...}
    }<|im_end|>
    """
    formatted_texts = []
    
    for i in range(len(examples['instruction'])):
        instruction = examples['instruction'][i]
        output = examples['output'][i]
        
        # Convert output dict to formatted JSON string
        if isinstance(output, dict):
            output_json = json.dumps(output, indent=2)
        else:
            output_json = output
        
        # Format with Qwen chat template
        text = f"""<|im_start|>user
{instruction}<|im_end|>
<|im_start|>assistant
{output_json}<|im_end|>"""
        
        formatted_texts.append(text)
    
    # Tokenize with padding to max length (simpler, works with IPEX)
    tokenized = tokenizer(
        formatted_texts,
        truncation=True,
        max_length=MAX_SEQ_LENGTH,
        padding='max_length',  # Pad all to 512
    )
    
    # Set labels (for causal LM, labels = input_ids)
    tokenized['labels'] = tokenized['input_ids'][:]
    
    return tokenized

print("Tokenizing dataset...")
tokenized_dataset = dataset.map(
    tokenize_function,
    batched=True,
    remove_columns=dataset.column_names,
    desc="Tokenizing"
)

# Analyze sequence lengths
print("\nAnalyzing sequence lengths...")
lengths = [len(x) for x in tokenized_dataset['input_ids']]
print(f"Min length: {min(lengths)}")
print(f"Max length: {max(lengths)}")
print(f"Mean length: {sum(lengths) / len(lengths):.1f}")
print(f"Median length: {sorted(lengths)[len(lengths)//2]}")

truncated = sum(1 for l in lengths if l >= MAX_SEQ_LENGTH)
print(f"Truncated sequences: {truncated} ({truncated/len(lengths)*100:.1f}%)")
print()

# Split into train/validation (90/10)
print("Splitting into train/validation sets...")
split_dataset = tokenized_dataset.train_test_split(test_size=0.1, seed=42)
train_dataset = split_dataset['train']
eval_dataset = split_dataset['test']

print(f"Train examples: {len(train_dataset)}")
print(f"Validation examples: {len(eval_dataset)}")
print()

# Load base model
print("Loading base model...")
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    torch_dtype=torch.bfloat16,
    device_map='xpu',  # Intel Arc GPU
    trust_remote_code=True
)

# Apply IPEX optimization for better XPU performance
print("Optimizing model for Intel XPU...")
model = ipex.optimize(model, dtype=torch.bfloat16)

print(f"✅ Model loaded and optimized on XPU")
print(f"Model device: {next(model.parameters()).device}")
print(f"Model parameters: {model.num_parameters() / 1e9:.2f}B")
print()

# Prepare for LoRA training
print("Preparing model for LoRA fine-tuning...")

# Configure LoRA
lora_config = LoraConfig(
    r=LORA_RANK,
    lora_alpha=LORA_ALPHA,
    target_modules=[
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj"
    ],
    lora_dropout=LORA_DROPOUT,
    bias="none",
    task_type="CAUSAL_LM"
)

model = get_peft_model(model, lora_config)

# Enable gradient checkpointing AFTER applying LoRA
model.enable_input_require_grads()

model.print_trainable_parameters()
print()

def collate_fn(batch):
    """Collate list of dicts into tensors."""
    input_ids = torch.tensor([item['input_ids'] for item in batch], dtype=torch.long)
    attention_mask = torch.tensor([item['attention_mask'] for item in batch], dtype=torch.long)
    labels = input_ids.clone()
    return {
        "input_ids": input_ids,
        "attention_mask": attention_mask,
        "labels": labels,
    }


def compute_validation_loss(model, dataloader, device, max_batches=10):
    """Run a few validation batches to monitor loss."""
    model.eval()
    total = 0.0
    count = 0
    with torch.no_grad():
        for batch in dataloader:
            if count >= max_batches:
                break
            batch = {k: v.to(device) for k, v in batch.items()}
            outputs = model(**batch)
            total += outputs.loss.item()
            count += 1
    model.train()
    return total / max(count, 1)


def save_checkpoint(model, optimizer, scheduler, global_step, epoch):
    checkpoint_dir = os.path.join(OUTPUT_DIR, f"checkpoint-{global_step}")
    os.makedirs(checkpoint_dir, exist_ok=True)
    model.save_pretrained(checkpoint_dir)
    torch.save(
        {
            "optimizer": optimizer.state_dict(),
            "scheduler": scheduler.state_dict(),
            "global_step": global_step,
            "epoch": epoch,
        },
        os.path.join(checkpoint_dir, "training_state.pt"),
    )
    print(f"Checkpoint saved to {checkpoint_dir}")


train_dataloader = DataLoader(
    train_dataset,
    batch_size=BATCH_SIZE,
    shuffle=True,
    collate_fn=collate_fn,
)
eval_dataloader = DataLoader(
    eval_dataset,
    batch_size=BATCH_SIZE,
    shuffle=False,
    collate_fn=collate_fn,
)

device = torch.device("xpu" if torch.xpu.is_available() else "cpu")

optimizer = AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=0.01)
num_update_steps_per_epoch = len(train_dataloader) // GRADIENT_ACCUMULATION_STEPS
total_steps = num_update_steps_per_epoch * NUM_EPOCHS
scheduler = get_linear_schedule_with_warmup(
    optimizer,
    num_warmup_steps=WARMUP_STEPS,
    num_training_steps=total_steps,
)

print("=" * 70)
print("Starting manual training loop...")
print("=" * 70)
print(f"Total optimization steps: {total_steps}")
print(f"Logging every: {LOGGING_STEPS} steps")
print(f"Saving every: {SAVE_STEPS} steps")
print("=" * 70)

model.train()
optimizer.zero_grad()
global_step = 0

for epoch in range(1, NUM_EPOCHS + 1):
    epoch_iterator = tqdm(train_dataloader, desc=f"Epoch {epoch}", leave=False)
    for step, batch in enumerate(epoch_iterator, start=1):
        batch = {k: v.to(device) for k, v in batch.items()}
        outputs = model(**batch)
        loss = outputs.loss
        loss_value = loss.item()
        (loss / GRADIENT_ACCUMULATION_STEPS).backward()

        if step % GRADIENT_ACCUMULATION_STEPS == 0:
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()
            optimizer.zero_grad()
            global_step += 1

            if global_step % LOGGING_STEPS == 0:
                val_loss = compute_validation_loss(model, eval_dataloader, device)
                print(f"Step {global_step}/{total_steps} | Loss: {loss_value:.4f} | Val Loss: {val_loss:.4f} | LR: {scheduler.get_last_lr()[0]:.2e}")

            if global_step % SAVE_STEPS == 0:
                save_checkpoint(model, optimizer, scheduler, global_step, epoch)

    print(f"Epoch {epoch} complete. Global step: {global_step}")

print("=" * 70)
print("Training complete! Saving final model...")
print("=" * 70)

final_dir = os.path.join(OUTPUT_DIR, "final")
os.makedirs(final_dir, exist_ok=True)
model.save_pretrained(final_dir)
tokenizer.save_pretrained(final_dir)
print(f"Final model saved to {final_dir}")

print()
print("=" * 70)
print("v3 Training Session Complete")
print("=" * 70)
