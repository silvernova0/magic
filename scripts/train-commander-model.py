"""
Fine-tune Llama 3.1 8B for Commander/EDH deck building using LoRA.

This script:
1. Loads the base Llama 3.1 8B Instruct model
2. Applies LoRA (Low-Rank Adaptation) for efficient fine-tuning
3. Trains on 65,480 examples (card knowledge + real Commander decks)
4. Optimized for Intel Arc B50 Pro (16GB VRAM)
5. Saves LoRA adapter weights for inference

Training configuration:
- LoRA rank: 16 (r=16)
- LoRA alpha: 32 (alpha=32)
- Batch size: 2 per device
- Gradient accumulation: 8 steps (effective batch = 16)
- Epochs: 3
- Learning rate: 2e-4
- Mixed precision: FP16
- Expected time: 12-18 hours on Arc B50 Pro

Output: models/commander-llama-lora/
"""

import os
import sys
import json
import torch
import gc
from pathlib import Path
from datetime import datetime

# Set memory limit (100GB max system RAM usage)
# This helps prevent system crashes from OOM errors
MAX_MEMORY_GB = 100
os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'max_split_size_mb:512'

try:
    import resource
    # On Unix systems, set memory limit
    MAX_MEMORY_BYTES = MAX_MEMORY_GB * 1024 * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (MAX_MEMORY_BYTES, MAX_MEMORY_BYTES))
except (ImportError, AttributeError, OSError):
    # Windows doesn't support resource module limits
    # Will rely on manual garbage collection instead
    pass

from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling,
    default_data_collator,
    TrainerCallback
)
from peft import LoraConfig, get_peft_model, TaskType, prepare_model_for_kbit_training
from datasets import Dataset
import logging


# Custom callback to save progress and manage memory
class ProgressCallback(TrainerCallback):
    """Save training progress to a file for monitoring and manage memory."""
    
    def __init__(self, output_dir):
        self.output_dir = output_dir
        self.progress_file = f"{output_dir}/training_progress.json"
    
    def on_step_end(self, args, state, control, **kwargs):
        """Update progress file after each step."""
        if state.global_step % 10 == 0:  # Update every 10 steps
            progress = {
                "global_step": state.global_step,
                "max_steps": state.max_steps,
                "epoch": state.epoch,
                "loss": state.log_history[-1].get('loss') if state.log_history else None,
                "learning_rate": state.log_history[-1].get('learning_rate') if state.log_history else None,
                "last_update": datetime.now().isoformat(),
                "progress_percent": round(100 * state.global_step / state.max_steps, 2) if state.max_steps else 0
            }
            
            with open(self.progress_file, 'w') as f:
                json.dump(progress, f, indent=2)
        
        # Aggressive garbage collection every 50 steps to prevent memory leaks
        if state.global_step % 50 == 0:
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            elif hasattr(torch, 'xpu') and torch.xpu.is_available():
                torch.xpu.empty_cache()
        
        return control

# Configure logging to both file and console
log_file = f"models/commander-llama-lora/training_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
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
BATCH_SIZE = 1  # Reduced from 2 to save RAM
GRADIENT_ACCUMULATION_STEPS = 16  # Increased from 8 to keep same effective batch size
MAX_SEQ_LENGTH = 2048
WARMUP_STEPS = 100
SAVE_STEPS = 100  # Save checkpoint every 100 steps (more frequent)
LOGGING_STEPS = 10


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
        # Training format
        return f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

You are a Magic: The Gathering Commander/EDH deck building expert. You have deep knowledge of all Magic cards, their synergies, power levels, and competitive rankings.<|eot_id|><|start_header_id|>user<|end_header_id|>

{instruction}<|eot_id|><|start_header_id|>assistant<|end_header_id|>

{output}<|eot_id|><|end_of_text|>"""
    else:
        # Inference format
        return f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

You are a Magic: The Gathering Commander/EDH deck building expert. You have deep knowledge of all Magic cards, their synergies, power levels, and competitive rankings.<|eot_id|><|start_header_id|>user<|end_header_id|>

{instruction}<|eot_id|><|start_header_id|>assistant<|end_header_id|>

"""


