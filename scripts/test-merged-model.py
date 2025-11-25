#!/usr/bin/env python3
"""Test with merged LoRA weights for faster inference"""

import torch
import intel_extension_for_pytorch as ipex
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel

BASE_MODEL = "google/gemma-3-4b-it"
LORA_PATH = "./gemma-3-4b-commander-lora/final"

print("Loading and merging model...")
tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)

# Load base model
base_model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    torch_dtype=torch.bfloat16,
    device_map="cpu",  # Load on CPU first
    trust_remote_code=True
)

# Load and MERGE LoRA weights
model = PeftModel.from_pretrained(base_model, LORA_PATH)
print("Merging LoRA weights...")
model = model.merge_and_unload()

# Now move to XPU and optimize
print("Moving to XPU...")
model = model.to("xpu")
model = ipex.optimize(model, dtype=torch.bfloat16)
model.eval()

print(f"Model ready on: {next(model.parameters()).device}\n")

# Test with simple prompt - try very short generation first
prompt = "Build a Commander deck with Atraxa, Praetors' Voice focused on counters at power level 8"

print(f"Prompt: {prompt}\n")

inputs = tokenizer(prompt, return_tensors="pt").to("xpu")

print(f"Input tokens: {inputs['input_ids'].shape[1]}")
print("Generating (max 100 tokens)...")

with torch.no_grad():
    outputs = model.generate(
        **inputs,
        max_new_tokens=100,  # Start with just 100 tokens
        temperature=0.7,
        top_p=0.9,
        do_sample=True,
        pad_token_id=tokenizer.eos_token_id,
        eos_token_id=tokenizer.eos_token_id
    )

generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)

print(f"\n{'='*60}")
print("GENERATED OUTPUT:")
print(f"{'='*60}")
print(generated_text)
print(f"\n{'='*60}")
print(f"Output length: {len(generated_text)} characters")
print(f"Output tokens: {outputs.shape[1]}")
