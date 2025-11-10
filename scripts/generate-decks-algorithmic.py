"""
Algorithmic Commander Deck Generator
Uses the local card database to build diverse, synergistic Commander decks
Much faster than AI generation - can create 1000s of decks in minutes
"""
import os
import sys
import json
import random
import sqlite3
from pathlib import Path
from collections import defaultdict

def connect_db():
    """Connect to the SQLite database"""
    return sqlite3.connect('prisma/dev.db')

def get_commanders(conn, limit=None):
    """Get all commanders from database"""
    cursor = conn.cursor()
    query = "SELECT id, name, colorIdentity, edhrecRank FROM Card WHERE isCommander = 1"
    if limit:
        query += f" ORDER BY RANDOM() LIMIT {limit}"
    cursor.execute(query)
    return cursor.fetchall()

def get_cards_by_criteria(conn, color_identity, card_types=None, tags=None, exclude_commander=None, limit=50):
    """Get cards matching criteria from database"""
    cursor = conn.cursor()
    
    # Build query - simplified to just get any playable cards
    conditions = []
    params = []
    
    # Type filter
    if card_types:
        type_conditions = [f"typeLine LIKE ?" for _ in card_types]
        conditions.append(f"({' OR '.join(type_conditions)})")
        params.extend([f"%{t}%" for t in card_types])
    
    # Exclude commander
    if exclude_commander:
        conditions.append("id != ?")
        params.append(exclude_commander)
    
    # Not a commander
    conditions.append("isCommander = 0")
    
    # Not a basic land (we handle those separately)
    conditions.append("name NOT IN ('Plains', 'Island', 'Swamp', 'Mountain', 'Forest')")
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    query = f"""
        SELECT id, name, typeLine, colorIdentity, edhrecRank, edhrecSaltiness
        FROM Card
        WHERE {where_clause}
        ORDER BY RANDOM()
        LIMIT ?
    """
    params.append(limit)
    
    cursor.execute(query, params)
    return cursor.fetchall()

def get_lands(conn, color_identity, num_basics=20):
    """Get appropriate lands for color identity"""
    cursor = conn.cursor()
    lands = []
    
    # Basic lands based on color identity
    basic_lands = {
        'W': 'Plains',
        'U': 'Island',
        'B': 'Swamp',
        'R': 'Mountain',
        'G': 'Forest'
    }
    
    colors = [c for c in ['W', 'U', 'B', 'R', 'G'] if c in color_identity]
    if colors:
        per_color = num_basics // len(colors)
        for color in colors:
            lands.append({
                'name': basic_lands[color],
                'quantity': per_color,
                'category': 'Land'
            })
    
    # Non-basic lands (utility, duals, etc.)
    # Prioritize multi-color lands if 2+ colors
    num_nonbasics = 35 - num_basics if len(colors) > 1 else 38 - num_basics
    
    cursor.execute("""
        SELECT name FROM Card
        WHERE typeLine LIKE '%Land%'
        AND (colorIdentity = '' OR colorIdentity IN (?, ?, ?))
        AND name NOT IN ('Plains', 'Island', 'Swamp', 'Mountain', 'Forest')
        ORDER BY edhrecRank ASC
        LIMIT ?
    """, (color_identity, '', 'C', num_nonbasics))
    
    for row in cursor.fetchall():
        lands.append({
            'name': row[0],
            'quantity': 1,
            'category': 'Land'
        })
    
    return lands

