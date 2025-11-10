"""
Card Validation System for Commander AI
Ensures only real Magic cards are suggested in deck lists
"""
import json
from pathlib import Path
from typing import List, Set, Dict, Optional
import re

class CardValidator:
    def __init__(self, card_data_path='data/mtgjson/AtomicCards.json'):
        """Initialize validator with card database"""
        print(f"Loading card database from {card_data_path}...")
        
        with open(card_data_path, 'r') as f:
            data = json.load(f)
            self.atomic_cards = data.get('data', {})
        
        # Create fast lookup sets
        self.valid_card_names = set(self.atomic_cards.keys())
        
        # Create normalized name lookup for fuzzy matching
        self.normalized_to_real = {}
        for card_name in self.valid_card_names:
            normalized = self._normalize_name(card_name)
            self.normalized_to_real[normalized] = card_name
        
        print(f"✓ Loaded {len(self.valid_card_names):,} valid card names")
    
    def _normalize_name(self, name: str) -> str:
        """Normalize card name for fuzzy matching"""
        # Remove special characters, convert to lowercase
        name = name.lower()
        name = re.sub(r'[^a-z0-9\s]', '', name)
        name = re.sub(r'\s+', ' ', name).strip()
        return name
    
    def is_valid_card(self, card_name: str) -> bool:
        """Check if card name is valid"""
        return card_name in self.valid_card_names
    
    def validate_card_name(self, card_name: str) -> Optional[str]:
        """
        Validate and correct card name if possible
        Returns corrected name or None if invalid
        """
        # Exact match
        if card_name in self.valid_card_names:
            return card_name
        
        # Try normalized match
        normalized = self._normalize_name(card_name)
        if normalized in self.normalized_to_real:
            return self.normalized_to_real[normalized]
        
        # No match found
        return None
    
    def validate_deck_list(self, deck_text: str) -> Dict:
        """
        Validate an entire deck list
        Returns dict with valid cards, invalid cards, and corrections
        """
        valid_cards = []
        invalid_cards = []
        corrections = []
        
        # Parse deck text line by line
        lines = deck_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Try to extract card name
            # Format: "1 Card Name" or just "Card Name"
            match = re.match(r'^\d+\s+(.+)$', line)
            if match:
                card_name = match.group(1).strip()
            else:
                card_name = line
            
            # Skip section headers
            if any(keyword in card_name.lower() for keyword in 
                   ['commander:', 'deck name:', 'theme:', 'color identity:', 'decklist:', 
                    'creatures', 'instants', 'sorceries', 'artifacts', 'enchantments', 
                    'planeswalkers', 'lands', '(', ')']):
                continue
            
            # Validate
            corrected_name = self.validate_card_name(card_name)
            
            if corrected_name:
                valid_cards.append(corrected_name)
                if corrected_name != card_name:
                    corrections.append({
                        'original': card_name,
                        'corrected': corrected_name
                    })
            else:
                invalid_cards.append(card_name)
        
        return {
            'valid_cards': valid_cards,
            'invalid_cards': invalid_cards,
            'corrections': corrections,
            'total_cards': len(valid_cards),
            'invalid_count': len(invalid_cards)
        }
    
    def get_card_info(self, card_name: str) -> Optional[Dict]:
        """Get full card information"""
        if card_name not in self.atomic_cards:
            return None
        
        # Return first version of the card
        card = self.atomic_cards[card_name][0]
        return {
            'name': card_name,
            'types': card.get('types', []),
            'colors': card.get('colors', []),
            'colorIdentity': card.get('colorIdentity', []),
            'manaCost': card.get('manaCost', ''),
            'text': card.get('text', ''),
            'power': card.get('power'),
            'toughness': card.get('toughness'),
            'supertypes': card.get('supertypes', []),
            'subtypes': card.get('subtypes', [])
        }


def create_constrained_generation_prompt(commander: str, theme: str, validator: CardValidator) -> str:
    """
    Create a prompt that encourages the model to use real card names
    """
    # Get some example cards for the color identity
    commander_info = validator.get_card_info(commander)
    
    if commander_info:
        colors = commander_info.get('colorIdentity', [])
        color_str = ', '.join(colors) if colors else 'Colorless'
    else:
        color_str = 'Unknown'
    
    prompt = f"""Build a Commander deck with {commander} focused on {theme}.

IMPORTANT: Only use real Magic: The Gathering card names. Each card must exist in the official card database.

Commander: {commander}
Theme: {theme}
Color Identity: {color_str}

Deck Name: {commander} {theme}

Decklist:
"""
    
    return prompt


