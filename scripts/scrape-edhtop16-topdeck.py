#!/usr/bin/env python3
"""
Scrape decklists from EDHTop16 tournament results
Focuses on TopDeck.gg platform (primary platform for EDHTop16)
Collects cEDH/high-power competitive decks
"""

import requests
from bs4 import BeautifulSoup
import json
import time
from pathlib import Path
import re
import sqlite3
import logging
from urllib.parse import urljoin

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)

class EDHTop16TopDeckScraper:
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
        
        logger.info(f"Existing EDHTop16 tournament decks: {len(self.scraped_urls)}")
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # Load commanders from database
        self.commanders = self.load_commanders()
        logger.info(f"Loaded {len(self.commanders)} legal commanders from database\n")

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
            logger.error(f"Warning: Could not load commanders from database: {e}")
        return commanders

    def get_tournaments(self, max_tournaments=50):
        """Get list of recent tournaments from EDHTop16"""
        tournaments = []
        
        try:
            url = f'{self.base_url}/tournaments'
            logger.info(f"Fetching tournament list from: {url}")
            
            response = self.session.get(url, timeout=15)
            if response.status_code != 200:
                logger.error(f"Failed to fetch tournaments (status {response.status_code})")
                return tournaments
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find tournament links
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                
                # Match tournament URLs like /tournament/commander-budget-16
                if href.startswith('/tournament/'):
                    tournament_url = f"{self.base_url}{href}"
                    
                    if tournament_url not in [t['url'] for t in tournaments]:
                        tournament_name = link.text.strip() or href.split('/')[-1]
                        tournaments.append({
                            'url': tournament_url,
                            'name': tournament_name
                        })
            
            logger.info(f"Found {len(tournaments)} total tournaments\n")
            
        except Exception as e:
            logger.error(f"Error fetching tournaments: {e}")
        
        return tournaments[:max_tournaments]

    def scrape_tournament_decks(self, tournament_url: str, tournament_name: str):
        """Scrape all decks from a tournament by extracting JSON entries"""
        decks = []
        try:
            response = requests.get(tournament_url, headers=self.session.headers, timeout=15)
            response.raise_for_status()
            
            # Extract entries JSON from the page
            text = response.text
            
            # Find the entries array
            match = re.search(r'"entries":\s*\[', text)
            if not match:
                logger.warning(f"  No entries found in tournament")
                return decks
            
            # Find matching closing bracket
            start = match.end() - 1
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
                logger.warning(f"  Failed to parse entries array")
                return decks
            
            entries_json = text[start:end]
            entries = json.loads(entries_json)
            
            logger.info(f"  Processing {len(entries)} entries...")
            
            valid_entries = 0
            skipped_unknown = 0
            skipped_invalid = 0
            scraped_count = 0
            
            # Process each entry
            for entry in entries:
                try:
                    commander_data = entry.get('commander', {})
                    commander_name = commander_data.get('name', '')
                    
                    # Skip "Unknown Commander" (no real decklist)
                    if commander_name == "Unknown Commander" or not commander_name:
                        skipped_unknown += 1
                        continue
                    
                    # Verify commander exists in database
                    if commander_name not in self.commanders:
                        skipped_invalid += 1
                        logger.debug(f"  Skipping unrecognized commander: {commander_name}")
                        continue
                    
                    valid_entries += 1
                    
                    decklist_url = entry.get('decklist', '')
                    if not decklist_url:
                        continue
                    
                    # Skip if already scraped
                    if decklist_url in self.scraped_urls:
                        logger.debug(f"  Already scraped: {commander_name}")
                        continue
                    
                    # Scrape based on platform
                    deck_data = None
                    if 'topdeck.gg' in decklist_url:
                        deck_data = self.scrape_topdeck_deck(decklist_url, commander_name, tournament_name, entry)
                    elif 'tappedout.net' in decklist_url:
                        deck_data = self.scrape_tappedout_deck(decklist_url, commander_name, tournament_name, entry)
                    elif 'moxfield.com' in decklist_url:
                        deck_data = self.scrape_moxfield_deck(decklist_url, commander_name, tournament_name, entry)
                    elif 'archidekt.com' in decklist_url:
                        deck_data = self.scrape_archidekt_deck(decklist_url, commander_name, tournament_name, entry)
                    else:
                        logger.debug(f"  Unsupported platform: {decklist_url}")
                        continue
                    
                    if deck_data:
                        decks.append(deck_data)
                        scraped_count += 1
                        logger.info(f"  ✓ {commander_name}")
                
                except Exception as e:
                    logger.error(f"  Error processing entry: {e}")
                    continue
            
            logger.info(f"  Results: {scraped_count} scraped, {skipped_unknown} unknown commander, {skipped_invalid} invalid commander\n")
        
        except Exception as e:
            logger.error(f"  Error scraping tournament {tournament_name}: {e}\n")
        
        return decks

    def scrape_topdeck_deck(self, url, commander_name, tournament_name, entry_data):
        """Scrape a TopDeck.gg decklist using HTML parsing"""
        try:
            if url in self.scraped_urls:
                return None
            
            response = self.session.get(url, timeout=15)
            if response.status_code != 200:
                logger.debug(f"  Failed to fetch {url} (status {response.status_code})")
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # TopDeck.gg uses <a class="game-card" data-name="CARDNAME"> elements
            cards = []
            
            # Find all card elements
            card_elements = soup.find_all('a', class_='game-card')
            
            for card_elem in card_elements:
                card_name = card_elem.get('data-name', '').strip()
                if card_name:
                    cards.append(card_name)
            
            if not cards:
                logger.debug(f"  No cards found in {url}")
                return None
            
            # Get player info
            player = entry_data.get('player', {}).get('name', 'Unknown')
            standing = entry_data.get('standing', '?')
            wins = entry_data.get('wins', 0)
            losses = entry_data.get('losses', 0)
            
            # Format as standard decklist (1x each card)
            all_cards = [commander_name] + [c for c in cards if c != commander_name]
            
            return {
                'url': url,
                'commander': commander_name,
                'name': f"{commander_name} - {player} - {tournament_name}",
                'source': 'EDHTop16 Tournament',
                'tournament': tournament_name,
                'player': player,
                'standing': standing,
                'record': f"{wins}-{losses}",
                'all_cards': all_cards,
                'total_cards': len(all_cards)
            }
        
        except Exception as e:
            logger.error(f"  Error scraping TopDeck deck {url}: {e}")
            return None

    def scrape_tappedout_deck(self, url, commander_name, tournament_name, entry_data):
        """Scrape a TappedOut decklist"""
        try:
            if url in self.scraped_urls:
                return None
            
            response = self.session.get(url, timeout=15)
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            cards = []
            
            # TappedOut uses board-container divs
            board = soup.find('div', class_='board-container')
            if board:
                for card_elem in board.find_all('a', class_='card-link'):
                    qty_elem = card_elem.find_previous('span', class_='qty')
                    card_name = card_elem.text.strip()
                    if card_name:
                        cards.append(card_name)
            
            if not cards:
                return None
            
            player = entry_data.get('player', {}).get('name', 'Unknown')
            standing = entry_data.get('standing', '?')
            wins = entry_data.get('wins', 0)
            losses = entry_data.get('losses', 0)
            
            all_cards = [commander_name] + [c for c in cards if c != commander_name]
            
            return {
                'url': url,
                'commander': commander_name,
                'name': f"{commander_name} - {player} - {tournament_name}",
                'source': 'EDHTop16 Tournament',
                'tournament': tournament_name,
                'player': player,
                'standing': standing,
                'record': f"{wins}-{losses}",
                'all_cards': all_cards,
                'total_cards': len(all_cards)
            }
        
        except Exception as e:
            logger.error(f"  Error scraping TappedOut deck {url}: {e}")
            return None

    def scrape_moxfield_deck(self, url, commander_name, tournament_name, entry_data):
        """Scrape a Moxfield decklist"""
        try:
            if url in self.scraped_urls:
                return None
            
            # Extract deck ID from URL
            deck_id = url.split('/')[-1]
            api_url = f"https://api2.moxfield.com/v3/decks/all/{deck_id}"
            
            response = self.session.get(api_url, timeout=15)
            if response.status_code != 200:
                return None
            
            data = response.json()
            cards = []
            
            # Get mainboard cards
            mainboard = data.get('boards', {}).get('mainboard', {}).get('cards', {})
            for card_data in mainboard.values():
                card_name = card_data.get('card', {}).get('name', '')
                if card_name:
                    cards.append(card_name)
            
            if not cards:
                return None
            
            player = entry_data.get('player', {}).get('name', 'Unknown')
            standing = entry_data.get('standing', '?')
            wins = entry_data.get('wins', 0)
            losses = entry_data.get('losses', 0)
            
            all_cards = [commander_name] + [c for c in cards if c != commander_name]
            
            return {
                'url': url,
                'commander': commander_name,
                'name': f"{commander_name} - {player} - {tournament_name}",
                'source': 'EDHTop16 Tournament',
                'tournament': tournament_name,
                'player': player,
                'standing': standing,
                'record': f"{wins}-{losses}",
                'all_cards': all_cards,
                'total_cards': len(all_cards)
            }
        
        except Exception as e:
            logger.error(f"  Error scraping Moxfield deck {url}: {e}")
            return None

    def scrape_archidekt_deck(self, url, commander_name, tournament_name, entry_data):
        """Scrape an Archidekt decklist"""
        try:
            if url in self.scraped_urls:
                return None
            
            # Extract deck ID from URL
            match = re.search(r'/decks/(\d+)', url)
            if not match:
                return None
            
            deck_id = match.group(1)
            api_url = f"https://archidekt.com/api/decks/{deck_id}/small/"
            
            response = self.session.get(api_url, timeout=15)
            if response.status_code != 200:
                return None
            
            data = response.json()
            cards = []
            
            # Get cards
            for card_data in data.get('cards', []):
                card_name = card_data.get('card', {}).get('oracleCard', {}).get('name', '')
                if card_name:
                    cards.append(card_name)
            
            if not cards:
                return None
            
            player = entry_data.get('player', {}).get('name', 'Unknown')
            standing = entry_data.get('standing', '?')
            wins = entry_data.get('wins', 0)
            losses = entry_data.get('losses', 0)
            
            all_cards = [commander_name] + [c for c in cards if c != commander_name]
            
            return {
                'url': url,
                'commander': commander_name,
                'name': f"{commander_name} - {player} - {tournament_name}",
                'source': 'EDHTop16 Tournament',
                'tournament': tournament_name,
                'player': player,
                'standing': standing,
                'record': f"{wins}-{losses}",
                'all_cards': all_cards,
                'total_cards': len(all_cards)
            }
        
        except Exception as e:
            logger.error(f"  Error scraping Archidekt deck {url}: {e}")
            return None

    def save_deck(self, deck):
        """Save a single deck to the output file"""
        try:
            with open(self.output_file, 'a') as f:
                f.write(json.dumps(deck) + '\n')
            self.scraped_urls.add(deck['url'])
        except Exception as e:
            logger.error(f"Error saving deck: {e}")

    def run(self, max_tournaments=50):
        """Main scraping loop"""
        logger.info("=== EDHTop16 Tournament Deck Scraper ===\n")
        
        # Get tournaments
        tournaments = self.get_tournaments(max_tournaments)
        
        if not tournaments:
            logger.error("No tournaments found!")
            return
        
        total_decks = 0
        
        # Scrape each tournament
        for i, tournament in enumerate(tournaments, 1):
            logger.info(f"[{i}/{len(tournaments)}] {tournament['name']}")
            
            decks = self.scrape_tournament_decks(tournament['url'], tournament['name'])
            
            # Save decks
            for deck in decks:
                self.save_deck(deck)
                total_decks += 1
            
            # Rate limiting
            time.sleep(2)
        
        logger.info(f"\n=== Scraping Complete ===")
        logger.info(f"Total decks collected: {total_decks}")
        logger.info(f"Output file: {self.output_file}")

if __name__ == '__main__':
    scraper = EDHTop16TopDeckScraper()
    scraper.run(max_tournaments=50)
