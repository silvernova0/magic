#!/usr/bin/env python3
"""
Add functional tags to cards in the database

This script analyzes card oracle text, type lines, and keywords to assign
functional tags like 'ramp', 'card_draw', 'removal', etc.

These tags are used by the v3 deck builder to find cards matching filters.

Usage:
    python3 scripts/tag-cards.py
"""

import sqlite3
import json
import re
from typing import List, Set

class CardTagger:
    def __init__(self, db_path="prisma/dev.db"):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        
        # Add tags column if it doesn't exist
        try:
            cursor = self.conn.cursor()
            cursor.execute("ALTER TABLE Card ADD COLUMN tags TEXT")
            self.conn.commit()
            print("✅ Added 'tags' column to Card table")
        except sqlite3.OperationalError:
            print("ℹ️  'tags' column already exists")
    
    def get_tags_for_card(self, card: dict) -> Set[str]:
        """Determine tags for a card based on its properties"""
        tags = set()
        
        oracle = (card['oracleText'] or '').lower()
        type_line = (card['typeLine'] or '').lower()
        name = (card['name'] or '').lower()
        
        # RAMP (mana acceleration)
        ramp_patterns = [
            r'add.*mana',
            r'search.*land',
            r'put.*land.*battlefield',
            r'treasure',
            r'{t}.*add',
            r'whenever.*land.*enters',
        ]
        
        ramp_cards = ['sol ring', 'mana crypt', 'mana vault', 'arcane signet', 
                      'birds of paradise', 'llanowar elves', 'elvish mystic']
        
        if any(re.search(pattern, oracle) for pattern in ramp_patterns):
            tags.add('ramp')
        if any(name == card_name for card_name in ramp_cards):
            tags.add('ramp')
        if 'land' in type_line and 'add' in oracle:
            tags.add('ramp')
        
        # CARD DRAW
        draw_patterns = [
            r'draw.*card',
            r'draws? a card',
            r'draws? \d+ card',
            r'you may draw',
        ]
        
        if any(re.search(pattern, oracle) for pattern in draw_patterns):
            tags.add('card_draw')
        
        # REMOVAL (single target)
        removal_patterns = [
            r'destroy target',
            r'exile target',
            r'return target.*to.*hand',
            r'sacrifice.*creature',
            r'deals? \d+ damage to',
        ]
        
        if any(re.search(pattern, oracle) for pattern in removal_patterns):
            tags.add('removal')
        
        # BOARD WIPES (mass removal)
        wipe_patterns = [
            r'destroy all',
            r'exile all',
            r'destroy each',
            r'exile each',
            r'damage to each',
            r'deals \d+ damage to all',
        ]
        
        if any(re.search(pattern, oracle) for pattern in wipe_patterns):
            tags.add('board_wipe')
        
        # TUTORS (search library for specific cards)
        tutor_patterns = [
            r'search your library for a.*card',
            r'search your library for an',
            r'search your library for up to',
        ]
        
        if any(re.search(pattern, oracle) for pattern in tutor_patterns):
            tags.add('tutor')
        
        # PROTECTION
        protection_patterns = [
            r'hexproof',
            r'shroud',
            r'protection from',
            r'indestructible',
            r"can't be countered",
            r'ward',
        ]
        
        if any(re.search(pattern, oracle) for pattern in protection_patterns):
            tags.add('protection')
        
        # COUNTERSPELLS
        if re.search(r'counter target', oracle) and 'instant' in type_line:
            tags.add('counterspell')
            tags.add('protection')
        
        # RECURSION (graveyard)
        recursion_patterns = [
            r'return.*from.*graveyard',
            r'from your graveyard to',
            r'play.*from.*graveyard',
            r'cast.*from.*graveyard',
        ]
        
        if any(re.search(pattern, oracle) for pattern in recursion_patterns):
            tags.add('recursion')
            tags.add('graveyard')
        
        # GRAVEYARD SYNERGY
        graveyard_patterns = [
            r'graveyard',
            r'dies',
            r'when.*enters.*graveyard',
            r'mill',
        ]
        
        if any(re.search(pattern, oracle) for pattern in graveyard_patterns):
            tags.add('graveyard')
        
        # COMBAT
        combat_patterns = [
            r'double strike',
            r'first strike',
            r'vigilance',
            r'trample',
            r'menace',
            r'lifelink',
            r'deathtouch',
            r'whenever.*attacks',
            r'whenever.*deals combat damage',
        ]
        
        if any(re.search(pattern, oracle) for pattern in combat_patterns):
            tags.add('combat')
        
        # TOKEN GENERATION
        if re.search(r'create.*token', oracle):
            tags.add('tokens')
        
        # SACRIFICE
        if re.search(r'sacrifice', oracle):
            tags.add('sacrifice')
        
        # LIFEGAIN
        if re.search(r'gain.*life|you gain \d+', oracle):
            tags.add('lifegain')
        
        # TRIBAL SYNERGY
        tribal_types = ['dragon', 'elf', 'goblin', 'zombie', 'vampire', 'merfolk', 
                       'wizard', 'knight', 'soldier', 'angel', 'demon']
        
        for tribe in tribal_types:
            if re.search(rf'\b{tribe}\b', oracle) or re.search(rf'\b{tribe}\b', type_line):
                tags.add(f'tribal_{tribe}')
        
        # COMBO PIECES (keywords that often indicate combo potential)
        combo_keywords = [
            r'infinite',
            r'untap all',
            r'take an extra turn',
            r'copy.*spell',
            r'double.*mana',
        ]
        
        if any(re.search(pattern, oracle) for pattern in combo_keywords):
            tags.add('combo')
        
        # STAX (resource denial)
        stax_patterns = [
            r"can't attack",
            r"can't cast",
            r"can't activate",
            r'opponents.*cost.*more',
            r'enter.*tapped',
            r'taxes?',
        ]
        
        if any(re.search(pattern, oracle) for pattern in stax_patterns):
            tags.add('stax')
        
        # TYPE-BASED TAGS
        if 'planeswalker' in type_line:
            tags.add('planeswalker')
        if 'artifact' in type_line:
            tags.add('artifact')
        if 'enchantment' in type_line:
            tags.add('enchantment')
        
        return tags
    
    def tag_all_cards(self, batch_size=1000):
        """Tag all cards in the database"""
        cursor = self.conn.cursor()
        
        # Get total count
        cursor.execute("SELECT COUNT(*) FROM Card")
        total = cursor.fetchone()[0]
        
        print(f"Tagging {total} cards...")
        
        # Process in batches
        offset = 0
        tagged_count = 0
        
        while offset < total:
            # Fetch batch
            cursor.execute("""
                SELECT id, name, oracleText, typeLine, keywords
                FROM Card
                LIMIT ? OFFSET ?
            """, (batch_size, offset))
            
            cards = cursor.fetchall()
            
            # Tag each card
            for card in cards:
                card_dict = dict(card)
                tags = self.get_tags_for_card(card_dict)
                
                # Store as JSON array
                tags_json = json.dumps(sorted(list(tags)))
                
                # Update database
                cursor.execute("""
                    UPDATE Card
                    SET tags = ?
                    WHERE id = ?
                """, (tags_json, card_dict['id']))
                
                tagged_count += 1
                
                # Progress indicator
                if tagged_count % 1000 == 0:
                    print(f"  Tagged {tagged_count}/{total} cards...")
            
            self.conn.commit()
            offset += batch_size
        
        print(f"✅ Tagged {tagged_count} cards")
    
    def show_tag_stats(self):
        """Show statistics about tagged cards"""
        cursor = self.conn.cursor()
        
        print("\n" + "="*70)
        print("TAG STATISTICS")
        print("="*70)
        
        # Get all tags
        cursor.execute("SELECT tags FROM Card WHERE tags IS NOT NULL AND tags != '[]'")
        
        tag_counts = {}
        for row in cursor.fetchall():
            try:
                tags = json.loads(row[0])
                for tag in tags:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1
            except:
                pass
        
        # Sort by count
        sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
        
        print(f"\nTop 30 tags:")
        for tag, count in sorted_tags[:30]:
            print(f"  {tag:20s} {count:5d} cards")
        
        print(f"\nTotal unique tags: {len(tag_counts)}")
        print(f"Total tagged cards: {len([t for t in tag_counts.values() if t > 0])}")
    
    def show_sample_tagged_cards(self, tag: str, limit=5):
        """Show sample cards with a specific tag"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT name, typeLine, oracleText, tags
            FROM Card
            WHERE tags LIKE ?
            LIMIT ?
        """, (f'%"{tag}"%', limit))
        
        print(f"\n{'='*70}")
        print(f"Sample '{tag}' cards:")
        print(f"{'='*70}")
        
        for row in cursor.fetchall():
            print(f"\n{row[0]}")
            print(f"  Type: {row[1]}")
            if row[2]:
                print(f"  Text: {row[2][:80]}...")
            tags = json.loads(row[3]) if row[3] else []
            print(f"  Tags: {', '.join(tags)}")
    
    def close(self):
        self.conn.close()


def main():
    print("="*70)
    print("CARD TAGGING SYSTEM")
    print("="*70)
    
    tagger = CardTagger()
    
    try:
        # Tag all cards
        tagger.tag_all_cards()
        
        # Show statistics
        tagger.show_tag_stats()
        
        # Show samples
        print("\n")
        tagger.show_sample_tagged_cards('ramp', limit=5)
        tagger.show_sample_tagged_cards('removal', limit=5)
        tagger.show_sample_tagged_cards('card_draw', limit=5)
        tagger.show_sample_tagged_cards('counterspell', limit=3)
        
        print("\n✅ Tagging complete!")
        
    finally:
        tagger.close()


if __name__ == '__main__':
    main()
