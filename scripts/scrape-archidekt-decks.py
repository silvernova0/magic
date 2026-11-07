"""
Scrape Commander decklists from Archidekt using their v3 API
Much cleaner than web scraping - official JSON API
"""
import requests
import json
import time
import random
from pathlib import Path

class ArchidektScraper:
    def __init__(self, output_dir='data/training'):
        self.api_base = 'https://archidekt.com/api'
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json'
        })
    
    def search_commander_decks(self, page=1, page_size=100, order_by='-viewCount'):
        """Search for Commander decks via Archidekt v3 API"""
        try:
            url = f'{self.api_base}/decks/v3/'
            
            params = {
                'formats': 7,  # Commander format
                'orderBy': order_by,  # -viewCount, -updatedAt, -createdAt
                'page': page,
                'pageSize': page_size
            }
            
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            return data.get('results', []), data.get('next'), data.get('count', 0)
            
        except Exception as e:
            print(f"Error searching decks (page {page}): {e}")
            return [], None, 0
    
    def get_deck_details(self, deck_id, retries=3):
        """Get full deck details including card list"""
        for attempt in range(retries):
            try:
                url = f'{self.api_base}/decks/{deck_id}/'
                
                response = self.session.get(url, timeout=15)
                response.raise_for_status()
                
                return response.json()
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:  # Rate limited
                    wait_time = (attempt + 1) * 10  # 10s, 20s, 30s
                    print(f"    ⏳ Rate limited, waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"Error fetching deck {deck_id}: {e}")
                    return None
            except Exception as e:
                print(f"Error fetching deck {deck_id}: {e}")
                return None
        
        print(f"    ✗ Failed after {retries} retries")
        return None
    
    def parse_deck(self, deck_data):
        """Parse Archidekt deck data into training format"""
        try:
            # Basic info
            deck_id = deck_data.get('id')
            name = deck_data.get('name', 'Untitled')
            view_count = deck_data.get('viewCount', 0)
            created_at = deck_data.get('createdAt', '')
            
            # Get commanders
            commanders = []
            commander_cards = deck_data.get('cards', {}).get('commanders', [])
            
            for cmd_card in commander_cards:
                card_data = cmd_card.get('card', {})
                commanders.append(card_data.get('oracleCard', {}).get('name', ''))
            
            commander_name = commanders[0] if commanders else 'Unknown'
            
            # Extract color identity from deck
            colors = []
            color_obj = deck_data.get('colors', {})
            if color_obj:
                if color_obj.get('w'): colors.append('W')
                if color_obj.get('u'): colors.append('U')
                if color_obj.get('b'): colors.append('B')
                if color_obj.get('r'): colors.append('R')
                if color_obj.get('g'): colors.append('G')
            
            # Parse cards - Archidekt returns a flat list
            cards = []
            card_list = deck_data.get('cards', [])
            
            # Handle if cards is a list (not dict)
            if isinstance(card_list, list):
                for card_entry in card_list:
                    card_data = card_entry.get('card', {})
                    oracle_card = card_data.get('oracleCard', {})
                    
                    card_name = oracle_card.get('name', '')
                    if not card_name:
                        continue
                    
                    quantity = card_entry.get('quantity', 1)
                    categories_list = card_entry.get('categories', [])
                    
                    # Get primary category
                    category = 'Other'
                    if categories_list:
                        category = categories_list[0] if categories_list else 'Other'
                    
                    cards.append({
                        'name': card_name,
                        'category': category,
                        'quantity': quantity
                    })
            else:
                # Fallback if it's a dict
                for category, category_cards in card_list.items():
                    if not isinstance(category_cards, list):
                        continue
                        
                    for card_entry in category_cards:
                        card_data = card_entry.get('card', {})
                        oracle_card = card_data.get('oracleCard', {})
                        
                        card_name = oracle_card.get('name', '')
                        if not card_name:
                            continue
                        
                        quantity = card_entry.get('quantity', 1)
                        
                        cards.append({
                            'name': card_name,
                            'category': category,
                            'quantity': quantity
                        })
            
            # Extract theme from tags or description
            theme = 'General'
            tags = deck_data.get('tags', [])
            if tags:
                # Use first meaningful tag as theme
                theme = tags[0] if tags else 'General'
            
            return {
                'commander': commander_name,
                'name': name,
                'theme': theme,
                'colors': colors,
                'cards': cards,
                'source': 'archidekt',
                'url': f'https://archidekt.com/decks/{deck_id}',
                'metadata': {
                    'views': view_count,
                    'created': created_at,
                    'quality_score': view_count,  # Simple quality metric
                    'tags': tags
                }
            }
            
        except Exception as e:
            print(f"Error parsing deck: {e}")
            return None
    
    def scrape_decks(self, num_decks=2000, min_views=50):
        """Main scraping function"""
        print(f"\n{'='*60}")
        print(f"ARCHIDEKT DECK SCRAPER")
        print(f"{'='*60}")
        print(f"Target: {num_decks} Commander decklists")
        print(f"Min views: {min_views}\n")
        
        decks = []
        page = 1
        failed = 0
        skipped = 0
        total_available = 0
        
        while len(decks) < num_decks:
            print(f"\nFetching page {page}...")
            
            # Search for decks
            results, next_page, count = self.search_commander_decks(page=page, page_size=100)
            
            if page == 1:
                total_available = count
                print(f"Total Commander decks available: {total_available:,}")
            
            if not results:
                print("No more decks found")
                break
            
            print(f"Processing {len(results)} decks from page {page}...")
            
            # Process each deck
            for i, deck_summary in enumerate(results, 1):
                if len(decks) >= num_decks:
                    break
                
                deck_id = deck_summary.get('id')
                deck_name = deck_summary.get('name', 'Unknown')
                views = deck_summary.get('viewCount', 0)
                
                # Quality filter
                if views < min_views:
                    skipped += 1
                    continue
                
                print(f"  [{len(decks)+1}/{num_decks}] {deck_name} ({views:,} views)...")
                
                # Get full deck details
                deck_data = self.get_deck_details(deck_id)
                
                if not deck_data:
                    failed += 1
                    print(f"    ✗ Failed to fetch")
                    continue
                
                # Parse deck
                parsed = self.parse_deck(deck_data)
                
                if not parsed:
                    failed += 1
                    print(f"    ✗ Failed to parse")
                    continue
                
                # Validate deck
                if len(parsed['cards']) < 80:  # Should be close to 100
                    failed += 1
                    print(f"    ✗ Incomplete ({len(parsed['cards'])} cards)")
                    continue
                
                decks.append(parsed)
                print(f"    ✓ {len(parsed['cards'])} cards")
                
                # Save progress every 25 decks
                if len(decks) % 25 == 0:
                    self._save_progress(decks)
                    print(f"\n  💾 Progress saved: {len(decks)} decks")
                
                # Rate limiting - be VERY nice to Archidekt (5-8 seconds between requests)
                time.sleep(random.uniform(5.0, 8.0))
            
            # Check for next page
            if not next_page:
                print("\nReached last page")
                break
            
            page += 1
            
            # Rate limiting between pages (10-15 seconds)
            time.sleep(random.uniform(10.0, 15.0))
        
        # Final save
        self._save_progress(decks)
        
        print(f"\n{'='*60}")
        print(f"SCRAPING COMPLETE")
        print(f"{'='*60}")
        print(f"✓ Successfully scraped: {len(decks)} decks")
        print(f"✗ Failed: {failed} decks")
        print(f"⊘ Skipped (low views): {skipped} decks")
        print(f"📁 Saved to: {self.output_dir / 'archidekt_decks.jsonl'}")
        
        return decks
    
    def _save_progress(self, decks):
        """Save decks to JSONL file"""
        output_file = self.output_dir / 'archidekt_decks.jsonl'
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for deck in decks:
                f.write(json.dumps(deck) + '\n')

if __name__ == '__main__':
    scraper = ArchidektScraper()
    
    # Scrape 500 high-quality decks from Archidekt (very slow - ~8 hours)
    # 500 decks × 7 seconds = 58 minutes + retries = ~1-2 hours
    decks = scraper.scrape_decks(num_decks=500, min_views=100)
    
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
        print(f"  Views: {sample['metadata']['views']:,}")
