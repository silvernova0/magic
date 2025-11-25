#!/usr/bin/env python3
"""Quick test to see raw model output"""

import torch
import intel_extension_for_pytorch as ipex
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel

BASE_MODEL = "google/gemma-3-4b-it"
LORA_PATH = "./gemma-3-4b-commander-lora/final"

print("Loading model...")
tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
base_model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    torch_dtype=torch.bfloat16,
    device_map="xpu",
    trust_remote_code=True
)
base_model = ipex.optimize(base_model, dtype=torch.bfloat16)
model = PeftModel.from_pretrained(base_model, LORA_PATH)
model.eval()

print(f"Model loaded on: {next(model.parameters()).device}\n")

# Test with simple prompt
prompt = "Build a Commander deck with Atraxa, Praetors' Voice focused on counters at power level 8"

print(f"Prompt: {prompt}\n")

# Try without chat template first
inputs = tokenizer(prompt, return_tensors="pt").to("xpu")

print(f"Input tokens: {inputs['input_ids'].shape[1]}")

with torch.no_grad():
    outputs = model.generate(
        **inputs,
        max_new_tokens=600,
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
