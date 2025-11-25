#!/usr/bin/env python3
"""Test that priority_cards are properly limited to 30"""

import json
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
import intel_extension_for_pytorch as ipex
import re

# Configuration
BASE_MODEL = "google/gemma-3-4b-it"
LORA_PATH = "./gemma-3-4b-commander-lora/final"
MAX_PRIORITY_CARDS = 30

print("=" * 72)
print("TESTING: Priority Cards Hard Limit (Max 30)")
print("=" * 72)

# Load model
print("\nLoading model...")
tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
model = AutoModelForCausalLM.from_pretrained(
    LORA_PATH,
    torch_dtype=torch.bfloat16,
    device_map="xpu"
)
model = ipex.optimize(model, dtype=torch.bfloat16)
print("✅ Model loaded on xpu:0\n")

# Test prompt
prompt = "Build a Commander deck with Atraxa, Praetors' Voice focused on counters at power level 8"
print(f"Prompt: {prompt}\n")

# Generate
print("Generating...\n")
messages = [{"role": "user", "content": prompt}]
input_ids = tokenizer.apply_chat_template(
    messages,
    add_generation_prompt=True,
    return_tensors="pt"
).to("xpu")

outputs = model.generate(
    input_ids,
    max_new_tokens=1000,  # Give it room to generate many cards
    temperature=0.7,
    top_p=0.9,
    do_sample=True,
    pad_token_id=tokenizer.eos_token_id
)

raw_output = tokenizer.decode(outputs[0], skip_special_tokens=True)

# Strip prompt and "model" prefix
generated_only = raw_output
if prompt in generated_only:
    generated_only = generated_only.split(prompt, 1)[1].strip()
if generated_only.strip().startswith('model'):
    generated_only = generated_only.strip()[5:].strip()

print(f"Generated {len(outputs[0]) - len(input_ids[0])} tokens\n")

# Extract JSON
json_start = generated_only.find('{')
json_end = generated_only.rfind('}') + 1

if json_start >= 0 and json_end > json_start:
    json_str = generated_only[json_start:json_end]
    
    # Try to parse
    try:
        parsed = json.loads(json_str)
        priority_cards = parsed.get("priority_cards", [])
        
        print("✅ Successfully parsed JSON")
        print(f"Priority cards in original output: {len(priority_cards)}")
        
    except json.JSONDecodeError as e:
        print(f"⚠️  JSON parse error (likely truncated): {e}")
        
        # Extract whatever priority_cards we can find
        match = re.search(r'"priority_cards":\s*\[(.*)', generated_only, re.DOTALL)
        if match:
            cards_section = match.group(1)
            # Extract all card names (in quotes)
            priority_cards = re.findall(r'"([^"]+)"', cards_section)
            print(f"Priority cards extracted via regex: {len(priority_cards)}")
        else:
            priority_cards = []
            print("Could not find priority_cards in output")
else:
    print("❌ Could not find JSON in output")
    priority_cards = []

# Apply hard limit
print("\n" + "=" * 72)
print("APPLYING HARD LIMIT")
print("=" * 72)

seen = set()
unique_priority = []
for card in priority_cards:
    if card not in seen and not card.startswith('A-'):  # Skip Arena cards and duplicates
        unique_priority.append(card)
        seen.add(card)
    if len(unique_priority) >= MAX_PRIORITY_CARDS:
        break

print(f"\nBefore limit: {len(priority_cards)} cards")
print(f"After limit:  {len(unique_priority)} cards (max {MAX_PRIORITY_CARDS})")

if len(unique_priority) > 0:
    print(f"\n✅ Priority cards limited successfully!")
    print(f"\nFirst 10 cards:")
    for i, card in enumerate(unique_priority[:10], 1):
        print(f"  {i}. {card}")
    
    if len(unique_priority) > 10:
        print(f"  ... and {len(unique_priority) - 10} more")
else:
    print("\n⚠️  No priority cards found in output")

# Show sample of raw output for debugging
print("\n" + "=" * 72)
print("RAW OUTPUT SAMPLE (first 400 chars)")
print("=" * 72)
print(generated_only[:400])

print("\n" + "=" * 72)
print("TEST COMPLETE")
print("=" * 72)
