#!/usr/bin/env python3
"""
Test trained Commander model with automatic validation against card database

Usage:
    python3 scripts/test-model-with-validation.py

Features:
- Generates decks with trained model
- Validates against MTGJson card database
- Checks for hallucinations, color identity violations, illegal cards
- Provides detailed error reports
"""

import json
import os
from collections import defaultdict
from pathlib import Path
import sys

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

# Add scripts directory to path for validator import
sys.path.append(str(Path(__file__).parent))
from validate_generated_deck import DeckValidator
from build_deck_from_structure import execute_plan, load_cards

class ValidatedDeckGenerator:
    def __init__(
        self,
        base_model_path=os.getenv('BASE_MODEL_PATH', 'models/qwen2.5-3b'),
        lora_path=os.getenv('LORA_PATH', 'models/commander-qwen-3b-v3/final'),
        device=os.getenv('MODEL_DEVICE', 'xpu')
    ):
        """Initialize model with validation"""
        print("Loading model...")
        self.device = device
        if self.device == 'xpu' and not torch.xpu.is_available():
            print("⚠️  XPU not available, falling back to CPU for testing.")
            self.device = 'cpu'
        
        # Load base model
        self.tokenizer = AutoTokenizer.from_pretrained(base_model_path)
        base_model = AutoModelForCausalLM.from_pretrained(
            base_model_path,
            torch_dtype=torch.bfloat16 if self.device != 'cpu' else torch.float32,
            device_map=self.device if self.device != 'cpu' else None
        )
        if self.device == 'cpu':
            base_model.to('cpu')
        
        # Load LoRA adapter
        self.model = PeftModel.from_pretrained(base_model, lora_path)
        self.model.eval()
        
        # Initialize validator
        self.validator = DeckValidator()
        try:
            self.card_pool = load_cards()
        except SystemExit as exc:
            print(f"⚠️  {exc}. Structured deck execution disabled.")
            self.card_pool = None

        print("✅ Model and validator loaded\n")
    
    def generate_deck(self, prompt: str, max_length=2048, temperature=0.7):
        """Generate deck with model"""
        # Format as instruction
        instruction = f"""<|im_start|>system
You are an expert Magic: The Gathering Commander deck builder.
<|im_end|>
<|im_start|>user
{prompt}
<|im_end|>
<|im_start|>assistant
"""
        
        # Tokenize
        inputs = self.tokenizer(instruction, return_tensors='pt')
        inputs = {k: v.to(self.model.device) for k, v in inputs.items()}
        
        # Generate
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_length=max_length,
                temperature=temperature,
                do_sample=True,
                top_p=0.9,
                pad_token_id=self.tokenizer.eos_token_id
            )
        
        # Decode
        generated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Extract just the assistant's response
        if '<|im_start|>assistant' in generated_text:
            deck_text = generated_text.split('<|im_start|>assistant')[1].strip()
        else:
            deck_text = generated_text
        
        return deck_text
    
    def generate_and_validate(self, prompt: str, save_path=None):
        """Generate deck and validate it"""
        print(f"{'='*60}")
        print(f"PROMPT: {prompt}")
        print(f"{'='*60}\n")
        
        print("Generating deck...")
        deck_text = self.generate_deck(prompt)
        
        print("\n" + "="*60)
        print("GENERATED DECK:")
        print("="*60)
        print(deck_text)
        
        structured_plan = None
        structured_deck_text = None
        if self.card_pool:
            try:
                maybe_json = json.loads(deck_text)
                if isinstance(maybe_json, dict) and maybe_json.get('card_selection'):
                    structured_plan = maybe_json
            except json.JSONDecodeError:
                structured_plan = None

        if structured_plan and self.card_pool:
            try:
                print("\nExecuting structured deck plan via card database...")
                deck_result = execute_plan(structured_plan, cards=self.card_pool)
                structured_deck_text = format_deck_result(deck_result)
                final_deck_text = structured_deck_text
            except Exception as exc:
                print(f"⚠️  Structured execution failed: {exc}")
                structured_plan = None
                final_deck_text = deck_text
        else:
            final_deck_text = deck_text

        # Validate
        result = self.validator.validate_deck(final_deck_text)

        # Save if requested
        if save_path:
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(f"Prompt: {prompt}\n\n")
                if structured_plan:
                    f.write("Structured Plan:\n")
                    f.write(json.dumps(structured_plan, indent=2))
                    f.write("\n\nConverted Deck:\n")
                    f.write(structured_deck_text or "(execution failed)\n")
                else:
                    f.write(deck_text)
                f.write(f"\n\n{'='*60}\n")
                f.write(f"VALIDATION RESULTS\n")
                f.write(f"{'='*60}\n")
                f.write(f"Valid: {result['valid']}\n")
                if result['errors']:
                    f.write(f"\nErrors:\n")
                    for error in result['errors']:
                        f.write(f"  - {error}\n")
                if result['warnings']:
                    f.write(f"\nWarnings:\n")
                    for warning in result['warnings']:
                        f.write(f"  - {warning}\n")
            print(f"\n💾 Saved to: {save_path}")
        
        return deck_text, result


