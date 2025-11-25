#!/usr/bin/env python3
"""
Quick test for normalize_card_name function
"""

def normalize_card_name(card_name: str) -> str:
    """
    Normalize card names to handle split cards, MDFCs, and other variants.
    """
    if not card_name or '//' not in card_name:
        return card_name
    
    # Split on //
    parts = [p.strip() for p in card_name.split('//')]
    
    # If both sides are identical, use just one
    if len(parts) == 2 and parts[0] == parts[1]:
        return parts[0]
    
    # Otherwise keep the full name (for actual split cards)
    return card_name


# Test cases
test_cases = [
    ("Command Tower // Command Tower", "Command Tower"),
    ("Command Tower", "Command Tower"),
    ("Fire // Ice", "Fire // Ice"),
    ("Valki, God of Lies // Tibalt, Cosmic Impostor", "Valki, God of Lies // Tibalt, Cosmic Impostor"),
    ("Wear // Tear", "Wear // Tear"),
]

print("Testing normalize_card_name():")
for input_name, expected in test_cases:
    result = normalize_card_name(input_name)
    status = "✅" if result == expected else "❌"
    print(f"{status} '{input_name}' -> '{result}' (expected: '{expected}')")
