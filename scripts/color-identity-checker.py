#!/usr/bin/env python3
"""
Add color identity enforcement to deck builder

This script updates the deck builder to properly filter cards by color identity,
ensuring all cards in a deck match the commander's color identity.

Color identity rules:
- A card's color identity includes:
  * Mana symbols in its cost
  * Mana symbols in its rules text
  * Color indicator
- Commander deck can only include cards with color identity ⊆ commander's identity

Example:
- Atraxa (WUBG) can include white, blue, black, green, and colorless cards
- Ur-Dragon (WUBRG) can include all colors
- Krenko (R) can only include red and colorless
"""

import sqlite3
import json
from typing import Set, List

class ColorIdentityChecker:
    """Helper class for color identity operations"""
    
    # Color mapping
    COLORS = {'W': 'White', 'U': 'Blue', 'B': 'Black', 'R': 'Red', 'G': 'Green', 'C': 'Colorless'}
    
    @staticmethod
    def parse_color_identity(color_identity_str: str) -> Set[str]:
        """Parse color identity from database string (comma-separated or JSON)"""
        if not color_identity_str:
            return set()
        
        # Try JSON first
        if color_identity_str.startswith('['):
            try:
                colors = json.loads(color_identity_str)
                return set(colors) if colors else set()
            except:
                pass
        
        # Otherwise treat as comma-separated
        colors = color_identity_str.split(',')
        return set(c.strip() for c in colors if c.strip())
    
    @staticmethod
    def is_within_identity(card_colors: Set[str], commander_colors: Set[str]) -> bool:
        """Check if card's color identity is within commander's identity"""
        # Empty set (colorless) is always valid
        if not card_colors:
            return True
        
        # Card colors must be subset of commander colors
        return card_colors.issubset(commander_colors)
    
    @staticmethod
    def get_commander_identity(db_path: str, commander_name: str) -> Set[str]:
        """Get commander's color identity from database"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT colorIdentity
            FROM Card
            WHERE name = ?
            LIMIT 1
        """, (commander_name,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row and row[0]:
            return ColorIdentityChecker.parse_color_identity(row[0])
        
        return set()
    
    @staticmethod
    def format_colors(colors: Set[str]) -> str:
        """Format color identity for display"""
        if not colors:
            return "Colorless"
        
        # Sort in WUBRG order
        order = ['W', 'U', 'B', 'R', 'G']
        sorted_colors = [c for c in order if c in colors]
        
        color_names = [ColorIdentityChecker.COLORS[c] for c in sorted_colors]
        return ', '.join(color_names) + f" ({'/'.join(sorted_colors)})"


def test_color_identity():
    """Test color identity checking"""
    checker = ColorIdentityChecker()
    
    print("="*70)
    print("COLOR IDENTITY TESTING")
    print("="*70)
    
    # Test cases
    test_commanders = [
        "The Ur-Dragon",  # WUBRG
        "Atraxa, Praetors' Voice",  # WUBG
        "Krenko, Mob Boss",  # R
        "Muldrotha, the Gravetide",  # UBG
    ]
    
    for commander in test_commanders:
        colors = checker.get_commander_identity("prisma/dev.db", commander)
        print(f"\n{commander}")
        print(f"  Color Identity: {checker.format_colors(colors)}")
        
        # Test some cards
        conn = sqlite3.connect("prisma/dev.db")
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT name, colorIdentity
            FROM Card
            WHERE name IN ('Sol Ring', 'Lightning Bolt', 'Counterspell', 'Growth Spiral')
        """)
        
        print(f"  Card compatibility:")
        for row in cursor.fetchall():
            card_name = row[0]
            card_colors = checker.parse_color_identity(row[1])
            is_legal = checker.is_within_identity(card_colors, colors)
            status = "✅" if is_legal else "❌"
            print(f"    {status} {card_name} ({checker.format_colors(card_colors)})")
        
        conn.close()


if __name__ == '__main__':
    test_color_identity()
