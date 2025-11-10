#!/usr/bin/env python3
"""
Convert Commander precon decks from CommanderPrecons GitHub repo to training format.
Extracts 173 precon JSON files and formats them for model fine-tuning.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional


def extract_commander_info(deck_data: Dict) -> Dict:
    """Extract commander names and count from deck data."""
    commanders = deck_data.get('commanders', {})
    commander_names = []
    for card_name, card_info in commanders.items():
        qty = card_info.get('quantity', 1)
        for _ in range(qty):
            commander_names.append(card_name)
    
    return {
        'names': commander_names,
        'count': len(commander_names)
    }


def extract_mainboard_cards(deck_data: Dict) -> List[Dict]:
    """Extract mainboard cards grouped by type."""
    boards = deck_data.get('boards', {})
    
    categories = {
        'Creatures': [],
        'Instants': [],
        'Sorceries': [],
        'Enchantments': [],
        'Artifacts': [],
        'Planeswalkers': [],
        'Lands': []
    }
    
    for card_name, card_info in boards.items():
        qty = card_info.get('quantity', 1)
        card_data = card_info.get('card', {})
        type_line = card_data.get('type_line', '')
        
        # Categorize based on type line
        if 'Creature' in type_line:
            categories['Creatures'].append((card_name, qty))
        elif 'Instant' in type_line:
            categories['Instants'].append((card_name, qty))
        elif 'Sorcery' in type_line:
            categories['Sorceries'].append((card_name, qty))
        elif 'Enchantment' in type_line:
            categories['Enchantments'].append((card_name, qty))
        elif 'Artifact' in type_line:
            categories['Artifacts'].append((card_name, qty))
        elif 'Planeswalker' in type_line:
            categories['Planeswalkers'].append((card_name, qty))
        elif 'Land' in type_line:
            categories['Lands'].append((card_name, qty))
    
    return categories


def format_decklist(commanders: Dict, categories: Dict, deck_name: str, deck_description: str) -> str:
    """Format deck into training output format."""
    output_lines = []
    
    # Commander section
    if commanders['count'] > 0:
        output_lines.append(f"Commander: {', '.join(commanders['names'])}")
        output_lines.append("")
    
    output_lines.append(f"Deck Name: {deck_name}")
    if deck_description:
        output_lines.append(f"Description: {deck_description}")
    output_lines.append("")
    output_lines.append("Decklist:")
    output_lines.append("")
    
    # Commanders as separate section
    if commanders['count'] > 0:
        output_lines.append("Commanders:")
        for name in commanders['names']:
            output_lines.append(f"1x {name}")
        output_lines.append("")
    
    # Card categories
    for category, cards in categories.items():
        if cards:
            output_lines.append(f"{category}:")
            for card_name, qty in cards:
                output_lines.append(f"{qty}x {card_name}")
            output_lines.append("")
    
    return "\n".join(output_lines).strip()


def create_training_instruction(commander_names: List[str], deck_name: str) -> str:
    """Create instruction prompt for training."""
    if len(commander_names) == 1:
        return f"Build a Commander deck with {commander_names[0]} as the commander."
    elif len(commander_names) == 2:
        return f"Build a Commander deck with {commander_names[0]} and {commander_names[1]} as partners."
    else:
        return f"Build a Commander deck for the preconstructed deck '{deck_name}'."


def validate_deck(deck_data: Dict, filename: str) -> Optional[str]:
    """Validate deck has exactly 100 cards."""
    commanders = deck_data.get('commanders', {})
    boards = deck_data.get('boards', {})
    
    commander_count = sum(card.get('quantity', 1) for card in commanders.values())
    mainboard_count = sum(card.get('quantity', 1) for card in boards.values())
    total_count = commander_count + mainboard_count
    
    if total_count != 100:
        return f"Invalid deck '{filename}': {total_count} cards (expected 100). Commanders: {commander_count}, Mainboard: {mainboard_count}"
    
    return None


def convert_precon_to_training(json_file: Path) -> Optional[Dict]:
    """Convert single precon JSON to training format."""
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            deck_data = json.load(f)
        
        # Validate deck
        error = validate_deck(deck_data, json_file.name)
        if error:
            print(f"SKIPPED: {error}")
            return None
        
        # Extract data
        deck_name = deck_data.get('name', 'Unknown Deck')
        deck_description = deck_data.get('description', '')
        commanders = extract_commander_info(deck_data)
        categories = extract_mainboard_cards(deck_data)
        
        # Format output
        instruction = create_training_instruction(commanders['names'], deck_name)
        output = format_decklist(commanders, categories, deck_name, deck_description)
        
        # Get color identity
        color_identity = deck_data.get('colors', [])
        colors_str = ''.join(sorted(color_identity)) if color_identity else 'Colorless'
        
        return {
            'instruction': instruction,
            'output': output,
            'metadata': {
                'source': 'CommanderPrecons',
                'deck_name': deck_name,
                'commanders': commanders['names'],
                'colors': colors_str,
                'total_cards': 100,
                'format': 'commander',
                'precon': True
            }
        }
    
    except Exception as e:
        print(f"ERROR processing {json_file.name}: {e}")
        return None


def main():
    """Process all precon JSON files."""
    precon_dir = Path('/home/social/magicapp/data/CommanderPrecons/precon_json')
    output_file = Path('/home/social/magicapp/data/training/precon_decks.jsonl')
    
    if not precon_dir.exists():
        print(f"Error: Precon directory not found: {precon_dir}")
        return
    
    # Find all JSON files
    json_files = sorted(precon_dir.glob('*.json'))
    print(f"Found {len(json_files)} precon JSON files")
    
    # Process each file
    training_data = []
    for json_file in json_files:
        result = convert_precon_to_training(json_file)
        if result:
            training_data.append(result)
            print(f"✓ Converted: {result['metadata']['deck_name']}")
    
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
