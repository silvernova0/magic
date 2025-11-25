# Windows RTX 5070 Ti Training Guide - BEST QUALITY

## Model Selection for Best Quality

### Recommended: **Llama 3.1 8B Instruct**

**Why Llama 3.1 8B over Mistral 7B:**
- ✅ Better instruction following (critical for structured JSON output)
- ✅ Superior reasoning for deck building logic
- ✅ Larger context window (128K vs 32K)
- ✅ Better at maintaining structure consistency
- ✅ Meta's best open-source model in this size class
- ⚠️ Slower inference (~20% slower than Mistral 7B)
- ⚠️ Higher VRAM usage (~14-15GB vs 12-13GB)

**VRAM Check:**
- Base model (BF16): ~16GB
- With LoRA (rank 16): ~14-15GB ✅ FITS
- Batch size: 1-2 (effective batch 8-16 with gradient accumulation)

### Alternative: Qwen 2.5 7B Instruct (Best Quality/Speed Balance)

If Llama 8B has VRAM issues:
- ✅ Excellent instruction following (rivals Llama)
- ✅ Better at structured output than Mistral
- ✅ Lower VRAM (~13GB with LoRA)
- ✅ Faster training than Llama 8B
- ✅ Strong multilingual support

## Training Configuration - Best Quality

### LoRA Settings (Optimized for Quality)
```python
from peft import LoraConfig

lora_config = LoraConfig(
    r=32,                      # Rank (higher = more capacity, use 32 for quality)
    lora_alpha=64,             # Alpha (2x rank is standard)
    lora_dropout=0.05,         # Low dropout for stability
    target_modules=[           # Target ALL attention + MLP layers
        "q_proj", "k_proj", "v_proj", "o_proj",  # Attention
        "gate_proj", "up_proj", "down_proj"       # MLP
    ],
    bias="none",
    task_type="CAUSAL_LM"
)
```

**Trainable Parameters:** ~67M (0.8% of 8B model)

### Training Arguments (Quality Focus)
```python
from transformers import TrainingArguments

training_args = TrainingArguments(
    output_dir="./llama-3.1-8b-commander-lora",
    
    # Training duration (longer = better quality)
    num_train_epochs=3,              # 3 full epochs
    max_steps=-1,                    # Let epochs determine length
    
    # Batch size (optimize for 16GB VRAM)
    per_device_train_batch_size=1,   # Small batch to fit VRAM
    gradient_accumulation_steps=16,  # Effective batch = 16
    
    # Learning rate (critical for quality)
    learning_rate=2e-4,              # Standard for LoRA
    lr_scheduler_type="cosine",      # Cosine decay (smoother than linear)
    warmup_steps=200,                # Warmup for stability
    weight_decay=0.01,
    
    # Optimization
    optim="adamw_torch_fused",       # Fastest AdamW
    bf16=True,                       # Use BF16 (RTX 50 series supports it)
    tf32=True,                       # Enable TF32 for speed
    
    # Memory optimization
    gradient_checkpointing=True,     # Save VRAM
    max_grad_norm=1.0,              # Gradient clipping
    
    # Logging
    logging_steps=10,
    save_strategy="steps",
    save_steps=500,
    save_total_limit=3,
    
    # Evaluation
    eval_strategy="steps",
    eval_steps=500,
    load_best_model_at_end=True,
    metric_for_best_model="eval_loss",
    
    # Performance
    dataloader_num_workers=4,
    remove_unused_columns=False,
)
```

### Dataset Preparation (Windows)
```python
from datasets import load_dataset

# Load v3 training data
dataset = load_dataset(
    'json',
    data_files='v3_structured_training.jsonl',
    split='train'
)

# Split for validation (90/10)
dataset = dataset.train_test_split(test_size=0.1, seed=42)

print(f"Training examples: {len(dataset['train'])}")    # 26,237
print(f"Validation examples: {len(dataset['test'])}")   # 2,915

# Format for Llama 3.1 instruction format
def format_llama3_prompt(example):
    instruction = example['instruction']
    output = json.dumps(example['output'])
    
    # Llama 3.1 chat format
    prompt = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

You are an expert Magic: The Gathering Commander deck builder. Generate structured deck-building specifications in JSON format.<|eot_id|><|start_header_id|>user<|end_header_id|>

{instruction}<|eot_id|><|start_header_id|>assistant<|end_header_id|>

{output}<|eot_id|>"""
    
    return {"text": prompt}

# Apply formatting
dataset = dataset.map(format_llama3_prompt, remove_columns=dataset['train'].column_names)
```

## Full Training Script (Windows)

Save as `train_commander_model.py`:

