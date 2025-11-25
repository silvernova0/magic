#!/usr/bin/env python3
"""
Scrape MTGGoldfish decks specifically for legendary vehicle commanders
These were missed by the original scraper that only checked for legendary creatures
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the existing MTGGoldfish scraper class
import sqlite3
import requests
from bs4 import BeautifulSoup
import json
import time
from pathlib import Path

class VehicleCommanderScraper:
    def __init__(self, output_file='data/training/vehicle_commander_decks.jsonl', decks_per_commander=25):
        self.output_file = Path(output_file)
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        self.decks_per_commander = decks_per_commander
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # Load existing deck IDs to avoid duplicates
        self.scraped_ids = set()
        if self.output_file.exists():
            with open(self.output_file, 'r') as f:
                for line in f:
                    try:
                        deck = json.loads(line)
                        if 'deck_id' in deck:
                            self.scraped_ids.add(deck['deck_id'])
                    except:
                        pass
        
        print(f"Existing vehicle commander decks: {len(self.scraped_ids)}")

    def get_vehicle_commanders(self):
        """Get all legendary vehicle commanders from database"""
        db_path = Path(__file__).parent.parent / "prisma" / "dev.db"
        
        if not db_path.exists():
            raise Exception(f"Database not found at {db_path}")
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT DISTINCT name 
            FROM Card 
            WHERE isCommander = 1
              AND typeLine LIKE '%Vehicle%'
            ORDER BY name
        """)
        
        vehicles = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        return vehicles

    def search_commander_decks(self, commander_name):
        """Search MTGGoldfish for decks with this commander"""
        try:
            # URL encode the commander name
            search_query = commander_name.replace(' ', '+').replace(',', '%2C')
            url = f'https://www.mtggoldfish.com/deck/custom/{search_query}'
            
            response = self.session.get(url, timeout=10)
            if response.status_code != 200:
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find deck links
            deck_links = soup.find_all('a', href=lambda x: x and '/deck/' in x and '/custom/' not in x)
            deck_ids = []
            
            for link in deck_links:
                href = link.get('href', '')
                if '/deck/' in href:
                    deck_id = href.split('/deck/')[-1].split('#')[0].split('?')[0]
                    if deck_id.isdigit():
                        deck_ids.append(deck_id)
            
            return list(set(deck_ids))[:self.decks_per_commander]
            
        except Exception as e:
            print(f"  Error searching for {commander_name}: {e}")
            return []

    def scrape_deck(self, deck_id):
        """Scrape a single deck from MTGGoldfish"""
        try:
            url = f'https://www.mtggoldfish.com/deck/{deck_id}'
            response = self.session.get(url, timeout=10)
            
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find commander section
            commander_section = soup.find('div', {'class': 'deck-col-title'}, string=lambda x: x and 'Commander' in x)
            if not commander_section:
                return None
            
            commander_table = commander_section.find_next('table', {'class': 'deck-view-deck-table'})
            if not commander_table:
                return None
            
            # Extract commander
            commander_rows = commander_table.find_all('tr', {'class': 'deck-category-line'})
            commanders = []
            for row in commander_rows:
                name_td = row.find('td', {'class': 'deck-col-card'})
                if name_td:
                    card_link = name_td.find('a')
                    if card_link:
                        commanders.append(card_link.text.strip())
            
            if not commanders:
                return None
            
            # Extract mainboard
            mainboard_section = soup.find('div', {'class': 'deck-col-title'}, string=lambda x: x and 'Deck' in x)
            if not mainboard_section:
                return None
            
            mainboard_table = mainboard_section.find_next('table', {'class': 'deck-view-deck-table'})
            if not mainboard_table:
                return None
            
            cards = []
            card_rows = mainboard_table.find_all('tr', {'class': 'deck-category-line'})
            
            for row in card_rows:
                qty_td = row.find('td', {'class': 'deck-col-qty'})
                name_td = row.find('td', {'class': 'deck-col-card'})
                
                if qty_td and name_td:
                    qty = qty_td.text.strip()
                    card_link = name_td.find('a')
                    if card_link:
                        card_name = card_link.text.strip()
                        cards.append(f"{qty}x {card_name}")
            
            # Build deck text
            total_cards = sum(int(c.split('x')[0]) for c in cards if 'x' in c) + len(commanders)
            
            if total_cards != 100:
                return None
            
            deck_text = f"Commander: {commanders[0]}\n\nDecklist:\n\n"
            deck_text += "Commanders:\n"
            for cmd in commanders:
                deck_text += f"1x {cmd}\n"
            deck_text += "\n"
            
            # Group cards by type (simplified)
            deck_text += "\n".join(cards)
            
            return {
                'deck_id': deck_id,
                'instruction': f"Build a Commander deck with {commanders[0]}.",
                'output': deck_text
            }
            
        except Exception as e:
            print(f"    Error scraping deck {deck_id}: {e}")
            return None

    def run(self):
        """Main scraping loop"""
        vehicles = self.get_vehicle_commanders()
        
        print(f"\n{'='*60}")
        print(f"VEHICLE COMMANDER SCRAPER")
        print(f"{'='*60}")
        print(f"Vehicle commanders: {len(vehicles)}")
        print(f"Decks per commander: {self.decks_per_commander}")
        print(f"Output: {self.output_file}")
        print(f"{'='*60}\n")
        
        total_new_decks = 0
        
        for i, commander in enumerate(vehicles, 1):
            print(f"[{i}/{len(vehicles)}] {commander}")
            
            # Search for decks
            deck_ids = self.search_commander_decks(commander)
            
            if not deck_ids:
                print(f"  No decks found")
                time.sleep(2)
                continue
            
            print(f"  Found {len(deck_ids)} deck IDs")
            
            # Filter out already scraped
            new_deck_ids = [did for did in deck_ids if did not in self.scraped_ids]
            
            if not new_deck_ids:
                print(f"  All decks already scraped")
                time.sleep(2)
                continue
            
            print(f"  Scraping {len(new_deck_ids)} new decks")
            
            # Scrape each deck
            with open(self.output_file, 'a') as f:
                for deck_id in new_deck_ids:
                    deck_data = self.scrape_deck(deck_id)
                    
                    if deck_data:
                        f.write(json.dumps(deck_data) + '\n')
                        f.flush()
                        self.scraped_ids.add(deck_id)
                        total_new_decks += 1
                        print(f"    ✓ [{total_new_decks}] {commander} (100 cards)")
                    else:
                        print(f"    ✗ Deck {deck_id} - invalid format")
                    
                    time.sleep(1)  # Be nice to MTGGoldfish
            
            time.sleep(2)  # Pause between commanders
        
        print(f"\n{'='*60}")
        print(f"SCRAPING COMPLETE")
        print(f"{'='*60}")
        print(f"Vehicle commanders processed: {len(vehicles)}")
        print(f"Total new decks collected: {total_new_decks}")
        print(f"Output: {self.output_file}")
        print(f"{'='*60}\n")


if __name__ == '__main__':
    scraper = VehicleCommanderScraper(decks_per_commander=25)
    scraper.run()
