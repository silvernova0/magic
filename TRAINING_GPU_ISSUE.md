# Training GPU Issue - Intel Arc B50 Not Being Used

## Current Status (Nov 8, 2025)

**Problem**: v3 training runs on CPU despite all XPU configurations appearing correct.

## Symptoms

- **CPU Usage**: 715% (multi-core saturation)
- **RAM Usage**: 9.1GB system RAM
- **GPU Usage**: 0% (Intel Arc B50 idle)
- **Training Speed**: ~48 minutes for initialization, 0 steps completed
- **Expected Speed**: ~2-3 seconds per step on GPU

## What Works

✅ PyTorch XPU available: `torch.xpu.is_available() = True`
✅ Model loads on XPU: `device_map='xpu'` succeeds
✅ Model device confirmed: `next(model.parameters()).device = xpu:0`
✅ Inference works on XPU: `model.generate()` runs on xpu:0
✅ IPEX optimization applies: `ipex.optimize(model)` succeeds

## What Doesn't Work

❌ **HuggingFace Trainer doesn't use XPU for training loop**
- Despite model being on xpu:0
- Despite `no_cuda=True, use_cpu=False` in TrainingArguments
- Despite IPEX optimization applied
- Training runs on CPU anyway

## Current Configuration

### Model Loading (scripts/train-v3-structured.py)
```python
import intel_extension_for_pytorch as ipex

model = AutoModelForCausalLM.from_pretrained(
    "Qwen/Qwen2.5-3B-Instruct",
    torch_dtype=torch.bfloat16,
    device_map='xpu',  # ✅ Works
    trust_remote_code=True
)

# Apply IPEX optimization
model = ipex.optimize(model, dtype=torch.bfloat16)  # ✅ Works

print(f"Model device: {next(model.parameters()).device}")  # Prints: xpu:0 ✅
```

### Training Arguments
```python
training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    num_train_epochs=NUM_EPOCHS,
    per_device_train_batch_size=BATCH_SIZE,
    gradient_accumulation_steps=GRADIENT_ACCUMULATION_STEPS,
    learning_rate=LEARNING_RATE,
    weight_decay=WEIGHT_DECAY,
    warmup_steps=WARMUP_STEPS,
    logging_steps=10,
    save_steps=500,
    eval_strategy="steps",
    eval_steps=500,
    save_total_limit=3,
    bf16=True,
    gradient_checkpointing=True,
    no_cuda=True,      # ✅ Don't use CUDA
    use_cpu=False,     # ✅ Don't force CPU
    report_to="none"
)
```

### LoRA Configuration
```python
from peft import LoraConfig, get_peft_model

lora_config = LoraConfig(
    r=16,
    lora_alpha=32,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM"
)

model = get_peft_model(model, lora_config)  # ✅ Works
model.enable_input_require_grads()          # ✅ Enables gradients
```

### Trainer Setup
```python
from transformers import Trainer

trainer = Trainer(
    model=model,                    # Model is on xpu:0 ✅
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=eval_dataset,
)

trainer.train()  # ❌ Uses CPU instead of XPU
```

## Attempted Solutions

### 1. IPEX Optimization
- **Tried**: Added `ipex.optimize(model)` after loading
- **Result**: Model optimized, but Trainer still uses CPU

### 2. Explicit Device in TrainingArguments
- **Tried**: Set `no_cuda=True, use_cpu=False`
- **Result**: No effect, still uses CPU

### 3. Model Device Verification
- **Tried**: Confirmed `next(model.parameters()).device = xpu:0`
- **Result**: Model IS on XPU, but training loop isn't

## Hypotheses

### Theory 1: Trainer Doesn't Support XPU Device
HuggingFace Transformers Trainer may not recognize 'xpu' as a valid device for training, even though PyTorch does. The Trainer might need explicit support for Intel XPU.

**Evidence**:
- Model loads on XPU ✅
- Inference works on XPU ✅
- Training runs on CPU ❌

**Fix**: May need to use a custom Trainer or training loop that explicitly moves tensors to XPU

### Theory 2: IPEX Not Integrated with Trainer
Intel Extension for PyTorch (IPEX) optimization might only apply to inference, not to the full training loop when using HuggingFace Trainer.