```python
import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from datasets import load_dataset
import json

# Configuration
MODEL_NAME = "meta-llama/Llama-3.1-8B-Instruct"
OUTPUT_DIR = "./llama-3.1-8b-commander-lora"
DATA_FILE = "v3_structured_training.jsonl"

print("=" * 60)
print("Commander Deck Builder - Training Script")
print("=" * 60)
print(f"\nModel: {MODEL_NAME}")
print(f"GPU: {torch.cuda.get_device_name(0)}")
print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
print()

# Load tokenizer
print("Loading tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
tokenizer.pad_token = tokenizer.eos_token
tokenizer.padding_side = "right"

# Load model
print("Loading base model...")
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    torch_dtype=torch.bfloat16,
    device_map="auto",
    trust_remote_code=True
)

# Prepare for training
model = prepare_model_for_kbit_training(model)

# Add LoRA
print("Adding LoRA adapters...")
lora_config = LoraConfig(
    r=32,
    lora_alpha=64,
    lora_dropout=0.05,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    bias="none",
    task_type="CAUSAL_LM"
)

model = get_peft_model(model, lora_config)
model.print_trainable_parameters()

# Load dataset
print("\nLoading dataset...")
dataset = load_dataset('json', data_files=DATA_FILE, split='train')
dataset = dataset.train_test_split(test_size=0.1, seed=42)

def format_prompt(example):
    instruction = example['instruction']
    output = json.dumps(example['output'])
    
    prompt = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

You are an expert Magic: The Gathering Commander deck builder. Generate structured deck-building specifications in JSON format.<|eot_id|><|start_header_id|>user<|end_header_id|>

{instruction}<|eot_id|><|start_header_id|>assistant<|end_header_id|>

{output}<|eot_id|>"""
    
    return {"text": prompt}

dataset = dataset.map(format_prompt, remove_columns=dataset['train'].column_names)

def tokenize(example):
    return tokenizer(
        example['text'],
        truncation=True,
        max_length=600,
        padding='max_length'
    )

dataset = dataset.map(tokenize, batched=True)

print(f"Training examples: {len(dataset['train'])}")
print(f"Validation examples: {len(dataset['test'])}")

# Training arguments
training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    num_train_epochs=3,
    per_device_train_batch_size=1,
    gradient_accumulation_steps=16,
    learning_rate=2e-4,
    lr_scheduler_type="cosine",
    warmup_steps=200,
    weight_decay=0.01,
    optim="adamw_torch_fused",
    bf16=True,
    tf32=True,
    gradient_checkpointing=True,
    max_grad_norm=1.0,
    logging_steps=10,
    save_strategy="steps",
    save_steps=500,
    save_total_limit=3,
    eval_strategy="steps",
    eval_steps=500,
    load_best_model_at_end=True,
    metric_for_best_model="eval_loss",
    dataloader_num_workers=4,
    remove_unused_columns=False,
    report_to="none"
)

# Data collator
data_collator = DataCollatorForLanguageModeling(
    tokenizer=tokenizer,
    mlm=False
)

# Trainer
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=dataset['train'],
    eval_dataset=dataset['test'],
    data_collator=data_collator
)

# Train
print("\n" + "=" * 60)
print("Starting training...")
print("=" * 60)
print()

trainer.train()

# Save final model
print("\nSaving final model...")
model.save_pretrained(f"{OUTPUT_DIR}/final")
tokenizer.save_pretrained(f"{OUTPUT_DIR}/final")

print("\n" + "=" * 60)
print("Training complete!")
print("=" * 60)
print(f"Model saved to: {OUTPUT_DIR}/final")
```

## Training Timeline (RTX 5070 Ti)

**Llama 3.1 8B:**
- Examples: 29,152
- Epochs: 3
- Effective batch size: 16
- Steps per epoch: ~1,822
- Total steps: ~5,466
- **Duration: 12-14 hours** ⏱️
- VRAM usage: ~14-15GB

**Expected Checkpoints:**
- Step 500 (1.5 hours)
- Step 1000 (3 hours)
- Step 1500 (4.5 hours)
- ... every 500 steps
- Final: 12-14 hours

## Running on Windows

### 1. Install Dependencies
```powershell
# Install PyTorch with CUDA 12.1
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Install training libraries
pip install transformers accelerate peft datasets bitsandbytes
```

### 2. Verify GPU
```python
import torch
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"GPU: {torch.cuda.get_device_name(0)}")
print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
```

### 3. Run Training
```powershell
# Start training (overnight)
python train_commander_model.py
```

### 4. Monitor Progress
- Check console output for loss values
- Eval loss should decrease over time
- Best checkpoint saved automatically

## Quality Indicators

**Good training:**
- ✅ Training loss decreases smoothly
- ✅ Eval loss tracks training loss
- ✅ No sudden spikes or NaN values
- ✅ Final eval loss < 0.5

**Issues to watch:**
- ⚠️ Eval loss stops decreasing = overfitting (stop early)
- ⚠️ Loss oscillates wildly = learning rate too high
- ⚠️ CUDA OOM = reduce batch size to 1, gradient_accumulation to 8

## After Training

### Test Generation
```python
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

# Load model
base_model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-3.1-8B-Instruct",
    torch_dtype=torch.bfloat16,
    device_map="auto"
)

model = PeftModel.from_pretrained(base_model, "./llama-3.1-8b-commander-lora/final")
tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-3.1-8B-Instruct")

# Test
prompt = """<|begin_of_text|><|start_header_id|>system<|end_header_id|>

You are an expert Magic: The Gathering Commander deck builder. Generate structured deck-building specifications in JSON format.<|eot_id|><|start_header_id|>user<|end_header_id|>

Build a Commander deck with Atraxa, Praetors' Voice focused on counters at power level 8<|eot_id|><|start_header_id|>assistant<|end_header_id|>

"""

inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
outputs = model.generate(**inputs, max_new_tokens=500, temperature=0.7)
print(tokenizer.decode(outputs[0]))
```

---

**Status**: Ready for Windows transfer
**Estimated time**: 12-14 hours training
**Expected quality**: BEST (Llama 3.1 8B with rank-32 LoRA)
