#!/usr/bin/env python3
"""
Scrape decklists from EDHTop16 tournament results
Supports: TopDeck.gg (primary), TappedOut, Moxfield, Archidekt
Focuses on collecting cEDH/high-power competitive decks
"""

import requests
from bs4 import BeautifulSoup
import json
import time
from pathlib import Path
import re
import sqlite3
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)

class EDHTop16TappedOutScraper:
    def __init__(self, output_file='data/training/edhtop16_tournament_decks.jsonl', db_path='prisma/dev.db'):
        self.base_url = 'https://edhtop16.com'
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
        
        print(f"Existing EDHTop16 tournament decks: {len(self.scraped_urls)}")
        
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

    def get_tournaments(self, max_pages=10):
        """Get list of recent tournaments from EDHTop16"""
        tournaments = []
        
        try:
            # Use the tournaments page which lists all recent tournaments
            url = f'{self.base_url}/tournaments'
            print(f"\nFetching tournament list from: {url}")
            
            response = self.session.get(url, timeout=15)
            if response.status_code != 200:
                print(f"  Failed to fetch tournaments (status {response.status_code})")
                return tournaments
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for tournament links - EDHTop16 uses /tournament/ URLs
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                
                # Match tournament URLs
                if href.startswith('/tournament/'):
                    tournament_url = f"{self.base_url}{href}"
                    
                    if tournament_url not in [t['url'] for t in tournaments]:
                        tournament_name = link.text.strip() or href.split('/')[-1]
                        tournaments.append({
                            'url': tournament_url,
                            'name': tournament_name
                        })
            
            print(f"  Found {len(tournaments)} tournaments")
            
        except Exception as e:
            print(f"  Error fetching tournaments: {e}")
        
        return tournaments[:max_pages * 10]  # Limit total

    def scrape_tournament_decks(self, tournament_url: str, tournament_name: str):
        """Scrape all decks from a tournament page by parsing the JSON data."""
        decks = []
        try:
            response = requests.get(tournament_url, headers=self.session.headers)
            response.raise_for_status()
            
            # Extract entries JSON from the page
            # The page embeds tournament data as JSON in a script tag
            text = response.text
            
            # Find the entries array with proper bracket matching
            match = re.search(r'"entries":\[', text)
            if not match:
                logger.warning(f"  No entries found in tournament page")
                return decks
            
            # Find matching closing bracket
            start = match.end() - 1  # Include the opening [
            depth = 0
            end = start
            for i, c in enumerate(text[start:], start):
                if c == '[':
                    depth += 1
                elif c == ']':
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
            
            if depth != 0:
                logger.warning(f"  Failed to find matching bracket for entries array")
                return decks
            
            entries_json = text[start:end]
            
            try:
                entries = json.loads(entries_json)
            except json.JSONDecodeError as e:
                logger.warning(f"  Failed to parse entries JSON: {e}")
                return decks
            
            logger.info(f"  Found {len(entries)} entries in tournament")
            
            # Process each entry
            for entry in entries:
                try:
                    commander_data = entry.get('commander', {})
                    commander_name = commander_data.get('name', '')
                    
                    # Skip "Unknown Commander" entries (no real decklist)
                    if commander_name == "Unknown Commander" or not commander_name:
                        continue
                    
                    # Verify commander exists in our database
                    if commander_name not in self.commanders:
                        logger.debug(f"  Skipping unknown commander: {commander_name}")
                        continue
                    
                    decklist_url = entry.get('decklist', '')
                    if not decklist_url:
                        continue
                    
                    # Determine platform and scrape accordingly
                    if 'topdeck.gg' in decklist_url:
                        deck_data = self.scrape_topdeck_deck(decklist_url, commander_name, tournament_name, entry)
                    elif 'tappedout.net' in decklist_url:
                        deck_data = self.scrape_tappedout_deck(decklist_url, commander_name, tournament_name)
                    elif 'moxfield.com' in decklist_url:
                        deck_data = self.scrape_moxfield_deck(decklist_url, commander_name, tournament_name)
                    elif 'archidekt.com' in decklist_url:
                        deck_data = self.scrape_archidekt_deck(decklist_url, commander_name, tournament_name)
                    else:
                        logger.debug(f"  Unsupported platform: {decklist_url}")
                        continue
                    
                    if deck_data:
                        decks.append(deck_data)
                        logger.info(f"  ✓ Scraped {commander_name} deck")
                
                except Exception as e:
                    logger.error(f"  Error processing entry: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"  Error scraping tournament {tournament_name}: {e}")
        
        return decks

    def scrape_topdeck_deck(self, url, commander_name, tournament_name, entry_data):
        """Scrape a TopDeck.gg decklist (most common in EDHTop16)"""
        try:
            response = self.session.get(url, timeout=15)
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # TopDeck.gg embeds deck data in JSON
            # Look for the deck data in script tags
            cards = []
            
            # Try to find JSON data
            for script in soup.find_all('script'):
                script_text = script.string
                if script_text and 'mainboard' in script_text:
                    # Extract card data
                    try:
                        # Parse the deck structure from TopDeck.gg
                        mainboard_match = re.search(r'"mainboard":\s*\[(.*?)\]', script_text, re.DOTALL)
                        if mainboard_match:
                            cards_json = f'[{mainboard_match.group(1)}]'
                            card_entries = json.loads(cards_json)
                            
                            for card_entry in card_entries:
                                card_name = card_entry.get('name', '')
                                qty = card_entry.get('quantity', 1)
                                if card_name:
                                    cards.append(f"{qty}x {card_name}")
                    except:
                        pass
            
            # If JSON parsing failed, try HTML parsing
            if not cards:
                for card_elem in soup.find_all('div', {'class': 'card-entry'}):
                    qty_elem = card_elem.find('span', {'class': 'quantity'})
                    name_elem = card_elem.find('span', {'class': 'name'})
                    if qty_elem and name_elem:
                        cards.append(f"{qty_elem.text.strip()}x {name_elem.text.strip()}")
            
            if not cards:
                return None
            
            # Get player info
            player = entry_data.get('player', {}).get('name', 'Unknown')
            standing = entry_data.get('standing', '?')
            wins = entry_data.get('wins', 0)
            losses = entry_data.get('losses', 0)
            
            # Build deck text
            deck_text = f"Commander: {commander_name}\n\n"
            deck_text += f"Tournament: {tournament_name}\n"
            deck_text += f"Player: {player} (#{standing})\n"
            deck_text += f"Record: {wins}-{losses}\n"
            deck_text += f"Source: EDHTop16 Tournament\n"
            deck_text += f"URL: {url}\n\n"
            deck_text += "Commanders:\n"
            deck_text += f"1x {commander_name}\n\n"
            deck_text += "Decklist:\n"
            deck_text += "\n".join([c for c in cards if commander_name not in c])
            
            return {
                'url': url,
                'commander': commander_name,
                'tournament': tournament_name,
                'player': player,
                'standing': standing,
                'record': f"{wins}-{losses}",
                'total_cards': len(cards),
                'source': 'edhtop16_topdeck',
                'competitive': True,
                'bracket': 4,  # Tournament decks are typically Bracket 4+
                'instruction': f"Build a competitive tournament deck with {commander_name}",
                'output': deck_text
            }
            
        except Exception as e:
            print(f"      Error scraping TopDeck {url}: {e}")
            return None

    def scrape_tappedout_deck(self, url, tournament_name):
        """Scrape a TappedOut decklist"""
        try:
            response = self.session.get(url, timeout=15)
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Get deck name
            title = soup.find('h1')
            deck_name = title.text.strip() if title else url.split('/')[-2]
            
            # Find commander in the board
            commander = None
            commander_section = soup.find('div', {'class': 'well', 'id': 'commander-tab'})
            
            if commander_section:
                commander_card = commander_section.find('a', {'class': 'card'})
                if commander_card:
                    commander = commander_card.get('data-name') or commander_card.text.strip()
            
            # If no commander section, try finding it in the page
            if not commander:
                # Look for "Commander: X" text
                for text in soup.stripped_strings:
                    if text.startswith('Commander:'):
                        commander = text.replace('Commander:', '').strip()
                        break
            
            # Get all cards from mainboard
            cards = []
            
            # Method 1: Find card list
            card_list = soup.find('div', {'id': 'board-list'})
            if card_list:
                for card_elem in card_list.find_all('a', {'class': 'card'}):
                    card_name = card_elem.get('data-name') or card_elem.text.strip()
                    if card_name and card_name not in cards:
                        cards.append(card_name)
            
            # Method 2: Parse card names from any card link
            if len(cards) < 50:
                cards = []
                for card_link in soup.find_all('a', {'class': 'card'}):
                    card_name = card_link.get('data-name') or card_link.text.strip()
                    if card_name and card_name not in cards:
                        cards.append(card_name)
            
            # Validate deck
            if not commander:
                print(f"      ✗ {deck_name}: No commander found")
                return None
            
            if len(cards) < 50:
                print(f"      ✗ {deck_name}: Only {len(cards)} cards")
                return None
            
            deck_data = {
                'commander': commander,
                'all_cards': cards[:99],  # Limit to 99 mainboard
                'themes': ['cedh', 'competitive', 'tournament'],
                'categories': {},
                'source': 'EDHTop16 TappedOut',
                'tournament': tournament_name,
                'url': url,
                'deck_name': deck_name
            }
            
            print(f"      ✓ {commander}: {len(cards)} cards")
            return deck_data
            
        except Exception as e:
            print(f"      Error scraping {url}: {e}")
            return None

    def scrape_moxfield_deck(self, url, commander_name, tournament_name):
        """Scrape a Moxfield decklist"""
        # Moxfield has an API but for now just return basic info
        print(f"      Moxfield deck (skipping for now): {url}")
        return None

    def scrape_archidekt_deck(self, url, commander_name, tournament_name):
        """Scrape an Archidekt decklist"""
        # Archidekt has an API but for now just return basic info
        print(f"      Archidekt deck (skipping for now): {url}")
        return None

    def run(self, max_tournaments=50):
        """Main scraping loop"""
        print(f"\n{'='*60}")
        print(f"EDHTOP16 TOURNAMENT SCRAPER")
        print(f"{'='*60}")
        print(f"Output: {self.output_file}")
        print(f"Target: {max_tournaments} tournaments")
        print(f"Platforms: TopDeck.gg (primary), TappedOut, Moxfield, Archidekt")
        print(f"Filtering: Only real commanders (skipping 'Unknown Commander')")
        print(f"{'='*60}")
        
        # Get tournament list
        tournaments = self.get_tournaments(max_pages=5)
        
        if not tournaments:
            print("\n⚠️  No tournaments found on /tournaments page")
            return
        
        total_decks = 0
        
        with open(self.output_file, 'a') as f:
            for i, tournament in enumerate(tournaments[:max_tournaments], 1):
                print(f"\n[{i}/{min(len(tournaments), max_tournaments)}]")
                
                decks = self.scrape_tournament_decks(tournament['url'], tournament['name'])
                
                for deck in decks:
                    f.write(json.dumps(deck) + '\n')
                    f.flush()
                    self.scraped_urls.add(deck['url'])
                    total_decks += 1
                
                if decks:
                    print(f"    Scraped {len(decks)} new decks")
                
                time.sleep(3)
        
        print(f"\n{'='*60}")
        print(f"SCRAPING COMPLETE")
        print(f"{'='*60}")
        print(f"Total new decks: {total_decks}")
        print(f"Output: {self.output_file}")
        print(f"{'='*60}\n")


if __name__ == '__main__':
    scraper = EDHTop16TappedOutScraper()
    scraper.run(max_tournaments=50)
