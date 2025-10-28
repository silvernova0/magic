"""
Prepare training data for Commander deck building model
Converts card knowledge + real decks into instruction-following format
"""
import json
import os

def load_jsonl(filepath):
    """Load JSONL file"""
    data = []
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    data.append(json.loads(line))
    return data

def format_deck_for_training(deck_data):
    """Convert deck to instruction-following format"""
    commander = deck_data.get('commander', 'Unknown')
    theme = deck_data.get('theme', 'general')
    power_level = deck_data.get('power_level', 5)
    cards = deck_data.get('cards', [])
    
    # Create instruction
    instruction = f"Build a Commander/EDH deck with {commander} as the commander. Theme: {theme}. Power level: {power_level}/10."
    
    # Create formatted decklist output
    card_lines = []
    for card in cards:
        name = card.get('name', '')
        qty = card.get('quantity', 1)
        category = card.get('category', 'Unknown')
        card_lines.append(f"{qty}x {name} ({category})")
    
    output = f"## Commander\n1x {commander}\n\n## Decklist ({len(cards)} cards)\n" + "\n".join(card_lines)
    
    return {
        "instruction": instruction,
        "output": output
    }

def main():
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
    
    # Format decks for training
    print("\n3. Formatting decks...")
    formatted_decks = []
    for deck in tappedout_decks:
        try:
            formatted = format_deck_for_training(deck)
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
