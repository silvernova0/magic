#!/usr/bin/env python3
"""
Scrape EDHREC tag pages for underrepresented strategies
https://edhrec.com/tags/{tag-name}

Each tag page shows top commanders and decklists for that strategy
"""

import requests
from bs4 import BeautifulSoup
import json
import time
from pathlib import Path
import re

class EDHRECTagScraper:
    def __init__(self, output_file='data/training/edhrec_tag_decks.jsonl'):
        self.base_url = 'https://edhrec.com'
        self.output_file = Path(output_file)
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing deck IDs
        self.scraped_urls = set()
        if self.output_file.exists():
            with open(self.output_file, 'r') as f:
                for line in f:
                    try:
                        deck = json.loads(line)
                        if 'url' in deck:
                            self.scraped_urls.add(deck['url'])
                    except:
                        pass
        
        print(f"Existing tag decks: {len(self.scraped_urls)}")
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    # EDHREC tag names for underrepresented strategies
    TAG_MAPPING = {
        'artifacts': ['artifacts', 'artifact-tokens'],
        'lifegain': ['lifegain', 'life-drain'],
        'lands_matter': ['lands-matter', 'landfall'],
        'stax': ['stax', 'prison'],
        'mill': ['mill'],
        'wheels': ['wheels'],
        'group_hug': ['group-hug'],
        'discard': ['discard', 'hand-disruption'],
        'group_slug': ['group-slug', 'punishment'],
        'superfriends': ['superfriends', 'planeswalkers'],
        'infect': ['infect', 'poison-counters'],
        'enchantments': ['enchantress', 'enchantments'],
        'pillowfort': ['pillowfort'],
        'tempo': ['tempo'],
        'hate_bears': ['hatebears', 'death-and-taxes']
    }

    def slugify(self, name):
        """Convert name to EDHREC slug format"""
        slug = name.lower()
        slug = slug.replace("'", "")
        slug = slug.replace(",", "")
        slug = slug.replace(" ", "-")
        slug = re.sub(r'[^a-z0-9-]', '', slug)
        return slug

    def scrape_tag_page(self, tag):
        """Scrape commanders and decks from an EDHREC tag page"""
        try:
            url = f'{self.base_url}/tags/{tag}'
            print(f"\n  Tag: {tag}")
            print(f"  URL: {url}")
            
            response = self.session.get(url, timeout=10)
            if response.status_code != 200:
                print(f"    ⚠️  Status {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find top commanders for this tag
            commanders = []
            commander_links = soup.find_all('a', href=lambda x: x and '/commanders/' in x)
            
            for link in commander_links[:20]:  # Top 20 commanders
                href = link.get('href', '')
                if '/commanders/' in href:
                    commander_name = href.split('/commanders/')[-1].replace('-', ' ').title()
                    commanders.append({
                        'name': commander_name,
                        'url': f"{self.base_url}{href}" if href.startswith('/') else href
                    })
            
            print(f"    Found {len(commanders)} commanders")
            
            # For each commander, get their average deck with this tag
            decks = []
            for commander in commanders:
                deck = self.scrape_commander_tag_deck(commander['name'], tag)
                if deck:
                    decks.append(deck)
                    time.sleep(1)
            
            return decks
            
        except Exception as e:
            print(f"    Error scraping tag {tag}: {e}")
            return []

    def scrape_commander_tag_deck(self, commander_name, tag):
        """Scrape average deck for commander+tag combination"""
        try:
            slug = self.slugify(commander_name)
            url = f'{self.base_url}/average-decks/{slug}?f=tag%3A{tag}'
            
            if url in self.scraped_urls:
                return None
            
            response = self.session.get(url, timeout=10)
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract cards from the deck
            cards = []
            
            # Method 1: Find card links
            card_links = soup.find_all('a', {'class': 'card-link'})
            for link in card_links:
                card_name = link.get('data-card-name') or link.text.strip()
                if card_name and card_name not in cards:
                    cards.append(card_name)
            
            # Method 2: Find all links to /cards/
            if len(cards) < 20:
                all_card_links = soup.find_all('a', href=lambda x: x and '/cards/' in x)
                for link in all_card_links:
                    card_name = link.text.strip()
                    if card_name and card_name not in cards and len(card_name) > 2:
                        cards.append(card_name)
            
            if len(cards) < 30:
                return None
            
            # Limit to 99 mainboard
            cards = cards[:99]
            
            deck_data = {
                'commander': commander_name,
                'all_cards': cards,
                'themes': [tag],
                'categories': {},
                'source': 'EDHREC Tag',
                'tag': tag,
                'url': url
            }
            
            print(f"      ✓ {commander_name}: {len(cards)} cards")
            return deck_data
            
        except Exception as e:
            return None

    def scrape_strategy(self, strategy_name, target_count=100):
        """Scrape decks for a specific strategy from all its tags"""
        tags = self.TAG_MAPPING.get(strategy_name, [strategy_name])
        
        print(f"\n{'='*60}")
        print(f"Strategy: {strategy_name}")
        print(f"Tags: {', '.join(tags)}")
        print(f"Target: {target_count} decks")
        print(f"{'='*60}")
        
        all_decks = []
        
        for tag in tags:
            decks = self.scrape_tag_page(tag)
            all_decks.extend(decks)
            
            if len(all_decks) >= target_count:
                break
            
            time.sleep(2)
        
        # Save to file
        with open(self.output_file, 'a') as f:
            for deck in all_decks[:target_count]:
                # Add strategy marker
                deck['target_strategy'] = strategy_name
                f.write(json.dumps(deck) + '\n')
                f.flush()
        
        self.scraped_urls.update(deck['url'] for deck in all_decks if 'url' in deck)
        
        print(f"\n  ✅ Scraped {len(all_decks)} {strategy_name} decks")
        return len(all_decks)

    def run(self):
        """Scrape all underrepresented strategies"""
        
        # Priorities based on current counts
        priorities = [
            ('artifacts', 150),       # 63 → 150
            ('lifegain', 100),        # 42 → 100
            ('lands_matter', 100),    # 25 → 100
            ('stax', 100),            # 23 → 100
            ('mill', 100),            # 22 → 100
            ('wheels', 80),           # 19 → 80
            ('group_hug', 80),        # 16 → 80
            ('discard', 80),          # 16 → 80
            ('group_slug', 80),       # 14 → 80
            ('superfriends', 100),    # 11 → 100
            ('infect', 80),           # 10 → 80
            ('enchantments', 80),     # 4 → 80
            ('pillowfort', 80),       # 2 → 80
            ('tempo', 80),            # 1 → 80
            ('hate_bears', 80),       # 1 → 80
        ]
        
        print(f"\n{'='*60}")
        print(f"EDHREC TAG SCRAPER")
        print(f"{'='*60}")
        print(f"Targeting {len(priorities)} underrepresented strategies")
        print(f"Output: {self.output_file}")
        print(f"{'='*60}\n")
        
        total_all = 0
        
        for strategy, target in priorities:
            scraped = self.scrape_strategy(strategy, target)
            total_all += scraped
            time.sleep(3)
        
        print(f"\n{'='*60}")
        print(f"SCRAPING COMPLETE")
        print(f"{'='*60}")
        print(f"Total new decks: {total_all}")
        print(f"Output: {self.output_file}")
        print(f"{'='*60}\n")


if __name__ == '__main__':
    scraper = EDHRECTagScraper()
    scraper.run()
