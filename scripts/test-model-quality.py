#!/usr/bin/env python3
"""
Test Gemma model with various commanders and strategies
Generates multiple decks and analyzes quality
"""

import torch
import intel_extension_for_pytorch as ipex
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
import json
import re
from pathlib import Path
from datetime import datetime

BASE_MODEL = "google/gemma-3-4b-it"
LORA_PATH = "./gemma-3-4b-commander-lora/final"
OUTPUT_DIR = "generated_decks/quality_test"

# Diverse test cases covering different strategies and power levels
TEST_CASES = [
    {
        "name": "atraxa-counters-high",
        "prompt": "Build a Commander deck with Atraxa, Praetors' Voice focused on counters at power level 8",
        "expected": {"strategy": "counters", "bracket": 4, "focus": "proliferate"}
    },
    {
        "name": "ur-dragon-tribal",
        "prompt": "Build a Commander deck with The Ur-Dragon focused on tribal dragons at power level 7",
        "expected": {"strategy": "tribal", "bracket": 4, "focus": "dragons"}
    },
    {
        "name": "korvold-aristocrats",
        "prompt": "Build a Commander deck with Korvold, Fae-Cursed King focused on aristocrats at power level 6",
        "expected": {"strategy": "aristocrats", "bracket": 3, "focus": "sacrifice"}
    },
    {
        "name": "kinnan-combo-cedh",
        "prompt": "Build a Commander deck with Kinnan, Bonder Prodigy focused on combo at power level 9",
        "expected": {"strategy": "combo", "bracket": 5, "focus": "fast mana"}
    },
    {
        "name": "edgar-markov-aggro",
        "prompt": "Build a Commander deck with Edgar Markov focused on vampire tribal at power level 7",
        "expected": {"strategy": "tribal", "bracket": 4, "focus": "vampires"}
    },
    {
        "name": "muldrotha-value",
        "prompt": "Build a Commander deck with Muldrotha, the Gravetide focused on value at power level 7",
        "expected": {"strategy": "midrange", "bracket": 4, "focus": "graveyard"}
    },
    {
        "name": "krenko-goblins",
        "prompt": "Build a Commander deck with Krenko, Mob Boss focused on tribal goblins at power level 5",
        "expected": {"strategy": "tribal", "bracket": 2, "focus": "goblins"}
    },
    {
        "name": "baral-control",
        "prompt": "Build a Commander deck with Baral, Chief of Compliance focused on control at power level 7",
        "expected": {"strategy": "control", "bracket": 4, "focus": "counterspells"}
    },
    {
        "name": "tymna-thrasios-cedh",
        "prompt": "Build a Commander deck with Tymna the Weaver and Thrasios, Triton Hero focused on combo at power level 10",
        "expected": {"strategy": "combo", "bracket": 5, "focus": "fast combo"}
    },
    {
        "name": "gitrog-lands",
        "prompt": "Build a Commander deck with The Gitrog Monster focused on lands at power level 8",
        "expected": {"strategy": "combo", "bracket": 4, "focus": "lands matter"}
    }
]

def load_model():
    """Load model once"""
    print("Loading Gemma 3 4B model...")
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
    
    base_model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        torch_dtype=torch.bfloat16,
        device_map="cpu",
        trust_remote_code=True
    )
    
    model = PeftModel.from_pretrained(base_model, LORA_PATH)
    print("Merging LoRA weights...")
    model = model.merge_and_unload()
    model = model.to("xpu")
    model = ipex.optimize(model, dtype=torch.bfloat16)
    model.eval()
    
    print(f"✅ Model ready on {next(model.parameters()).device}\n")
    return model, tokenizer

def generate_deck(model, tokenizer, prompt):
    """Generate deck structure"""
    inputs = tokenizer(prompt, return_tensors="pt").to("xpu")
    
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
    
    if generated_only.startswith('model'):
        generated_only = generated_only[5:].strip()
    
    return generated_only, len(outputs[0]) - len(inputs['input_ids'][0])

def parse_output(text):
    """Parse and clean model output"""
    try:
        json_start = text.find('{')
        json_end = text.rfind('}') + 1
        
        if json_start < 0 or json_end <= json_start:
            return None
        
        json_str = text[json_start:json_end]
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            # Try to reconstruct from partial output
            match = re.search(r'{.*?"card_selection":\s*{.*?}\s*}', text, re.DOTALL)
            if match:
                base_json = match.group(0)
                
                # Extract priority cards
                cards_match = re.search(r'"priority_cards":\s*\[(.*?)\]', text, re.DOTALL)
                if cards_match:
                    cards_str = cards_match.group(1)
                    cards = re.findall(r'"([^"]+)"', cards_str)
                    
                    unique_cards = []
                    seen = set()
                    for card in cards:
                        if card not in seen and not card.startswith('A-'):
                            unique_cards.append(card)
                            seen.add(card)
                        if len(unique_cards) >= 20:
                            break
                    
                    cards_json = '[\n    ' + ',\n    '.join(f'"{c}"' for c in unique_cards) + '\n  ]'
                    complete = base_json + ',\n  "priority_cards": ' + cards_json + '\n}'
                    return json.loads(complete)
            
            return None
    except Exception as e:
        return None

