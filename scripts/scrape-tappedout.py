"""
Scrape TappedOut Commander decks
TappedOut has thousands of user-submitted Commander decks with ratings
"""
import requests
from bs4 import BeautifulSoup
import json
import re
import time
import random
from pathlib import Path

class TappedOutScraper:
    def __init__(self, output_dir='data/training'):
        self.base_url = 'https://tappedout.net'
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    def search_commander_decks(self, page=1):
        """Search for Commander decks"""
        try:
            # Use the direct search URL with EDH filter and top decks
            url = f'{self.base_url}/mtg-decks/search/'
            
            params = {
                'q': '',  # Empty query = all decks
                'format': 'edh',  # Commander/EDH format
                'is_top': 'on',  # Only top-rated decks
                'o': '-Views',  # Sort by most viewed (capital V matters!)
                'page': page,
                'submit': 'Filter+results'
            }
            
            response = requests.get(url, params=params, headers=self.headers, timeout=15)
            
            if response.status_code != 200:
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find deck links in search results
            deck_urls = []
            
            # Look for all links matching deck pattern
            all_deck_links = soup.find_all('a', href=re.compile(r'/mtg-decks/[^/]+/$'))
            
            for link in all_deck_links:
                deck_url = link.get('href')
                
                # Filter out non-deck URLs
                if deck_url and '/search/' not in deck_url and '/log-in/' not in deck_url:
                    # Must have a valid deck slug (not just /mtg-decks/)
                    if deck_url.count('/') >= 3:  # e.g., /mtg-decks/deck-name/
                        full_url = self.base_url + deck_url if not deck_url.startswith('http') else deck_url
                        
                        # Avoid duplicates
                        if full_url not in deck_urls:
                            deck_urls.append(full_url)
            
            return deck_urls
            
        except Exception as e:
            print(f"Error searching page {page}: {e}")
            return []
    
    def fetch_deck(self, deck_url):
        """Fetch and parse a single deck"""
        try:
            response = requests.get(deck_url, headers=self.headers, timeout=15)
            
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Get deck name
            deck_name_elem = soup.find('h2', class_='deck-title')
            if not deck_name_elem:
                deck_name_elem = soup.find('h1')
            deck_name = deck_name_elem.text.strip() if deck_name_elem else 'Unknown'
            
            # Extract commander from the "Commander (1)" section
            commander_name = 'Unknown'
            commander_h3 = soup.find('h3', string=lambda x: x and 'commander' in x.lower() and '(' in x)
            if commander_h3:
                # Get the next div.row which contains the commander card
                next_div = commander_h3.find_next('div', class_='row')
                if next_div:
                    # Find the card-hover link which has data-name attribute
                    card_hover = next_div.find('a', class_='card-hover')
                    if card_hover:
                        commander_name = card_hover.get('data-name', '').strip()
            
            # Fallback: try deck title if commander not found
            if not commander_name or commander_name == 'Unknown':
                if ',' in deck_name:
                    commander_name = deck_name.split(',')[0].strip()
                else:
                    commander_name = deck_name
            
            # Parse card list
            cards = []
            seen_cards = set()  # Track seen cards to avoid duplicates
            
            # TappedOut uses li elements with card-link class
            card_elements = soup.find_all('li', class_='member')
            
            for card_elem in card_elements:
                # Get category from parent section
                category = 'Other'
                parent_board = card_elem.find_parent('div', class_='board-container')
                if parent_board:
                    header = parent_board.find(['h3', 'h4'])
                    if header:
                        category = header.text.strip()
                
                # Skip Maybeboard and Sideboard cards
                if 'maybe' in category.lower() or 'sideboard' in category.lower():
                    continue
                
                # Get quantity
                qty_span = card_elem.find('span', class_='qty')
                quantity = 1
                if qty_span:
                    try:
                        quantity = int(qty_span.text.strip())
                    except:
                        quantity = 1
                
                # Get card name
                card_link = card_elem.find('a', class_='card-link')
                if not card_link:
                    card_link = card_elem.find('a')
                
                if card_link:
                    card_name = card_link.text.strip()
                    
                    # Skip duplicates (TappedOut might show cards multiple times)
                    card_key = f"{card_name}|{category}"
                    if card_key in seen_cards:
                        continue
                    seen_cards.add(card_key)
                    
                    cards.append({
                        'name': card_name,
                        'category': category,
                        'quantity': quantity
                    })
            
            if not cards:
                return None
            
            # Get colors - would need to determine from cards
            colors = []
            
            return {
                'commander': commander_name,
                'name': deck_name,
                'theme': 'User Deck',
                'colors': colors,
                'cards': cards,
                'source': 'tappedout',
                'url': deck_url,
                'metadata': {
                    'database': 'TappedOut'
                }
            }
            
        except Exception as e:
            print(f"  Error parsing deck: {e}")
            return None
    
    def scrape_decks(self, num_decks=500, max_pages=50):
        """Main scraping function"""
        print(f"\n{'='*60}")
        print("TAPPEDOUT COMMANDER SCRAPER")
        print(f"{'='*60}\n")
        print(f"Target: {num_decks} decks from top-rated Commander lists\n")
        
        all_decks = []
        failed = 0
        seen_urls = set()
        page = 1
        
        while len(all_decks) < num_decks and page <= max_pages:
            print(f"\n[Page {page}/{max_pages}]")
            
            # Get deck URLs from search page
            deck_urls = self.search_commander_decks(page=page)
            
            if not deck_urls:
                print("  No more decks found")
                break
            
            print(f"  Found {len(deck_urls)} deck link(s)")
            
            # Fetch each deck
            for deck_url in deck_urls:
                if len(all_decks) >= num_decks:
                    break
                
                if deck_url in seen_urls:
                    continue
                
                seen_urls.add(deck_url)
                
                print(f"  [{len(all_decks)+1}/{num_decks}] Fetching...")
                
                deck_data = self.fetch_deck(deck_url)
                
                if not deck_data:
                    failed += 1
                    print(f"    ✗ Failed to parse")
                    time.sleep(1)
                    continue
                
                # Validate
                if len(deck_data['cards']) < 80:
                    failed += 1
                    print(f"    ✗ Incomplete ({len(deck_data['cards'])} cards)")
                    time.sleep(1)
                    continue
                
                # Also skip if way too many cards (indicates we're including sideboards/maybeboards)
                if len(deck_data['cards']) > 150:
                    failed += 1
                    print(f"    ✗ Too many cards ({len(deck_data['cards'])} cards)")
                    time.sleep(1)
                    continue
                
                all_decks.append(deck_data)
                print(f"    ✓ {deck_data['commander']} ({len(deck_data['cards'])} cards)")
                
                # Save progress every 25 decks
                if len(all_decks) % 25 == 0:
                    self._save_progress(all_decks)
                    print(f"\n💾 Progress saved: {len(all_decks)} decks\n")
                
                # Rate limiting
                time.sleep(random.uniform(2.0, 4.0))
            
            page += 1
            time.sleep(random.uniform(3.0, 5.0))
        
        # Final save
        self._save_progress(all_decks)
        
        print(f"\n{'='*60}")
        print("SCRAPING COMPLETE")
        print(f"{'='*60}")
        print(f"✓ Successfully scraped: {len(all_decks)} decks")
        print(f"✗ Failed: {failed} decks")
        print(f"📁 Saved to: {self.output_dir / 'tappedout_decks.jsonl'}")
        
        return all_decks
    
    def _save_progress(self, decks):
        """Save decks to JSONL file"""
        output_file = self.output_dir / 'tappedout_decks.jsonl'
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for deck in decks:
                f.write(json.dumps(deck) + '\n')

if __name__ == '__main__':
    scraper = TappedOutScraper()
    
    # Scrape 500 top-rated Commander decks
    decks = scraper.scrape_decks(num_decks=500, max_pages=50)
    
    if decks:
        print(f"\n✅ Sample deck:")
        sample = decks[0]
        print(f"  Commander: {sample['commander']}")
        print(f"  Cards: {len(sample['cards'])}")
        print(f"  URL: {sample['url']}")
