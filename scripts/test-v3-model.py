#!/usr/bin/env python3
"""
Test v3 trained Commander model that outputs structured JSON

The v3 model generates structured JSON with database query filters,
which are then executed against the Prisma database to build actual decks.

Usage:
    python3 scripts/test-v3-model.py
"""

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import os
import json
from pathlib import Path

class V3DeckGenerator:
    def __init__(
        self,
        base_model_path=os.getenv('BASE_MODEL_PATH', 'models/qwen2.5-3b'),
        lora_path=os.getenv('LORA_PATH', 'models/commander-qwen-3b-v3/final'),
        device=os.getenv('MODEL_DEVICE', 'xpu')
    ):
        """Initialize v3 model (structured JSON output)"""
        print("Loading v3 model...")
        self.device = device
        if self.device == 'xpu' and not torch.xpu.is_available():
            print("⚠️  XPU not available, falling back to CPU for testing.")
            self.device = 'cpu'
        
        # Load base model
        print(f"Loading base model from {base_model_path}...")
        self.tokenizer = AutoTokenizer.from_pretrained(base_model_path, trust_remote_code=True)
        base_model = AutoModelForCausalLM.from_pretrained(
            base_model_path,
            torch_dtype=torch.bfloat16 if self.device != 'cpu' else torch.float32,
            device_map=self.device if self.device != 'cpu' else None,
            trust_remote_code=True
        )
        if self.device == 'cpu':
            base_model.to('cpu')
        
        # Load LoRA adapter
        print(f"Loading LoRA adapter from {lora_path}...")
        self.model = PeftModel.from_pretrained(base_model, lora_path)
        self.model.eval()
        
        print("✅ v3 Model loaded\n")
    
    def generate_structure(self, prompt: str, max_new_tokens=600, temperature=0.7):
        """Generate structured JSON deck plan"""
        # Format as Qwen chat template
        messages = [
            {"role": "system", "content": "You are an expert Magic: The Gathering Commander deck builder. Generate structured JSON output with commander, strategy, bracket, power_level, and card_selection filters."},
            {"role": "user", "content": prompt}
        ]
        
        # Use chat template
        text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        
        # Tokenize
        inputs = self.tokenizer(text, return_tensors='pt')
        inputs = {k: v.to(self.model.device) for k, v in inputs.items()}
        
        # Generate
        print(f"Generating with max_new_tokens={max_new_tokens}, temperature={temperature}...")
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                do_sample=True,
                top_p=0.9,
                pad_token_id=self.tokenizer.eos_token_id
            )
        
        # Decode
        generated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Extract assistant response
        if '<|im_start|>assistant' in generated_text:
            response = generated_text.split('<|im_start|>assistant')[-1].strip()
        elif 'assistant\n' in generated_text:
            response = generated_text.split('assistant\n')[-1].strip()
        else:
            response = generated_text
        
        # Remove any trailing tags
        if '<|im_end|>' in response:
            response = response.split('<|im_end|>')[0].strip()
        
        return response
    
    def validate_json_structure(self, json_obj):
        """Validate that generated JSON has required fields"""
        errors = []
        warnings = []
        
        required_fields = ['commander', 'strategy', 'bracket', 'power_level', 'card_selection']
        for field in required_fields:
            if field not in json_obj:
                errors.append(f"Missing required field: {field}")
        
        # Validate card_selection structure
        if 'card_selection' in json_obj:
            card_sel = json_obj['card_selection']
            if not isinstance(card_sel, dict):
                errors.append("card_selection must be a dictionary")
            else:
                # Check that each category has count and filters
                for category, spec in card_sel.items():
                    if not isinstance(spec, dict):
                        errors.append(f"card_selection.{category} must be a dictionary")
                        continue
                    if 'count' not in spec:
                        errors.append(f"card_selection.{category} missing 'count'")
                    if 'filters' not in spec:
                        warnings.append(f"card_selection.{category} missing 'filters' (will use empty filters)")
        
        # Calculate total cards
        total_cards = 0
        if 'card_selection' in json_obj:
            for category, spec in json_obj['card_selection'].items():
                if isinstance(spec, dict) and 'count' in spec:
                    total_cards += spec['count']
        
        if total_cards != 100:
            warnings.append(f"Total cards is {total_cards}, expected 100")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'total_cards': total_cards
        }


