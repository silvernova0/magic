#!/usr/bin/env python3
"""
MTGGoldfish Advanced Search Scraper - Access 100k+ Commander Decks

Uses the advanced search endpoint to scrape massive amounts of Commander decks:
- Tournament decks
- User-submitted decks
- Date range filtering (search maxes at 10k decks per range)
- Pagination support (32 decks per page, 313 pages max per search)

IMPORTANT: MTGGoldfish limits searches to 10k decks (~313 pages).
Use date range batching to scrape more:
- 2-month batches yield ~10k decks each
- Example: 09/13/2025-11/06/2025 = 10k decks
- Example: 07/13/2025-09/12/2025 = 10k decks

Usage:
    # Single date range (up to 10k decks)
    python3 scripts/scrape-mtggoldfish-advanced.py --date-start "09/13/2025" --date-end "11/06/2025"
    
    # Multiple date ranges (auto-batch)
    python3 scripts/scrape-mtggoldfish-advanced.py --date-start "01/01/2024" --date-end "11/06/2025" --batch-months 2
    
    # Resume from specific page
    python3 scripts/scrape-mtggoldfish-advanced.py --date-start "09/13/2025" --date-end "11/06/2025" --start-page 100
"""

import requests
import re
import time
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import random
import argparse

class MTGGoldfishAdvancedScraper:
    def __init__(self, output_file='data/training/mtggoldfish_advanced_decks.jsonl', db_path='prisma/dev.db'):
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
    
    def is_commander(self, card_name: str) -> tuple:
        """Check if a card is a legendary creature/planeswalker (potential commander)
        
        Returns: (is_legendary, color_identity)
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT typeLine, colorIdentity FROM Card 
                WHERE name = ? COLLATE NOCASE 
                LIMIT 1
            """, (card_name,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                type_line = row[0]
                color_identity_str = row[1]
                
                # Parse color identity
                try:
                    color_identity = json.loads(color_identity_str) if color_identity_str else []
                except:
                    color_identity = []
                
                is_legendary = 'Legendary' in type_line and ('Creature' in type_line or 'Planeswalker' in type_line)
                return (is_legendary, set(color_identity))
            return (False, set())
        except:
            return (False, set())
    
    def get_deck_ids_from_page(self, page: int, date_range: str) -> list:
        """Get deck IDs from a search results page"""
        params = {
            'deck_search[name]': '',
            'deck_search[format]': 'commander',
            'deck_search[types][]': ['', 'tournament', 'user'],
            'deck_search[player]': '',
            'deck_search[date_range]': date_range,
            'page': page
        }
        
        try:
            response = self.session.get(self.search_url, params=params, timeout=30)
            response.raise_for_status()
            
            # Extract deck IDs (32 per page)
            deck_ids = re.findall(r'href="/deck/(\d+)"', response.text)
            return list(set(deck_ids))  # Remove duplicates
            
        except Exception as e:
            print(f"Error fetching page {page}: {e}")
            return []
    
    def download_deck(self, deck_id: str) -> str:
        """Download deck in plain text format
        
        Returns: deck_text (commander will be identified from the decklist)
        """
        url = f'{self.base_url}/deck/download/{deck_id}'
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"  Error downloading deck {deck_id}: {e}")
            return None
    
    def parse_deck(self, deck_text: str, deck_id: str, commander_name: str = None) -> dict:
        """Parse deck text into structured format
        
        Args:
            deck_text: Plain text decklist
            deck_id: Deck ID
            commander_name: Commander name from deck page (not used, kept for compatibility)
        """
        lines = [l.strip() for l in deck_text.strip().split('\n') if l.strip()]
        
        if len(lines) < 90 or len(lines) > 110:
            return None
        
        cards = []
        legendary_candidates = []  # Store (card_name, color_identity)
        
        for line in lines:
            # Remove set codes and foil markers: "1 Card Name [SET] (F)" -> "1 Card Name"
            line = re.sub(r'\s*\[.*?\].*$', '', line)
            line = re.sub(r'\s*\(F\).*$', '', line)
            
            # Parse quantity and name
            match = re.match(r'^(\d+)\s+(.+)$', line.strip())
            if match:
                quantity = int(match.group(1))
                name = match.group(2).strip()
                cards.append({'name': name, 'quantity': quantity})
                
                # Check if this card is a legendary creature/planeswalker
                is_legendary, color_identity = self.is_commander(name)
                if is_legendary:
                    legendary_candidates.append((name, color_identity))
        
        # Find commander by checking which legendary matches the deck's color identity
        commander = None
        if legendary_candidates:
            # Calculate deck color identity (union of all cards' colors)
            deck_colors = set()
            for card in cards:
                _, card_colors = self.is_commander(card['name'])
                deck_colors.update(card_colors)
            
            # Find legendary that matches or is subset of deck colors
            for legend_name, legend_colors in legendary_candidates:
                if legend_colors.issubset(deck_colors) or legend_colors == deck_colors:
                    commander = legend_name
                    break
            
            # If no perfect match, use first legendary as fallback
            if not commander:
                commander = legendary_candidates[0][0]
        
        # If no legendary found at all, use first card as fallback
        if not commander and cards:
            commander = cards[0]['name']
        
        total_cards = sum(c['quantity'] for c in cards)
        
        # Validate card count (99-101 to allow for commander variations)
        if total_cards < 99 or total_cards > 101:
            return None
        
        return {
            'deck_id': deck_id,
            'commander': commander,
            'cards': cards,
            'total_cards': total_cards
        }
    
    def to_training_format(self, deck: dict) -> dict:
        """Convert deck to training format"""
        # Build decklist text
        decklist = f"Commander: {deck['commander']}\n\nDecklist:\n\nCommanders:\n1x {deck['commander']}\n\n"
        
        # Group cards by type (simplified)
        other_cards = [c for c in deck['cards'][1:]]  # Skip commander
        
        for card in other_cards:
            decklist += f"{card['quantity']}x {card['name']}\n"
        
        instruction = f"Build a Commander deck with {deck['commander']}."
        
        return {
            'deck_id': deck['deck_id'],
            'instruction': instruction,
            'output': decklist.strip()
        }
    
    def scrape_date_range(self, date_range: str, max_decks=10000, start_page=1):
        """
        Scrape decks for a specific date range
        
        Args:
            date_range: Date range string like "09/13/2025 - 11/06/2025"
            max_decks: Maximum decks for this range (MTGGoldfish limits to ~10k per search)
            start_page: Page to start from
        
        Returns:
            Number of new decks collected
        """
        print(f"\n{'='*60}")
        print(f"DATE RANGE: {date_range}")
        print(f"{'='*60}")
        print(f"Target: {max_decks} decks (MTGGoldfish limit: ~10,000 per search)")
        print(f"Starting from page: {start_page}")
        print(f"{'='*60}\n")
        
        collected_this_range = 0
        current_page = start_page
        max_pages = 313  # MTGGoldfish pagination limit
        
        while collected_this_range < max_decks and current_page <= max_pages:
            print(f"\n[Page {current_page}] Fetching deck IDs...")
            deck_ids = self.get_deck_ids_from_page(current_page, date_range)
            
            if not deck_ids:
                print(f"  No decks found on page {current_page}, ending this range")
                break
            
            print(f"  Found {len(deck_ids)} deck IDs on this page")
            
            # Filter out already scraped
            new_ids = [did for did in deck_ids if did not in self.scraped_ids]
            print(f"  {len(new_ids)} new decks to scrape")
            
            if not new_ids:
                current_page += 1
                time.sleep(random.uniform(1.0, 2.0))
                continue
            
            # Process each deck
            for deck_id in new_ids:
                if collected_this_range >= max_decks:
                    break
                
                # Download deck
                deck_text = self.download_deck(deck_id)
                if not deck_text:
                    continue
                
                # Parse deck (commander identified from legendary cards in list)
                deck = self.parse_deck(deck_text, deck_id)
                if not deck:
                    print(f"  ✗ Deck {deck_id} - invalid format")
                    continue
                
                # Convert to training format
                training_example = self.to_training_format(deck)
                
                # Save incrementally
                with open(self.output_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(training_example, ensure_ascii=False) + '\n')
                
                self.scraped_ids.add(deck_id)
                collected_this_range += 1
                total = len(self.scraped_ids)
                
                print(f"  ✓ [{total}] {deck['commander']} ({deck['total_cards']} cards)")
                
                # Rate limiting
                time.sleep(random.uniform(1.5, 3.0))
            
            current_page += 1
            
            # Progress update every 10 pages
            if current_page % 10 == 0:
                print(f"\n{'='*60}")
                print(f"Progress - Page {current_page}")
                print(f"This range: {collected_this_range}")
                print(f"Total collected: {len(self.scraped_ids)}")
                print(f"{'='*60}\n")
            
            # Longer delay between pages
            time.sleep(random.uniform(2.0, 4.0))
        
        print(f"\n{'='*60}")
        print(f"DATE RANGE COMPLETE: {date_range}")
        print(f"Collected: {collected_this_range} decks")
        print(f"{'='*60}\n")
        
        return collected_this_range
    
    def generate_date_ranges(self, start_date: str, end_date: str, months: int = 2):
        """
        Generate date range batches for scraping
        
        Args:
            start_date: Start date in MM/DD/YYYY format
            end_date: End date in MM/DD/YYYY format
            months: Number of months per batch (2 months = ~10k decks)
        
        Returns:
            List of date range strings
        """
        start = datetime.strptime(start_date, '%m/%d/%Y')
        end = datetime.strptime(end_date, '%m/%d/%Y')
        
        ranges = []
        current = start
        
        while current < end:
            range_end = min(current + relativedelta(months=months), end)
            range_str = f"{current.strftime('%m/%d/%Y')} - {range_end.strftime('%m/%d/%Y')}"
            ranges.append(range_str)
            current = range_end + timedelta(days=1)
        
        return ranges
    
    def scrape_advanced_search(self, date_ranges: list, max_decks_per_range=10000, start_page=1):
        """
        Scrape decks across multiple date ranges
        
        Args:
            date_ranges: List of date range strings
            max_decks_per_range: Max decks per range (default 10k, MTGGoldfish limit)
            start_page: Page to start from for first range
        """
        print(f"\n{'='*60}")
        print(f"MTGGOLDFISH ADVANCED SEARCH SCRAPER")
        print(f"{'='*60}")
        print(f"Loaded {len(self.scraped_ids)} existing deck IDs")
        print(f"Date ranges to scrape: {len(date_ranges)}")
        print(f"Max decks per range: {max_decks_per_range}")
        print(f"Output: {self.output_file}")
        print(f"{'='*60}\n")
        
        for i, date_range in enumerate(date_ranges, 1):
            print(f"\n{'#'*60}")
            print(f"RANGE {i}/{len(date_ranges)}: {date_range}")
            print(f"{'#'*60}")
            
            collected = self.scrape_date_range(
                date_range=date_range,
                max_decks=max_decks_per_range,
                start_page=start_page if i == 1 else 1  # Only use start_page for first range
            )
            
            print(f"\nRange {i} complete: {collected} decks collected")
            print(f"Total so far: {len(self.scraped_ids)} decks")
            
            # Longer delay between date ranges
            if i < len(date_ranges):
                print(f"\n⏳ Waiting 10 seconds before next date range...")
                time.sleep(10)
        
        print(f"\n{'='*60}")
        print(f"SCRAPING COMPLETE")
        print(f"{'='*60}")
        print(f"Total decks collected: {len(self.scraped_ids)}")
        print(f"Output saved to: {self.output_file}")
        print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(
        description='Scrape MTGGoldfish Commander decks using advanced search with date range batching',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single 2-month range (~10k decks)
  python3 scripts/scrape-mtggoldfish-advanced.py \\
    --date-start "09/13/2025" --date-end "11/06/2025"
  
  # Auto-batch entire year into 2-month chunks (~60k decks)
  python3 scripts/scrape-mtggoldfish-advanced.py \\
    --date-start "01/01/2025" --date-end "11/06/2025" --batch-months 2
  
  # Custom batch size and limits
  python3 scripts/scrape-mtggoldfish-advanced.py \\
    --date-start "01/01/2024" --date-end "11/06/2025" \\
    --batch-months 2 --max-per-range 5000
  
  # Resume from specific page in first range
  python3 scripts/scrape-mtggoldfish-advanced.py \\
    --date-start "09/13/2025" --date-end "11/06/2025" --start-page 100

Date Range Strategy:
  - Each 2-month period yields ~10,000 decks (MTGGoldfish search limit)
  - Use --batch-months 2 to auto-split long ranges
  - 2024-2025 (22 months) = ~11 batches = ~110,000 decks!
        """
    )
    
    parser.add_argument('--date-start', type=str, required=True,
                       help='Start date in MM/DD/YYYY format (e.g., "01/01/2024")')
    parser.add_argument('--date-end', type=str, required=True,
                       help='End date in MM/DD/YYYY format (e.g., "11/06/2025")')
    parser.add_argument('--batch-months', type=int, default=None,
                       help='Auto-batch into N-month chunks (recommended: 2 months = ~10k decks)')
    parser.add_argument('--max-per-range', type=int, default=10000,
                       help='Maximum decks per date range (default: 10000, MTGGoldfish limit)')
    parser.add_argument('--start-page', type=int, default=1,
                       help='Page to start from for first range (default: 1)')
    parser.add_argument('--output', type=str, default='data/training/mtggoldfish_advanced_decks.jsonl',
                       help='Output file path')
    
    args = parser.parse_args()
    
    scraper = MTGGoldfishAdvancedScraper(output_file=args.output)
    
    # Generate date ranges
    if args.batch_months:
        date_ranges = scraper.generate_date_ranges(
            args.date_start,
            args.date_end,
            args.batch_months
        )
        print(f"Generated {len(date_ranges)} date range batches:")
        for i, dr in enumerate(date_ranges, 1):
            print(f"  {i}. {dr}")
        print()
    else:
        # Single date range
        date_ranges = [f"{args.date_start} - {args.date_end}"]
    
    scraper.scrape_advanced_search(
        date_ranges=date_ranges,
        max_decks_per_range=args.max_per_range,
        start_page=args.start_page
    )


if __name__ == '__main__':
    main()
