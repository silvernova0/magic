#!/usr/bin/env python3
"""Quick single deck test with complete output"""

import torch
import intel_extension_for_pytorch as ipex
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
import json

BASE_MODEL = "google/gemma-3-4b-it"
LORA_PATH = "./gemma-3-4b-commander-lora/final"

print("Loading model...")
tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)

base_model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    torch_dtype=torch.bfloat16,
    device_map="cpu",
    trust_remote_code=True
)

model = PeftModel.from_pretrained(base_model, LORA_PATH)
model = model.merge_and_unload()
model = model.to("xpu")
model = ipex.optimize(model, dtype=torch.bfloat16)
model.eval()

print(f"Model ready!\n")

# Test
prompt = "Build a Commander deck with The Ur-Dragon focused on tribal dragons at power level 7"

print(f"Prompt: {prompt}\n")
inputs = tokenizer(prompt, return_tensors="pt").to("xpu")

print("Generating (max 1000 tokens)...")
with torch.no_grad():
    outputs = model.generate(
        **inputs,
        max_new_tokens=1000,
        temperature=0.7,
        top_p=0.9,
        do_sample=True,
        pad_token_id=tokenizer.eos_token_id,
        eos_token_id=tokenizer.eos_token_id
    )

generated = tokenizer.decode(outputs[0], skip_special_tokens=True)
generated_only = generated[len(prompt):].strip()

# Strip "model" prefix
if generated_only.startswith('model'):
    generated_only = generated_only[5:].strip()

print(f"\n{'='*70}")
print("COMPLETE OUTPUT:")
print(f"{'='*70}")
print(generated_only)
print(f"\n{'='*70}")
print(f"Tokens generated: {len(outputs[0]) - len(inputs['input_ids'][0])}")

# Try to parse
try:
    parsed = json.loads(generated_only)
    print("\n✅ Valid JSON!")
    print(f"Commander: {parsed.get('commander')}")
    print(f"Strategy: {parsed.get('strategy')}")
    print(f"Power Level: {parsed.get('power_level')}")
    print(f"Bracket: {parsed.get('bracket')}")
    if 'card_selection' in parsed:
        print(f"Card categories: {len(parsed['card_selection'])}")
    if 'priority_cards' in parsed:
        print(f"Priority cards: {len(parsed['priority_cards'])}")
except Exception as e:
    print(f"\n❌ JSON parsing failed: {e}")