def analyze_deck(parsed, expected, test_name):
    """Analyze deck quality and compare to expectations"""
    issues = []
    notes = []
    
    if not parsed:
        return {
            "status": "failed",
            "error": "Failed to parse JSON",
            "issues": ["Parse failure"],
            "notes": []
        }
    
    # Check required fields
    required = ["commander", "strategy", "power_level", "bracket", "card_selection"]
    missing = [f for f in required if f not in parsed]
    if missing:
        issues.append(f"Missing fields: {', '.join(missing)}")
    
    # Strategy match
    if "strategy" in parsed and parsed["strategy"] != expected["strategy"]:
        issues.append(f"Strategy mismatch: got '{parsed['strategy']}', expected '{expected['strategy']}'")
    else:
        notes.append(f"✓ Strategy correct: {parsed.get('strategy')}")
    
    # Bracket match
    if "bracket" in parsed:
        if parsed["bracket"] != expected["bracket"]:
            issues.append(f"Bracket off: got {parsed['bracket']}, expected {expected['bracket']}")
        else:
            notes.append(f"✓ Bracket correct: {parsed['bracket']}")
    
    # Card selection analysis
    if "card_selection" in parsed:
        categories = list(parsed["card_selection"].keys())
        notes.append(f"✓ {len(categories)} card categories")
        
        # Count total cards
        total = 0
        for cat, data in parsed["card_selection"].items():
            if isinstance(data, dict) and "count" in data:
                total += data["count"]
        
        notes.append(f"Card selection total: {total}/99")
        if total > 100:
            issues.append(f"Too many cards in selection: {total}")
        elif total < 50:
            issues.append(f"Too few cards in selection: {total}")
    
    # Priority cards
    if "priority_cards" in parsed:
        priority = parsed["priority_cards"]
        if isinstance(priority, list):
            notes.append(f"✓ {len(priority)} priority cards")
            
            # Check for Arena cards
            arena_cards = [c for c in priority if c.startswith('A-')]
            if arena_cards:
                issues.append(f"Contains {len(arena_cards)} Arena-only cards")
        else:
            issues.append("priority_cards is not a list")
    
    status = "passed" if not issues else "failed"
    
    return {
        "status": status,
        "issues": issues,
        "notes": notes,
        "parsed": parsed
    }

def main():
    print("="*70)
    print("GEMMA 3 4B MODEL - QUALITY TEST SUITE")
    print("="*70)
    print(f"Test cases: {len(TEST_CASES)}")
    print(f"Output directory: {OUTPUT_DIR}\n")
    
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    
    # Load model once
    model, tokenizer = load_model()
    
    results = []
    passed = 0
    failed = 0
    
    for i, test in enumerate(TEST_CASES, 1):
        print(f"\n{'='*70}")
        print(f"TEST {i}/{len(TEST_CASES)}: {test['name']}")
        print(f"{'='*70}")
        print(f"Prompt: {test['prompt']}")
        print(f"Expected: {test['expected']}\n")
        
        # Generate
        output, tokens = generate_deck(model, tokenizer, test['prompt'])
        print(f"Generated {tokens} tokens")
        
        # Parse
        parsed = parse_output(output)
        
        # Analyze
        analysis = analyze_deck(parsed, test['expected'], test['name'])
        
        # Report
        print(f"\nStatus: {analysis['status'].upper()}")
        
        if analysis.get('notes'):
            print("\nNotes:")
            for note in analysis['notes']:
                print(f"  {note}")
        
        if analysis.get('issues'):
            print("\n❌ Issues:")
            for issue in analysis['issues']:
                print(f"  - {issue}")
            failed += 1
        else:
            print("\n✅ All checks passed!")
            passed += 1
        
        # Save
        result = {
            "test_name": test['name'],
            "prompt": test['prompt'],
            "expected": test['expected'],
            "raw_output": output[:500] + "..." if len(output) > 500 else output,
            "parsed": analysis.get('parsed'),
            "analysis": {
                "status": analysis['status'],
                "issues": analysis['issues'],
                "notes": analysis['notes']
            },
            "tokens": tokens,
            "timestamp": datetime.now().isoformat()
        }
        results.append(result)
        
        output_file = Path(OUTPUT_DIR) / f"{test['name']}.json"
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        print(f"\n💾 Saved to: {output_file}")
    
    # Summary
    print(f"\n{'='*70}")
    print("FINAL SUMMARY")
    print(f"{'='*70}")
    print(f"Total tests: {len(TEST_CASES)}")
    print(f"✅ Passed: {passed} ({passed/len(TEST_CASES)*100:.1f}%)")
    print(f"❌ Failed: {failed} ({failed/len(TEST_CASES)*100:.1f}%)")
    
    # Save summary
    summary_file = Path(OUTPUT_DIR) / "summary.json"
    summary = {
        "timestamp": datetime.now().isoformat(),
        "total": len(TEST_CASES),
        "passed": passed,
        "failed": failed,
        "pass_rate": passed / len(TEST_CASES),
        "results": results
    }
    
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n💾 Summary saved to: {summary_file}")
    print(f"{'='*70}\n")

if __name__ == "__main__":
    main()
