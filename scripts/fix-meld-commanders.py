#!/usr/bin/env python3
"""
Fix commander flags for meld/back-face cards that cannot be commanders.

Meld cards like "Hanweir, the Writhing Township" and "Ragnarok, Divine Deliverance"
are legendary but cannot be cast as commanders since they only exist as the back
face of meld/transform cards.
"""

import sqlite3
from pathlib import Path

def fix_meld_commanders():
    """Remove isCommander flag from meld results and back-face-only cards"""
    
    db_path = Path(__file__).parent.parent / 'prisma' / 'dev.db'
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("=" * 70)
    print("FIXING MELD/BACK-FACE COMMANDER FLAGS")
    print("=" * 70)
    
    # Find all legendary cards without '//' in their name
    # These might be meld results or back faces
    query = """
        SELECT id, name, typeLine
        FROM Card
        WHERE isCommander = 1
        AND typeLine LIKE '%Legendary%'
        AND name NOT LIKE '%//%'
    """
    
    cursor.execute(query)
    potential_meld_cards = cursor.fetchall()
    
    print(f"\n📊 Found {len(potential_meld_cards)} legendary cards without '//' in name")
    
    # Check if each card has a front-face version (card with '//' that includes this name)
    meld_results = []
    
    for card in potential_meld_cards:
        # Check if there's a card with '//' that has this card's name as the back face
        cursor.execute("""
            SELECT name FROM Card 
            WHERE name LIKE ? 
            AND name LIKE '%//%'
            LIMIT 1
        """, (f'%{card["name"]}',))
        
        front_face = cursor.fetchone()
        if front_face:
            meld_results.append(card)
            print(f"   🔍 {card['name']} <- Back face of: {front_face['name']}")
    
    if len(meld_results) == 0:
        print("\n✅ No meld/back-face cards found with isCommander = 1")
        conn.close()
        return
    
    print(f"\n🔧 Removing isCommander flag from {len(meld_results)} meld/back-face cards:")
    for card in meld_results:
        print(f"   - {card['name']}")
    
    # Update the database
    meld_ids = [card['id'] for card in meld_results]
    placeholders = ','.join(['?'] * len(meld_ids))
    update_query = f"UPDATE Card SET isCommander = 0 WHERE id IN ({placeholders})"
    cursor.execute(update_query, meld_ids)
    conn.commit()
    
    print(f"\n✅ Updated {len(meld_results)} cards")
    print(f"   These cards can no longer be selected as commanders")
    
    conn.close()
    print("\n" + "=" * 70)

if __name__ == '__main__':
    fix_meld_commanders()
