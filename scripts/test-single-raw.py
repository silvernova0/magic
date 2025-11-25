#!/usr/bin/env python3
"""Test model and save RAW output (even if truncated)"""

import json
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
import intel_extension_for_pytorch as ipex

# Configuration
BASE_MODEL = "google/gemma-3-4b-it"
LORA_PATH = "./gemma-3-4b-commander-lora/final"
OUTPUT_DIR = "generated_decks/raw_test"

# Create output directory
import os
os.makedirs(OUTPUT_DIR, exist_ok=True)

print("=" * 72)
print("TESTING: Atraxa Counters Deck")
print("=" * 72)

# Load model
print("Loading model...")
tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
model = AutoModelForCausalLM.from_pretrained(
    LORA_PATH,
    torch_dtype=torch.bfloat16,
    device_map="xpu"
)
model = ipex.optimize(model, dtype=torch.bfloat16)
print("Model loaded on xpu:0\n")

# Generate
prompt = "Build a Commander deck with Atraxa, Praetors' Voice focused on counters at power level 8"
print(f"Prompt: {prompt}\n")
print("Generating...\n")

messages = [{"role": "user", "content": prompt}]
input_ids = tokenizer.apply_chat_template(
    messages,
    add_generation_prompt=True,
    return_tensors="pt"
).to("xpu")

outputs = model.generate(
    input_ids,
    max_new_tokens=800,
    temperature=0.7,
    top_p=0.9,
    do_sample=True,
    pad_token_id=tokenizer.eos_token_id
)

raw_output = tokenizer.decode(outputs[0], skip_special_tokens=True)

# Save RAW output first
raw_path = os.path.join(OUTPUT_DIR, "atraxa_raw.txt")
with open(raw_path, 'w') as f:
    f.write(raw_output)
print(f"✅ Saved raw output: {raw_path}")

# Try to extract JSON
if "```json" in raw_output:
    json_str = raw_output.split("```json")[1].split("```")[0].strip()
elif raw_output.strip().startswith("{"):
    json_str = raw_output.strip()
else:
    # Find first { and take everything after
    start = raw_output.find("{")
    if start >= 0:
        json_str = raw_output[start:].strip()
    else:
        json_str = raw_output

# Save extracted JSON attempt
json_path = os.path.join(OUTPUT_DIR, "atraxa_extracted.json")
with open(json_path, 'w') as f:
    f.write(json_str)
print(f"✅ Saved extracted JSON: {json_path}")

# Show preview
print("\n" + "=" * 72)
print("RAW OUTPUT (first 500 chars):")
print("=" * 72)
print(raw_output[:500])
print("\n" + "=" * 72)
print("EXTRACTED JSON (first 500 chars):")
print("=" * 72)
print(json_str[:500])

print("\n" + "=" * 72)
print(f"Full raw output length: {len(raw_output)} chars")
print(f"Extracted JSON length: {len(json_str)} chars")
print("=" * 72)
