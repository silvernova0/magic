#!/usr/bin/env python3
"""
Scrape Commander decklists from TappedOut.net
Includes official precons and community decks
"""
import requests
import json
import time
import random
import re
from pathlib import Path
from bs4 import BeautifulSoup

class TappedOutScraper:
    def __init__(self, output_dir='data/training'):
        self.base_url = 'https://tappedout.net'
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.output_file = self.output_dir / 'tappedout_decks.jsonl'
        self.scraped_ids = set()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        })
        
        # Load existing deck IDs
        self._load_existing_ids()
    
    def _load_existing_ids(self):
        """Load already-scraped deck IDs to avoid duplicates"""
        if self.output_file.exists():
            with open(self.output_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        try:
                            data = json.loads(line)
                            url = data.get('metadata', {}).get('url', '')
                            if 'tappedout.net/mtg-decks/' in url:
                                deck_slug = url.split('/mtg-decks/')[1].rstrip('/')
                                self.scraped_ids.add(deck_slug)
                        except:
                            pass
            print(f"Loaded {len(self.scraped_ids)} existing TappedOut deck IDs")
    
    def get_deck_details(self, deck_slug):
        """Fetch and parse deck page"""
        try:
            url = f'{self.base_url}/mtg-decks/{deck_slug}/'
            
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Get deck name
            name_elem = soup.find('h2', class_='deck-name')
            if not name_elem:
                name_elem = soup.find('h1')
            name = name_elem.text.strip() if name_elem else 'Unknown'
            
            # Check card count - MUST be exactly 100
            # Find the card count in the deck info table
            cards_td = soup.find('td', string='Cards')
            if not cards_td or not cards_td.find_next_sibling('td'):
                print(f"  Card count not found for {deck_slug}")
                return None
            
            try:
                card_count = int(cards_td.find_next_sibling('td').text.strip())
            except (ValueError, AttributeError):
                print(f"  Could not parse card count for {deck_slug}")
                return None
            
            # Only proceed if exactly 100 cards (Commander requirement)
            if card_count != 100:
                print(f"  ⚠️  Skipping {name}: {card_count} cards (need exactly 100)")
                return None
            
            # Get commander
            commander_section = soup.find('div', class_='boardgroup', attrs={'data-board-id': 'commander'})
            commander = 'Unknown'
            if commander_section:
                card_link = commander_section.find('a', class_='card-link')
                if card_link:
                    commander = card_link.text.strip()
            
            # Parse deck sections
            mainboard = []
            
            # Find all board groups (mainboard, sideboard, maybeboard)
            board_groups = soup.find_all('div', class_='boardgroup')
            
            for board in board_groups:
                board_name_elem = board.find('h3', class_='board-name')
                if not board_name_elem:
                    continue
                
                board_name = board_name_elem.text.strip().lower()
                
                # Only process mainboard (skip sideboard/maybeboard)
                if 'main' not in board_name and 'commander' not in board_name:
                    continue
                
                # Get all card entries
                card_entries = board.find_all('li', class_='member')
                
                for entry in card_entries:
                    qty_elem = entry.find('span', class_='qty')
                    card_link = entry.find('a', class_='card-link')
                    
                    if not card_link:
                        continue
                    
                    quantity = 1
                    if qty_elem:
                        try:
                            quantity = int(qty_elem.text.strip())
                        except:
                            quantity = 1
                    
                    card_name = card_link.text.strip()
                    
                    # Get card type from board-group
                    card_type = 'Other'
                    type_header = entry.find_parent('ul').find_previous_sibling('h4')
                    if type_header:
                        card_type = type_header.text.strip()
                    
                    mainboard.append({
                        'name': card_name,
                        'quantity': quantity,
                        'type': card_type
                    })
            
            # Get description/theme
            description_elem = soup.find('div', class_='deck-description')
            description = description_elem.text.strip()[:200] if description_elem else ''
            
            return {
                'name': name,
                'commander': commander,
                'cards': mainboard,
                'description': description,
                'url': url,
                'slug': deck_slug
            }
            
        except Exception as e:
            print(f"  Error fetching {deck_slug}: {e}")
            return None
    
    def _to_training_format(self, deck):
        """Convert deck to instruction/output training format"""
        try:
            commander = deck['commander']
            name = deck['name']
            
            # Build instruction
            instruction = f"Build a Commander deck with {commander} as the commander."
            
            # Build output (formatted decklist)
            output_lines = [
                f"Commander: {commander}",
                "",
                f"Deck Name: {name}",
                "",
                "Decklist:",
                ""
            ]
            
            # Group cards by type
            cards_by_type = {}
            for card in deck['cards']:
                card_type = card['type']
                if card_type not in cards_by_type:
                    cards_by_type[card_type] = []
                
                quantity = card['quantity']
                card_name = card['name']
                cards_by_type[card_type].append(f"{quantity}x {card_name}")
            
            # Standard type order
            type_order = [
                'Commander', 'Planeswalker', 'Creature', 'Instant', 'Sorcery',
                'Enchantment', 'Artifact', 'Land'
            ]
            
            # Output standard types first
            for card_type in type_order:
                if card_type in cards_by_type:
                    cards = cards_by_type[card_type]
                    total_in_type = sum(int(c.split('x')[0]) for c in cards)
                    output_lines.append(f"{card_type}s ({total_in_type}):")
                    for card_line in sorted(cards):
                        output_lines.append(card_line)
                    output_lines.append("")
            
            # Output any remaining types
            for card_type in sorted(cards_by_type.keys()):
                if card_type not in type_order:
                    cards = cards_by_type[card_type]
                    total_in_type = sum(int(c.split('x')[0]) for c in cards)
                    output_lines.append(f"{card_type}s ({total_in_type}):")
                    for card_line in sorted(cards):
                        output_lines.append(card_line)
                    output_lines.append("")
            
            output = '\n'.join(output_lines)
            
            # Build metadata
            metadata = {
                'type': 'deck_building',
                'commander': commander,
                'source': 'tappedout',
                'url': deck['url']
            }
            
            return {
                'instruction': instruction,
                'output': output,
                'metadata': metadata
            }
            
        except Exception as e:
            print(f"  Error converting to training format: {e}")
            return None
    
    def scrape_precons(self):
        """Scrape official Commander precon decks"""
        print("\n" + "="*60)
        print("TAPPEDOUT PRECON SCRAPER")
        print("="*60)
        
        # List of precon deck slugs from the precon list page
        precon_slugs = [
            'heavenly-inferno-cmd-3',  # 2011
            'counterpunch-cmd-2',
            'devour-for-power-cmd-1',
            'political-puppets-cmd-4',
            # Add more as needed - would need to scrape the list page
        ]
        
        collected = []
        
        for slug in precon_slugs:
            if slug in self.scraped_ids:
                print(f"  Skipping {slug} (already scraped)")
                continue
            
            print(f"  Fetching: {slug}")
            
            deck = self.get_deck_details(slug)
            if not deck:
                continue
            
            # Validate
            total_cards = sum(card['quantity'] for card in deck['cards'])
            if total_cards < 98 or total_cards > 102:
                print(f"  ⚠️  Invalid card count: {total_cards}")
                continue
            
            # Convert to training format
            training_data = self._to_training_format(deck)
            if not training_data:
                continue
            
            # Save
            with open(self.output_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(training_data, ensure_ascii=False) + '\n')
            
            self.scraped_ids.add(slug)
            collected.append(deck)
            
            print(f"  ✓ Saved: {deck['name']}")
            time.sleep(random.uniform(2.0, 4.0))  # Respectful rate limiting
        
        print(f"\n✓ Collected {len(collected)} precon decks")
        return collected
    
    def scrape_community_decks(self, num_decks=500):
        """Scrape community EDH decks from search results"""
        print("\n" + "="*60)
        print("TAPPEDOUT COMMUNITY DECK SCRAPER")
        print("="*60)
        print(f"Target: {num_decks} decks\n")
        
        collected = []
        page = 1
        max_pages = 100
        
        while len(collected) < num_decks and page <= max_pages:
            try:
                # Use search page with EDH format filter
                url = f'{self.base_url}/mtg-decks/search/'
                params = {
                    'q': '',
                    'format': 'edh',
                    'o': '-date_updated',  # Sort by recently updated
                    'p': page
                }
                
                print(f"\n[Page {page}] Fetching search results...")
                response = self.session.get(url, params=params, timeout=15)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find deck links - they appear twice (title and image), so use set to dedupe
                deck_links = soup.find_all('a', href=re.compile(r'/mtg-decks/[^/]+/$'))
                
                # Extract unique slugs from this page
                deck_slugs = set()
                for link in deck_links:
                    deck_url = link['href']
                    if '/mtg-decks/' in deck_url:
                        slug = deck_url.split('/mtg-decks/')[1].rstrip('/')
                        if slug and slug != 'search':  # Skip search page link
                            deck_slugs.add(slug)
                
                if not deck_slugs:
                    print(f"  No more decks found on page {page}")
                    break
                
                print(f"  Found {len(deck_slugs)} unique decks on page {page}")
                
                for deck_slug in deck_slugs:
                    if len(collected) >= num_decks:
                        break
                    
                    if deck_slug in self.scraped_ids:
                        continue
                    
                    print(f"  Fetching: {deck_slug}")
                    time.sleep(random.uniform(2.0, 4.0))  # Rate limiting
                    
                    deck = self.get_deck_details(deck_slug)
                    if not deck:
                        continue
                    
                    # Validate card count
                    total_cards = sum(card['quantity'] for card in deck['cards'])
                    if total_cards < 98 or total_cards > 102:
                        print(f"    ✗ Wrong card count: {total_cards}")
                        continue
                    
                    # Convert and save
                    training_data = self._to_training_format(deck)
                    if not training_data:
                        continue
                    
                    with open(self.output_file, 'a', encoding='utf-8') as f:
                        f.write(json.dumps(training_data, ensure_ascii=False) + '\n')
                    
                    self.scraped_ids.add(deck_slug)
                    collected.append(deck)
                    
                    print(f"  ✓ [{len(collected)}/{num_decks}] {deck['name']}")
                
                page += 1
                time.sleep(random.uniform(1.0, 2.0))  # Pause between pages
                
            except Exception as e:
                print(f"  Error on page {page}: {e}")
                page += 1  # Try next page instead of breaking
                continue
        
        print(f"\n✓ Collected {len(collected)} community decks")
        return collected

if __name__ == '__main__':
    scraper = TappedOutScraper()
    
    # Scrape community decks from search results
    community = scraper.scrape_community_decks(num_decks=1000)
    
    print("\n" + "="*60)
    print("SCRAPING COMPLETE")
    print("="*60)
    print(f"Community decks: {len(community)}")
    print(f"Output: {scraper.output_file}")