def main():
    """Run test suite with validation"""
    
    # Initialize generator
    generator = ValidatedDeckGenerator()
    
    # Test cases
    test_cases = [
        {
            'prompt': "Build a Commander deck with The Ur-Dragon focused on tribal Dragons with ramp and card draw.",
            'name': 'ur-dragon-tribal'
        },
        {
            'prompt': "Build a Commander deck with Atraxa, Praetors' Voice focused on +1/+1 counters and proliferate.",
            'name': 'atraxa-counters'
        },
        {
            'prompt': "Build a budget Commander deck with Krenko, Mob Boss focused on goblins tribal aggro under $100.",
            'name': 'krenko-budget'
        },
        {
            'prompt': "Build a cEDH Commander deck with Tymna the Weaver and Thrasios, Triton Hero focused on control and combo.",
            'name': 'tymna-thrasios-cedh'
        },
        {
            'prompt': "Build a Commander deck with Muldrotha, the Gravetide focused on graveyard value and self-mill.",
            'name': 'muldrotha-graveyard'
        }
    ]
    
    results = []
    output_dir = Path('generated_decks/validated')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n\n{'#'*60}")
        print(f"TEST {i}/{len(test_cases)}: {test['name']}")
        print(f"{'#'*60}\n")
        
        save_path = output_dir / f"{test['name']}.txt"
        deck_text, validation = generator.generate_and_validate(
            test['prompt'],
            save_path=save_path
        )
        
        results.append({
            'name': test['name'],
            'valid': validation['valid'],
            'stats': validation['stats']
        })
        
        # Wait between tests to avoid memory issues
        import time
        if i < len(test_cases):
            print("\n⏳ Waiting 5 seconds before next test...")
            time.sleep(5)
    
    # Summary
    print(f"\n\n{'='*60}")
    print(f"VALIDATION SUMMARY")
    print(f"{'='*60}\n")
    
    valid_count = sum(1 for r in results if r['valid'])
    
    for result in results:
        status = "✅ VALID" if result['valid'] else "❌ INVALID"
        print(f"{status} - {result['name']}")
        print(f"  Cards: {result['stats']['total_cards']}")
        print(f"  Hallucinated: {result['stats']['hallucinated']}")
        print(f"  Illegal: {result['stats']['illegal']}")
        print(f"  Color violations: {result['stats']['color_violations']}")
        print()
    
    print(f"Overall: {valid_count}/{len(results)} decks passed validation")
    
    if valid_count == len(results):
        print("\n🎉 ALL DECKS VALID!")
    elif valid_count == 0:
        print("\n⚠️  NO DECKS PASSED VALIDATION - Model needs more training")
    else:
        print(f"\n⚠️  {len(results) - valid_count} decks failed validation - Model needs improvement")


if __name__ == '__main__':
    main()


def format_deck_result(deck_result):
    commander = deck_result.get('commander')
    cards = deck_result.get('cards', [])
    sections = defaultdict(list)
    for entry in cards:
        role = entry.get('role') or 'Deck'
        sections[role].append(entry.get('name', 'Unknown Card'))

    lines = []
    if commander:
        lines.append('Commander:')
        lines.append(f"1x {commander}")
        lines.append('')

    for role, names in sections.items():
        lines.append(f"{role.title() if role else 'Deck'}:")
        for name in names:
            lines.append(f"1x {name}")
        lines.append('')

    return '\n'.join(lines).strip()
