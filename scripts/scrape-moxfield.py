"""
Scrape Commander decklists from Moxfield
Moxfield has high-quality public decks with ratings (1-5 stars)
Uses their public API for clean data extraction
"""
import requests
import json
import time
import random
from pathlib import Path

class MoxfieldScraper:
    def __init__(self, output_dir='data/training'):
        self.api_base = 'https://api2.moxfield.com/v2/decks/search'
        self.deck_api = 'https://api2.moxfield.com/v3/decks/all'
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
    
    def search_commander_decks(self, page_num=1, page_size=32, sort_by="views", commander_name=None, archetype=None):
        """Search for Commander decks via Moxfield API
        
        Args:
            page_num: Page number to fetch
            page_size: Number of results per page
            sort_by: Sort type (views, updated, created, likes)
            commander_name: Filter by specific commander
            archetype: Search for specific archetype/theme
        """
        try:
            url = self.api_base
            
            # Use GET with query parameters instead of POST
            params = {
                "pageNumber": page_num,
                "pageSize": page_size,
                "sortType": sort_by,
                "sortDirection": "Descending",
                "fmt": "commander",  # Commander format only
                "board": "mainboard"
            }
            
            # Add commander filter if specified
            if commander_name:
                params["cardFilters"] = [{"type": "commander", "name": commander_name}]
            
            # Add search query for archetype
            if archetype:
                params["q"] = archetype
            
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            return data.get('data', []), data.get('totalResults', 0)
            
        except Exception as e:
            print(f"Error searching decks (page {page_num}): {e}")
            return [], 0
    
    def get_deck_details(self, deck_id, retries=3):
        """Get full deck details including card list"""
        for attempt in range(retries):
            try:
                url = f'{self.deck_api}/{deck_id}'
                
                response = self.session.get(url, timeout=15)
                response.raise_for_status()
                
                return response.json()
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:  # Rate limited
                    wait_time = (attempt + 1) * 10
                    print(f"    ⏳ Rate limited, waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                elif e.response.status_code == 404:
                    print(f"    ✗ Deck {deck_id} not found (deleted or private)")
                    return None
                else:
                    print(f"    Error fetching deck {deck_id}: {e}")
                    return None
            except Exception as e:
                print(f"    Error fetching deck {deck_id}: {e}")
                return None
        
        print(f"    ✗ Failed after {retries} retries")
        return None
    
    def parse_deck(self, deck_data):
        """Parse Moxfield deck data into training format"""
        try:
            # Basic info
            deck_id = deck_data.get('publicId', '')
            name = deck_data.get('name', 'Untitled')
            description = deck_data.get('description', '')
            view_count = deck_data.get('viewCount', 0)
            like_count = deck_data.get('likeCount', 0)
            comment_count = deck_data.get('commentCount', 0)
            
            # Moxfield's own quality rating (1-5)
            # This comes from the search results, not the deck details
            
            # Get commanders
            commanders = []
            commanders_data = deck_data.get('commanders', [])
            
            for cmd in commanders_data:
                card = cmd.get('card', {})
                commanders.append(card.get('name', ''))
            
            if not commanders:
                # Try getting from mainboard with "Commander" category
                mainboard = deck_data.get('boards', {}).get('mainboard', {}).get('cards', {})
                for card_data in mainboard.values():
                    if card_data.get('boardType') == 'commanders':
                        commanders.append(card_data.get('card', {}).get('name', ''))
            
            commander_name = commanders[0] if commanders else 'Unknown'
            
            # Extract color identity
            colors = []
            color_str = deck_data.get('colors', '')
            if color_str:
                # Moxfield uses single letters: W, U, B, R, G
                for c in ['W', 'U', 'B', 'R', 'G']:
                    if c in color_str:
                        colors.append(c)
            
            # Parse cards from mainboard
            cards = []
            mainboard = deck_data.get('boards', {}).get('mainboard', {}).get('cards', {})
            
            for card_id, card_entry in mainboard.items():
                card = card_entry.get('card', {})
                card_name = card.get('name', '')
                
                if not card_name:
                    continue
                
                quantity = card_entry.get('quantity', 1)
                
                # Determine category from card type
                type_line = card.get('type_line', '')
                
                if 'Creature' in type_line:
                    category = 'Creature'
                elif 'Planeswalker' in type_line:
                    category = 'Planeswalker'
                elif 'Instant' in type_line:
                    category = 'Instant'
                elif 'Sorcery' in type_line:
                    category = 'Sorcery'
                elif 'Artifact' in type_line:
                    category = 'Artifact'
                elif 'Enchantment' in type_line:
                    category = 'Enchantment'
                elif 'Land' in type_line:
                    category = 'Land'
                else:
                    category = 'Other'
                
                cards.append({
                    'name': card_name,
                    'category': category,
                    'quantity': quantity
                })
            
            # Extract theme from description or tags
            theme = 'General'
            tags = deck_data.get('tags', [])
            if tags:
                theme = tags[0] if tags else 'General'
            elif description:
                # Simple theme extraction from description
                desc_lower = description.lower()
                if 'tribal' in desc_lower or 'typal' in desc_lower:
                    theme = 'tribal'
                elif 'combo' in desc_lower:
                    theme = 'combo'
                elif 'control' in desc_lower:
                    theme = 'control'
                elif 'aggro' in desc_lower:
                    theme = 'aggro'
                elif 'voltron' in desc_lower:
                    theme = 'voltron'
                elif 'token' in desc_lower:
                    theme = 'tokens'
            
            # Calculate quality score from engagement metrics
            quality_score = view_count + (like_count * 10) + (comment_count * 5)
            
            return {
                'commander': commander_name,
                'name': name,
                'theme': theme,
                'colors': colors,
                'cards': cards,
                'source': 'moxfield',
                'url': f'https://moxfield.com/decks/{deck_id}',
                'metadata': {
                    'views': view_count,
                    'likes': like_count,
                    'comments': comment_count,
                    'quality_score': quality_score,
                    'description': description[:200] if description else ''
                }
            }
            
        except Exception as e:
            print(f"Error parsing deck: {e}")
            return None
    
    def scrape_decks(self, num_decks=1000, min_quality_score=50):
        """Main scraping function"""
        print(f"\n{'='*60}")
        print(f"MOXFIELD DECK SCRAPER")
        print(f"{'='*60}")
        print(f"Target: {num_decks} Commander decklists")
        print(f"Min quality score: {min_quality_score}\n")
        
        all_decks = []
        page_num = 1
        failed = 0
        skipped = 0
        total_available = 0
        
        output_file = self.output_dir / 'moxfield_decks.jsonl'
        
        # Open file in append mode to preserve existing decks
        with open(output_file, 'a', encoding='utf-8') as f:
            while len(all_decks) < num_decks:
                print(f"\nFetching page {page_num}...")
                
                # Search for decks
                results, total = self.search_commander_decks(page_num=page_num, page_size=32)
                
                if page_num == 1:
                    total_available = total
                    print(f"Total Commander decks available: {total_available:,}")
                
                if not results:
                    print("No more decks found. Stopping.")
                    break
                
                print(f"Found {len(results)} decks on this page")
                
                for i, deck_summary in enumerate(results):
                    if len(all_decks) >= num_decks:
                        break
                    
                    try:
                        deck_id = deck_summary.get('publicId', '')
                        deck_name = deck_summary.get('name', 'Unknown')
                        views = deck_summary.get('viewCount', 0)
                        
                        print(f"  [{len(all_decks) + 1}/{num_decks}] {deck_name} ({views:,} views)...")
                        
                        # Get full deck details
                        deck_data = self.get_deck_details(deck_id)
                        
                        if not deck_data:
                            failed += 1
                            print(f"    ✗ Failed to fetch")
                            continue
                        
                        # Parse deck
                        parsed_deck = self.parse_deck(deck_data)
                        
                        if not parsed_deck:
                            failed += 1
                            print(f"    ✗ Failed to parse")
                            continue
                        
                        # Quality filter
                        if parsed_deck['metadata']['quality_score'] < min_quality_score:
                            skipped += 1
                            print(f"    ⊘ Skipped (quality score too low)")
                            continue
                        
                        # Convert to training format
                        training_example = {
                            'instruction': f"Build a Commander deck with {parsed_deck['commander']} focused on {parsed_deck['theme']}.",
                            'output': self._format_deck_output(parsed_deck),
                            'metadata': {
                                'type': 'deck_building',
                                'commander': parsed_deck['commander'],
                                'theme': parsed_deck['theme'],
                                'colors': parsed_deck['colors'],
                                'source': 'moxfield',
                                'quality_score': parsed_deck['metadata']['quality_score']
                            }
                        }
                        
                        # Save immediately (append mode)
                        f.write(json.dumps(training_example) + '\n')
                        f.flush()  # Ensure it's written to disk
                        
                        all_decks.append(parsed_deck)
                        print(f"    ✓ Saved ({len(parsed_deck['cards'])} cards)")
                        
                    except Exception as e:
                        failed += 1
                        print(f"    ✗ Error: {e}")
                        continue
                    
                    # Rate limiting - be nice to Moxfield
                    time.sleep(random.uniform(1.0, 2.0))
                
                page_num += 1
                
                # Longer pause between pages
                if len(all_decks) < num_decks:
                    time.sleep(random.uniform(2.0, 4.0))
        
        print(f"\n{'='*60}")
        print("SCRAPING COMPLETE")
        print(f"{'='*60}")
        print(f"✓ Successfully scraped: {len(all_decks)} decks")
        print(f"✗ Failed: {failed} decks")
        print(f"⊘ Skipped (low quality): {skipped} decks")
        print(f"📁 Saved to: {output_file}")
        
        print(f"\n✓ Scraping complete!")
        print(f"Total decks: {len(all_decks)}")
        
        return all_decks
    
    def _format_deck_output(self, deck):
        """Format deck as training output"""
        from collections import defaultdict
        
        output = f"Commander: {deck['commander']}\n\n"
        output += f"Deck Name: {deck['name']}\n"
        output += f"Theme: {deck['theme']}\n"
        output += f"Color Identity: {', '.join(deck['colors']) if deck['colors'] else 'Colorless'}\n\n"
        output += "Decklist:\n"
        
        # Group cards by category
        by_category = defaultdict(list)
        for card in deck['cards']:
            by_category[card['category']].append(card['name'])
        
        for category in ['Creature', 'Planeswalker', 'Instant', 'Sorcery', 'Artifact', 'Enchantment', 'Land', 'Other']:
            if category in by_category:
                output += f"\n{category}s ({len(by_category[category])}):\n"
                for card_name in sorted(by_category[category]):
                    output += f"1 {card_name}\n"
        
        return output


if __name__ == '__main__':
    scraper = MoxfieldScraper()
    
    # Scrape 1000 high-quality Commander decks
    decks = scraper.scrape_decks(num_decks=1000, min_quality_score=50)
    
    if decks:
        print(f"\n✅ Sample deck:")
        sample = decks[0]
        print(f"  Commander: {sample['commander']}")
        print(f"  Theme: {sample['theme']}")
        print(f"  Cards: {len(sample['cards'])}")
        print(f"  Quality Score: {sample['metadata']['quality_score']}")
        print(f"  URL: {sample['url']}")
