"""
Prepare balanced training dataset for Commander deck building
Combines deck-building examples with card knowledge in an 80/20 ratio (80% card knowledge)
This ratio helps prevent hallucinations by teaching the model real card names and abilities
"""
import json
import random
from pathlib import Path
from collections import defaultdict

def load_jsonl(filepath):
    """Load JSONL file"""
    examples = []
    if not Path(filepath).exists():
        return examples
    
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    examples.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return examples

def count_examples():
    """Count examples in each training file"""
    data_dir = Path('data/training')
    
    print("\n" + "="*60)
    print("CURRENT TRAINING DATA")
    print("="*60)
    
    # Deck-building examples
    deck_files = [
        'moxfield_decks.jsonl',
        'tappedout_decks.jsonl',
        'archidekt_decks.jsonl',
        'edhrec_decks.jsonl',
        'mtggoldfish_decks.jsonl',
        'cedh_decks.jsonl',
        'synthetic_decks.jsonl'
    ]
    
    total_decks = 0
    for filename in deck_files:
        filepath = data_dir / filename
        if filepath.exists():
            count = len(load_jsonl(filepath))
            if count > 0:
                print(f"  {filename:30s} {count:5d} decks")
                total_decks += count
    
    print(f"  {'-'*37}")
    print(f"  {'TOTAL DECK EXAMPLES':30s} {total_decks:5d}")
    
    # Card knowledge examples
    card_knowledge = load_jsonl(data_dir / 'card_knowledge.jsonl')
    print(f"\n  Card knowledge examples:       {len(card_knowledge):5d}")
    
    print(f"\n  Current ratio: {total_decks}/{len(card_knowledge)} = {total_decks/(total_decks+len(card_knowledge))*100:.1f}% decks")
    
    return total_decks, len(card_knowledge)

def create_balanced_dataset(deck_ratio=0.5, output_file='data/training/combined_training_balanced.jsonl'):
    """Create balanced training dataset"""
    data_dir = Path('data/training')
    
    print(f"\n" + "="*60)
    print("CREATING BALANCED TRAINING DATASET")
    print("="*60)
    print(f"Target ratio: {deck_ratio*100:.0f}% decks, {(1-deck_ratio)*100:.0f}% card knowledge\n")
    
    # Load all deck examples
    deck_files = [
        'moxfield_decks.jsonl',
        'tappedout_decks.jsonl',
        'archidekt_decks.jsonl',
        'edhrec_decks.jsonl',
        'mtggoldfish_decks.jsonl',
        'cedh_decks.jsonl',
        'synthetic_decks.jsonl'
    ]
    
    all_deck_examples = []
    for filename in deck_files:
        filepath = data_dir / filename
        examples = load_jsonl(filepath)
        all_deck_examples.extend(examples)
        if examples:
            print(f"✓ Loaded {len(examples):4d} decks from {filename}")
    
    print(f"\nTotal deck examples: {len(all_deck_examples)}")
    
    # Load card knowledge
    card_knowledge = load_jsonl(data_dir / 'card_knowledge.jsonl')
    print(f"Total card knowledge: {len(card_knowledge)}")
    
    # Calculate balanced dataset size
    num_decks = len(all_deck_examples)
    num_card_knowledge = int(num_decks * (1 - deck_ratio) / deck_ratio)
    
    print(f"\n" + "="*60)
    print("BALANCE CALCULATION")
    print("="*60)
    print(f"Available decks: {num_decks}")
    print(f"Available card knowledge: {len(card_knowledge)}")
    print(f"\nFor {deck_ratio*100:.0f}% deck ratio:")
    print(f"  Using: {num_decks} deck examples")
    print(f"  Need: {num_card_knowledge} card knowledge examples")
    
    # Sample card knowledge if we have more than needed
    if len(card_knowledge) > num_card_knowledge:
        print(f"  → Sampling {num_card_knowledge} from {len(card_knowledge)} available")
        sampled_card_knowledge = random.sample(card_knowledge, num_card_knowledge)
    else:
        print(f"  → Using all {len(card_knowledge)} card knowledge examples")
        sampled_card_knowledge = card_knowledge
    
    # Combine and shuffle
    combined = all_deck_examples + sampled_card_knowledge
    random.shuffle(combined)
    
    total_examples = len(combined)
    actual_deck_ratio = len(all_deck_examples) / total_examples
    
    print(f"\n" + "="*60)
    print("FINAL DATASET")
    print("="*60)
    print(f"Total examples: {total_examples}")
    print(f"  Deck examples: {len(all_deck_examples)} ({actual_deck_ratio*100:.1f}%)")
    print(f"  Card knowledge: {len(sampled_card_knowledge)} ({(1-actual_deck_ratio)*100:.1f}%)")
    
    # Save to file
    output_path = Path(output_file)
    print(f"\nSaving to: {output_path}")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        for example in combined:
            f.write(json.dumps(example) + '\n')
    
    print(f"✓ Saved {total_examples} examples")
    
    # Show sample distribution
    print(f"\n" + "="*60)
    print("EXAMPLE TYPE DISTRIBUTION")
    print("="*60)
    
    type_counts = defaultdict(int)
    for example in combined[:1000]:  # Sample first 1000
        ex_type = example.get('metadata', {}).get('type', 'unknown')
        type_counts[ex_type] += 1
    
    for ex_type, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"  {ex_type:20s} {count:4d} ({count/10:.1f}% of first 1000)")
    
    print(f"\n✓ Balanced dataset created successfully!")
    print(f"\nNext steps:")
    print(f"  1. Update training script to use: {output_file}")
    print(f"  2. Run training with: ./train-model-optimized.sh")
    print(f"  3. Expect better deck generation with balanced data!")
    
    return output_path

def main():
    # Count current examples
    num_decks, num_card_knowledge = count_examples()
    
    if num_decks < 100:
        print(f"\n⚠️  Warning: Only {num_decks} deck examples available")
        print(f"    Recommend waiting for scrapers to collect 500-1000 decks")
        response = input("\nContinue anyway? (y/n): ")
        if response.lower() != 'y':
            print("Exiting. Run scrapers first to collect more deck data.")
            return
    
    # Create balanced dataset with 80/20 ratio (80% card knowledge, 20% decks)
    # This helps prevent hallucinations by ensuring the model learns real card names
    output_file = create_balanced_dataset(deck_ratio=0.2)
    
    print(f"\n{'='*60}")
    print(f"✓ Ready for training!")
    print(f"{'='*60}")

if __name__ == '__main__':
    random.seed(42)  # Reproducible sampling
    main()
