"""
Scrape cEDH Decklist Database
This site has all deck data embedded as JSON in the HTML - perfect!
"""
import requests
from bs4 import BeautifulSoup
import json
import re
import time
import random
from pathlib import Path

class CEDHDatabaseScraper:
    def __init__(self, output_dir='data/training'):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    def fetch_database(self):
        """Fetch the cEDH database page and extract deck links"""
        print("Fetching cEDH Decklist Database...")
        
        response = requests.get(
            'https://cedh-decklist-database.com/',
            headers=self.headers,
            timeout=15
        )
        
        if response.status_code != 200:
            print(f"❌ Failed to fetch database: {response.status_code}")
            return []
        
        print(f"✅ Database page loaded ({len(response.text)} bytes)")
        
        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract all deck links from the page
        deck_links = {
            'moxfield': set(),
            'archidekt': set(),
            'other': set()
        }
        
        # Find all links in the HTML
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            
            if 'moxfield.com/decks/' in href:
                # Extract Moxfield deck ID
                match = re.search(r'moxfield\.com/decks/([a-zA-Z0-9_-]+)', href)
                if match:
                    deck_links['moxfield'].add(match.group(1))
            
            elif 'archidekt.com/decks/' in href:
                # Extract Archidekt deck ID
                match = re.search(r'archidekt\.com/decks/(\d+)', href)
                if match:
                    deck_links['archidekt'].add(match.group(1))
        
        # Also check script tags for embedded data
        for script in soup.find_all('script'):
            script_text = script.string or ''
            
            # Find Moxfield links
            moxfield_matches = re.findall(r'moxfield\.com/decks/([a-zA-Z0-9_-]+)', script_text)
            deck_links['moxfield'].update(moxfield_matches)
            
            # Find Archidekt links
            archidekt_matches = re.findall(r'archidekt\.com/decks/(\d+)', script_text)
            deck_links['archidekt'].update(archidekt_matches)
        
        print(f"\n📊 Found deck links:")
        print(f"  Moxfield: {len(deck_links['moxfield'])}")
        print(f"  Archidekt: {len(deck_links['archidekt'])}")
        
        return deck_links
    
    def fetch_moxfield_deck(self, deck_id):
        """Fetch a Moxfield deck using public API"""
        try:
            url = f'https://api2.moxfield.com/v2/decks/all/{deck_id}'
            
            response = requests.get(url, headers=self.headers, timeout=10)
            
            # Moxfield blocks API access, try direct page scraping instead
            if response.status_code == 403:
                return None
            
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            return None
    
    def fetch_archidekt_deck(self, deck_id):
        """Fetch an Archidekt deck"""
        try:
            url = f'https://archidekt.com/api/decks/{deck_id}/'
            
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            return None
    
    def parse_archidekt_deck(self, deck_data):
        """Parse Archidekt deck data"""
        try:
            deck_id = deck_data.get('id')
            name = deck_data.get('name', 'Untitled')
            
            # Get commanders
            commanders = []
            cards_list = deck_data.get('cards', [])
            
            if isinstance(cards_list, list):
                for card_entry in cards_list:
                    categories = card_entry.get('categories', [])
                    if 'Commander' in categories:
                        card_data = card_entry.get('card', {})
                        oracle_card = card_data.get('oracleCard', {})
                        card_name = oracle_card.get('name', '')
                        if card_name:
                            commanders.append(card_name)
            
            commander_name = commanders[0] if commanders else 'Unknown'
            
            # Get color identity
            colors = []
            color_obj = deck_data.get('colors', {})
            if color_obj:
                if color_obj.get('w'): colors.append('W')
                if color_obj.get('u'): colors.append('U')
                if color_obj.get('b'): colors.append('B')
                if color_obj.get('r'): colors.append('R')
                if color_obj.get('g'): colors.append('G')
            
            # Parse all cards
            cards = []
            if isinstance(cards_list, list):
                for card_entry in cards_list:
                    card_data = card_entry.get('card', {})
                    oracle_card = card_data.get('oracleCard', {})
                    
                    card_name = oracle_card.get('name', '')
                    if not card_name:
                        continue
                    
                    quantity = card_entry.get('quantity', 1)
                    categories = card_entry.get('categories', [])
                    category = categories[0] if categories else 'Other'
                    
                    cards.append({
                        'name': card_name,
                        'category': category,
                        'quantity': quantity
                    })
            
            return {
                'commander': commander_name,
                'name': name,
                'theme': 'cEDH',
                'colors': colors,
                'cards': cards,
                'source': 'cedh-database-archidekt',
                'url': f'https://archidekt.com/decks/{deck_id}',
                'metadata': {
                    'competitive': True,
                    'database': 'cEDH Decklist Database'
                }
            }
            
        except Exception as e:
            print(f"Error parsing Archidekt deck: {e}")
            return None
    
    def scrape_decks(self):
        """Main scraping function"""
        print(f"\n{'='*60}")
        print("CEDH DECKLIST DATABASE SCRAPER")
        print(f"{'='*60}\n")
        
        # Fetch database
        deck_links = self.fetch_database()
        
        if not deck_links:
            print("❌ No deck links found")
            return []
        
        # Focus on Archidekt since Moxfield API is blocked
        archidekt_ids = list(deck_links['archidekt'])
        total = len(archidekt_ids)
        
        print(f"\n🎯 Scraping {total} Archidekt decks from cEDH database...")
        print("(Skipping Moxfield - API blocked)\n")
        
        decks = []
        failed = 0
        
        for i, deck_id in enumerate(archidekt_ids, 1):
            print(f"[{i}/{total}] Fetching deck {deck_id}...")
            
            # Fetch deck data
            deck_data = self.fetch_archidekt_deck(deck_id)
            
            if not deck_data:
                failed += 1
                print(f"  ✗ Failed to fetch")
                time.sleep(2)  # Rate limit
                continue
            
            # Parse deck
            parsed = self.parse_archidekt_deck(deck_data)
            
            if not parsed:
                failed += 1
                print(f"  ✗ Failed to parse")
                time.sleep(2)
                continue
            
            # Validate
            if len(parsed['cards']) < 80:
                failed += 1
                print(f"  ✗ Incomplete ({len(parsed['cards'])} cards)")
                time.sleep(2)
                continue
            
            decks.append(parsed)
            print(f"  ✓ {parsed['commander']} ({len(parsed['cards'])} cards)")
            
            # Save progress every 25 decks
            if len(decks) % 25 == 0:
                self._save_progress(decks)
                print(f"\n💾 Progress saved: {len(decks)} decks\n")
            
            # Rate limiting - be respectful
            time.sleep(random.uniform(3.0, 5.0))
        
        # Final save
        self._save_progress(decks)
        
        print(f"\n{'='*60}")
        print("SCRAPING COMPLETE")
        print(f"{'='*60}")
        print(f"✓ Successfully scraped: {len(decks)} cEDH decks")
        print(f"✗ Failed: {failed} decks")
        print(f"📁 Saved to: {self.output_dir / 'cedh_decks.jsonl'}")
        
        return decks
    
    def _save_progress(self, decks):
        """Save decks to JSONL file"""
        output_file = self.output_dir / 'cedh_decks.jsonl'
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for deck in decks:
                f.write(json.dumps(deck) + '\n')

if __name__ == '__main__':
    scraper = CEDHDatabaseScraper()
    decks = scraper.scrape_decks()
    
    if decks:
        print(f"\n✅ Sample deck:")
        sample = decks[0]
        print(f"  Commander: {sample['commander']}")
        print(f"  Theme: {sample['theme']}")
        print(f"  Colors: {', '.join(sample['colors'])}")
        print(f"  Cards: {len(sample['cards'])}")
