#!/usr/bin/env python3
"""
MTGGoldfish Commander Deck Scraper

Scrapes Commander decks from MTGGoldfish metagame archetypes.
Uses the clean text download endpoint for easy parsing.
"""

import requests
import json
import time
import random
import re
import sys
from pathlib import Path
from bs4 import BeautifulSoup

class MTGGoldfishScraper:
    def __init__(self):
        self.base_url = 'https://www.mtggoldfish.com'
        self.output_file = Path('data/training/mtggoldfish_decks.jsonl')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # Load existing deck IDs to avoid duplicates
        self.scraped_ids = set()
        if self.output_file.exists():
            with open(self.output_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        if 'metadata' in data and 'deck_id' in data['metadata']:
                            self.scraped_ids.add(data['metadata']['deck_id'])
                    except:
                        continue
        
        print(f"Loaded {len(self.scraped_ids)} existing MTGGoldfish deck IDs")
    
    def get_commander_archetypes(self):
        """Get list of Commander archetype URLs from metagame page"""
        try:
            url = f'{self.base_url}/metagame/commander'
            print(f"Fetching archetypes from: {url}")
            
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all archetype links
            archetype_links = soup.find_all('a', href=re.compile(r'/archetype/[^#]+'))
            
            archetypes = set()
            for link in archetype_links:
                href = link['href']
                # Remove #paper or #online suffix
                archetype_url = re.sub(r'#(paper|online)$', '', href)
                if archetype_url.startswith('/archetype/'):
                    archetypes.add(archetype_url)
            
            print(f"Found {len(archetypes)} unique Commander archetypes")
            return sorted(list(archetypes))
            
        except Exception as e:
            print(f"Error fetching archetypes: {e}")
            return []
    
    def get_deck_ids_from_archetype(self, archetype_url, max_decks=50):
        """Extract deck IDs from an archetype page"""
        try:
            url = f'{self.base_url}{archetype_url}'
            print(f"  Fetching decks from: {archetype_url}")
            
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            # Find all deck links (format: /deck/XXXXXXX)
            deck_ids = re.findall(r'/deck/(\d+)', response.text)
            
            # Remove duplicates and limit
            unique_ids = []
            seen = set()
            for deck_id in deck_ids:
                if deck_id not in seen and deck_id not in self.scraped_ids:
                    seen.add(deck_id)
                    unique_ids.append(deck_id)
                    if len(unique_ids) >= max_decks:
                        break
            
            print(f"    Found {len(unique_ids)} new decks")
            return unique_ids
            
        except Exception as e:
            print(f"  Error fetching archetype {archetype_url}: {e}")
            return []
    
    def download_deck(self, deck_id):
        """Download deck in plain text format"""
        try:
            url = f'{self.base_url}/deck/download/{deck_id}'
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            return response.text
            
        except Exception as e:
            print(f"    Error downloading deck {deck_id}: {e}")
            return None
    
    def parse_deck(self, deck_text, deck_id):
        """Parse plain text deck into structured format"""
        try:
            lines = deck_text.strip().split('\n')
            
            # Parse cards
            cards = []
            commander_name = None
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Parse format: "1 Card Name [SET] (F)"
                # Remove set codes and foil markers
                line = re.sub(r'\[.*?\]', '', line)  # Remove [SET]
                line = re.sub(r'\(F\)', '', line)     # Remove (F)
                line = re.sub(r'<.*?>', '', line)     # Remove <prerelease>
                line = line.strip()
                
                # Extract quantity and name
                match = re.match(r'^(\d+)\s+(.+)$', line)
                if match:
                    quantity = int(match.group(1))
                    name = match.group(2).strip()
                    cards.append({'name': name, 'quantity': quantity})
            
            # Total cards
            total_cards = sum(card['quantity'] for card in cards)
            
            # Validate: Must be exactly 100 cards (or 101 with commander listed separately)
            if total_cards < 99 or total_cards > 101:
                print(f"    ✗ Deck {deck_id} has {total_cards} cards, need 100")
                return None
            
            # Assume first card is the commander (MTGGoldfish lists commander first)
            if cards:
                commander_name = cards[0]['name']
            
            return {
                'deck_id': deck_id,
                'commander': commander_name,
                'cards': cards,
                'total_cards': total_cards
            }
            
        except Exception as e:
            print(f"    Error parsing deck {deck_id}: {e}")
            return None
    
    def categorize_cards(self, cards):
        """
        Categorize cards by type. MTGGoldfish lists cards in order:
        Commander, Creatures, Planeswalkers, Spells, Artifacts, Enchantments, Lands
        
        We'll use simple heuristics based on card names and common patterns.
        """
        categories = {
            'Commander': [],
            'Creatures': [],
            'Planeswalkers': [],
            'Instants': [],
            'Sorceries': [],
            'Artifacts': [],
            'Enchantments': [],
            'Lands': []
        }
        
        # First card is usually the commander
        if cards:
            categories['Commander'].append(cards[0])
            remaining_cards = cards[1:]
        else:
            remaining_cards = cards
        
        # Common land names/patterns
        land_patterns = [
            'Plains', 'Island', 'Swamp', 'Mountain', 'Forest',
            'Land', 'Wastes', 'Territory', 'Tower', 'Sanctum',
            'Pathway', 'Triome', 'Shock', 'Fetch', 'Temple',
            'Cave', 'Field', 'Grove', 'Heath', 'Lagoon',
            'Mesa', 'Mire', 'Peak', 'Prairie', 'Strand',
            'Tarn', 'Vista', 'Barrens', 'Gardens', 'Ruins'
        ]
        
        # Common planeswalker names
        planeswalker_names = [
            'Jace', 'Chandra', 'Liliana', 'Gideon', 'Nissa',
            'Ajani', 'Garruk', 'Sorin', 'Elspeth', 'Teferi',
            'Vraska', 'Narset', 'Tamiyo', 'Kiora', 'Ashiok',
            'Karn', 'Ugin', 'Nicol Bolas', 'Arlinn', 'Domri'
        ]
        
        for card in remaining_cards:
            name = card['name']
            
            # Check for lands
            is_land = any(pattern in name for pattern in land_patterns)
            if is_land or name == 'Command Tower' or 'Fetch' in name:
                categories['Lands'].append(card)
                continue
            
            # Check for planeswalkers
            is_planeswalker = any(pw in name for pw in planeswalker_names)
            if is_planeswalker:
                categories['Planeswalkers'].append(card)
                continue
            
            # Default to creatures (most common in Commander)
            # More sophisticated version would check card types from Scryfall/MTGJson
            categories['Creatures'].append(card)
        
        return categories
    
    def to_training_format(self, deck):
        """Convert deck to training format"""
        try:
            commander = deck['commander']
            cards = deck['cards']
            
            # Build instruction
            instruction = f"Build a Commander deck with {commander}."
            
            # Categorize cards (simple version - just list them)
            # Commander is first, rest are in order from MTGGoldfish
            output_lines = [
                f"Commander: {commander}",
                "",
                "Deck:",
                ""
            ]
            
            # Add all cards (skip first if it's the commander)
            start_idx = 1 if cards[0]['name'] == commander else 0
            for card in cards[start_idx:]:
                qty = card['quantity']
                name = card['name']
                output_lines.append(f"{qty}x {name}")
            
            output = '\n'.join(output_lines)
            
            return {
                'instruction': instruction,
                'output': output,
                'metadata': {
                    'type': 'deck_building',
                    'commander': commander,
                    'source': 'mtggoldfish',
                    'deck_id': deck['deck_id'],
                    'total_cards': deck['total_cards']
                }
            }
            
        except Exception as e:
            print(f"    Error converting deck to training format: {e}")
            return None
    
    def scrape_archetypes(self, target_decks=3000, decks_per_archetype=50):
        """Scrape decks from all Commander archetypes"""
        print("\n" + "="*60)
        print("MTGGOLDFISH COMMANDER SCRAPER")
        print("="*60)
        print(f"Target: {target_decks} decks\n")
        
        # Get archetypes
        archetypes = self.get_commander_archetypes()
        if not archetypes:
            print("No archetypes found!")
            return []
        
        collected = []
        
        for i, archetype_url in enumerate(archetypes, 1):
            if len(collected) >= target_decks:
                break
            
            print(f"\n[{i}/{len(archetypes)}] {archetype_url}")
            
            # Get deck IDs from this archetype
            deck_ids = self.get_deck_ids_from_archetype(archetype_url, max_decks=decks_per_archetype)
            
            for deck_id in deck_ids:
                if len(collected) >= target_decks:
                    break
                
                # Download deck
                deck_text = self.download_deck(deck_id)
                if not deck_text:
                    continue
                
                # Parse deck
                deck = self.parse_deck(deck_text, deck_id)
                if not deck:
                    continue
                
                # Convert to training format
                training_data = self.to_training_format(deck)
                if not training_data:
                    continue
                
                # Save
                with open(self.output_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(training_data, ensure_ascii=False) + '\n')
                
                self.scraped_ids.add(deck_id)
                collected.append(deck)
                
                print(f"    ✓ [{len(collected)}/{target_decks}] {deck['commander']} ({deck['total_cards']} cards)")
                
                # Rate limiting
                time.sleep(random.uniform(1.5, 3.0))
            
            # Pause between archetypes
            time.sleep(random.uniform(2.0, 4.0))
        
        print(f"\n✓ Collected {len(collected)} decks from MTGGoldfish")
        return collected

if __name__ == '__main__':
    scraper = MTGGoldfishScraper()
    
    # Scrape Commander decks
    decks = scraper.scrape_archetypes(target_decks=3000, decks_per_archetype=100)
    
    print("\n" + "="*60)
    print("SCRAPING COMPLETE")
    print("="*60)
    print(f"Total decks: {len(decks)}")
    print(f"Output: {scraper.output_file}")
