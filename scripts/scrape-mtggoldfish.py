"""
Scrape MTGGoldfish Commander decklists
MTGGoldfish hosts decklists directly and shows popular Commander archetypes
"""
import requests
from bs4 import BeautifulSoup
import json
import re
import time
import random
from pathlib import Path

class MTGGoldfishScraper:
    def __init__(self, output_dir='data/training'):
        self.base_url = 'https://www.mtggoldfish.com'
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    def get_popular_commanders(self):
        """Fetch list of popular Commander archetypes"""
        print("Fetching popular Commander archetypes from MTGGoldfish...")
        
        response = requests.get(
            f'{self.base_url}/metagame/commander#paper',
            headers=self.headers,
            timeout=15
        )
        
        if response.status_code != 200:
            print(f"❌ Failed: {response.status_code}")
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find commander archetype links
        commanders = []
        
        # Look for archetype links
        for link in soup.find_all('a', href=re.compile(r'/archetype/')):
            archetype_url = link.get('href')
            commander_name = link.text.strip()
            
            if commander_name and archetype_url:
                commanders.append({
                    'name': commander_name,
                    'url': self.base_url + archetype_url if not archetype_url.startswith('http') else archetype_url
                })
        
        print(f"✅ Found {len(commanders)} Commander archetypes")
        return commanders
    
    def get_archetype_decks(self, archetype_url):
        """Get sample decklists for an archetype"""
        try:
            response = requests.get(archetype_url, headers=self.headers, timeout=15)
            
            if response.status_code != 200:
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for deck links in the archetype page
            deck_links = []
            
            # MTGGoldfish deck URLs pattern: /deck/DECKID#paper
            for link in soup.find_all('a', href=re.compile(r'/deck/')):
                deck_href = link.get('href')
                
                # Skip arena/online versions, only get paper
                if '#paper' in deck_href or ('#' not in deck_href and '/deck/' in deck_href):
                    full_url = self.base_url + deck_href if not deck_href.startswith('http') else deck_href
                    
                    # Make sure it's a full deck link, not a category
                    if '/deck/' in full_url and '/decks/' not in full_url:
                        deck_links.append(full_url)
            
            # Get unique links
            unique_links = list(set(deck_links))
            return unique_links[:5]  # Limit to 5 decks per archetype
            
        except Exception as e:
            print(f"  Error fetching archetype: {e}")
            return []
    
    def fetch_deck(self, deck_url):
        """Fetch and parse a single deck"""
        try:
            response = requests.get(deck_url, headers=self.headers, timeout=15)
            
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Get deck name
            deck_name_elem = soup.find('h1', class_='title')
            deck_name = deck_name_elem.text.strip() if deck_name_elem else 'Unknown'
            
            # Get commander from deck name or page
            commander_name = deck_name
            
            # Parse card list
            cards = []
            
            # MTGGoldfish uses tables for deck lists
            deck_tables = soup.find_all('table', class_='deck-view-deck-table')
            
            for table in deck_tables:
                # Get category from table header
                category_header = table.find_previous('h5')
                category = category_header.text.strip() if category_header else 'Other'
                
                # Get cards from table rows
                rows = table.find_all('tr', class_='deck-category-count-item')
                
                for row in rows:
                    # Find quantity
                    qty_td = row.find('td', class_='text-right')
                    quantity = 1
                    if qty_td:
                        try:
                            quantity = int(qty_td.text.strip())
                        except:
                            quantity = 1
                    
                    # Find card name
                    card_link = row.find('a', class_='card-link')
                    if card_link:
                        card_name = card_link.text.strip()
                        
                        cards.append({
                            'name': card_name,
                            'category': category,
                            'quantity': quantity
                        })
            
            if not cards:
                return None
            
            # Determine colors from cards
            colors = []  # Would need card database to determine actual colors
            
            return {
                'commander': commander_name,
                'name': deck_name,
                'theme': 'Popular Archetype',
                'colors': colors,
                'cards': cards,
                'source': 'mtggoldfish',
                'url': deck_url,
                'metadata': {
                    'database': 'MTGGoldfish'
                }
            }
            
        except Exception as e:
            print(f"  Error parsing deck: {e}")
            return None
    
    def scrape_decks(self, max_commanders=50, decks_per_commander=3):
        """Main scraping function"""
        print(f"\n{'='*60}")
        print("MTGGOLDFISH COMMANDER SCRAPER")
        print(f"{'='*60}\n")
        
        # Get popular commanders
        commanders = self.get_popular_commanders()
        
        if not commanders:
            print("❌ No commanders found")
            return []
        
        # Limit commanders
        commanders = commanders[:max_commanders]
        print(f"\n🎯 Scraping decks from {len(commanders)} archetypes...")
        print(f"Target: {decks_per_commander} decks per archetype\n")
        
        all_decks = []
        failed = 0
        
        for i, commander_info in enumerate(commanders, 1):
            commander_name = commander_info['name']
            archetype_url = commander_info['url']
            
            print(f"[{i}/{len(commanders)}] {commander_name}")
            
            # Get deck links for this archetype
            deck_links = self.get_archetype_decks(archetype_url)
            
            if not deck_links:
                print(f"  ⊘ No decks found")
                time.sleep(2)
                continue
            
            print(f"  Found {len(deck_links)} deck(s)")
            
            # Fetch decks
            archetype_decks = 0
            for deck_url in deck_links[:decks_per_commander]:
                deck_data = self.fetch_deck(deck_url)
                
                if not deck_data:
                    failed += 1
                    continue
                
                # Validate
                if len(deck_data['cards']) < 80:
                    failed += 1
                    print(f"    ✗ Incomplete ({len(deck_data['cards'])} cards)")
                    continue
                
                all_decks.append(deck_data)
                archetype_decks += 1
                print(f"    ✓ {len(deck_data['cards'])} cards")
                
                time.sleep(random.uniform(1.0, 2.0))
            
            if archetype_decks > 0:
                print(f"  ✓ Scraped {archetype_decks} deck(s)")
            
            # Save progress every 10 commanders
            if (i % 10 == 0) and all_decks:
                self._save_progress(all_decks)
                print(f"\n💾 Progress saved: {len(all_decks)} decks\n")
            
            # Rate limiting between commanders
            time.sleep(random.uniform(2.0, 4.0))
        
        # Final save
        self._save_progress(all_decks)
        
        print(f"\n{'='*60}")
        print("SCRAPING COMPLETE")
        print(f"{'='*60}")
        print(f"✓ Successfully scraped: {len(all_decks)} decks")
        print(f"✗ Failed: {failed} decks")
        print(f"📁 Saved to: {self.output_dir / 'mtggoldfish_decks.jsonl'}")
        
        return all_decks
    
    def _save_progress(self, decks):
        """Save decks to JSONL file"""
        output_file = self.output_dir / 'mtggoldfish_decks.jsonl'
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for deck in decks:
                f.write(json.dumps(deck) + '\n')

if __name__ == '__main__':
    scraper = MTGGoldfishScraper()
    
    # Scrape 50 popular commanders, 3 decks each = ~150 decks
    decks = scraper.scrape_decks(max_commanders=50, decks_per_commander=3)
    
    if decks:
        print(f"\n✅ Sample deck:")
        sample = decks[0]
        print(f"  Commander: {sample['commander']}")
        print(f"  Cards: {len(sample['cards'])}")
        print(f"  URL: {sample['url']}")
