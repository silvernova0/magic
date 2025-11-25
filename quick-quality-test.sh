#!/bin/bash
# Quick quality test - generate 5 diverse decks and analyze

echo "========================================================================"
echo "QUICK QUALITY TEST - 5 Commanders"
echo "========================================================================"
echo ""

VENV="/home/social/.virtualenvs/magicapp/bin/activate"
OUTPUT_DIR="generated_decks/quick_test"
mkdir -p "$OUTPUT_DIR"

source "$VENV"

# Test cases
declare -a PROMPTS=(
    "Build a Commander deck with Atraxa, Praetors' Voice focused on counters at power level 8"
    "Build a Commander deck with The Ur-Dragon focused on tribal dragons at power level 7"
    "Build a Commander deck with Kinnan, Bonder Prodigy focused on combo at power level 9"
    "Build a Commander deck with Krenko, Mob Boss focused on tribal goblins at power level 5"
    "Build a Commander deck with Muldrotha, the Gravetide focused on value at power level 7"
)

declare -a NAMES=(
    "atraxa-counters"
    "urdragon-tribal"
    "kinnan-combo"
    "krenko-goblins"
    "muldrotha-value"
)

for i in "${!PROMPTS[@]}"; do
    NAME="${NAMES[$i]}"
    PROMPT="${PROMPTS[$i]}"
    
    echo "========================================================================"
    echo "TEST $((i+1))/5: $NAME"
    echo "========================================================================"
    echo "Prompt: $PROMPT"
    echo ""
    
    # Run generation
    python3 - <<PY
import torch
import intel_extension_for_pytorch as ipex
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
import json, re

BASE_MODEL = "google/gemma-3-4b-it"
LORA_PATH = "./gemma-3-4b-commander-lora/final"

print("Loading model...")
tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
base_model = AutoModelForCausalLM.from_pretrained(BASE_MODEL, torch_dtype=torch.bfloat16, device_map="cpu", trust_remote_code=True)
model = PeftModel.from_pretrained(base_model, LORA_PATH)
model = model.merge_and_unload()
model = model.to("xpu")
model = ipex.optimize(model, dtype=torch.bfloat16)
model.eval()

prompt = "$PROMPT"
inputs = tokenizer(prompt, return_tensors="pt").to("xpu")

print("Generating...")
with torch.no_grad():
    outputs = model.generate(**inputs, max_new_tokens=800, temperature=0.7, top_p=0.9, do_sample=True, pad_token_id=tokenizer.eos_token_id, eos_token_id=tokenizer.eos_token_id)

generated = tokenizer.decode(outputs[0], skip_special_tokens=True)[len(prompt):].strip()
if generated.startswith('model'):
    generated = generated[5:].strip()

# Try to parse
json_start = generated.find('{')
json_end = generated.rfind('}') + 1
if json_start >= 0 and json_end > json_start:
    json_str = generated[json_start:json_end]
    try:
        parsed = json.loads(json_str)
        print("\n✅ Valid JSON!")
        print(f"Commander: {parsed.get('commander')}")
        print(f"Strategy: {parsed.get('strategy')}")
        print(f"Bracket: {parsed.get('bracket')}")
        if 'card_selection' in parsed:
            print(f"Categories: {len(parsed['card_selection'])}")
        if 'priority_cards' in parsed:
            print(f"Priority cards: {len(parsed['priority_cards'])}")
        
        # Save
        with open("$OUTPUT_DIR/${NAME}.json", 'w') as f:
            json.dump(parsed, f, indent=2)
        print(f"\n💾 Saved to: $OUTPUT_DIR/${NAME}.json")
    except:
        print("\n❌ JSON parse failed (truncated)")
        print(f"First 200 chars: {generated[:200]}")
else:
    print("\n❌ No JSON found in output")
PY
    
    echo ""
    echo "Waiting 2 seconds..."
    sleep 2
done

echo ""
echo "========================================================================"
echo "SUMMARY"
echo "========================================================================"
ls -1 "$OUTPUT_DIR"/*.json 2>/dev/null | wc -l | xargs echo "Decks generated:"
echo ""
echo "Results in: $OUTPUT_DIR/"
