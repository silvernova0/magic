#!/usr/bin/env python3
"""
Prepare Balanced Dataset v2 for Commander Model Training
70/30 ratio: 70% card knowledge, 30% decks
Uses all available card knowledge (65k) + subset of decks (28k)
"""

import json
import random
import argparse
from pathlib import Path
from datetime import datetime

def load_jsonl(filepath):
    """Load JSONL file"""
    data = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    data.append(json.loads(line))
                except json.JSONDecodeError as e:
                    print(f"Warning: Skipping invalid JSON line: {e}")
    return data

def validate_deck(deck_data):
    """Validate deck has proper structure and 100 cards"""
    output = deck_data.get('output', '')
    
    # Count cards (lines starting with digit and containing 'x')
    card_lines = [l for l in output.split('\n') if l.strip() and l.strip()[0].isdigit()]
    total_cards = 0
    for line in card_lines:
        try:
            if 'x' in line:
                qty = int(line.split('x')[0].strip())
                total_cards += qty
        except:
            pass
    
    # Valid if between 98-101 cards (allow some tolerance for parsing)
    is_valid = 98 <= total_cards <= 101
    
    # Must have Commander section
    has_commander = 'Commander:' in output or 'Commanders:' in output
    
    return is_valid and has_commander

def main():
    parser = argparse.ArgumentParser(description='Prepare maximum training dataset v2 (use ALL available data)')
    parser.add_argument('--use-all', action='store_true', default=True, 
                        help='Use all available data (default: True)')
    parser.add_argument('--card-ratio', type=float, default=None, 
                        help='Force specific card ratio (e.g., 0.7 for 70%%). Default: use all data')
    parser.add_argument('--seed', type=int, default=42, help='Random seed for reproducibility')
    parser.add_argument('--output', type=str, default='data/training/combined_training_balanced_v2.jsonl', 
                        help='Output file path')
    args = parser.parse_args()
    
    random.seed(args.seed)
    
    print("="*60)
    print("PREPARING MAXIMUM TRAINING DATASET V2")
    print("="*60)
    if args.card_ratio is None:
        print("Strategy: Use ALL available data (maximum dataset)")
    else:
        print(f"Strategy: Force {args.card_ratio*100:.0f}% cards, {(1-args.card_ratio)*100:.0f}% decks ratio")
    print()
    
    # Load card knowledge FIRST
    print("Loading card knowledge...")
    card_knowledge = load_jsonl('data/training/card_knowledge.jsonl')
    print(f"  Card knowledge examples: {len(card_knowledge):,}")
    
    # Load all deck sources
    print("\nLoading deck sources...")
    deck_sources = [
        'data/training/archidekt_decks.jsonl',
        'data/training/moxfield_decks.jsonl',
        'data/training/mtggoldfish_decks.jsonl',
        'data/training/mtggoldfish_by_commander_decks.jsonl',
        'data/training/edhrec_decks.jsonl',
        'data/training/tappedout_decks.jsonl',
        'data/training/cedh_decks.jsonl',
    ]
    
    all_decks = []
    deck_counts = {}
    for source in deck_sources:
        filepath = Path(source)
        if filepath.exists():
            decks = load_jsonl(filepath)
            valid_decks = [d for d in decks if validate_deck(d)]
            print(f"  {filepath.name}: {len(valid_decks)}/{len(decks)} valid decks")
            all_decks.extend(valid_decks)
            deck_counts[filepath.name] = len(valid_decks)
        else:
            print(f"  {filepath.name}: FILE NOT FOUND (skipping)")
            deck_counts[filepath.name] = 0
    
    print(f"\nTotal valid decks: {len(all_decks):,}")
    
    # Calculate target counts
    if args.card_ratio is None:
        # Use ALL available data (maximum dataset)
        num_card_examples = len(card_knowledge)
        num_deck_examples = len(all_decks)
        actual_card_ratio = num_card_examples / (num_card_examples + num_deck_examples)
        actual_deck_ratio = num_deck_examples / (num_card_examples + num_deck_examples)
        print(f"\n✅ Using ALL available data (maximum dataset)")
        print(f"   Natural ratio: {actual_card_ratio*100:.1f}% cards, {actual_deck_ratio*100:.1f}% decks")
    else:
        # Use specified ratio (calculate how many of each to use)
        num_card_examples = len(card_knowledge)
        num_deck_examples = int((num_card_examples / args.card_ratio) * (1 - args.card_ratio))
        
        if num_deck_examples > len(all_decks):
            print(f"\n⚠️  WARNING: Need {num_deck_examples:,} decks for {args.card_ratio*100:.0f}% ratio")
            print(f"   Only {len(all_decks):,} available, using all decks")
            num_deck_examples = len(all_decks)
            # Recalculate actual ratio
            actual_card_ratio = num_card_examples / (num_card_examples + num_deck_examples)
            actual_deck_ratio = num_deck_examples / (num_card_examples + num_deck_examples)
            print(f"   Actual ratio: {actual_card_ratio*100:.1f}% cards, {actual_deck_ratio*100:.1f}% decks")
    
    print(f"\n{'='*60}")
    print("DATASET COMPOSITION")
    print(f"{'='*60}")
    print(f"Card examples: {num_card_examples:,} ({num_card_examples/(num_deck_examples+num_card_examples)*100:.1f}%)")
    print(f"Deck examples: {num_deck_examples:,} ({num_deck_examples/(num_deck_examples+num_card_examples)*100:.1f}%)")
    print(f"Total examples: {num_deck_examples + num_card_examples:,}")
    print(f"\nDeck sources:")
    for source_name, count in deck_counts.items():
        if count > 0:
            print(f"  - {source_name}: {count:,}")
    
    # Sample datasets (or use all if that's what we want)
    print("\nPreparing final dataset...")
    if num_deck_examples == len(all_decks):
        deck_sample = all_decks
        print(f"Using ALL {len(all_decks):,} decks")
    else:
        deck_sample = random.sample(all_decks, num_deck_examples)
        print(f"Randomly sampled {num_deck_examples:,} decks from {len(all_decks):,}")
    
    if num_card_examples == len(card_knowledge):
        card_sample = card_knowledge
        print(f"Using ALL {len(card_knowledge):,} card examples")
    else:
        card_sample = random.sample(card_knowledge, num_card_examples)
        print(f"Randomly sampled {num_card_examples:,} card examples from {len(card_knowledge):,}")
    
    # Combine and shuffle
    combined = card_sample + deck_sample
    random.shuffle(combined)
    
    print(f"\nFinal dataset: {len(combined):,} examples (shuffled)")
    
    # Save combined dataset
    print(f"\nSaving to {args.output}...")
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        for item in combined:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    
    # Calculate training estimates
    # Based on v1: 8,142 examples = 21 hours with BATCH_SIZE=4
    # v2 with BATCH_SIZE=24: ~3x speedup
    v1_time_per_example = 21.0 / 8142  # hours per example
    v2_time_hours = len(combined) * v1_time_per_example / 3  # 3x speedup with batch 24
    
    print(f"\n{'='*60}")
    print("DATASET PREPARATION COMPLETE")
    print(f"{'='*60}")
    print(f"\nOutput: {output_path}")
    print(f"Total examples: {len(combined):,}")
    print(f"  - Card knowledge: {num_card_examples:,} ({num_card_examples/len(combined)*100:.1f}%)")
    print(f"  - Decks: {num_deck_examples:,} ({num_deck_examples/len(combined)*100:.1f}%)")
    
    print(f"\n{'='*60}")
    print("TRAINING ESTIMATES (BATCH_SIZE=24)")
    print(f"{'='*60}")
    print(f"\nEstimated training time: ~{v2_time_hours:.1f} hours ({v2_time_hours/24:.1f} days)")
    print(f"VRAM usage: ~11.3GB (4.7GB headroom)")
    
    print(f"\n{'='*60}")
    print("NEXT STEPS")
    print(f"{'='*60}")
    print(f"\n1. Verify dataset looks good:")
    print(f"   head -1 {output_path} | python3 -m json.tool")
    print(f"\n2. Update training script to use new dataset:")
    print(f"   Edit scripts/train-commander-model-optimized.py")
    print(f"   Change TRAINING_DATA_PATH to: '{output_path}'")
    print(f"\n3. Start training:")
    print(f"   BATCH_SIZE=24 GRADIENT_ACCUMULATION_STEPS=1 \\")
    print(f"     nohup python3 scripts/train-commander-model-optimized.py > training_v2.log 2>&1 &")
    print(f"\n4. Monitor progress:")
    print(f"   tail -f training_v2.log")
    print()

if __name__ == '__main__':
    main()
