#!/usr/bin/env python3
"""
Test the trained Commander AI model by generating sample decks
"""

import os
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

# Paths
BASE_MODEL_PATH = "models/qwen2.5-3b"
LORA_ADAPTER_PATH = "models/commander-llama-lora"

def generate_deck(prompt, max_tokens=1024, temperature=0.7):
    """Generate a Commander deck from a prompt."""
    print("Loading model...")
    
    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(
        BASE_MODEL_PATH,
        trust_remote_code=True
    )
    
    # Load base model
    print("Loading base model...")
    base_model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL_PATH,
        trust_remote_code=True,
        torch_dtype=torch.bfloat16,
        low_cpu_mem_usage=True,
    )
    
    # Load LoRA adapters
    print("Loading LoRA adapters...")
    model = PeftModel.from_pretrained(
        base_model,
        LORA_ADAPTER_PATH,
        torch_dtype=torch.bfloat16,
    )
    
    # Move to XPU if available
    if torch.xpu.is_available():
        device = torch.device("xpu")
        print(f"Using Intel XPU: {torch.xpu.get_device_name(0)}")
    else:
        device = torch.device("cpu")
        print("Using CPU")
    
    model = model.to(device)
    model.eval()
    
    print("\n" + "="*60)
    print("GENERATING DECK")
    print("="*60)
    print(f"Prompt: {prompt}\n")
    
    # Tokenize input
    inputs = tokenizer(prompt, return_tensors="pt").to(device)
    
    # Generate
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            temperature=temperature,
            do_sample=True,
            top_p=0.9,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )
    
    # Decode output
    generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
    
    print("GENERATED DECK:")
    print("="*60)
    print(generated_text)
    print("="*60)
    
    return generated_text


if __name__ == "__main__":
    # Test prompts
    test_prompts = [
        "Build a Commander deck with Atraxa, Praetors' Voice as the commander.",
        "Build a Commander deck with Krenko, Mob Boss as the commander, focusing on goblin tribal.",
        "Build a Commander deck with Muldrotha, the Gravetide as the commander.",
    ]
    
    print("Testing trained Commander AI model...")
    print("This will generate 3 sample decks\n")
    
    for i, prompt in enumerate(test_prompts, 1):
        print(f"\n{'#'*60}")
        print(f"TEST {i}/{len(test_prompts)}")
        print(f"{'#'*60}\n")
        
        generated_deck = generate_deck(prompt)
        
        if i < len(test_prompts):
            input("\nPress Enter to generate next deck...")
    
    print("\n" + "="*60)
    print("TESTING COMPLETE!")
    print("="*60)
    print("\nIf the decks look good, you're ready to integrate with your app!")
