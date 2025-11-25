#!/usr/bin/env python3
"""
Comprehensive test suite for trained Gemma 3 4B Commander deck builder
Tests multiple commanders and strategies, saves outputs for analysis
"""

import torch
import intel_extension_for_pytorch as ipex
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
import json
import os
from datetime import datetime

BASE_MODEL = "google/gemma-3-4b-it"
LORA_PATH = "./gemma-3-4b-commander-lora/final"
OUTPUT_DIR = "./generated_decks/gemma_test"

# Test cases covering different strategies and power levels
TEST_CASES = [
    {
        "name": "atraxa-counters",
        "prompt": "Build a Commander deck with Atraxa, Praetors' Voice focused on counters at power level 8",
        "expected_strategy": "counters",
        "expected_bracket": 4
    },
    {
        "name": "ur-dragon-tribal",
        "prompt": "Build a Commander deck with The Ur-Dragon focused on tribal dragons at power level 7",
        "expected_strategy": "tribal",
        "expected_bracket": 3
    },
    {
        "name": "korvold-aristocrats",
        "prompt": "Build a Commander deck with Korvold, Fae-Cursed King focused on aristocrats at power level 6",
        "expected_strategy": "aristocrats",
        "expected_bracket": 2
    },
    {
        "name": "kinnan-combo",
        "prompt": "Build a Commander deck with Kinnan, Bonder Prodigy focused on combo at power level 9",
        "expected_strategy": "combo",
        "expected_bracket": 4
    },
    {
        "name": "gishath-tribal",
        "prompt": "Build a Commander deck with Gishath, Sun's Avatar focused on tribal dinosaurs at power level 6",
        "expected_strategy": "tribal",
        "expected_bracket": 2
    }
]

def setup_model():
    """Load and prepare model for inference"""
    print("Loading and merging model...")
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
    
    # Load base model on CPU first
    base_model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        torch_dtype=torch.bfloat16,
        device_map="cpu",
        trust_remote_code=True
    )
    
    # Load and merge LoRA weights
    model = PeftModel.from_pretrained(base_model, LORA_PATH)
    print("Merging LoRA weights...")
    model = model.merge_and_unload()
    
    # Move to XPU and optimize
    print("Moving to XPU...")
    model = model.to("xpu")
    model = ipex.optimize(model, dtype=torch.bfloat16)
    model.eval()
    
    print(f"Model ready on: {next(model.parameters()).device}\n")
    return model, tokenizer

def generate_deck(model, tokenizer, prompt, max_tokens=800):
    """Generate deck structure from prompt"""
    inputs = tokenizer(prompt, return_tensors="pt").to("xpu")
    
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            temperature=0.7,
            top_p=0.9,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id,
            eos_token_id=tokenizer.eos_token_id
        )
    
    generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
    
    # Extract just the generated part (remove the prompt)
    generated_only = generated_text[len(prompt):].strip()
    
    return generated_only, len(outputs[0]) - len(inputs['input_ids'][0])

def parse_output(text):
    """Try to parse JSON output from model"""
    try:
        # Strip "model" prefix if present
        text = text.strip()
        if text.startswith('model'):
            text = text[5:].strip()
        
        # Try to find JSON in the output
        json_start = text.find('{')
        json_end = text.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_str = text[json_start:json_end]
            # Try to parse even if incomplete
            return json.loads(json_str)
        else:
            return None
    except json.JSONDecodeError as e:
        # If truncated, try to close the JSON
        try:
            # Find last complete key-value pair
            last_comma = text.rfind(',')
            if last_comma > 0:
                truncated = text[:last_comma] + '\n    }\n  }\n}'
                return json.loads(truncated)
        except:
            pass
        return None

