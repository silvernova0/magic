#!/usr/bin/env python3
"""
Analyze land counts from training data to build a reference database
Output: JSON file with land count statistics per commander and bracket
"""

import json
import sys
from pathlib import Path
from collections import defaultdict
from typing import Dict, List

def analyze_land_counts():
    """Analyze training data to extract land count patterns"""
    
    training_files = [
        'data/training/v3_structured_training.jsonl',
        'data/training/mtggoldfish_commander_decks.jsonl',
        'data/training/edhrec_average_decks.jsonl',
    ]
    
    # Stats by commander
    commander_stats = defaultdict(lambda: defaultdict(list))
    
    # Stats by bracket (for defaults)
    bracket_stats = defaultdict(list)
    
    total_decks = 0
    
    for file_path in training_files:
        try:
            with open(file_path, 'r') as f:
                for line in f:
                    try:
                        deck = json.loads(line)
                        output = deck.get('output', {})
                        
                        if isinstance(output, str):
                            try:
                                output = json.loads(output)
                            except:
                                continue
                        
                        commander = output.get('commander', '')
                        bracket = output.get('bracket', 3)
                        card_selection = output.get('card_selection', {})
                        
                        if not commander or not card_selection:
                            continue
                        
                        # Get land count
                        land_count = 0
                        if 'lands' in card_selection:
                            lands_info = card_selection['lands']
                            land_count = lands_info.get('count', 0)
                        else:
                            # Infer from total (99 - sum of non-lands)
                            total_non_lands = sum(
                                cat.get('count', 0)
                                for cat_name, cat in card_selection.items()
                                if cat_name != 'lands' and isinstance(cat, dict)
                            )
                            land_count = 99 - total_non_lands
                        
                        if land_count > 0 and land_count <= 99:
                            # Store by commander and bracket
                            commander_stats[commander][bracket].append(land_count)
                            # Store by bracket for defaults
                            bracket_stats[bracket].append(land_count)
                            total_decks += 1
                    
                    except Exception as e:
                        continue
        
        except FileNotFoundError:
            print(f"Warning: {file_path} not found", file=sys.stderr)
            continue
    
    print(f"Analyzed {total_decks} decks")
    
    # Calculate statistics
    land_database = {
        'commanders': {},
        'bracket_defaults': {},
        'global_default': {'min': 32, 'max': 38, 'avg': 35}
    }
    
    # Per-commander stats
    for commander, brackets in commander_stats.items():
        land_database['commanders'][commander] = {}
        
        for bracket, counts in brackets.items():
            if len(counts) >= 3:  # Need at least 3 samples
                land_database['commanders'][commander][str(bracket)] = {
                    'min': min(counts),
                    'max': max(counts),
                    'avg': round(sum(counts) / len(counts), 1),
                    'samples': len(counts)
                }
    
    # Per-bracket defaults
    for bracket, counts in bracket_stats.items():
        if len(counts) >= 10:  # Need decent sample size
            # Use 10th and 90th percentile for min/max to avoid outliers
            sorted_counts = sorted(counts)
            p10_idx = int(len(sorted_counts) * 0.10)
            p90_idx = int(len(sorted_counts) * 0.90)
            
            land_database['bracket_defaults'][str(bracket)] = {
                'min': sorted_counts[p10_idx],
                'max': sorted_counts[p90_idx],
                'avg': round(sum(counts) / len(counts), 1),
                'samples': len(counts)
            }
    
    # Save to file
    output_dir = Path('data')
    output_dir.mkdir(exist_ok=True)
    
    output_file = output_dir / 'land_count_reference.json'
    with open(output_file, 'w') as f:
        json.dump(land_database, f, indent=2, sort_keys=True)
    
    print(f"\nSaved land count database to: {output_file}")
    
    # Print summary
    print(f"\nCommanders with data: {len(land_database['commanders'])}")
    print(f"Bracket defaults calculated: {len(land_database['bracket_defaults'])}")
    
    print("\nBracket Defaults:")
    for bracket in sorted(land_database['bracket_defaults'].keys(), key=int):
        stats = land_database['bracket_defaults'][bracket]
        print(f"  Bracket {bracket}: {stats['min']}-{stats['max']} lands (avg: {stats['avg']}, {stats['samples']} samples)")
    
    # Show some example commanders
    print("\nExample Commander Stats:")
    for i, (commander, brackets) in enumerate(list(land_database['commanders'].items())[:10]):
        print(f"  {commander}:")
        for bracket, stats in sorted(brackets.items(), key=lambda x: int(x[0])):
            print(f"    Bracket {bracket}: {stats['min']}-{stats['max']} lands (avg: {stats['avg']}, {stats['samples']} samples)")

if __name__ == '__main__':
    analyze_land_counts()