**Evidence**:
- `ipex.optimize()` is called ✅
- Model is optimized for XPU ✅
- Trainer doesn't use optimized path ❌

**Fix**: May need to use `ipex.optimize()` with `optimizer` parameter on the Trainer's optimizer

### Theory 3: DataLoader Not Using XPU
The Trainer's internal DataLoader might be creating tensors on CPU and not moving them to XPU, causing the entire training loop to fall back to CPU.

**Evidence**:
- Training args have `no_cuda=True` ✅
- No explicit `device` parameter in TrainingArguments
- Tokenization happens on CPU ✅ (expected)

**Fix**: May need custom DataLoader that moves batches to XPU

## Potential Solutions to Try

### Solution 1: Custom Training Loop
Replace HuggingFace Trainer with manual training loop:

```python
import torch
from torch.utils.data import DataLoader
from tqdm import tqdm

# Create DataLoader
train_dataloader = DataLoader(train_dataset, batch_size=4, shuffle=True)

# Move model to XPU (already done)
model = model.to('xpu')

# Create optimizer
optimizer = torch.optim.AdamW(model.parameters(), lr=2e-4)

# Optimize with IPEX
model, optimizer = ipex.optimize(model, optimizer=optimizer, dtype=torch.bfloat16)

# Training loop
for epoch in range(3):
    for batch in tqdm(train_dataloader):
        # Move batch to XPU explicitly
        input_ids = batch['input_ids'].to('xpu')
        attention_mask = batch['attention_mask'].to('xpu')
        labels = batch['labels'].to('xpu')
        
        # Forward pass
        outputs = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
        loss = outputs.loss
        
        # Backward pass
        loss.backward()
        optimizer.step()
        optimizer.zero_grad()
```

### Solution 2: IPEX Optimize Trainer's Optimizer
Try optimizing the Trainer's optimizer after Trainer creation:

```python
trainer = Trainer(...)

# Access internal optimizer and optimize it with IPEX
trainer.create_optimizer()  # Create optimizer first
trainer.optimizer = ipex.optimize(model, optimizer=trainer.optimizer, dtype=torch.bfloat16)[1]

trainer.train()
```

### Solution 3: Use Accelerate with XPU
Use HuggingFace Accelerate library which might have better XPU support:

```python
from accelerate import Accelerator

accelerator = Accelerator(device_placement=True)

model, optimizer, train_dataloader = accelerator.prepare(
    model, optimizer, train_dataloader
)

# Then use accelerator in training loop
for batch in train_dataloader:
    outputs = model(**batch)
    loss = outputs.loss
    accelerator.backward(loss)
    optimizer.step()
    optimizer.zero_grad()
```

### Solution 4: Check IPEX Trainer Integration
Look for IPEX-specific Trainer integration or patches:

```bash
# Check if there's an IPEX-specific training API
python3 -c "import intel_extension_for_pytorch as ipex; help(ipex)"
```

## Timeline

- **v2 Training**: Completed successfully with XPU (31 hours, 3 epochs)
  - This suggests XPU training DID work before
  - Need to check what changed between v2 and v3 scripts

- **v3 First Attempt**: Padding errors
- **v3 Second Attempt**: Gradient computation errors  
- **v3 Third Attempt**: 33 min/step (too slow, likely CPU)
- **v3 Current Attempt**: 48 min for initialization, confirmed CPU usage

## Next Steps

1. **Compare v2 vs v3 training scripts** - See what changed
2. **Try custom training loop** - Bypass HuggingFace Trainer
3. **Test IPEX optimizer optimization** - Optimize Trainer's optimizer
4. **Check v2 training logs** - Confirm v2 actually used GPU
5. **Research IPEX + Transformers integration** - Find official documentation

## Hardware Info

```
Intel Arc B50 16GB
- Device: Intel(R) Graphics [0xe212]
- VRAM: 15.13 GB available
- PyTorch: 2.8.0+xpu
- IPEX: 2.8.10+xpu
- XPU Available: True
```

## Resources

- Intel PyTorch XPU: https://intel.github.io/intel-extension-for-pytorch/
- HuggingFace Trainer: https://huggingface.co/docs/transformers/main_classes/trainer
- IPEX Optimization Guide: https://intel.github.io/intel-extension-for-pytorch/cpu/latest/tutorials/optimization.html
