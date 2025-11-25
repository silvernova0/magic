#!/usr/bin/env python3
"""
MTGGoldfish Commander-Specific Scraper

Searches MTGGoldfish by specific commander names, so we KNOW who the commander is!
Uses the advanced search with commander filter.

Strategy:
- Get list of all legendary creatures/planeswalkers from database
- Search MTGGoldfish for decks with each commander
- Collect 10-20 decks per commander
- Last 6 months date range to get recent decks

Usage:
    python3 scripts/scrape-mtggoldfish-by-commander.py --decks-per-commander 10
"""

import requests
import re
import time
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from urllib.parse import urlencode, quote_plus
import random
import argparse

class MTGGoldfishCommanderScraper:
    def __init__(self, output_file='data/training/mtggoldfish_by_commander_decks.jsonl', db_path='prisma/dev.db'):
        self.base_url = 'https://www.mtggoldfish.com'
        self.search_url = f'{self.base_url}/deck_searches/create'
        self.output_file = Path(output_file)
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        
        # Load existing deck IDs to avoid duplicates
        self.scraped_ids = set()
        if self.output_file.exists():
            with open(self.output_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        data = json.loads(line.strip())
                        if 'deck_id' in data:
                            self.scraped_ids.add(data['deck_id'])
                    except:
                        continue
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
        })
        
        # Calculate date range (last 6 months)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=180)
        self.date_range = f"{start_date.strftime('%m/%d/%Y')} - {end_date.strftime('%m/%d/%Y')}"
    
    def get_commander_list(self) -> list:
        """Get all commanders from database (creatures, vehicles, planeswalkers with commander text)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get all legal commanders using the isCommander field
            # This includes: Legendary Creatures, Legendary Vehicles, and cards with "can be your commander"
            cursor.execute("""
                SELECT DISTINCT name FROM Card 
                WHERE isCommander = 1
                AND name NOT LIKE 'A-%'
                AND edhrecRank IS NOT NULL
                ORDER BY edhrecRank
            """)
            
            commanders = [row[0] for row in cursor.fetchall()]
            conn.close()
            
            return commanders
        except Exception as e:
            print(f"Error getting commander list: {e}")
            return []
    
    def search_by_commander(self, commander_name: str, page: int = 1) -> list:
        """Search for decks with specific commander"""
        # Build search parameters - MUST include format=commander
        params = {
            'deck_search[name]': '',
            'deck_search[format]': 'commander',  # Critical: filter to Commander format only
            'deck_search[types][]': ['', 'tournament', 'user'],
            'deck_search[player]': '',
            'deck_search[date_range]': self.date_range,
            'deck_search[deck_search_card_filters_attributes][0][card]': commander_name,
            'deck_search[deck_search_card_filters_attributes][0][quantity]': '1',
            'deck_search[deck_search_card_filters_attributes][0][type]': 'commander',
            'page': page
        }
        
        try:
            response = self.session.get(self.search_url, params=params, timeout=30)
            response.raise_for_status()
            
            # Extract deck IDs (32 per page)
            deck_ids = re.findall(r'href="/deck/(\d+)"', response.text)
            return list(set(deck_ids))  # Remove duplicates
            
        except Exception as e:
            print(f"  Error searching for {commander_name}: {e}")
            return []
    
    def download_deck(self, deck_id: str) -> str:
        """Download deck in plain text format"""
        url = f'{self.base_url}/deck/download/{deck_id}'
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.text
        except Exception as e:
            return None
    
    def parse_deck(self, deck_text: str, deck_id: str, commander_name: str) -> dict:
        """Parse deck text into structured format"""
        lines = [l.strip() for l in deck_text.strip().split('\n') if l.strip()]
        
        cards = []
        total_cards = 0
        
        for line in lines:
            # Remove set codes and foil markers
            line = re.sub(r'\s*\[.*?\].*$', '', line)
            line = re.sub(r'\s*\(F\).*$', '', line)
            
            # Parse quantity and name
            match = re.match(r'^(\d+)\s+(.+)$', line.strip())
            if match:
                quantity = int(match.group(1))
                name = match.group(2).strip()
                cards.append({'name': name, 'quantity': quantity})
                total_cards += quantity
        
        # Validate card count (99-101 to allow for commander variations)
        if total_cards < 99 or total_cards > 101:
            return None
        
        return {
            'deck_id': deck_id,
            'commander': commander_name,  # We know this from the search!
            'cards': cards,
            'total_cards': total_cards
        }
    
    def to_training_format(self, deck: dict) -> dict:
        """Convert deck to training format"""
        decklist = f"Commander: {deck['commander']}\n\nDecklist:\n\nCommanders:\n1x {deck['commander']}\n\n"
        
        # Add other cards
        other_cards = [c for c in deck['cards']]
        for card in other_cards:
            decklist += f"{card['quantity']}x {card['name']}\n"
        
        instruction = f"Build a Commander deck with {deck['commander']}."
        
        return {
            'deck_id': deck['deck_id'],
            'instruction': instruction,
            'output': decklist.strip()
        }
    
    def scrape_commanders(self, decks_per_commander=10, max_commanders=None):
        """
        Scrape decks for each commander
        
        Args:
            decks_per_commander: Target decks per commander (default 10)
            max_commanders: Maximum number of commanders to process (None = all)
        """
        print(f"\n{'='*60}")
        print(f"MTGGOLDFISH COMMANDER-SPECIFIC SCRAPER")
        print(f"{'='*60}")
        print(f"Date range: {self.date_range} (last 6 months)")
        print(f"Target: {decks_per_commander} decks per commander")
        print(f"Output: {self.output_file}")
        print(f"{'='*60}\n")
        
        # Get commander list
        print("Loading commander list from database...")
        commanders = self.get_commander_list()
        
        if max_commanders:
            commanders = commanders[:max_commanders]
        
        print(f"Found {len(commanders)} potential commanders\n")
        
        total_collected = 0
        commanders_with_decks = 0
        commanders_processed = 0
        
        for i, commander in enumerate(commanders, 1):
            commanders_processed += 1
            print(f"\n[{i}/{len(commanders)}] {commander}")
            
            # Search for decks with this commander
            deck_ids = self.search_by_commander(commander, page=1)
            
            if not deck_ids:
                print(f"  No decks found")
                continue
            
            print(f"  Found {len(deck_ids)} deck IDs")
            
            # Filter out already scraped
            new_ids = [did for did in deck_ids if did not in self.scraped_ids]
            
            if not new_ids:
                print(f"  All decks already scraped")
                continue
            
            # Limit to target per commander
            new_ids = new_ids[:decks_per_commander]
            print(f"  Scraping {len(new_ids)} new decks")
            
            decks_collected_for_commander = 0
            
            for deck_id in new_ids:
                # Download deck
                deck_text = self.download_deck(deck_id)
                if not deck_text:
                    continue
                
                # Parse deck with known commander
                deck = self.parse_deck(deck_text, deck_id, commander)
                if not deck:
                    print(f"    ✗ Deck {deck_id} - invalid format")
                    continue
                
                # Convert to training format
                training_example = self.to_training_format(deck)
                
                # Save incrementally
                with open(self.output_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(training_example, ensure_ascii=False) + '\n')
                
                self.scraped_ids.add(deck_id)
                total_collected += 1
                decks_collected_for_commander += 1
                
                print(f"    ✓ [{total_collected}] {deck['commander']} ({deck['total_cards']} cards)")
                
                # Rate limiting
                time.sleep(random.uniform(1.5, 3.0))
            
            if decks_collected_for_commander > 0:
                commanders_with_decks += 1
            
            # Progress update every 50 commanders
            if i % 50 == 0:
                print(f"\n{'='*60}")
                print(f"Progress Update - {i}/{len(commanders)} commanders")
                print(f"Total decks: {total_collected}")
                print(f"Commanders with decks: {commanders_with_decks}")
                print(f"{'='*60}\n")
            
            # Longer delay between commanders
            time.sleep(random.uniform(2.0, 4.0))
        
        print(f"\n{'='*60}")
        print(f"SCRAPING COMPLETE")
        print(f"{'='*60}")
        print(f"Commanders processed: {commanders_processed}")
        print(f"Commanders with decks: {commanders_with_decks}")
        print(f"Total decks collected: {total_collected}")
        print(f"Output: {self.output_file}")
        print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(
        description='Scrape MTGGoldfish decks by specific commanders',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scrape 10 decks per commander (all commanders)
  python3 scripts/scrape-mtggoldfish-by-commander.py --decks-per-commander 10
  
  # Scrape 20 decks per commander
  python3 scripts/scrape-mtggoldfish-by-commander.py --decks-per-commander 20
  
  # Test with first 100 commanders only
  python3 scripts/scrape-mtggoldfish-by-commander.py --decks-per-commander 10 --max-commanders 100
  
  # Run in background
  nohup python3 scripts/scrape-mtggoldfish-by-commander.py --decks-per-commander 10 > mtggoldfish_commander.log 2>&1 &

Notes:
  - Searches last 6 months of decks
  - Automatically identifies commander from search filter
  - ~3,000+ legendary creatures/planeswalkers in database
  - 10 decks/commander × 3,000 = ~30,000 decks potential!
        """
    )
    
    parser.add_argument('--decks-per-commander', type=int, default=10,
                       help='Target decks per commander (default: 10)')
    parser.add_argument('--max-commanders', type=int, default=None,
                       help='Maximum commanders to process (default: all)')
    parser.add_argument('--output', type=str, default='data/training/mtggoldfish_by_commander_decks.jsonl',
                       help='Output file path')
    
    args = parser.parse_args()
    
    scraper = MTGGoldfishCommanderScraper(output_file=args.output)
    scraper.scrape_commanders(
        decks_per_commander=args.decks_per_commander,
        max_commanders=args.max_commanders
    )


if __name__ == '__main__':
    main()
