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
import json
import os
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Paths
BASE_MODEL_PATH = "models/llama-3.1-8b"
LORA_MODEL_PATH = "models/commander-llama-lora"


def format_prompt(commander, theme="balanced", power=5, inventory_summary="", recent_summary=""):
    """Format a deck building prompt, optionally including inventory and recent decks context."""
    context = ""
    if inventory_summary:
        context += f"\n\nAvailable inventory highlights: {inventory_summary}"
    if recent_summary:
        context += f"\n\nAvoid duplicates from recent builds: {recent_summary}"
    return f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

You are a Magic: The Gathering Commander/EDH deck building expert. You have deep knowledge of all Magic cards, their synergies, power levels, and competitive rankings.<|eot_id|><|start_header_id|>user<|end_header_id|>

Build a Commander/EDH deck with {commander} as the commander. Theme: {theme}. Power level: {power}/10.{context}<|eot_id|><|start_header_id|>assistant<|end_header_id|>

"""


def summarize_inventory(inv_items, top_n=20):
    try:
        from collections import Counter
        agg = Counter()
        for it in (inv_items or []):
            name = it.get('name', '')
            if not name:
                continue
            try:
                q = int(it.get('quantity', 1))
            except Exception:
                q = 1
            agg[name] += max(1, q)
        return ", ".join([f"{n}x {name}" for name, n in agg.most_common(top_n)])
    except Exception:
        return ""


def summarize_recent_decks(recent_decks, top_n=15):
    try:
        from collections import Counter
        card_counts = Counter()
        for d in (recent_decks or []):
            for c in d.get('cards', []) or []:
                name = c.get('name', '')
                if not name:
                    continue
                try:
                    q = int(c.get('quantity', 1))
                except Exception:
                    q = 1
                card_counts[name] += max(1, q)
        return ", ".join([name for name, _ in card_counts.most_common(top_n)])
    except Exception:
        return ""


def generate_deck(model, tokenizer, commander, theme="balanced", power=5, max_length=1536, inventory_summary="", recent_summary="", device="cpu", dtype=torch.float32):
    """Generate a Commander deck."""
    prompt = format_prompt(commander, theme, power, inventory_summary, recent_summary)
    
    logger.info(f"Generating deck for {commander}...")
    logger.info(f"Theme: {theme}, Power: {power}/10")
    
    inputs = tokenizer(prompt, return_tensors="pt")
    inputs = {k: v.to(device) for k, v in inputs.items()}
    
    with torch.no_grad():
        gen_kwargs = dict(
            max_length=max_length,
            num_return_sequences=1,
            temperature=0.7,
            top_p=0.9,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id,
        )
        if device in ("xpu", "cuda"):
            with torch.autocast(device_type=("xpu" if device == "xpu" else "cuda"), dtype=dtype):
                outputs = model.generate(**inputs, **gen_kwargs)
        else:
            outputs = model.generate(**inputs, **gen_kwargs)
    
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
    parser.add_argument("--inventory", type=str, default="", help="Optional inventory JSON file for context")
    parser.add_argument("--recent", type=str, default="", help="Optional recent decks JSONL file for context")
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("Commander AI Model Test")
    logger.info("=" * 60)
    
    # Check device (support Intel XPU)
    device = "cpu"
    try:
        import intel_extension_for_pytorch as ipex  # noqa: F401
        if hasattr(torch, 'xpu') and torch.xpu.is_available():
            device = "xpu"
    except Exception:
        pass
    if device == "cpu" and torch.cuda.is_available():
        device = "cuda"
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
    dtype = (torch.bfloat16 if device == "xpu" else (torch.float16 if device == "cuda" else torch.float32))
    base_model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL_PATH,
        torch_dtype=dtype,
        device_map=None,
        low_cpu_mem_usage=True,
        trust_remote_code=True
    )
    if device != "cpu":
        base_model = base_model.to(device)
    logger.info("✓ Base model loaded")
    logger.info("")
    
    # Load LoRA adapter
    logger.info("Loading LoRA adapter...")
    model = PeftModel.from_pretrained(base_model, LORA_MODEL_PATH)
    if device != "cpu":
        model = model.to(device)
    logger.info("✓ LoRA adapter loaded")
    logger.info("")
    
    # Generate deck
    logger.info("=" * 60)
    logger.info("GENERATING DECK")
    logger.info("=" * 60)
    
    # Optional context summaries
    inv_summary = ""
    if args.inventory and os.path.exists(args.inventory):
        try:
            with open(args.inventory, 'r', encoding='utf-8') as f:
                inv_items = json.load(f)
            inv_summary = summarize_inventory(inv_items)
        except Exception as e:
            logger.warning(f"Failed to load inventory file: {e}")
    rec_summary = ""
    if args.recent and os.path.exists(args.recent):
        try:
            rec_list = []
            with open(args.recent, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        rec_list.append(json.loads(line))
            rec_summary = summarize_recent_decks(rec_list)
        except Exception as e:
            logger.warning(f"Failed to load recent decks file: {e}")

    deck = generate_deck(
        model,
        tokenizer,
        commander=args.commander,
        theme=args.theme,
        power=args.power,
        inventory_summary=inv_summary,
        recent_summary=rec_summary,
        device=device,
        dtype=dtype
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
