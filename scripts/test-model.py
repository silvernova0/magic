"""
Test the trained Commander AI model by generating a sample deck.

This script loads the LoRA-adapted model and generates a Commander deck
to verify that training was successful.

Usage:
    python scripts/test-model.py
    python scripts/test-model.py --commander "Atraxa, Praetors' Voice"
    python scripts/test-model.py --theme "voltron" --power 7
"""

import argparse
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Paths
BASE_MODEL_PATH = "models/llama-3.1-8b"
LORA_MODEL_PATH = "models/commander-llama-lora"


def format_prompt(commander, theme="balanced", power=5):
    """Format a deck building prompt."""
    return f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

You are a Magic: The Gathering Commander/EDH deck building expert. You have deep knowledge of all Magic cards, their synergies, power levels, and competitive rankings.<|eot_id|><|start_header_id|>user<|end_header_id|>

Build a Commander/EDH deck with {commander} as the commander. Theme: {theme}. Power level: {power}/10.<|eot_id|><|start_header_id|>assistant<|end_header_id|>

"""


def generate_deck(model, tokenizer, commander, theme="balanced", power=5, max_length=2048):
    """Generate a Commander deck."""
    prompt = format_prompt(commander, theme, power)
    
    logger.info(f"Generating deck for {commander}...")
    logger.info(f"Theme: {theme}, Power: {power}/10")
    
    inputs = tokenizer(prompt, return_tensors="pt")
    
    if torch.cuda.is_available():
        inputs = inputs.to("cuda")
    
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_length=max_length,
            num_return_sequences=1,
            temperature=0.7,
            top_p=0.9,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id
        )
    
    generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
    
    # Extract just the assistant's response
    if "<|start_header_id|>assistant<|end_header_id|>" in generated_text:
        response = generated_text.split("<|start_header_id|>assistant<|end_header_id|>")[-1].strip()
    else:
        response = generated_text
    
    return response


def main():
    parser = argparse.ArgumentParser(description="Test the trained Commander AI model")
    parser.add_argument("--commander", type=str, default="Atraxa, Praetors' Voice",
                        help="Commander name")
    parser.add_argument("--theme", type=str, default="balanced",
                        help="Deck theme (e.g., aggro, control, combo, tokens)")
    parser.add_argument("--power", type=int, default=5,
                        help="Power level (1-10)")
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("Commander AI Model Test")
    logger.info("=" * 60)
    
    # Check device
    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"Device: {device}")
    if device == "cuda":
        logger.info(f"GPU: {torch.cuda.get_device_name(0)}")
    logger.info("")
    
    # Load tokenizer
    logger.info("Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(LORA_MODEL_PATH)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    logger.info("✓ Tokenizer loaded")
    logger.info("")
    
    # Load base model
    logger.info("Loading base model...")
    logger.info("  This may take a few minutes...")
    base_model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL_PATH,
        torch_dtype=torch.float16 if device == "cuda" else torch.float32,
        device_map="auto" if device == "cuda" else None,
        trust_remote_code=True
    )
    logger.info("✓ Base model loaded")
    logger.info("")
    
    # Load LoRA adapter
    logger.info("Loading LoRA adapter...")
    model = PeftModel.from_pretrained(base_model, LORA_MODEL_PATH)
    logger.info("✓ LoRA adapter loaded")
    logger.info("")
    
    # Generate deck
    logger.info("=" * 60)
    logger.info("GENERATING DECK")
    logger.info("=" * 60)
    
    deck = generate_deck(
        model,
        tokenizer,
        commander=args.commander,
        theme=args.theme,
        power=args.power
    )
    
    logger.info("")
    logger.info("=" * 60)
    logger.info("GENERATED DECK")
    logger.info("=" * 60)
    print(deck)
    logger.info("")
    logger.info("=" * 60)
    logger.info("Test complete!")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
