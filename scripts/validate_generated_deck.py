#!/usr/bin/env python3
"""
Deck Validator - Validates AI-generated decks against card database

Checks:
1. All card names exist in database
2. Exactly 100 cards total
3. No invalid duplicates (except legal ones like Relentless Rats)
4. Color identity matches commander
5. All cards are Commander-legal
"""

import sqlite3
import re
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple

class DeckValidator:
    def __init__(self, db_path='prisma/dev.db'):
        self.db_path = db_path
        self.card_cache = {}
        self.legal_duplicates = {
            'Relentless Rats', 'Rat Colony', 'Persistent Petitioners',
            'Shadowborn Apostle', 'Dragon\'s Approach', 'Seven Dwarves',
            'Slime Against Humanity', 'Nazgûl'
        }
        self.basic_lands = {'Plains', 'Island', 'Swamp', 'Mountain', 'Forest', 'Wastes'}
        
    def get_card_info(self, card_name: str) -> Dict:
        """Get card information from database"""
        if card_name in self.card_cache:
            return self.card_cache[card_name]
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Query card info
            cursor.execute("""
                SELECT name, colorIdentity, typeLine, legalities
                FROM Card
                WHERE name = ? COLLATE NOCASE
                LIMIT 1
            """, (card_name,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                # Parse color identity (handle empty strings and JSON)
                color_identity = []
                if row[1]:
                    try:
                        color_identity = json.loads(row[1])
                    except:
                        # Fallback: split by comma if not JSON
                        color_identity = [c.strip() for c in row[1].split(',') if c.strip()]
                
                card_info = {
                    'name': row[0],  # Use exact name from DB
                    'colorIdentity': color_identity,  # Parsed color identity
                    'typeLine': row[2],  # Full type line string
                    'legalities': row[3]
                }
                self.card_cache[card_name] = card_info
                return card_info
            
            return None
            
        except Exception as e:
            print(f"Database error: {e}")
            return None
    
    def is_commander_legal(self, legalities: str) -> bool:
        """Check if card is legal in Commander format"""
        if not legalities:
            return False
        try:
            leg_dict = json.loads(legalities)
            commander_status = leg_dict.get('commander', '').lower()
            return commander_status in ['legal', 'restricted']
        except:
            # Fallback to string check
            return 'commander:legal' in legalities.lower() or 'commander:restricted' in legalities.lower()
    
    def parse_deck(self, deck_text: str) -> Tuple[str, List[Dict]]:
        """Parse deck text into commander and card list"""
        lines = deck_text.strip().split('\n')
        
        commander = None
        cards = []
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Look for "Commander: X"
            if line.lower().startswith('commander:'):
                commander = line.split(':', 1)[1].strip()
                continue
            
            # Parse card line: "1x Card Name" or "1 Card Name"
            match = re.match(r'^(\d+)\s*x?\s*(.+)$', line)
            if match:
                quantity = int(match.group(1))
                name = match.group(2).strip()
                cards.append({'name': name, 'quantity': quantity})
        
        return commander, cards
    
    def validate_deck(self, deck_text: str, verbose=True) -> Dict:
        """
        Validate an AI-generated deck
        
        Returns dict with:
        - valid: bool
        - errors: List[str]
        - warnings: List[str]
        - stats: Dict
        """
        errors = []
        warnings = []
        
        # Parse deck
        commander, cards = self.parse_deck(deck_text)
        
        if verbose:
            print(f"\n{'='*60}")
            print(f"VALIDATING DECK")
            print(f"{'='*60}")
            print(f"Commander: {commander}")
            print(f"Cards to validate: {len(cards)}")
        
        # Check commander exists
        commander_info = None
        if commander:
            commander_info = self.get_card_info(commander)
            if not commander_info:
                errors.append(f"Commander '{commander}' not found in database")
            elif 'Legendary' not in commander_info.get('typeLine', ''):
                errors.append(f"Commander '{commander}' is not legendary")
            elif 'Creature' not in commander_info.get('typeLine', '') and 'Planeswalker' not in commander_info.get('typeLine', ''):
                # Some commanders can be enchantments (e.g., Grist)
                warnings.append(f"Commander '{commander}' is not a creature or planeswalker (unusual but may be legal)")
        else:
            errors.append("No commander specified")
        
        # Get commander color identity
        commander_colors = set(commander_info['colorIdentity']) if commander_info else set()
        
        # Validate cards
        total_cards = 0
        card_counts = {}
        hallucinated_cards = []
        illegal_cards = []
        color_violations = []
        
        for card_entry in cards:
            name = card_entry['name']
            quantity = card_entry['quantity']
            
            total_cards += quantity
            card_counts[name] = card_counts.get(name, 0) + quantity
            
            # Check if card exists
            card_info = self.get_card_info(name)
            
            if not card_info:
                hallucinated_cards.append(name)
                continue
            
            # Check Commander legality
            if not self.is_commander_legal(card_info['legalities']):
                illegal_cards.append(name)
            
            # Check color identity (skip basic lands)
            if name not in self.basic_lands and commander_info:
                card_colors = set(card_info['colorIdentity'])
                if not card_colors.issubset(commander_colors):
                    color_violations.append(f"{name} ({','.join(card_colors)}) violates commander identity ({','.join(commander_colors)})")
            
            # Check for invalid duplicates
            if card_counts[name] > 1:
                if name not in self.legal_duplicates and name not in self.basic_lands:
                    errors.append(f"Invalid duplicate: {card_counts[name]}x {name} (not a legal duplicate)")
        
        # Add commander to total (if not already counted)
        if commander and commander not in card_counts:
            total_cards += 1
        
        # Check card count
        if total_cards != 100:
            errors.append(f"Deck has {total_cards} cards, need exactly 100")
        
        # Add errors for hallucinated/illegal cards
        if hallucinated_cards:
            errors.append(f"Hallucinated cards (not in database): {', '.join(hallucinated_cards[:5])}" + 
                         (f" and {len(hallucinated_cards)-5} more" if len(hallucinated_cards) > 5 else ""))
        
        if illegal_cards:
            errors.append(f"Commander-illegal cards: {', '.join(illegal_cards[:5])}" +
                         (f" and {len(illegal_cards)-5} more" if len(illegal_cards) > 5 else ""))
        
        if color_violations:
            for violation in color_violations[:3]:
                errors.append(violation)
            if len(color_violations) > 3:
                errors.append(f"... and {len(color_violations)-3} more color identity violations")
        
        # Print results
        if verbose:
            print(f"\nResults:")
            print(f"  Total cards: {total_cards}")
            print(f"  Unique cards: {len(card_counts)}")
            print(f"  Hallucinated: {len(hallucinated_cards)}")
            print(f"  Illegal: {len(illegal_cards)}")
            print(f"  Color violations: {len(color_violations)}")
            
            if errors:
                print(f"\n❌ ERRORS ({len(errors)}):")
                for error in errors:
                    print(f"  - {error}")
            
            if warnings:
                print(f"\n⚠️  WARNINGS ({len(warnings)}):")
                for warning in warnings:
                    print(f"  - {warning}")
            
            if not errors:
                print(f"\n✅ DECK IS VALID!")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'stats': {
                'total_cards': total_cards,
                'unique_cards': len(card_counts),
                'hallucinated': len(hallucinated_cards),
                'illegal': len(illegal_cards),
                'color_violations': len(color_violations)
            }
        }


def validate_deck_file(file_path: str):
    """Validate a deck from a file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        deck_text = f.read()
    
    validator = DeckValidator()
    return validator.validate_deck(deck_text)


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        result = validate_deck_file(sys.argv[1])
        sys.exit(0 if result['valid'] else 1)
    else:
        # Test with sample deck
        sample_deck = """
Commander: Atraxa, Praetors' Voice

1x Sol Ring
1x Arcane Signet
1x Command Tower
1x Exotic Orchard
1x Llanowar Elves
1x Birds of Paradise
1x Cultivate
1x Kodama's Reach
10x Plains
10x Island
10x Swamp
10x Forest
        """
        
        validator = DeckValidator()
        result = validator.validate_deck(sample_deck.strip())