def validate_output(parsed, test_case):
    """Validate that output matches expected format and content"""
    issues = []
    
    if not parsed:
        issues.append("Failed to parse JSON")
        return issues
    
    # Check required fields
    required_fields = ["commander", "strategy", "power_level", "bracket", "card_selection"]
    for field in required_fields:
        if field not in parsed:
            issues.append(f"Missing required field: {field}")
    
    # Check commander matches
    if "commander" in parsed:
        expected_commander = test_case["prompt"].split("with ")[1].split(" focused")[0]
        if expected_commander not in parsed["commander"]:
            issues.append(f"Commander mismatch: expected '{expected_commander}', got '{parsed['commander']}'")
    
    # Check strategy matches
    if "strategy" in parsed and "expected_strategy" in test_case:
        if parsed["strategy"] != test_case["expected_strategy"]:
            issues.append(f"Strategy mismatch: expected '{test_case['expected_strategy']}', got '{parsed['strategy']}'")
    
    # Check bracket is reasonable
    if "bracket" in parsed:
        if not isinstance(parsed["bracket"], int) or not 1 <= parsed["bracket"] <= 5:
            issues.append(f"Invalid bracket: {parsed['bracket']} (should be 1-5)")
    
    # Check card_selection structure
    if "card_selection" in parsed:
        if not isinstance(parsed["card_selection"], dict):
            issues.append("card_selection should be a dictionary")
        else:
            # Each category should have count and filters
            for category, data in parsed["card_selection"].items():
                if not isinstance(data, dict):
                    issues.append(f"card_selection.{category} should be a dictionary")
                elif "count" not in data:
                    issues.append(f"card_selection.{category} missing 'count' field")
                elif "filters" not in data:
                    issues.append(f"card_selection.{category} missing 'filters' field")
    
    return issues

def main():
    """Run comprehensive test suite"""
    print("="*70)
    print("GEMMA 3 4B COMMANDER DECK BUILDER - COMPREHENSIVE TEST")
    print("="*70)
    print(f"Test cases: {len(TEST_CASES)}")
    print(f"Output directory: {OUTPUT_DIR}")
    print("="*70 + "\n")
    
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Load model once
    model, tokenizer = setup_model()
    
    results = []
    
    for i, test_case in enumerate(TEST_CASES, 1):
        print(f"\n{'='*70}")
        print(f"TEST {i}/{len(TEST_CASES)}: {test_case['name']}")
        print(f"{'='*70}")
        print(f"Prompt: {test_case['prompt']}\n")
        
        # Generate
        output_text, token_count = generate_deck(model, tokenizer, test_case['prompt'])
        
        print(f"Generated {token_count} tokens")
        print(f"\nRaw Output:\n{'-'*70}")
        print(output_text)
        print(f"{'-'*70}\n")
        
        # Parse and validate
        parsed = parse_output(output_text)
        issues = validate_output(parsed, test_case)
        
        # Report validation
        if issues:
            print(f"❌ Validation Issues:")
            for issue in issues:
                print(f"   - {issue}")
        else:
            print(f"✅ Validation passed!")
        
        # Save results
        result = {
            "test_case": test_case['name'],
            "prompt": test_case['prompt'],
            "raw_output": output_text,
            "parsed_output": parsed,
            "token_count": token_count,
            "validation_issues": issues,
            "timestamp": datetime.now().isoformat()
        }
        results.append(result)
        
        # Save individual output
        output_file = os.path.join(OUTPUT_DIR, f"{test_case['name']}.json")
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"\n💾 Saved to: {output_file}")
    
    # Save summary
    summary_file = os.path.join(OUTPUT_DIR, "test_summary.json")
    summary = {
        "timestamp": datetime.now().isoformat(),
        "model": BASE_MODEL,
        "lora_path": LORA_PATH,
        "total_tests": len(TEST_CASES),
        "passed": sum(1 for r in results if not r['validation_issues']),
        "failed": sum(1 for r in results if r['validation_issues']),
        "results": results
    }
    
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    # Final summary
    print(f"\n{'='*70}")
    print("TEST SUMMARY")
    print(f"{'='*70}")
    print(f"Total tests: {summary['total_tests']}")
    print(f"✅ Passed: {summary['passed']}")
    print(f"❌ Failed: {summary['failed']}")
    print(f"\n💾 Summary saved to: {summary_file}")
    print(f"{'='*70}\n")

if __name__ == "__main__":
    main()
