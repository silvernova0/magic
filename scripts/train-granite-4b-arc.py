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
    MODEL_NAME = "ibm-granite/granite-4.0-micro"
    OUTPUT_DIR = "./granite-4.0-micro-commander-lora"
    DATA_FILE = "data/training/v3_structured_training.jsonl"
    
    print("=" * 60)
    print("IBM Granite 4.0 Micro - Commander Deck Builder Training (Intel Arc)")
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
        r=64,  # Higher rank for better quality (3B can handle it)
        lora_alpha=128,  # Alpha = 2 * rank
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
            messages = [
                {"role": "user", "content": instruction},
                {"role": "assistant", "content": output_str}
            ]
            prompts.append(tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False))
        
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
        num_train_epochs=4,  # More epochs for 3B to learn better
        per_device_train_batch_size=4,  # 3B model is smaller, can use batch 4
        gradient_accumulation_steps=4,  # Effective batch = 16
        learning_rate=2e-4,
        lr_scheduler_type="cosine",  # Cosine often better than linear for quality
        warmup_ratio=0.05,  # 5% warmup for smoother start
        logging_steps=10,
        eval_strategy="steps",
        eval_steps=500,
        save_strategy="steps",
        save_steps=500,
        save_total_limit=3,
        bf16=True,
        gradient_checkpointing=False,
        optim="adamw_torch",
        weight_decay=0.01,
        max_grad_norm=1.0,
        dataloader_num_workers=0,
        remove_unused_columns=False,
        report_to="none",
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
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
