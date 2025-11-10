#!/usr/bin/env python3
"""
Convert Commander precon decks from CSV file to training format.
The CSV contains individual card rows; need to group by deck.
"""

import csv
import json
from pathlib import Path
from collections import defaultdict
from typing import Dict, List

def parse_csv_to_decks(csv_file: Path) -> Dict[str, Dict]:
    """Parse CSV file and group cards by deck."""
    decks = defaultdict(lambda: {
        'name': '',
        'commanders': [],
        'mainboard': defaultdict(int),
        'metadata': {}
    })
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            deck_name = row.get('name', '').strip()
            if not deck_name:
                continue
            
            card_name = row.get('info.name', '').strip()
            if not card_name:
                continue
            
            deck_section = row.get('Deck Section', '').lower()
            
            # Track commanders separately
            if 'commander' in deck_section:
                if card_name not in decks[deck_name]['commanders']:
                    decks[deck_name]['commanders'].append(card_name)
            else:
                # Mainboard cards
                decks[deck_name]['mainboard'][card_name] += 1
            
            # Store deck name
            if not decks[deck_name]['name']:
                decks[deck_name]['name'] = deck_name
    
    return decks


def categorize_cards(cards: Dict[str, int]) -> Dict[str, List[tuple]]:
    """Categorize cards (simplified - actual card types would need database lookup)."""
    # For precons, we'll just list all cards alphabetically
    # Real implementation would query card database for types
    categories = {'Cards': []}
    
    for card_name, qty in sorted(cards.items()):
        categories['Cards'].append((card_name, qty))
    
    return categories


def format_decklist(commanders: List[str], cards: Dict[str, int], deck_name: str) -> str:
    """Format deck into training output format."""
    output_lines = []
    
    # Commander section
    if commanders:
        output_lines.append(f"Commander: {', '.join(commanders)}")
        output_lines.append("")
    
    output_lines.append(f"Deck Name: {deck_name}")
    output_lines.append("")
    output_lines.append("Decklist:")
    output_lines.append("")
    
    # Commanders as separate section
    if commanders:
        output_lines.append("Commanders:")
        for name in commanders:
            output_lines.append(f"1x {name}")
        output_lines.append("")
    
    # Mainboard cards
    output_lines.append("Cards:")
    for card_name, qty in sorted(cards.items()):
        output_lines.append(f"{qty}x {card_name}")
    
    return "\n".join(output_lines).strip()


def create_training_instruction(commanders: List[str], deck_name: str) -> str:
    """Create instruction prompt for training."""
    if len(commanders) == 1:
        return f"Build a Commander deck with {commanders[0]} as the commander."
    elif len(commanders) == 2:
        return f"Build a Commander deck with {commanders[0]} and {commanders[1]} as partners."
    else:
        return f"Build a Commander preconstructed deck."


def validate_deck(commanders: List[str], mainboard: Dict[str, int], deck_name: str) -> bool:
    """Validate deck has exactly 100 cards."""
    commander_count = len(commanders)
    mainboard_count = sum(mainboard.values())
    total_count = commander_count + mainboard_count
    
    if total_count != 100:
        print(f"SKIPPED: '{deck_name}': {total_count} cards (expected 100). Commanders: {commander_count}, Mainboard: {mainboard_count}")
        return False
    
    return True


def main():
    """Process CSV file."""
    csv_file = Path('/home/social/magicapp/data/CommanderPrecons/All_Precons_2025-09-20.csv')
    output_file = Path('/home/social/magicapp/data/training/precon_decks.jsonl')
    
    if not csv_file.exists():
        print(f"Error: CSV file not found: {csv_file}")
        return
    
    print(f"Parsing CSV file: {csv_file}")
    decks = parse_csv_to_decks(csv_file)
    print(f"Found {len(decks)} unique decks")
    
    # Process each deck
    training_data = []
    for deck_name, deck_info in decks.items():
        commanders = deck_info['commanders']
        mainboard = deck_info['mainboard']
        
        # Validate
        if not validate_deck(commanders, mainboard, deck_name):
            continue
        
        # Format output
        instruction = create_training_instruction(commanders, deck_name)
        output = format_decklist(commanders, mainboard, deck_name)
        
        training_data.append({
            'instruction': instruction,
            'output': output,
            'metadata': {
                'source': 'CommanderPrecons',
                'deck_name': deck_name,
                'commanders': commanders,
                'total_cards': 100,
                'format': 'commander',
                'precon': True
            }
        })
        
        print(f"✓ Converted: {deck_name}")
    
    # Save to JSONL
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        for item in training_data:
            f.write(json.dumps(item) + '\n')
    
    print(f"\n{'='*60}")
    print(f"Conversion complete!")
    print(f"Total precons processed: {len(training_data)}")
    print(f"Output saved to: {output_file}")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
