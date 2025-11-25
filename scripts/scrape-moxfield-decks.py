"""
Scrape Commander decklists from Moxfield
Focuses on highly-rated public decklists with descriptions
"""
import requests
import json
import time
import random
from pathlib import Path
from datetime import datetime

class MoxfieldScraper:
    def __init__(self, output_dir='data/training'):
        self.api_base = 'https://api2.moxfield.com/v2'
        self.web_base = 'https://www.moxfield.com'
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.moxfield.com/',
            'Origin': 'https://www.moxfield.com'
        })
    
    def search_commander_decks(self, page=1, page_size=100, sort_type='views', sort_direction='Descending'):
        """Search for public Commander decks via Moxfield API"""
        try:
            url = f'{self.api_base}/decks/search'
            
            params = {
                'fmt': 'commander',  # Commander format
                'pageNumber': page,
                'pageSize': page_size,
                'sortType': sort_type,  # Configurable: 'views', 'updated', 'created'
                'sortDirection': sort_direction,
                'board': 'mainboard',
                'visibility': 'public'
            }
            
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            return data.get('data', [])
            
        except Exception as e:
            print(f"Error searching decks (page {page}): {e}")
            return []
    
    def get_deck_details(self, deck_id):
        """Get full deck details including card list"""
        try:
            url = f'{self.api_base}/decks/all/{deck_id}'
            
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            print(f"Error fetching deck {deck_id}: {e}")
            return None
    
    def parse_deck(self, deck_data):
        """Parse Moxfield deck data into training format"""
        try:
            # Extract basic info
            name = deck_data.get('name', 'Untitled')
            description = deck_data.get('description', '')
            format_type = deck_data.get('format', 'commander')
            
            # Get commanders
            commanders = []
            commanders_data = deck_data.get('commanders', [])
            for cmd in commanders_data:
                card = cmd.get('card', {})
                commanders.append(card.get('name', ''))
            
            # If no commanders in that field, check mainboard
            if not commanders:
                mainboard = deck_data.get('mainboard', {})
                for card_id, card_data in mainboard.items():
                    card = card_data.get('card', {})
                    if card.get('type_line', '').startswith('Legendary Creature'):
                        commanders.append(card.get('name', ''))
                        break
            
            commander_name = commanders[0] if commanders else 'Unknown'
            
            # Extract color identity
            colors = deck_data.get('colorIdentity', [])
            
            # Parse cards by category
            cards = []
            
            mainboard = deck_data.get('mainboard', {})
            for card_id, card_data in mainboard.items():
                card = card_data.get('card', {})
                quantity = card_data.get('quantity', 1)
                
                card_name = card.get('name', '')
                if not card_name:
                    continue
                
                # Determine category
                type_line = card.get('type_line', '')
                category = self._determine_category(type_line)
                
                # Get tags if available
                tags = card_data.get('tags', [])
                
                cards.append({
                    'name': card_name,
                    'category': category,
                    'quantity': quantity,
                    'type': type_line,
                    'tags': tags
                })
            
            # Get theme from description or tags
            theme = self._extract_theme(description, name)
            
            # Get metadata
            views = deck_data.get('viewCount', 0)
            likes = deck_data.get('likeCount', 0)
            comments = deck_data.get('commentCount', 0)
            updated_at = deck_data.get('lastUpdatedAt', '')
            
            return {
                'commander': commander_name,
                'name': name,
                'theme': theme,
                'description': description[:500] if description else '',  # Limit length
                'colors': colors,
                'cards': cards,
                'source': 'moxfield',
                'metadata': {
                    'views': views,
                    'likes': likes,
                    'comments': comments,
                    'updated_at': updated_at,
                    'quality_score': views + (likes * 10)  # Weighted quality
                }
            }
            
        except Exception as e:
            print(f"Error parsing deck: {e}")
            return None
    
    def _determine_category(self, type_line):
        """Determine card category from type line"""
        type_lower = type_line.lower()
        
        if 'creature' in type_lower:
            return 'Creatures'
        elif 'instant' in type_lower:
            return 'Instants'
        elif 'sorcery' in type_lower:
            return 'Sorceries'
        elif 'artifact' in type_lower:
            return 'Artifacts'
        elif 'enchantment' in type_lower:
            return 'Enchantments'
        elif 'planeswalker' in type_lower:
            return 'Planeswalkers'
        elif 'land' in type_lower:
            return 'Lands'
        else:
            return 'Other'
    
    def _extract_theme(self, description, name):
        """Extract deck theme from description or name"""
        themes = [
            'Aggro', 'Control', 'Midrange', 'Combo', 'Voltron', 'Aristocrats',
            'Tokens', 'Tribal', 'Landfall', 'Storm', 'Group Hug', 'Stax',
            'Reanimator', 'Spellslinger', 'Lifegain', 'Mill', 'Sacrifice',
            'Artifact', 'Enchantment', 'Graveyard', 'Blink', 'Ramp', 'Kindred'
        ]
        
        text = (description + ' ' + name).lower()
        
        for theme in themes:
            if theme.lower() in text:
                return theme
        
        return 'General'
    
    def scrape_decks(self, num_decks=2000, min_quality=100, min_date=None, sort_by='views'):
        """Main scraping function"""
        print(f"\n{'='*60}")
        print(f"MOXFIELD DECK SCRAPER")
        print(f"{'='*60}")
        print(f"Target: {num_decks} Commander decklists")
        print(f"Min quality score: {min_quality}")
        if min_date:
            print(f"Min date: {min_date}")
        print(f"Sort by: {sort_by}\n")
        
        decks = []
        page = 1
        failed = 0
        skipped = 0
        
        while len(decks) < num_decks:
            print(f"\nFetching page {page}...")
            
            # Search for decks
            search_results = self.search_commander_decks(page=page, page_size=100, sort_type=sort_by)
            
            if not search_results:
                print("No more decks found")
                break
            
            # Process each deck
            for result in search_results:
                if len(decks) >= num_decks:
                    break
                
                # Check date limit if enabled
                if min_date:
                    updated_str = result.get('lastUpdatedAt')
                    if updated_str:
                        try:
                            # Handle ISO format with Z
                            updated_str = updated_str.replace('Z', '+00:00')
                            deck_date = datetime.fromisoformat(updated_str)
                            
                            if deck_date < min_date:
                                print(f"  🛑 Reached date limit: {deck_date.date()} < {min_date.date()}")
                                # Save whatever we have and return
                                self._save_progress(decks)
                                return decks
                        except ValueError:
                            pass # Ignore date parse errors
                
                deck_id = result.get('publicId')
                deck_name = result.get('name', 'Unknown')
                
                print(f"  [{len(decks)+1}/{num_decks}] {deck_name}...")
                
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
                
                # Quality filter (only apply if we are sorting by views, otherwise we might skip recent good decks)
                # If sorting by updated, we might want to lower the quality threshold or ignore it
                quality = parsed['metadata']['quality_score']
                if sort_by == 'views' and quality < min_quality:
                    skipped += 1
                    print(f"    ⊘ Skipped (quality: {quality})")
                    continue
                elif sort_by == 'updated' and quality < 10: # Minimal quality for new decks
                     skipped += 1
                     print(f"    ⊘ Skipped (low quality new deck: {quality})")
                     continue
                
                # Validate deck
                if len(parsed['cards']) < 80:  # Should be close to 100
                    failed += 1
                    print(f"    ✗ Incomplete ({len(parsed['cards'])} cards)")
                    continue
                
                decks.append(parsed)
                print(f"    ✓ {len(parsed['cards'])} cards (quality: {quality})")
                
                # Save progress every 25 decks
                if len(decks) % 25 == 0:
                    self._save_progress(decks)
                    print(f"\n  💾 Progress saved: {len(decks)} decks")
                
                # Rate limiting
                time.sleep(random.uniform(1.0, 2.0))
            
            page += 1
            
            # Safety check - don't scrape forever
            if page > 100:
                print("\nReached page limit")
                break
            
            time.sleep(random.uniform(2.0, 3.0))
        
        # Final save
        self._save_progress(decks)
        
        print(f"\n{'='*60}")
        print(f"SCRAPING COMPLETE")
        print(f"{'='*60}")
        print(f"✓ Successfully scraped: {len(decks)} decks")
        print(f"✗ Failed: {failed} decks")
        print(f"⊘ Skipped (low quality): {skipped} decks")
        print(f"📁 Saved to: {self.output_dir / 'moxfield_decks.jsonl'}")
        
        return decks
    
    def _save_progress(self, decks):
        """Save decks to JSONL file"""
        output_file = self.output_dir / 'moxfield_decks.jsonl'
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for deck in decks:
                f.write(json.dumps(deck) + '\n')

if __name__ == '__main__':
    scraper = MoxfieldScraper()
    
    # Scrape 2000 high-quality decks from Moxfield
    decks = scraper.scrape_decks(num_decks=2000, min_quality=100)
    
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
        print(f"  Quality: {sample['metadata']['quality_score']}")