def validate_and_correct_generation(generated_text: str, validator: CardValidator, 
                                   max_corrections: int = 10) -> str:
    """
    Validate AI-generated deck and correct invalid cards
    """
    result = validator.validate_deck_list(generated_text)
    
    if result['invalid_count'] == 0:
        print(f"✓ All {result['total_cards']} cards are valid!")
        return generated_text
    
    print(f"⚠️  Found {result['invalid_count']} invalid cards:")
    
    corrected_text = generated_text
    corrections_made = 0
    
    for invalid_card in result['invalid_cards'][:max_corrections]:
        print(f"  - Invalid: {invalid_card}")
        
        # Try to find similar valid card
        # Simple approach: look for cards with similar normalized names
        normalized = validator._normalize_name(invalid_card)
        
        # Find closest match by checking if normalized name is substring
        candidates = []
        for valid_name in validator.valid_card_names:
            valid_normalized = validator._normalize_name(valid_name)
            if normalized in valid_normalized or valid_normalized in normalized:
                candidates.append(valid_name)
        
        if candidates:
            replacement = candidates[0]
            print(f"    → Replacing with: {replacement}")
            corrected_text = corrected_text.replace(invalid_card, replacement)
            corrections_made += 1
        else:
            print(f"    → No replacement found, removing card")
            # Remove the line with this card
            lines = corrected_text.split('\n')
            corrected_text = '\n'.join([line for line in lines if invalid_card not in line])
    
    print(f"\n✓ Made {corrections_made} corrections")
    return corrected_text


def filter_generation_with_constraints(model, tokenizer, prompt: str, 
                                       validator: CardValidator,
                                       max_new_tokens: int = 1024,
                                       temperature: float = 0.7) -> str:
    """
    Generate deck with real-time card name validation (streaming approach)
    This is more advanced - requires custom generation loop
    """
    # This would require implementing a custom generation loop that:
    # 1. Generates one token at a time
    # 2. When a complete card name is detected, validate it
    # 3. If invalid, use constrained beam search to force valid alternatives
    
    # For now, we'll use post-generation validation
    # But this function signature shows how you'd implement streaming validation
    pass


# Example usage functions
def example_validate_single_card():
    """Example: Validate a single card"""
    validator = CardValidator()
    
    # Test exact match
    print("\n=== Testing exact match ===")
    card = "Sol Ring"
    is_valid = validator.is_valid_card(card)
    print(f"{card}: {'✓ Valid' if is_valid else '✗ Invalid'}")
    
    # Test fuzzy match
    print("\n=== Testing fuzzy match ===")
    card = "sol ring"  # lowercase
    corrected = validator.validate_card_name(card)
    print(f"{card} → {corrected}")
    
    # Test invalid card
    print("\n=== Testing invalid card ===")
    card = "Made Up Card Name"
    corrected = validator.validate_card_name(card)
    print(f"{card} → {corrected if corrected else 'NOT FOUND'}")


def example_validate_deck():
    """Example: Validate a complete deck"""
    validator = CardValidator()
    
    deck_text = """Commander: The Ur-Dragon

Deck Name: The Ur-Dragon Dragon Tribal
Theme: Dragon Tribal
Color Identity: W, U, B, R, G

Decklist:

Creatures (30):
1 Dragon Broodmother
1 Utvara Hellkite
1 Dragonlord Dromoka
1 Fake Dragon Card
1 Sol Ring
1 Arcane Signet
1 Lightning Greaves

Lands (35):
1 Command Tower
1 Path of Ancestry
1 Exotic Orchard
1 Made Up Land
"""
    
    print("\n=== Validating deck ===")
    result = validator.validate_deck_list(deck_text)
    
    print(f"\nValid cards: {result['total_cards']}")
    print(f"Invalid cards: {result['invalid_count']}")
    
    if result['invalid_cards']:
        print("\nInvalid cards found:")
        for card in result['invalid_cards']:
            print(f"  - {card}")
    
    if result['corrections']:
        print("\nAuto-corrections made:")
        for correction in result['corrections']:
            print(f"  {correction['original']} → {correction['corrected']}")


if __name__ == '__main__':
    print("Card Validation System\n")
    
    # Run examples
    example_validate_single_card()
    example_validate_deck()
