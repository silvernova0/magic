"""
Test trained Commander model with card validation
Generates decks and ensures all cards are real
"""
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import sys
from pathlib import Path

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent))
from card_validator import CardValidator, validate_and_correct_generation, create_constrained_generation_prompt

def load_model_with_lora(base_model_path, lora_path, device='xpu'):
    """Load base model and apply LoRA weights"""
    print(f"Loading base model from {base_model_path}...")
    
    base_model = AutoModelForCausalLM.from_pretrained(
        base_model_path,
        torch_dtype=torch.bfloat16,
        device_map=device,
        trust_remote_code=True
    )
    
    print(f"Loading LoRA adapters from {lora_path}...")
    model = PeftModel.from_pretrained(base_model, lora_path)
    model.eval()
    
    print("✓ Model loaded successfully")
    return model

def generate_deck_with_validation(model, tokenizer, validator, commander, theme, 
                                  max_new_tokens=1024, temperature=0.7):
    """Generate a deck and validate all cards"""
    
    # Create prompt that emphasizes real cards
    prompt = create_constrained_generation_prompt(commander, theme, validator)
    
    print(f"\n{'='*60}")
    print(f"GENERATING DECK: {commander} - {theme}")
    print(f"{'='*60}\n")
    
    # Tokenize input
    inputs = tokenizer(prompt, return_tensors="pt")
    
    # Move to XPU if available
    if torch.xpu.is_available():
        inputs = {k: v.to('xpu') for k, v in inputs.items()}
    
    # Generate
    print("Generating deck...")
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_p=0.9,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id
        )
    
    # Decode
    generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
    
    # Extract just the generated part (after prompt)
    deck_output = generated_text[len(prompt):]
    
    print("\n" + "="*60)
    print("RAW GENERATION (before validation)")
    print("="*60)
    print(deck_output)
    
    # Validate and correct
    print("\n" + "="*60)
    print("VALIDATING CARDS")
    print("="*60)
    
    validated_deck = validate_and_correct_generation(deck_output, validator)
    
    # Get validation stats
    result = validator.validate_deck_list(validated_deck)
    
    print("\n" + "="*60)
    print("FINAL VALIDATED DECK")
    print("="*60)
    print(validated_deck)
    
    print("\n" + "="*60)
    print("VALIDATION SUMMARY")
    print("="*60)
    print(f"Total cards: {result['total_cards']}")
    print(f"Valid cards: {result['total_cards'] - result['invalid_count']}")
    print(f"Invalid cards remaining: {result['invalid_count']}")
    
    if result['invalid_count'] > 0:
        print(f"\n⚠️  Warning: {result['invalid_count']} invalid cards could not be corrected:")
        for card in result['invalid_cards']:
            print(f"  - {card}")
    else:
        print("\n✓ All cards are valid!")
    
    return validated_deck, result


def main():
    # Paths
    BASE_MODEL_PATH = "models/qwen2.5-3b"
    LORA_PATH = "models/commander-llama-lora"
    
    print("\n" + "="*60)
    print("COMMANDER DECK GENERATOR WITH CARD VALIDATION")
    print("="*60)
    
    # Initialize validator
    print("\nInitializing card validator...")
    validator = CardValidator()
    
    # Load model
    print("\nLoading model...")
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_PATH)
    model = load_model_with_lora(BASE_MODEL_PATH, LORA_PATH)
    
    # Test prompts
    test_decks = [
        ("The Ur-Dragon", "dragon tribal"),
        ("Atraxa, Praetors' Voice", "proliferate"),
        ("Krenko, Mob Boss", "goblin tribal"),
    ]
    
    for commander, theme in test_decks:
        validated_deck, stats = generate_deck_with_validation(
            model, tokenizer, validator, commander, theme,
            max_new_tokens=1024,
            temperature=0.7
        )
        
        # Save to file
        output_file = Path(f"generated_decks/{commander.replace(',', '').replace(' ', '_')}.txt")
        output_file.parent.mkdir(exist_ok=True)
        
        with open(output_file, 'w') as f:
            f.write(validated_deck)
        
        print(f"\n✓ Saved to: {output_file}")
        
        # Wait for user
        input("\nPress Enter to generate next deck...")


if __name__ == '__main__':
    main()
