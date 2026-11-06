"""
Prepare training data for Commander deck building model
Converts card knowledge + real decks into instruction-following format.

Enhancements:
- Optional inventory and recent-decks summaries can be injected into the instruction
  to teach the model to leverage user context at inference.
"""
import json
import os
import argparse
from collections import Counter

def load_jsonl(filepath):
    """Load JSONL file"""
    data = []
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    data.append(json.loads(line))
    return data

def format_deck_for_training(deck_data, inventory_summary: str = "", recent_summary: str = ""):
    """Convert deck to instruction-following format, optionally including context summaries."""
    commander = deck_data.get('commander', 'Unknown')
    theme = deck_data.get('theme', 'general')
    power_level = deck_data.get('power_level', 5)
    cards = deck_data.get('cards', [])
    
    # Create instruction
    instruction = f"Build a Commander/EDH deck with {commander} as the commander. Theme: {theme}. Power level: {power_level}/10."
    if inventory_summary:
        instruction += f"\n\nAvailable inventory highlights: {inventory_summary}"
    if recent_summary:
        instruction += f"\n\nAvoid duplicates from recent builds: {recent_summary}"
    
    # Create formatted decklist output
    card_lines = []
    for card in cards:
        name = card.get('name', '')
        qty = card.get('quantity', 1)
        category = card.get('category', 'Unknown')
        card_lines.append(f"{qty}x {name} ({category})")
    
    output = f"## Commander\n1x {commander}\n\n## Decklist ({len(cards)} cards)\n" + "\n".join(card_lines)
    
    # Simple length caps to avoid overly long examples
    def truncate(s: str, max_chars: int) -> str:
        return s if len(s) <= max_chars else s[: max_chars - 3] + "..."

    return {
        "instruction": truncate(instruction, 1200),
        "output": truncate(output, 6000)
    }


def summarize_inventory(inv_items, top_n=20):
    # inv_items: list of {name, quantity}
    if not inv_items:
        return ""
    agg = Counter()
    for it in inv_items:
        try:
            q = int(it.get('quantity', 1))
        except Exception:
            q = 1
        name = it.get('name', '')
        if name:
            agg[name] += max(1, q)
    top = [f"{n}x {name}" for name, n in agg.most_common(top_n)]
    return ", ".join(top)


def summarize_recent_decks(recent_decks, top_n=15):
    # recent_decks: list of {commander, cards:[{name,quantity}]}
    if not recent_decks:
        return ""
    card_counts = Counter()
    for d in recent_decks:
        for c in d.get('cards', []) or []:
            name = c.get('name', '')
            if name:
                try:
                    q = int(c.get('quantity', 1))
                except Exception:
                    q = 1
                card_counts[name] += max(1, q)
    top = [name for name, _ in card_counts.most_common(top_n)]
    return ", ".join(top)

def main():
    import argparse as _argparse
    parser = _argparse.ArgumentParser(description="Prepare Commander training data")
    parser.add_argument("--inventory", type=str, default="data/training/inventory.json", help="Optional inventory JSON file")
    parser.add_argument("--recent", type=str, default="data/training/recent_decks.jsonl", help="Optional recent decks JSONL file")
    args = parser.parse_args()

    print("="*60)
    print("TRAINING DATA PREPARATION")
    print("="*60)
    
    # Load card knowledge
    print("\n1. Loading card knowledge...")
    card_knowledge = load_jsonl('data/training/card_knowledge.jsonl')
    print(f"   ✓ Loaded {len(card_knowledge)} card knowledge examples")
    
    # Load real decks
    print("\n2. Loading TappedOut decks...")
    tappedout_decks = load_jsonl('data/training/tappedout_decks.jsonl')
    print(f"   ✓ Loaded {len(tappedout_decks)} real Commander decks")
    
    # Optional context: inventory and recent decks
    inventory_items = []
    try:
        if os.path.exists(args.inventory):
            with open(args.inventory, 'r', encoding='utf-8') as f:
                inventory_items = json.load(f)
            print(f"\nLoaded inventory items: {len(inventory_items)} from {args.inventory}")
    except Exception as e:
        print(f"\nWarning: failed to load inventory file: {e}")
        inventory_items = []
    recent_decks = []
    try:
        if os.path.exists(args.recent):
            with open(args.recent, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        recent_decks.append(json.loads(line))
            print(f"Loaded recent decks: {len(recent_decks)} from {args.recent}")
    except Exception as e:
        print(f"Warning: failed to load recent decks file: {e}")
        recent_decks = []
    inv_summary = summarize_inventory(inventory_items, top_n=20)
    rec_summary = summarize_recent_decks(recent_decks, top_n=15)

    # Format decks for training
    print("\n3. Formatting decks...")
    formatted_decks = []
    for deck in tappedout_decks:
        try:
            formatted = format_deck_for_training(deck, inventory_summary=inv_summary, recent_summary=rec_summary)
            formatted_decks.append(formatted)
        except Exception as e:
            print(f"   ⚠️ Failed to format deck: {str(e)[:50]}")
    
    print(f"   ✓ Formatted {len(formatted_decks)} decks")
    
    # Combine all training data
    print("\n4. Combining training data...")
    training_data = card_knowledge + formatted_decks
    print(f"   ✓ Total training examples: {len(training_data)}")
    
    # Save combined training data
    print("\n5. Saving combined training data...")
    output_file = 'data/training/combined_training.jsonl'
    with open(output_file, 'w', encoding='utf-8') as f:
        for item in training_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    
    # Get file size
    file_size_mb = os.path.getsize(output_file) / (1024 * 1024)
    print(f"   ✓ Saved to: {output_file}")
    print(f"   ✓ File size: {file_size_mb:.2f} MB")
    
    # Summary
    print("\n" + "="*60)
    print("PREPARATION COMPLETE")
    print("="*60)
    print(f"Card knowledge examples: {len(card_knowledge)}")
    print(f"Commander deck examples: {len(formatted_decks)}")
    print(f"Total training examples: {len(training_data)}")
    print(f"Output file: {output_file}")
    print(f"File size: {file_size_mb:.2f} MB")
    
    # Show sample
    print("\n" + "="*60)
    print("SAMPLE TRAINING EXAMPLE (Deck)")
    print("="*60)
    if formatted_decks:
        sample = formatted_decks[0]
        print(f"\nInstruction:\n{sample['instruction']}")
        print(f"\nOutput (first 500 chars):\n{sample['output'][:500]}...")

if __name__ == '__main__':
    main()