def main():
    """Test v3 model JSON generation"""
    
    # Initialize generator
    generator = V3DeckGenerator()
    
    # Test cases
    test_cases = [
        {
            'prompt': "Build a Commander deck with The Ur-Dragon focused on tribal dragons at power level 7",
            'name': 'ur-dragon-tribal'
        },
        {
            'prompt': "Build a Commander deck with Atraxa, Praetors' Voice focused on +1/+1 counters at power level 8",
            'name': 'atraxa-counters'
        },
        {
            'prompt': "Build a Commander deck with Krenko, Mob Boss focused on goblins tribal at power level 6",
            'name': 'krenko-goblins'
        },
        {
            'prompt': "Build a Commander deck with Muldrotha, the Gravetide focused on graveyard value at power level 7",
            'name': 'muldrotha-graveyard'
        }
    ]
    
    output_dir = Path('generated_decks/v3_test')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    results = []
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{'='*70}")
        print(f"TEST {i}/{len(test_cases)}: {test['name']}")
        print(f"{'='*70}")
        print(f"Prompt: {test['prompt']}\n")
        
        # Generate
        json_text = generator.generate_structure(test['prompt'])
        
        print(f"\n{'='*70}")
        print("GENERATED OUTPUT:")
        print(f"{'='*70}")
        print(json_text)
        print()
        
        # Try to parse as JSON
        try:
            # Find JSON in output (might have extra text)
            json_start = json_text.find('{')
            json_end = json_text.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                print("❌ No JSON found in output")
                results.append({
                    'name': test['name'],
                    'valid': False,
                    'error': 'No JSON found in output',
                    'raw_output': json_text
                })
                continue
            
            json_str = json_text[json_start:json_end]
            deck_structure = json.loads(json_str)
            
            print(f"{'='*70}")
            print("PARSED JSON:")
            print(f"{'='*70}")
            print(json.dumps(deck_structure, indent=2))
            print()
            
            # Validate structure
            validation = generator.validate_json_structure(deck_structure)
            
            print(f"{'='*70}")
            print("VALIDATION:")
            print(f"{'='*70}")
            print(f"Valid: {validation['valid']}")
            print(f"Total cards: {validation['total_cards']}/100")
            
            if validation['errors']:
                print(f"\nErrors:")
                for error in validation['errors']:
                    print(f"  ❌ {error}")
            
            if validation['warnings']:
                print(f"\nWarnings:")
                for warning in validation['warnings']:
                    print(f"  ⚠️  {warning}")
            
            # Save
            save_path = output_dir / f"{test['name']}.json"
            with open(save_path, 'w') as f:
                json.dump(deck_structure, f, indent=2)
            print(f"\n💾 Saved to: {save_path}")
            
            results.append({
                'name': test['name'],
                'valid': validation['valid'],
                'total_cards': validation['total_cards'],
                'errors': validation['errors'],
                'warnings': validation['warnings']
            })
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing error: {e}")
            print(f"\nAttempted to parse:")
            print(json_text[json_start:json_end])
            
            results.append({
                'name': test['name'],
                'valid': False,
                'error': f'JSON parse error: {e}',
                'raw_output': json_text
            })
    
    # Summary
    print(f"\n\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}\n")
    
    valid_count = sum(1 for r in results if r.get('valid', False))
    
    for result in results:
        if result.get('valid'):
            status = "✅ VALID"
            print(f"{status} - {result['name']}")
            print(f"  Total cards: {result['total_cards']}/100")
            if result.get('warnings'):
                print(f"  Warnings: {len(result['warnings'])}")
        else:
            status = "❌ INVALID"
            print(f"{status} - {result['name']}")
            if 'error' in result:
                print(f"  Error: {result['error']}")
            elif result.get('errors'):
                print(f"  Errors: {len(result['errors'])}")
        print()
    
    print(f"Overall: {valid_count}/{len(results)} decks generated valid JSON")
    
    if valid_count == len(results):
        print("\n🎉 ALL DECKS GENERATED VALID JSON!")
        print("\nNext step: Implement database query executor to build actual decks from these structures.")
    elif valid_count == 0:
        print("\n⚠️  NO VALID JSON GENERATED - Model may need more training or different prompt format")
    else:
        print(f"\n⚠️  {len(results) - valid_count} decks failed - Model needs improvement")
    
    print(f"\n📁 Results saved to: {output_dir}/")


if __name__ == '__main__':
    main()
