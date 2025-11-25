#!/usr/bin/env python3
"""
Scrape cEDH decks directly from TappedOut
Bypasses EDHTop16 since most tournaments have "Unknown Commander" (no real decks)
"""

import requests
from bs4 import BeautifulSoup
import json
import time
from pathlib import Path
import sqlite3

class TappedOutCEDHScraper:
    def __init__(self, output_file='data/training/tappedout_cedh_decks.jsonl', db_path='prisma/dev.db'):
        self.base_url = 'https://tappedout.net'
        self.output_file = Path(output_file)
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        
        # Load existing deck URLs
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
        
        print(f"Existing TappedOut cEDH decks: {len(self.scraped_urls)}")
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # Load commanders from database
        self.commanders = self.load_commanders()
        print(f"Loaded {len(self.commanders)} legal commanders from database")

    def load_commanders(self):
        """Load list of legal commander names from the database"""
        commanders = set()
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM Card WHERE isCommander = 1")
            for row in cursor.fetchall():
                commanders.add(row[0])
            conn.close()
        except Exception as e:
            print(f"Warning: Could not load commanders from database: {e}")
        return commanders

    def search_cedh_decks(self, page=1):
        """Search TappedOut for cEDH/competitive Commander decks"""
        try:
            # TappedOut search URL for competitive Commander decks
            # Format: commander, sorted by rating/views, competitive tag
            url = f"{self.base_url}/mtg-decks/search/"
            params = {
                'format': 'commander-edh',
                'q': 'cedh OR competitive',
                'p': page,
                'o': '-rating'  # Sort by rating descending
            }
            
            response = self.session.get(url, params=params, timeout=15)
            if response.status_code != 200:
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find deck links
            deck_links = []
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                if '/mtg-decks/' in href and href.count('/') >= 3:
                    full_url = href if href.startswith('http') else f"{self.base_url}{href}"
                    if full_url not in self.scraped_urls:
                        deck_links.append(full_url)
            
            return list(set(deck_links))
            
        except Exception as e:
            print(f"  Error searching page {page}: {e}")
            return []

    def scrape_deck(self, url):
        """Scrape a TappedOut decklist"""
        try:
            response = self.session.get(url, timeout=15)
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Get deck name
            title = soup.find('h1')
            deck_name = title.text.strip() if title else url.split('/')[-2]
            
            # Find commander
            commander = None
            commander_section = soup.find('div', {'id': 'commander-tab'})
            
            if commander_section:
                commander_card = commander_section.find('a', {'class': 'card'})
                if commander_card:
                    commander = commander_card.get('data-name') or commander_card.text.strip()
            
            # Verify commander is legal
            if not commander or commander not in self.commanders:
                return None
            
            # Get all cards
            cards = []
            card_list = soup.find('div', {'id': 'board-list'})
            
            if card_list:
                for card_elem in card_list.find_all('a', {'class': 'card'}):
                    card_name = card_elem.get('data-name') or card_elem.text.strip()
                    if card_name:
                        # Find quantity
                        qty_elem = card_elem.find_parent().find('span', {'class': 'qty'})
                        qty = int(qty_elem.text.strip()) if qty_elem else 1
                        cards.append({'name': card_name, 'quantity': qty})
            
            # Validate deck size
            total_cards = sum(c['quantity'] for c in cards)
            if total_cards < 98 or total_cards > 101:  # Allow for partner commanders
                return None
            
            # Build deck text format
            deck_text = f"Commander: {commander}\n\n"
            deck_text += f"Deck Name: {deck_name}\n"
            deck_text += f"Source: cEDH (TappedOut competitive)\n"
            deck_text += f"URL: {url}\n\n"
            deck_text += "Commanders:\n"
            deck_text += f"1x {commander}\n\n"
            
            # Group cards by type (simplified)
            deck_text += "Decklist:\n"
            for card in cards:
                if card['name'] != commander:
                    deck_text += f"{card['quantity']}x {card['name']}\n"
            
            return {
                'url': url,
                'commander': commander,
                'deck_name': deck_name,
                'total_cards': total_cards,
                'source': 'tappedout_cedh',
                'competitive': True,
                'bracket': 5,  # cEDH is Bracket 5
                'instruction': f"Build a competitive cEDH deck with {commander}",
                'output': deck_text
            }
            
        except Exception as e:
            print(f"      Error scraping {url}: {e}")
            return None

    def run(self, max_pages=20):
        """Main scraping loop"""
        print(f"\n{'='*60}")
        print(f"TAPPEDOUT CEDH SCRAPER")
        print(f"{'='*60}")
        print(f"Output: {self.output_file}")
        print(f"Target: {max_pages} pages of cEDH decks")
        print(f"{'='*60}")
        
        total_decks = 0
        
        with open(self.output_file, 'a') as f:
            for page in range(1, max_pages + 1):
                print(f"\n[Page {page}/{max_pages}]")
                
                deck_links = self.search_cedh_decks(page)
                print(f"  Found {len(deck_links)} deck links")
                
                if not deck_links:
                    print("  No more decks found, stopping")
                    break
                
                for url in deck_links:
                    deck = self.scrape_deck(url)
                    if deck:
                        f.write(json.dumps(deck) + '\n')
                        f.flush()
                        self.scraped_urls.add(url)
                        total_decks += 1
                        print(f"    ✓ {deck['commander']} ({deck['total_cards']} cards)")
                    
                    time.sleep(2)  # Be nice to TappedOut
                
                time.sleep(3)  # Longer pause between pages
        
        print(f"\n{'='*60}")
        print(f"SCRAPING COMPLETE")
        print(f"Total new decks: {total_decks}")
        print(f"{'='*60}")

if __name__ == "__main__":
    scraper = TappedOutCEDHScraper()
    scraper.run(max_pages=20)  # ~20 decks per page = ~400 cEDH decks
