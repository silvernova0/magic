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
