import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling
)
from peft import LoraConfig, get_peft_model
from datasets import load_dataset
import json
import intel_extension_for_pytorch as ipex

def main():
    # Use Qwen 3 4B base model (no instruction tuning)
    MODEL_NAME = "Qwen/Qwen3-4B"  # Base model, pure pattern completion
    OUTPUT_DIR = "./qwen3-4b-commander-lora"
    DATA_FILE = "data/training/v3_structured_training.jsonl"
    
    print("=" * 60)
    print("Qwen 3 4B BASE - Commander Deck Builder Training (Intel Arc)")
    print("LoRA Rank 48 for High Quality")
    print("=" * 60)
    print()
    
    # Check XPU
    if torch.xpu.is_available():
        print(f"XPU Device: {torch.xpu.get_device_name(0)}")
        print(f"VRAM: {torch.xpu.get_device_properties(0).total_memory / 1e9:.1f} GB")
        print()
    else:
        print("WARNING: No XPU detected! Check Intel Extension for PyTorch.")
        print()
    
    print("Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"
    
    print("Loading model in bfloat16...")
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        torch_dtype=torch.bfloat16,
        trust_remote_code=True
    )
    
    # Move to XPU and optimize with IPEX
    model = model.to("xpu")
    model = ipex.optimize(model, dtype=torch.bfloat16)
    
    print("Adding LoRA adapters...")
    lora_config = LoraConfig(
        r=48,  # Increased from 32 for better quality (have VRAM headroom)
        lora_alpha=96,  # Alpha = 2 * rank
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM"
    )
    model = get_peft_model(model, lora_config)
    model.enable_input_require_grads()
    model.gradient_checkpointing_enable()
    model.print_trainable_parameters()
    print()
    
    print("Loading dataset...")
    dataset = load_dataset('json', data_files=DATA_FILE, split='train')
    dataset = dataset.train_test_split(test_size=0.1, seed=42)
    
    def tokenize_function(examples):
        prompts = []
        for instruction, output in zip(examples['instruction'], examples['output']):
            output_str = json.dumps(output, indent=2) if isinstance(output, dict) else str(output)
            # Base model: simple concatenation, no chat template
            # Format: "INSTRUCTION\n\nOUTPUT"
            prompt = f"{instruction}\n\n{output_str}"
            prompts.append(prompt)
        
        # Pad to max_length during tokenization to avoid collator issues
        tokenized = tokenizer(
            prompts,
            truncation=True,
            max_length=600,
            padding='max_length'
        )
        # Labels are same as input_ids for causal LM
        tokenized["labels"] = tokenized["input_ids"][:]
        return tokenized
    
    print("Tokenizing datasets...")
    tokenized_train = dataset['train'].map(tokenize_function, batched=True, remove_columns=dataset['train'].column_names)
    tokenized_eval = dataset['test'].map(tokenize_function, batched=True, remove_columns=dataset['test'].column_names)
    print(f"Training: {len(tokenized_train)}, Validation: {len(tokenized_eval)}\n")
    
    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        num_train_epochs=3,  # Standard 3 epochs (proven effective)
        per_device_train_batch_size=3,  # Increased from 2 (have VRAM headroom)
        gradient_accumulation_steps=8,  # Effective batch = 24
        learning_rate=2e-4,
        lr_scheduler_type="cosine",  # Cosine often better than linear for quality
        warmup_ratio=0.05,  # 5% warmup for smoother start
        logging_steps=10,
        eval_strategy="no",  # DISABLED - eval causes VRAM spikes
        save_strategy="steps",
        save_steps=500,
        save_total_limit=3,
        bf16=True,
        gradient_checkpointing=True,  # ENABLED to save memory
        optim="adamw_torch",
        weight_decay=0.01,
        max_grad_norm=1.0,
        dataloader_num_workers=0,
        remove_unused_columns=False,
        report_to="none",
        load_best_model_at_end=False,  # Can't load best without eval
        use_cpu=False  # Force XPU usage
    )
    
    # Data collator with padding
    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=False,
        pad_to_multiple_of=8  # Efficient padding for GPU
    )
    
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_train,
        eval_dataset=tokenized_eval,
        data_collator=data_collator
    )
    
    print("=" * 60)
    print("Starting training...")
    print("=" * 60)
    print()
    trainer.train()
    
    print("\n" + "=" * 60)
    print("Saving final model...")
    final_dir = f"{OUTPUT_DIR}/final"
    trainer.model.save_pretrained(final_dir)
    tokenizer.save_pretrained(final_dir)
    print(f"Saved to: {final_dir}")
    print("Training complete! 🎉")

if __name__ == '__main__':
    main()
