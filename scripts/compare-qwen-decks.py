#!/usr/bin/env python3
"""
Test the fine-tuned Qwen 2.5 3B Commander deck builder model.
Loads the model with LoRA adapters and generates sample decks.
"""

import torch
import intel_extension_for_pytorch as ipex
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
import json
import time
from pathlib import Path

# Configuration
BASE_MODEL = "Qwen/Qwen2.5-3B-Instruct"
LORA_PATH = "./qwen-2.5-3b-commander-lora/final"
OUTPUT_DIR = "./generated_decks/qwen_test"
MAX_NEW_TOKENS = 600
TEMPERATURE = 0.7
TOP_P = 0.9

def load_model():
    """Load base model and apply LoRA adapters"""
    print("🔄 Loading base model...")
    
    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
    
    # Load base model on XPU
    base_model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        torch_dtype=torch.bfloat16,
        device_map="xpu",
        trust_remote_code=True
    )
    
    # Apply IPEX optimization
    base_model = ipex.optimize(base_model, dtype=torch.bfloat16)
    
    print("🔧 Applying LoRA adapters...")
    # Load LoRA adapters
    model = PeftModel.from_pretrained(base_model, LORA_PATH)
    model.eval()
    
    print(f"✅ Model loaded on device: {next(model.parameters()).device}")
    
    return model, tokenizer

def format_prompt(commander: str, strategy: str, power_level: int):
    """Format instruction prompt for the model using chat template"""
    instruction = f"Build a Commander deck with {commander} focused on {strategy} at power level {power_level}"
    
    # Format as chat messages for Qwen
    messages = [
        {"role": "user", "content": instruction}
    ]
    
    return messages, instruction

def generate_deck(model, tokenizer, messages: list, instruction: str):
    """Generate a deck from the model"""
    print(f"\n📝 Prompt: {instruction}")
    
    # Apply chat template
    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )
    
    # Tokenize
    inputs = tokenizer(prompt, return_tensors="pt").to("xpu")
    
    # Generate
    start_time = time.time()
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=MAX_NEW_TOKENS,
            temperature=TEMPERATURE,
            top_p=TOP_P,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id
        )
    
    generation_time = time.time() - start_time
    
    # Decode
    generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
    
    # Extract just the generated output (remove prompt)
    if "assistant" in generated_text:
        parts = generated_text.split("assistant")
        output = parts[-1].strip() if len(parts) > 1 else generated_text
    else:
        output = generated_text
    
    print(f"⏱️  Generation time: {generation_time:.2f}s")
    print(f"📊 Output length: {len(output)} characters")
    
    return output, generation_time

def parse_json_output(output: str):
    """Try to parse the output as JSON"""
    try:
        # Try to find JSON in the output
        start = output.find('{')
        end = output.rfind('}') + 1
        if start >= 0 and end > start:
            json_str = output[start:end]
            parsed = json.loads(json_str)
            return parsed, None
        else:
            return None, "No JSON found in output"
    except json.JSONDecodeError as e:
        return None, f"JSON parse error: {str(e)}"

def validate_deck_structure(deck_json: dict):
    """Validate the deck structure matches training format"""
    issues = []
    
    # Check required top-level fields
    required_fields = ["commander", "strategy", "bracket", "power_level", "card_selection"]
    for field in required_fields:
        if field not in deck_json:
            issues.append(f"Missing required field: {field}")
    
    # Check card_selection structure
    if "card_selection" in deck_json:
        card_selection = deck_json["card_selection"]
        if not isinstance(card_selection, dict):
            issues.append("card_selection should be a dictionary")
        else:
            # Count total cards
            total_cards = 0
            for category, config in card_selection.items():
                if isinstance(config, dict) and "count" in config:
                    total_cards += config["count"]
            
            # Should be close to 99 (commander is separate)
            if total_cards < 95 or total_cards > 100:
                issues.append(f"Total card count is {total_cards}, expected ~99")
    
    return issues

def save_result(test_name: str, prompt: str, output: str, deck_json: dict, 
                validation_issues: list, generation_time: float):
    """Save test results to file"""
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    
    result = {
        "test_name": test_name,
        "prompt": prompt,
        "raw_output": output,
        "parsed_json": deck_json,
        "validation_issues": validation_issues,
        "generation_time": generation_time,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    output_path = Path(OUTPUT_DIR) / f"{test_name}.json"
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"💾 Saved to: {output_path}")

def run_test(model, tokenizer, test_name: str, commander: str, strategy: str, power_level: int):
    """Run a single test case"""
    print(f"\n{'='*60}")
    print(f"TEST: {test_name}")
    print(f"{'='*60}")
    
    # Generate prompt
    messages, instruction = format_prompt(commander, strategy, power_level)
    
    # Generate output
    output, gen_time = generate_deck(model, tokenizer, messages, instruction)
    
    # Parse JSON
    deck_json, parse_error = parse_json_output(output)
    
    if parse_error:
        print(f"⚠️  {parse_error}")
        print(f"\nRaw output preview:\n{output[:500]}...")
        validation_issues = [parse_error]
    else:
        print("✅ JSON parsed successfully")
        
        # Validate structure
        validation_issues = validate_deck_structure(deck_json)
        if validation_issues:
            print(f"⚠️  Validation issues:")
            for issue in validation_issues:
                print(f"   - {issue}")
        else:
            print("✅ Structure validation passed")
        
        # Show summary
        if "card_selection" in deck_json:
            total_cards = sum(
                cfg.get("count", 0) 
                for cfg in deck_json["card_selection"].values() 
                if isinstance(cfg, dict)
            )
            print(f"\n📊 Deck Summary:")
            print(f"   Commander: {deck_json.get('commander', 'N/A')}")
            print(f"   Strategy: {deck_json.get('strategy', 'N/A')}")
            print(f"   Bracket: {deck_json.get('bracket', 'N/A')}")
            print(f"   Power Level: {deck_json.get('power_level', 'N/A')}")
            print(f"   Total Cards: {total_cards}")
            print(f"   Categories: {len(deck_json['card_selection'])}")
    
    # Save results
    save_result(test_name, instruction, output, deck_json, validation_issues, gen_time)
    
    return validation_issues == []

def main():
    print("🎴 Qwen 2.5 3B Commander Model Test Suite\n")
    
    # Load model
    model, tokenizer = load_model()
    
    # Test cases
    test_cases = [
        {
            "name": "atraxa-counters",
            "commander": "Atraxa, Praetors' Voice",
            "strategy": "Counters/Proliferate",
            "power_level": 4,
        },
        {
            "name": "ur-dragon-tribal",
            "commander": "The Ur-Dragon",
            "strategy": "Dragon Tribal",
            "power_level": 3,
        },
        {
            "name": "korvold-aristocrats",
            "commander": "Korvold, Fae-Cursed King",
            "strategy": "Aristocrats/Sacrifice",
            "power_level": 3,
        },
    ]
    
    # Run tests
    results = []
    for test in test_cases:
        success = run_test(
            model, tokenizer,
            test["name"],
            test["commander"],
            test["strategy"],
            test["power_level"]
        )
        results.append((test["name"], success))
    
    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {name}")
    
    print(f"\nResults: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 All tests passed!")
    else:
        print("\n⚠️  Some tests failed. Check individual results in generated_decks/qwen_test/")

if __name__ == "__main__":
    main()
