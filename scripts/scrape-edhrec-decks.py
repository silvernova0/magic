"""
Scrape Commander decklists from EDHREC
Collects deck structure, card lists, themes, and metadata
"""
import requests
from bs4 import BeautifulSoup
import json
import time
import random
from pathlib import Path
from urllib.parse import urljoin
import re

class EDHRECScraper:
    def __init__(self, output_dir='data/training'):
        self.base_url = 'https://edhrec.com'
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
    def get_top_commanders(self, limit=500):
        """Get list of top commanders by scraping individual color pages"""
        print(f"Fetching top {limit} commanders from EDHREC...")
        
        commanders = []
        
        # EDHREC organizes by color combinations
        color_pages = [
            '/commanders/mono-white',
            '/commanders/mono-blue',
            '/commanders/mono-black', 
            '/commanders/mono-red',
            '/commanders/mono-green',
            '/commanders/azorius',
            '/commanders/dimir',
            '/commanders/rakdos',
            '/commanders/gruul',
            '/commanders/selesnya',
            '/commanders/orzhov',
            '/commanders/izzet',
            '/commanders/golgari',
            '/commanders/boros',
            '/commanders/simic',
            '/commanders/esper',
            '/commanders/grixis',
            '/commanders/jund',
            '/commanders/naya',
            '/commanders/bant',
            '/commanders/abzan',
            '/commanders/jeskai',
            '/commanders/sultai',
            '/commanders/mardu',
            '/commanders/temur',
            '/commanders/5c',
            '/commanders/4c',
            '/commanders/colorless'
        ]
        
        for color_page in color_pages:
            if len(commanders) >= limit:
                break
                
            try:
                url = f'{self.base_url}{color_page}'
                print(f"Scraping {color_page}...")
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find all commander card links on this color page
                # EDHREC structure: links with /commanders/color/commander-name pattern
                for link in soup.find_all('a', href=True):
                    href = link.get('href')
                    
                    # Match commander pages (not category pages)
                    if href and href.startswith(color_page + '/') and href.count('/') >= 3:
                        # Extract commander name from link text
                        name = link.get_text(strip=True)
                        
                        # Filter out UI elements
                        if name and len(name) > 3 and len(name) < 60:
                            full_url = urljoin(self.base_url, href)
                            
                            # Avoid duplicates
                            if full_url not in [c['url'] for c in commanders]:
                                commanders.append({
                                    'name': name,
                                    'url': full_url
                                })
                                
                                if len(commanders) >= limit:
                                    break
                
                time.sleep(random.uniform(1.5, 3.0))  # Be nice to EDHREC
                
            except Exception as e:
                print(f"Error fetching {color_page}: {e}")
                continue
        
        print(f"Found {len(commanders)} commanders")
        return commanders[:limit]
    
    def scrape_commander_page(self, commander_url, commander_name):
        """Scrape average decklist for a commander"""
        try:
            print(f"Scraping deck for {commander_name}...")
            response = self.session.get(commander_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract theme if available
            theme = 'General'
            theme_elem = soup.select_one('.theme, .commander-theme, h2')
            if theme_elem:
                theme_text = theme_elem.get_text(strip=True)
                if 'Theme' in theme_text:
                    theme = theme_text.replace('Theme:', '').strip()
            
            # Extract color identity from page
            colors = []
            color_icons = soup.select('.mana-icon, .color-icon')
            for icon in color_icons:
                classes = icon.get('class', [])
                for cls in classes:
                    if cls in ['w', 'u', 'b', 'r', 'g', 'W', 'U', 'B', 'R', 'G']:
                        colors.append(cls.upper())
            colors = list(set(colors))
            
            # Parse decklist sections
            deck = {
                'commander': commander_name,
                'theme': theme,
                'colors': colors,
                'source': 'edhrec',
                'url': commander_url,
                'cards': []
            }
            
            # Find all card entries
            sections = {
                'Creatures': [],
                'Instants': [],
                'Sorceries': [],
                'Artifacts': [],
                'Enchantments': [],
                'Planeswalkers': [],
                'Lands': []
            }
            
            # Try multiple selectors for card lists
            card_containers = soup.select('.Card_card__1OqeH, .card-list-item, .card-entry')
            
            for card_elem in card_containers:
                card_name_elem = card_elem.select_one('.Card_name__2hVRR, .card-name, h3, a')
                if not card_name_elem:
                    continue
                    
                card_name = card_name_elem.get_text(strip=True)
                
                # Determine category from section headers
                category = 'Other'
                parent_section = card_elem.find_parent('section')
                if parent_section:
                    header = parent_section.find(['h2', 'h3', 'h4'])
                    if header:
                        header_text = header.get_text(strip=True)
                        for section_name in sections.keys():
                            if section_name.lower() in header_text.lower():
                                category = section_name
                                break
                
                # Extract synergy percentage if available
                synergy = None
                synergy_elem = card_elem.select_one('.synergy, .percentage, [class*="synergy"]')
                if synergy_elem:
                    synergy_text = synergy_elem.get_text(strip=True)
                    match = re.search(r'(\d+)%', synergy_text)
                    if match:
                        synergy = int(match.group(1))
                
                deck['cards'].append({
                    'name': card_name,
                    'category': category,
                    'synergy': synergy
                })
            
            # If no cards found, try alternative parsing
            if not deck['cards']:
                # Look for card links in the page
                for link in soup.select('a[href*="/cards/"]'):
                    card_name = link.get_text(strip=True)
                    if card_name and len(card_name) > 2:
                        deck['cards'].append({
                            'name': card_name,
                            'category': 'Unknown',
                            'synergy': None
                        })
            
            return deck
            
        except Exception as e:
            print(f"Error scraping {commander_name}: {e}")
            return None
    
    def scrape_decks(self, num_decks=5000):
        """Main scraping function"""
        print(f"\n{'='*60}")
        print(f"EDHREC DECK SCRAPER")
        print(f"{'='*60}")
        print(f"Target: {num_decks} Commander decklists\n")
        
        # Get commanders to scrape
        commanders = self.get_top_commanders(limit=num_decks)
        
        decks = []
        failed = 0
        
        for i, commander in enumerate(commanders, 1):
            print(f"\n[{i}/{len(commanders)}] Scraping {commander['name']}...")
            
            deck = self.scrape_commander_page(commander['url'], commander['name'])
            
            if deck and len(deck['cards']) >= 50:  # Minimum viable deck
                decks.append(deck)
                print(f"  ✓ Found {len(deck['cards'])} cards")
            else:
                failed += 1
                print(f"  ✗ Failed or incomplete deck")
            
            # Save progress every 50 decks
            if len(decks) % 50 == 0:
                self._save_progress(decks)
                print(f"\n  Progress saved: {len(decks)} decks collected")
            
            # Rate limiting
            time.sleep(random.uniform(2.0, 4.0))
            
            # Stop if we have enough
            if len(decks) >= num_decks:
                break
        
        # Final save
        self._save_progress(decks)
        
        print(f"\n{'='*60}")
        print(f"SCRAPING COMPLETE")
        print(f"{'='*60}")
        print(f"✓ Successfully scraped: {len(decks)} decks")
        print(f"✗ Failed: {failed} decks")
        print(f"📁 Saved to: {self.output_dir / 'edhrec_decks.jsonl'}")
        
        return decks
    
    def _save_progress(self, decks):
        """Save decks to JSONL file"""
        output_file = self.output_dir / 'edhrec_decks.jsonl'
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for deck in decks:
                f.write(json.dumps(deck) + '\n')

if __name__ == '__main__':
    scraper = EDHRECScraper()
    
    # Scrape 3000 decks from EDHREC
    decks = scraper.scrape_decks(num_decks=3000)
    
    print(f"\n✓ Scraping complete!")
    print(f"Total decks: {len(decks)}")
    
    # Show sample
    if decks:
        print(f"\nSample deck:")
        sample = decks[0]
        print(f"  Commander: {sample['commander']}")
        print(f"  Theme: {sample['theme']}")
        print(f"  Colors: {', '.join(sample['colors'])}")
        print(f"  Cards: {len(sample['cards'])}")