def build_deck_algorithmic(commander_info, theme, power_level_target):
    """Build a Commander deck algorithmically"""
    conn = connect_db()
    
    commander_id, commander_name, color_identity, edhrec = commander_info
    
    deck = {
        'commander': commander_name,
        'theme': theme,
        'power_level': power_level_target,
        'cards': []
    }
    
    # Add commander
    deck['cards'].append({
        'name': commander_name,
        'quantity': 1,
        'category': 'Commander'
    })
    
    # Get lands (35-38 depending on colors)
    num_colors = len([c for c in ['W', 'U', 'B', 'R', 'G'] if c in color_identity])
    num_basics = 20 if num_colors > 2 else 25 if num_colors > 1 else 30
    lands = get_lands(conn, color_identity, num_basics)
    deck['cards'].extend(lands)
    
    cards_added = 1 + sum(l['quantity'] for l in lands)
    remaining = 99 - cards_added
    
    # Theme-based card selection
    theme_tags = {
        'aggro': ['creature', 'combat', 'haste'],
        'control': ['counterspell', 'removal', 'card-draw'],
        'combo': ['tutor', 'card-draw', 'storm'],
        'tokens': ['token', 'sacrifice', 'aristocrats'],
        'voltron': ['equipment', 'aura', 'protection'],
        'graveyard': ['graveyard', 'reanimator', 'sacrifice'],
        'ramp': ['ramp', 'land', 'mana'],
        'tribal': ['tribal', 'creature'],
        'artifacts': ['artifact', 'equipment'],
        'enchantments': ['enchantment', 'aura']
    }
    
    tags = theme_tags.get(theme, ['creature', 'removal', 'card-draw'])
    
    # Get theme cards (40% of deck)
    theme_cards = get_cards_by_criteria(
        conn, color_identity, 
        tags=tags,
        exclude_commander=commander_id,
        limit=int(remaining * 0.4)
    )
    
    for card in theme_cards:
        deck['cards'].append({
            'name': card[1],
            'quantity': 1,
            'category': card[2].split('—')[0].strip()
        })
        cards_added += 1
    
    # Add staples (ramp, draw, removal) - 30% of deck
    staple_tags = ['ramp', 'card-draw', 'removal']
    staple_cards = get_cards_by_criteria(
        conn, color_identity,
        tags=staple_tags,
        exclude_commander=commander_id,
        limit=int(remaining * 0.3)
    )
    
    for card in staple_cards:
        if card[1] not in [c['name'] for c in deck['cards']]:  # Avoid duplicates
            deck['cards'].append({
                'name': card[1],
                'quantity': 1,
                'category': card[2].split('—')[0].strip()
            })
            cards_added += 1
    
    # Fill remaining slots with creatures and spells
    attempts = 0
    while cards_added < 99 and attempts < 5:
        needed = 99 - cards_added
        filler = get_cards_by_criteria(
            conn, color_identity,
            card_types=['Creature', 'Instant', 'Sorcery', 'Artifact', 'Enchantment'],
            exclude_commander=commander_id,
            limit=needed * 2  # Get extra to account for duplicates
        )
        
        added_this_round = 0
        for card in filler:
            if card[1] not in [c['name'] for c in deck['cards']]:
                deck['cards'].append({
                    'name': card[1],
                    'quantity': 1,
                    'category': card[2].split('—')[0].strip() if '—' in card[2] else card[2].split(' ')[0]
                })
                cards_added += 1
                added_this_round += 1
                if cards_added >= 99:
                    break
        
        if added_this_round == 0:
            attempts += 1
        else:
            attempts = 0
    
    conn.close()
    return deck

def generate_decks(num_decks=1900, output_file='data/training/synthetic_decks.jsonl'):
    """Generate multiple decks"""
    conn = connect_db()
    
    # Load existing progress
    existing_decks = []
    if os.path.exists(output_file):
        with open(output_file, 'r', encoding='utf-8') as f:
            existing_decks = [json.loads(line) for line in f]
        print(f"📂 Found {len(existing_decks)} existing decks, resuming...")
    
    decks = existing_decks
    
    # Get all commanders
    commanders = get_commanders(conn)
    print(f"Found {len(commanders)} commanders")
    
    themes = ['aggro', 'control', 'combo', 'tokens', 'voltron', 'graveyard', 'ramp', 'tribal', 'artifacts', 'enchantments']
    power_levels = list(range(4, 8))  # Focus on 4-7 power level (most common)
    
    print(f"\n{'='*60}")
    print(f"ALGORITHMIC DECK GENERATOR")
    print(f"{'='*60}\n")
    print(f"Target: {num_decks} decks")
    print(f"Starting from: {len(decks)}\n")
    
    try:
        while len(decks) < num_decks:
            # Random commander, theme, power level
            commander = random.choice(commanders)
            theme = random.choice(themes)
            power_level = random.choice(power_levels)
            
            deck_num = len(decks) + 1
            print(f"[{deck_num}/{num_decks}] {commander[1]} ({theme}, PL {power_level})", end='')
            
            try:
                deck = build_deck_algorithmic(commander, theme, power_level)
                
                # Validate card count
                total_cards = sum(c['quantity'] for c in deck['cards'])
                
                if 95 <= total_cards <= 105:
                    decks.append(deck)
                    print(f" ✓ ({total_cards} cards)")
                    
                    # Save progress every 50 decks
                    if len(decks) % 50 == 0:
                        with open(output_file, 'w', encoding='utf-8') as f:
                            for d in decks:
                                f.write(json.dumps(d, ensure_ascii=False) + '\n')
                        print(f"\n💾 Progress saved: {len(decks)} decks\n")
                else:
                    print(f" ✗ Invalid count ({total_cards} cards)")
            
            except Exception as e:
                print(f" ✗ Error: {str(e)[:50]}")
    
    except KeyboardInterrupt:
        print(f"\n\n⚠️ Interrupted by user")
    
    finally:
        # Final save
        with open(output_file, 'w', encoding='utf-8') as f:
            for d in decks:
                f.write(json.dumps(d, ensure_ascii=False) + '\n')
        
        print(f"\n{'='*60}")
        print(f"GENERATION COMPLETE")
        print(f"{'='*60}")
        print(f"✓ Successfully generated: {len(decks)} decks")
        print(f"📁 Saved to: {output_file}")
        
        conn.close()

if __name__ == '__main__':
    generate_decks(1900)
