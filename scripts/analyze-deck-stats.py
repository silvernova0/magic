import sqlite3
import json
import os
import statistics
from collections import defaultdict

DB_PATH = 'prisma/dev.db'
OUTPUT_FILE = 'data/deck_stats.json'

def load_card_types(conn):
    print("Loading card types...")
    cursor = conn.cursor()
    cursor.execute("SELECT name, typeLine FROM Card")
    card_types = {}
    for name, type_line in cursor.fetchall():
        # Handle split cards (take first half type usually, or both)
        # For simplicity, we'll store the full type line and parse it later
        card_types[name] = type_line
        # Also store the first half of split cards
        if ' // ' in name:
            card_types[name.split(' // ')[0]] = type_line
    print(f"Loaded {len(card_types)} card definitions.")
    return card_types

def get_card_category(type_line):
    type_line = type_line.lower()
    if 'land' in type_line: return 'lands'
    if 'creature' in type_line: return 'creatures'
    if 'instant' in type_line: return 'instants'
    if 'sorcery' in type_line: return 'sorceries'
    if 'artifact' in type_line: return 'artifacts'
    if 'enchantment' in type_line: return 'enchantments'
    if 'planeswalker' in type_line: return 'planeswalkers'
    return 'other'

def analyze_decks():
    if not os.path.exists('data'):
        os.makedirs('data')

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    card_types = load_card_types(conn)
    
    print("Fetching decks...")
    cursor = conn.cursor()
    cursor.execute("SELECT decklist, theme FROM CommanderDeck")
    decks = cursor.fetchall()
    
    stats = {
        'global': defaultdict(list),
        'by_theme': defaultdict(lambda: defaultdict(list))
    }
    
    valid_decks_count = 0
    
    for row in decks:
        try:
            deck_data = json.loads(row['decklist'])
            mainboard = deck_data.get('mainboard', [])
            
            if not mainboard:
                continue
                
            # Count types for this deck
            deck_counts = defaultdict(int)
            unknown_cards = 0
            
            for card_name in mainboard:
                # Normalize name
                clean_name = card_name.split(' // ')[0]
                
                type_line = card_types.get(card_name) or card_types.get(clean_name)
                
                if type_line:
                    category = get_card_category(type_line)
                    deck_counts[category] += 1
                else:
                    # Try basic lands manually if missing from DB for some reason
                    if clean_name in ['Plains', 'Island', 'Swamp', 'Mountain', 'Forest', 'Wastes']:
                        deck_counts['lands'] += 1
                    else:
                        unknown_cards += 1
            
            # Only include decks that look reasonably complete (e.g. > 80 cards identified)
            total_identified = sum(deck_counts.values())
            if total_identified < 80:
                continue
                
            valid_decks_count += 1
            theme = row['theme'] or 'Unknown'
            
            for category in ['creatures', 'instants', 'sorceries', 'artifacts', 'enchantments', 'planeswalkers', 'lands']:
                count = deck_counts[category]
                stats['global'][category].append(count)
                stats['by_theme'][theme][category].append(count)
                
        except json.JSONDecodeError:
            continue
            
    print(f"Analyzed {valid_decks_count} valid decks.")
    
    # Calculate aggregates
    final_output = {
        'global': {},
        'by_theme': {}
    }
    
    def calculate_metrics(counts):
        if not counts:
            return {'avg': 0, 'min': 0, 'max': 0, 'std_dev': 0}
        return {
            'avg': round(statistics.mean(counts), 1),
            'min': min(counts),
            'max': max(counts),
            'std_dev': round(statistics.stdev(counts), 1) if len(counts) > 1 else 0
        }
    
    print("Calculating statistics...")
    
    for category, counts in stats['global'].items():
        final_output['global'][category] = calculate_metrics(counts)
        
    for theme, categories in stats['by_theme'].items():
        # Only include themes with enough samples
        if len(categories['lands']) < 5:
            continue
            
        final_output['by_theme'][theme] = {}
        for category, counts in categories.items():
            final_output['by_theme'][theme][category] = calculate_metrics(counts)
            
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(final_output, f, indent=2)
        
    print(f"Stats saved to {OUTPUT_FILE}")
    conn.close()

if __name__ == "__main__":
    analyze_decks()