def preprocess_data(examples, tokenizer):
    """Tokenize and prepare training examples."""
    # Handle both single example and batch
    if isinstance(examples, dict) and 'instruction' in examples:
        # Single example
        instruction = examples.get('instruction', '')
        output = examples.get('output', '')
        text = format_prompt(instruction, output)
        
        # Tokenize
        tokenized = tokenizer(
            text,
            truncation=True,
            max_length=MAX_SEQ_LENGTH,
            padding=False,
            return_tensors=None
        )
        
        # Labels are the same as input_ids for causal LM
        tokenized["labels"] = tokenized["input_ids"]
        
        return tokenized
    else:
        # Batch of examples
        texts = []
        for i in range(len(examples['instruction'])):
            instruction = examples['instruction'][i]
            output = examples['output'][i]
            text = format_prompt(instruction, output)
            texts.append(text)
        
        # Tokenize with padding to max length in batch
        tokenized = tokenizer(
            texts,
            truncation=True,
            max_length=MAX_SEQ_LENGTH,
            padding="max_length",  # Pad to max_length
            return_tensors=None
        )
        
        # Labels are the same as input_ids for causal LM
        tokenized["labels"] = tokenized["input_ids"]
        
        return tokenized


def main():
    logger.info("=" * 60)
    logger.info("Commander Deck Builder - LoRA Fine-Tuning")
    logger.info("=" * 60)
    logger.info(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Base model: {BASE_MODEL_PATH}")
    logger.info(f"Training data: {TRAINING_DATA_PATH}")
    logger.info(f"Output directory: {OUTPUT_DIR}")
    logger.info("")
    
    # Create output directories
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    
    # Check device availability (CUDA, XPU, or CPU)
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
    
    if device == "cpu":
        if torch.cuda.is_available():
            device = "cuda"
            device_name = torch.cuda.get_device_name(0)
    
    logger.info(f"Device: {device}")
    logger.info(f"Hardware: {device_name}")
    
    if device == "xpu":
        logger.info("Training on Intel Arc GPU with XPU acceleration")
        logger.info("Expected training time: 12-18 hours")
    elif device == "cuda":
        logger.info(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")
        logger.info("Expected training time: 12-18 hours")
    else:
        logger.info("Training on CPU (slower but reliable)")
        logger.info("Expected training time: 24-36 hours")
        logger.info("Tip: Install Intel oneAPI Base Toolkit for GPU training")
        logger.info("See SETUP_INTEL_GPU_TRAINING.md for instructions")
    
    logger.info("")
    
    # Load tokenizer
    logger.info("Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_PATH)
    
    # Set padding token (Llama doesn't have one by default)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
        tokenizer.pad_token_id = tokenizer.eos_token_id
    
    logger.info("✓ Tokenizer loaded")
    logger.info(f"  Vocab size: {len(tokenizer):,}")
    logger.info(f"  Padding token: {tokenizer.pad_token}")
    logger.info("")
    
    # Load training data
    training_data = load_training_data(TRAINING_DATA_PATH)
    num_training_examples = len(training_data)
    
    # Create dataset
    logger.info("Creating dataset...")
    dataset = Dataset.from_list(training_data)
    logger.info(f"✓ Dataset created with {len(dataset):,} examples")
    
    # Free up memory
    del training_data
    logger.info("")
    
    # Tokenize dataset with memory optimization
    logger.info("Tokenizing dataset (this may take a few minutes)...")
    tokenized_dataset = dataset.map(
        lambda examples: preprocess_data(examples, tokenizer),
        batched=True,
        batch_size=50,  # Reduced batch size to save memory
        remove_columns=dataset.column_names,
        desc="Tokenizing",
        num_proc=1  # Single process to avoid memory duplication
    )
    
    # Free up memory
    del dataset
    gc.collect()
    
    # Filter out examples that are too long
    logger.info("Filtering sequences...")
    tokenized_dataset = tokenized_dataset.filter(
        lambda example: len(example["input_ids"]) <= MAX_SEQ_LENGTH,
        desc="Filtering"
    )
    
    logger.info("✓ Dataset tokenized and filtered")
    logger.info(f"  Examples after filtering: {len(tokenized_dataset):,}")
    
    # Final memory cleanup before loading model
    gc.collect()
    logger.info("")
    
    # Load base model
    logger.info("Loading base model...")
    logger.info("  This may take a few minutes...")
    
    # Determine dtype based on device
    if device == "xpu":
        dtype = torch.float16  # XPU supports FP16
    elif device == "cuda":
        dtype = torch.float16
    else:
        dtype = torch.float32  # CPU uses FP32
    
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL_PATH,
        torch_dtype=dtype,
        device_map=None,  # Manual device placement
        low_cpu_mem_usage=True,
        trust_remote_code=True
    )
    
    # Enable gradient checkpointing to save memory
    model.gradient_checkpointing_enable()
    
    # Move model to device
    if device != "cpu":
        model = model.to(device)
    
    logger.info("✓ Base model loaded")
    logger.info(f"  Parameters: {sum(p.numel() for p in model.parameters()):,}")
    logger.info(f"  Trainable parameters: {sum(p.numel() for p in model.parameters() if p.requires_grad):,}")
    logger.info("")
    
    # Configure LoRA
    logger.info("Configuring LoRA...")
    lora_config = LoraConfig(
        r=LORA_RANK,
        lora_alpha=LORA_ALPHA,
        target_modules=[
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj"
        ],
        lora_dropout=LORA_DROPOUT,
        bias="none",
        task_type=TaskType.CAUSAL_LM
    )
    
    # Apply LoRA to model
    model = get_peft_model(model, lora_config)
    
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total_params = sum(p.numel() for p in model.parameters())
    trainable_percent = 100 * trainable_params / total_params
    
    logger.info("✓ LoRA configured and applied")
    logger.info(f"  LoRA rank: {LORA_RANK}")
    logger.info(f"  LoRA alpha: {LORA_ALPHA}")
    logger.info(f"  LoRA dropout: {LORA_DROPOUT}")
    logger.info(f"  Total parameters: {total_params:,}")
    logger.info(f"  Trainable parameters: {trainable_params:,}")
    logger.info(f"  Trainable %: {trainable_percent:.2f}%")
    logger.info("")
    
    # Training arguments
    logger.info("Configuring training...")
    
    # Use FP16 for GPU (XPU/CUDA), FP32 for CPU
    # Note: XPU has issues with fp16 in Transformers, use bf16 or fp32
    use_fp16 = False  # Disabled for XPU compatibility
    use_bf16 = (device == "xpu")  # Use bfloat16 for XPU instead
    
    training_args = TrainingArguments(
        output_dir=CHECKPOINT_DIR,
        num_train_epochs=NUM_EPOCHS,
        per_device_train_batch_size=BATCH_SIZE,
        gradient_accumulation_steps=GRADIENT_ACCUMULATION_STEPS,
        learning_rate=LEARNING_RATE,
        fp16=use_fp16,
        bf16=use_bf16,
        logging_steps=LOGGING_STEPS,
        save_steps=SAVE_STEPS,
        save_total_limit=10,  # Keep last 10 checkpoints (100-step intervals)
        warmup_steps=WARMUP_STEPS,
        lr_scheduler_type="cosine",
        report_to="none",  # Disable wandb/tensorboard
        remove_unused_columns=False,
        dataloader_num_workers=0,
        logging_dir=f"{OUTPUT_DIR}/logs",
        save_strategy="steps",
        load_best_model_at_end=False,
        gradient_checkpointing=True,  # Enable gradient checkpointing to save RAM
        optim="adamw_torch",  # Use PyTorch's AdamW (more memory efficient)
        dataloader_pin_memory=False  # Disable pin memory to save RAM
    )
    
    effective_batch_size = BATCH_SIZE * GRADIENT_ACCUMULATION_STEPS
    total_steps = (len(tokenized_dataset) // effective_batch_size) * NUM_EPOCHS
    
    logger.info("✓ Training configured")
    logger.info(f"  Epochs: {NUM_EPOCHS}")
    logger.info(f"  Batch size per device: {BATCH_SIZE}")
    logger.info(f"  Gradient accumulation steps: {GRADIENT_ACCUMULATION_STEPS}")
    logger.info(f"  Effective batch size: {effective_batch_size}")
    logger.info(f"  Learning rate: {LEARNING_RATE}")
    logger.info(f"  Total training steps: {total_steps:,}")
    logger.info(f"  Warmup steps: {WARMUP_STEPS}")
    logger.info(f"  Save every {SAVE_STEPS} steps (more frequent for safety)")
    logger.info(f"  Keep last {training_args.save_total_limit} checkpoints")
    logger.info(f"  Mixed precision: BF16={use_bf16}, FP16={use_fp16}")
    logger.info("")
    
    # Use default data collator (simpler, works better with XPU)
    data_collator = default_data_collator
    
    # Initialize trainer
    logger.info("Initializing trainer...")
    
    # Add progress callback
    progress_callback = ProgressCallback(OUTPUT_DIR)
    
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset,
        data_collator=data_collator,
        callbacks=[progress_callback]
    )
    logger.info("✓ Trainer initialized")
    logger.info("")
    
    # Save training configuration
    config_path = f"{OUTPUT_DIR}/training_config.json"
    with open(config_path, 'w') as f:
        json.dump({
            "base_model": BASE_MODEL_PATH,
            "training_data": TRAINING_DATA_PATH,
            "num_examples": num_training_examples,
            "lora_rank": LORA_RANK,
            "lora_alpha": LORA_ALPHA,
            "lora_dropout": LORA_DROPOUT,
            "learning_rate": LEARNING_RATE,
            "num_epochs": NUM_EPOCHS,
            "batch_size": BATCH_SIZE,
            "gradient_accumulation_steps": GRADIENT_ACCUMULATION_STEPS,
            "effective_batch_size": effective_batch_size,
            "max_seq_length": MAX_SEQ_LENGTH,
            "total_steps": total_steps,
            "trainable_params": trainable_params,
            "trainable_percent": trainable_percent,
            "device": device,
            "start_time": datetime.now().isoformat()
        }, f, indent=2)
    logger.info(f"✓ Training configuration saved to {config_path}")
    logger.info("")
    
    # Start training
    logger.info("=" * 60)
    logger.info("STARTING TRAINING")
    logger.info("=" * 60)
    logger.info("This will take approximately 12-18 hours on Intel Arc B50 Pro")
    logger.info("Progress will be logged every 10 steps")
    logger.info("Checkpoints will be saved every 100 steps")
    logger.info(f"Training log file: {log_file}")
    logger.info("You can safely interrupt training with Ctrl+C and resume later")
    logger.info("")
    
    try:
        trainer.train()
        logger.info("")
        logger.info("=" * 60)
        logger.info("TRAINING COMPLETE!")
        logger.info("=" * 60)
    except KeyboardInterrupt:
        logger.warning("")
        logger.warning("Training interrupted by user")
        logger.warning("Progress has been saved to checkpoints")
        logger.warning("You can resume training by running this script again")
    except Exception as e:
        logger.error(f"Training failed with error: {e}")
        raise
    
    # Save final model
    logger.info("")
    logger.info("Saving final LoRA adapter...")
    model.save_pretrained(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)
    logger.info(f"✓ Model saved to {OUTPUT_DIR}")
    
    # Save completion timestamp
    with open(f"{OUTPUT_DIR}/training_complete.json", 'w') as f:
        json.dump({
            "end_time": datetime.now().isoformat(),
            "total_examples": num_training_examples,
            "epochs_completed": NUM_EPOCHS,
            "final_loss": trainer.state.log_history[-1].get('loss', 'N/A') if trainer.state.log_history else 'N/A'
        }, f, indent=2)
    
    logger.info("")
    logger.info("=" * 60)
    logger.info("Training session complete!")
    logger.info(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"LoRA adapter: {OUTPUT_DIR}")
    logger.info("")
    logger.info("Next steps:")
    logger.info("1. Export to OpenVINO format for optimized inference")
    logger.info("2. Create inference API for deck generation")
    logger.info("3. Integrate with Next.js app")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
