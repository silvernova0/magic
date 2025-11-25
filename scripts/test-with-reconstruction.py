#!/usr/bin/env python3
"""Test with proper stop conditions to prevent infinite loops"""

import torch
import intel_extension_for_pytorch as ipex
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
import json
import re

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

# Test with Atraxa
prompt = "Build a Commander deck with Atraxa, Praetors' Voice focused on counters at power level 8"

print(f"Prompt: {prompt}\n")
inputs = tokenizer(prompt, return_tensors="pt").to("xpu")

# Add stop strings for when model completes the JSON
# The model should stop after generating the closing brace
stop_strings = [
    '"notes"',  # Stop when it starts the notes field
    '}\n}',     # Stop on closing braces
    ']}\n',     # Alternative closing pattern
]

print("Generating (max 1000 tokens with early stopping)...")
with torch.no_grad():
    outputs = model.generate(
        **inputs,
        max_new_tokens=1000,
        temperature=0.7,
        top_p=0.9,
        do_sample=True,
        pad_token_id=tokenizer.eos_token_id,
        eos_token_id=tokenizer.eos_token_id,
        # Note: stop_strings not directly supported, we'll truncate manually
    )

generated = tokenizer.decode(outputs[0], skip_special_tokens=True)
generated_only = generated[len(prompt):].strip()

# Strip "model" prefix
if generated_only.startswith('model'):
    generated_only = generated_only[5:].strip()

print(f"\n{'='*70}")
print("RAW OUTPUT (first 2000 chars):")
print(f"{'='*70}")
print(generated_only[:2000])
print(f"\n{'='*70}")

# Try to extract just the valid JSON by finding where priority_cards ends
# Look for the pattern of 20 cards in the array
try:
    # Find the priority_cards array
    match = re.search(r'"priority_cards":\s*\[(.*?)\]', generated_only, re.DOTALL)
    if match:
        cards_str = match.group(1)
        # Count how many cards
        cards = re.findall(r'"([^"]+)"', cards_str)
        print(f"\nFound {len(cards)} priority cards (first 10):")
        for i, card in enumerate(cards[:10], 1):
            print(f"  {i}. {card}")
        
        # If we have around 20 cards, try to close the JSON properly
        if len(cards) >= 15:
            # Take first 20 unique cards
            unique_cards = []
            seen = set()
            for card in cards:
                if card not in seen:
                    unique_cards.append(card)
                    seen.add(card)
                if len(unique_cards) >= 20:
                    break
            
            # Reconstruct just the priority_cards array
            cards_json = '[\n    ' + ',\n    '.join(f'"{c}"' for c in unique_cards) + '\n  ]'
            
            # Find the card_selection part
            selection_match = re.search(r'"card_selection":\s*{.*?}\s*}', generated_only, re.DOTALL)
            if selection_match:
                # Build complete JSON
                complete_json = re.search(r'{.*?"card_selection":\s*{.*?}\s*}', generated_only, re.DOTALL)
                if complete_json:
                    base_json = complete_json.group(0)
                    # Close it properly
                    complete = base_json + ',\n  "priority_cards": ' + cards_json + '\n}'
                    
                    # Try to parse
                    parsed = json.loads(complete)
                    print(f"\n✅ RECONSTRUCTED VALID JSON!")
                    print(f"Commander: {parsed.get('commander')}")
                    print(f"Strategy: {parsed.get('strategy')}")
                    print(f"Power Level: {parsed.get('power_level')}")
                    print(f"Bracket: {parsed.get('bracket')}")
                    print(f"Card categories: {len(parsed.get('card_selection', {}))}")
                    print(f"Priority cards: {len(parsed.get('priority_cards', []))}")
                    
                    # Save to file
                    with open('generated_decks/gemma_test/atraxa-cleaned.json', 'w') as f:
                        json.dump(parsed, f, indent=2)
                    print(f"\n💾 Saved to: generated_decks/gemma_test/atraxa-cleaned.json")
                    
except Exception as e:
    print(f"\n❌ Reconstruction failed: {e}")
    import traceback
    traceback.print_exc()

print(f"\n{'='*70}")
print(f"Tokens generated: {len(outputs[0]) - len(inputs['input_ids'][0])}")
print(f"{'='*70}")
