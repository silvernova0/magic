#!/usr/bin/env python3
"""
Update isCommander flag for all qualifying legendary cards.

This script identifies cards that can be commanders based on current rules:
1. Legendary Creature (traditional commanders)
2. Legendary Artifact Creature (e.g., Hope of Ghirapur, Karn)
3. Legendary Artifact — Vehicle (new rule allows vehicles as commanders)
4. Legendary Enchantment Creature — Background (with "Choose a Background")

NOTE: Regular Legendary Artifacts (Equipment, etc.) CANNOT be commanders
"""

import sqlite3
from pathlib import Path

def update_commander_flags():
    """Update isCommander flag for all qualifying legendary cards"""
    
    db_path = Path(__file__).parent.parent / 'prisma' / 'dev.db'
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("=" * 70)
    print("UPDATING COMMANDER FLAGS")
    print("=" * 70)
    
    # First, get current count
    cursor.execute("SELECT COUNT(*) FROM Card WHERE isCommander = 1")
    current_count = cursor.fetchone()[0]
    print(f"\n📊 Current cards with isCommander = 1: {current_count}")
    
    # Find all cards that should be commanders but aren't flagged
    # Criteria:
    # 1. Legendary Creature (includes Artifact Creatures, Enchantment Creatures, etc.)
    # 2. Legendary Artifact — Vehicle
    # 3. Legal in Commander format
    query = """
        SELECT id, name, typeLine, colorIdentity, legalities
        FROM Card
        WHERE (
            typeLine LIKE '%Legendary Creature%'
            OR typeLine LIKE '%Legendary Artifact — Vehicle%'
            OR typeLine LIKE '%Legendary Artifact — Spacecraft%'
        )
        AND legalities LIKE '%"commander":"Legal"%'
        AND isCommander = 0
        ORDER BY name
    """
    
    cursor.execute(query)
    candidates = cursor.fetchall()
    
    print(f"\n🔍 Found {len(candidates)} cards that should have isCommander = 1:")
    print()
    
    if len(candidates) == 0:
        print("✅ All qualifying cards already have isCommander = 1")
        conn.close()
        return
    
    # Group by type for display
    creatures = []
    artifact_creatures = []
    vehicles = []
    other = []
    
    for card in candidates:
        type_line = card['typeLine']
        if 'Legendary Artifact Creature' in type_line:
            artifact_creatures.append(card)
        elif 'Legendary Artifact — Vehicle' in type_line or 'Legendary Artifact — Spacecraft' in type_line:
            vehicles.append(card)
        elif 'Legendary Creature' in type_line:
            creatures.append(card)
        else:
            other.append(card)
    
    if creatures:
        print(f"🧙 Legendary Creatures ({len(creatures)}):")
        for card in creatures:
            print(f"   - {card['name']} ({card['typeLine']})")
        print()
    
    if artifact_creatures:
        print(f"🤖 Legendary Artifact Creatures ({len(artifact_creatures)}):")
        for card in artifact_creatures:
            print(f"   - {card['name']} ({card['typeLine']})")
        print()
    
    if vehicles:
        print(f"🚗 Legendary Vehicles/Spacecraft ({len(vehicles)}):")
        for card in vehicles:
            print(f"   - {card['name']} ({card['typeLine']})")
        print()
    
    if other:
        print(f"❓ Other ({len(other)}):")
        for card in other:
            print(f"   - {card['name']} ({card['typeLine']})")
        print()
    
    # Update all candidates
    print(f"🔧 Updating {len(candidates)} cards...")
    card_ids = [card['id'] for card in candidates]
    
    placeholders = ','.join(['?'] * len(card_ids))
    update_query = f"UPDATE Card SET isCommander = 1 WHERE id IN ({placeholders})"
    cursor.execute(update_query, card_ids)
    conn.commit()
    
    # Verify update
    cursor.execute("SELECT COUNT(*) FROM Card WHERE isCommander = 1")
    new_count = cursor.fetchone()[0]
    
    print(f"\n✅ Updated successfully!")
    print(f"   Before: {current_count} commanders")
    print(f"   After:  {new_count} commanders")
    print(f"   Added:  {new_count - current_count} commanders")
    
    # Show colorless commander count
    cursor.execute("""
        SELECT COUNT(*) FROM Card 
        WHERE colorIdentity = '' 
        AND isCommander = 1 
        AND (typeLine LIKE '%Legendary Creature%' OR typeLine LIKE '%Legendary Artifact — Vehicle%')
        AND legalities LIKE '%"commander":"Legal"%'
    """)
    colorless_count = cursor.fetchone()[0]
    print(f"\n🎯 Colorless commanders: {colorless_count}")
    
    conn.close()
    print("\n" + "=" * 70)

if __name__ == '__main__':
    update_commander_flags()
