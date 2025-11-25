#!/usr/bin/env python3
"""
Scrape Moxfield for underrepresented strategies to balance training data.

Target strategies with <100 examples:
- artifacts, lifegain, lands_matter, stax, mill, wheels
- group_hug, discard, group_slug, superfriends, infect
- enchantments, pillowfort, tempo, hate_bears
"""

import requests
import json
import time
from pathlib import Path

class MoxfieldStrategyBalancer:
    def __init__(self, output_file='data/training/moxfield_strategies_balanced.jsonl'):
        self.api_base = 'https://api2.moxfield.com/v3/decks/search'
        self.output_file = Path(output_file)
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing deck IDs
        self.scraped_ids = set()
        if self.output_file.exists():
            with open(self.output_file, 'r') as f:
                for line in f:
                    try:
                        deck = json.loads(line)
                        if 'publicId' in deck:
                            self.scraped_ids.add(deck['publicId'])
                    except:
                        pass
        
        print(f"Existing strategy decks: {len(self.scraped_ids)}")
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json'
        })

    # Moxfield themes for each strategy
    STRATEGY_THEMES = {
        'artifacts': ['Artifacts', 'Artifact'],
        'lifegain': ['Lifegain', 'Life Gain'],
        'lands_matter': ['Lands', 'Landfall', 'Lands Matter'],
        'stax': ['Stax'],
        'mill': ['Mill'],
        'wheels': ['Wheels', 'Wheel'],
        'group_hug': ['Group Hug', 'Hug'],
        'discard': ['Discard'],
        'group_slug': ['Group Slug', 'Slug'],
        'superfriends': ['Superfriends', 'Planeswalkers'],
        'infect': ['Infect', 'Poison'],
        'enchantments': ['Enchantments', 'Enchantress'],
        'pillowfort': ['Pillowfort'],
        'tempo': ['Tempo'],
        'hate_bears': ['Hatebears', 'Death and Taxes']
    }

    def search_decks(self, theme, bracket=None, page=1, page_size=32):
        """Search Moxfield for decks by theme"""
        try:
            params = {
                'pageNumber': page,
                'pageSize': page_size,
                'sortType': 'views',
                'sortDirection': 'Descending',
                'board': 'mainboard',
                'fmt': 'commander',
                'themes': theme
            }
            
            if bracket:
                params['edhBracket'] = bracket
            
            response = self.session.get(self.api_base, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            return data.get('data', []), data.get('totalResults', 0)
            
        except Exception as e:
            print(f"      Error searching {theme}: {e}")
            return [], 0

    def get_deck_details(self, deck_id):
        """Get full deck details from Moxfield"""
        try:
            url = f'https://api2.moxfield.com/v3/decks/all/{deck_id}'
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"      Error fetching deck {deck_id}: {e}")
            return None

    def parse_deck(self, deck_data):
        """Parse Moxfield deck data"""
        try:
            # Get commanders
            commanders = []
            for cmd in deck_data.get('commanders', []):
                card = cmd.get('card', {})
                if card.get('name'):
                    commanders.append(card['name'])
            
            if not commanders:
                return None
            
            # Get mainboard cards
            cards = []
            for card_entry in deck_data.get('mainboard', {}).values():
                card = card_entry.get('card', {})
                if card.get('name'):
                    cards.append(card['name'])
            
            if len(cards) < 50:
                return None
            
            # Get themes
            themes = [t.get('name', '') for t in deck_data.get('themes', [])]
            
            return {
                'publicId': deck_data.get('publicId'),
                'commander': commanders[0],
                'all_cards': cards,
                'themes': themes,
                'categories': {},
                'hubs': deck_data.get('hubs', []),
                'format': 'commander',
                'source': 'Moxfield Strategy Balancer'
            }
            
        except Exception as e:
            print(f"      Error parsing deck: {e}")
            return None

    def scrape_strategy(self, strategy_name, target_count=200):
        """Scrape decks for a specific strategy"""
        themes = self.STRATEGY_THEMES.get(strategy_name, [strategy_name])
        
        print(f"\n{'='*60}")
        print(f"Strategy: {strategy_name}")
        print(f"Themes: {', '.join(themes)}")
        print(f"Target: {target_count} decks")
        print(f"{'='*60}")
        
        total_scraped = 0
        
        with open(self.output_file, 'a') as f:
            for theme in themes:
                print(f"\n  Theme: {theme}")
                
                # Try different brackets
                for bracket in [None, '2', '3', '4', '5']:
                    if total_scraped >= target_count:
                        break
                    
                    bracket_label = f"Bracket {bracket}" if bracket else "All brackets"
                    print(f"    {bracket_label}...")
                    
                    page = 1
                    max_pages = 10
                    
                    while page <= max_pages and total_scraped < target_count:
                        decks, total = self.search_decks(theme, bracket, page)
                        
                        if not decks:
                            break
                        
                        new_decks = 0
                        for deck_summary in decks:
                            deck_id = deck_summary.get('publicId')
                            
                            if not deck_id or deck_id in self.scraped_ids:
                                continue
                            
                            # Get full deck
                            deck_data = self.get_deck_details(deck_id)
                            if not deck_data:
                                continue
                            
                            parsed = self.parse_deck(deck_data)
                            if not parsed:
                                continue
                            
                            # Add strategy tag
                            parsed['target_strategy'] = strategy_name
                            
                            f.write(json.dumps(parsed) + '\n')
                            f.flush()
                            
                            self.scraped_ids.add(deck_id)
                            total_scraped += 1
                            new_decks += 1
                            
                            print(f"      ✓ [{total_scraped}] {parsed['commander']}")
                            
                            if total_scraped >= target_count:
                                break
                            
                            time.sleep(0.5)
                        
                        print(f"      Page {page}: {new_decks} new decks")
                        
                        if new_decks == 0:
                            break
                        
                        page += 1
                        time.sleep(1)
                    
                    if total_scraped >= target_count:
                        break
        
        print(f"\n  ✅ Scraped {total_scraped} {strategy_name} decks")
        return total_scraped

    def run(self):
        """Balance all underrepresented strategies"""
        
        # Priorities based on current counts
        priorities = [
            ('artifacts', 200),       # 63 → 200
            ('lifegain', 150),        # 42 → 150
            ('lands_matter', 150),    # 25 → 150
            ('stax', 150),            # 23 → 150
            ('mill', 150),            # 22 → 150
            ('wheels', 100),          # 19 → 100
            ('group_hug', 100),       # 16 → 100
            ('discard', 100),         # 16 → 100
            ('group_slug', 100),      # 14 → 100
            ('superfriends', 150),    # 11 → 150
            ('infect', 100),          # 10 → 100
            ('enchantments', 100),    # 4 → 100
            ('pillowfort', 100),      # 2 → 100
            ('tempo', 100),           # 1 → 100
            ('hate_bears', 100),      # 1 → 100
        ]
        
        print(f"\n{'='*60}")
        print(f"MOXFIELD STRATEGY BALANCER")
        print(f"{'='*60}")
        print(f"Targeting {len(priorities)} underrepresented strategies")
        print(f"Output: {self.output_file}")
        print(f"{'='*60}\n")
        
        total_all = 0
        
        for strategy, target in priorities:
            scraped = self.scrape_strategy(strategy, target)
            total_all += scraped
            time.sleep(2)
        
        print(f"\n{'='*60}")
        print(f"BALANCING COMPLETE")
        print(f"{'='*60}")
        print(f"Total new decks: {total_all}")
        print(f"Output: {self.output_file}")
        print(f"{'='*60}\n")


if __name__ == '__main__':
    scraper = MoxfieldStrategyBalancer()
    scraper.run()
