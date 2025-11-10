"""
Scrape Commander decklists from Archidekt using their v3 API
Much cleaner than web scraping - official JSON API
"""
import sys
import requests
import json
import time
import random
from pathlib import Path

# Unbuffered output for real-time logging
sys.stdout = sys.__stdout__
sys.stderr = sys.__stderr__

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
    
    def search_commander_decks(self, page=1, page_size=100, order_by='-viewCount', edh_bracket=None, deck_tag_name=None):
        """Search for Commander decks via Archidekt v3 API"""
        try:
            url = f'{self.api_base}/decks/v3/'
            
            params = {
                'formats': 7,  # Commander format
                'orderBy': order_by,  # -viewCount, -updatedAt, -createdAt
                'page': page,
                'pageSize': page_size
            }
            
            # Add bracket filter if specified
            if edh_bracket is not None:
                params['edhBracket'] = edh_bracket
            
            # Add tag filter if specified
            if deck_tag_name is not None:
                params['deckTagName'] = deck_tag_name
            
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
            
            # Get commanders - they're in the flat cards list with 'Commander' in categories
            commanders = []
            card_list = deck_data.get('cards', [])
            
            if isinstance(card_list, list):
                for card_entry in card_list:
                    categories = card_entry.get('categories', [])
                    # Skip maybeboard cards
                    if 'Maybeboard' in categories:
                        continue
                    if 'Commander' in categories:
                        card_data = card_entry.get('card', {})
                        oracle_card = card_data.get('oracleCard', {})
                        commander_name = oracle_card.get('name', '')
                        if commander_name:
                            commanders.append(commander_name)
            
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
                    
                    # SKIP maybeboard cards - they're not part of the actual deck
                    if 'Maybeboard' in categories_list:
                        continue
                    
                    # Use actual card type from oracle data, not user's custom category
                    # This handles user categories like "Copy", "Counter", "Win Condition" etc.
                    card_types = oracle_card.get('types', [])
                    
                    # Determine category based on card type
                    if 'Commander' in categories_list:
                        category = 'Commander'
                    elif not card_types:
                        category = 'Other'
                    elif 'Land' in card_types:
                        category = 'Land'
                    elif 'Creature' in card_types:
                        category = 'Creature'
                    elif 'Planeswalker' in card_types:
                        category = 'Planeswalker'
                    elif 'Instant' in card_types:
                        category = 'Instant'
                    elif 'Sorcery' in card_types:
                        category = 'Sorcery'
                    elif 'Enchantment' in card_types:
                        category = 'Enchantment'
                    elif 'Artifact' in card_types:
                        category = 'Artifact'
                    elif 'Battle' in card_types:
                        category = 'Battle'
                    else:
                        category = 'Other'
                    
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
                
                # Validate deck - check TOTAL card count (sum of all quantities)
                total_cards = sum(card['quantity'] for card in parsed['cards'])
                if total_cards < 98 or total_cards > 102:  # Should be exactly 100, but allow 98-102 for edge cases
                    failed += 1
                    print(f"    ✗ Invalid card count ({total_cards} total, {len(parsed['cards'])} unique)")
                    continue
                
                decks.append(parsed)
                print(f"    ✓ {total_cards} total cards ({len(parsed['cards'])} unique)")
                
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
    
    def _save_progress(self, decks, append=True):
        """Save decks to JSONL file in training format"""
        output_file = self.output_dir / 'archidekt_decks.jsonl'
        
        # Use append mode to preserve existing decks
        mode = 'a' if append else 'w'
        
        with open(output_file, mode, encoding='utf-8') as f:
            for deck in decks:
                # Convert to training format
                training_example = self._to_training_format(deck)
                if training_example:
                    f.write(json.dumps(training_example, ensure_ascii=False) + '\n')
    
    def _to_training_format(self, deck):
        """Convert parsed deck to instruction/output training format"""
        try:
            commander = deck['commander']
            theme = deck['theme']
            
            # Build instruction
            instruction = f"Build a Commander deck with {commander} focused on {theme}."
            
            # Build output (formatted decklist)
            output_lines = [
                f"Commander: {commander}",
                "",
                f"Deck Name: {deck['name']}",
                f"Theme: {theme}",
                f"Color Identity: {', '.join(deck['colors'])}",
                "",
                "Decklist:",
                ""
            ]
            
            # Group cards by category
            cards_by_category = {}
            for card in deck['cards']:
                category = card['category']
                if category not in cards_by_category:
                    cards_by_category[category] = []
                
                # Format with quantity (e.g., "29x Rat Colony" or "1x Sol Ring")
                quantity = card['quantity']
                card_name = card['name']
                cards_by_category[category].append(f"{quantity}x {card_name}")
            
            # Standard category order
            category_order = [
                'Commander', 'Creature', 'Instant', 'Sorcery', 
                'Enchantment', 'Artifact', 'Planeswalker', 'Battle', 'Land'
            ]
            
            # First output categories in preferred order
            for category in category_order:
                if category in cards_by_category:
                    cards = cards_by_category[category]
                    total_in_category = sum(int(c.split('x')[0]) for c in cards)
                    output_lines.append(f"{category}s ({total_in_category}):")
                    for card_line in sorted(cards):
                        output_lines.append(card_line)
                    output_lines.append("")
            
            # Then output any remaining categories not in the standard order
            for category in sorted(cards_by_category.keys()):
                if category not in category_order:
                    cards = cards_by_category[category]
                    total_in_category = sum(int(c.split('x')[0]) for c in cards)
                    output_lines.append(f"{category}s ({total_in_category}):")
                    for card_line in sorted(cards):
                        output_lines.append(card_line)
                    output_lines.append("")
            
            output = '\n'.join(output_lines)
            
            # Build metadata
            metadata = {
                'type': 'deck_building',
                'commander': commander,
                'theme': theme,
                'colors': deck['colors'],
                'source': 'archidekt',
                'url': deck['url'],
                'quality_score': deck['metadata']['views'],
                'views': deck['metadata']['views'],
                'tags': deck['metadata'].get('tags', [])
            }
            
            return {
                'instruction': instruction,
                'output': output,
                'metadata': metadata
            }
            
        except Exception as e:
            print(f"Error converting deck to training format: {e}")
            return None
    
    def scrape_by_themes_and_brackets(self, 
                                       themes_file='data/archidekt_themes.txt',
                                       decks_per_theme=50,
                                       min_views=50):
        """
        Scrape decks targeting specific themes and brackets for diversity
        
        This ensures we get a balanced dataset across:
        - Strategy types (Aggro, Combo, Control, etc.)
        - Tribal types (Dragons, Elves, Goblins, etc.)
        - Power brackets (1-5, from precon to cEDH)
        """
        print(f"\n{'='*60}")
        print(f"ARCHIDEKT THEME-BASED SCRAPER")
        print(f"{'='*60}")
        print(f"Target: {decks_per_theme} decks per theme")
        print(f"Min views: {min_views}\n")
        
        # Load themes from file
        themes = []
        themes_path = Path(themes_file)
        if themes_path.exists():
            with open(themes_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        themes.append(line)
        
        print(f"Loaded {len(themes)} themes from {themes_file}")
        
        all_decks = []
        scraped_ids = set()
        
        # Load existing decks to avoid duplicates
        output_file = self.output_dir / 'archidekt_decks.jsonl'
        if output_file.exists():
            print(f"\n📂 Loading existing decks from {output_file}")
            existing_count = 0
            with open(output_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        existing_count += 1
                        try:
                            deck_data = json.loads(line)
                            # Extract deck ID from URL in metadata
                            url = deck_data.get('metadata', {}).get('url', '')
                            if 'archidekt.com/decks/' in url:
                                deck_id = int(url.split('/decks/')[1].rstrip('/'))
                                scraped_ids.add(deck_id)
                        except:
                            pass
            print(f"   Found {existing_count} existing decks, will skip {len(scraped_ids)} IDs")
        
        # First, scrape by power brackets (evenly distributed)
        print(f"\n{'='*60}")
        print(f"PHASE 1: Power Bracket Distribution")
        print(f"{'='*60}")
        
        brackets = {
            1: "Precon Level",
            2: "Casual Optimized", 
            3: "Focused/Tuned",
            4: "High Power",
            5: "cEDH"
        }
        
        decks_per_bracket = decks_per_theme * 2  # More decks per bracket
        
        for bracket_num, bracket_name in brackets.items():
            print(f"\n[Bracket {bracket_num}] {bracket_name}")
            print(f"Target: {decks_per_bracket} decks")
            
            bracket_decks = []
            page = 1
            
            while len(bracket_decks) < decks_per_bracket and page <= 10:
                # Filter by bracket in the search query for efficiency
                results, _, _ = self.search_commander_decks(page=page, page_size=100, edh_bracket=bracket_num)
                
                if not results:
                    break
                
                for deck_summary in results:
                    if len(bracket_decks) >= decks_per_bracket:
                        break
                    
                    deck_id = deck_summary.get('id')
                    if deck_id in scraped_ids:
                        continue
                    
                    # Fetch full deck details
                    time.sleep(random.uniform(1.0, 2.0))
                    deck_data = self.get_deck_details(deck_id)
                    
                    if not deck_data:
                        continue
                    
                    # Bracket already filtered in search, but double-check
                    if deck_data.get('edhBracket') != bracket_num:
                        print(f"    ⚠️  Deck {deck_id} reports bracket {deck_data.get('edhBracket')} (expected {bracket_num})")
                        continue
                    
                    # Check view count
                    if deck_data.get('viewCount', 0) < min_views:
                        continue
                    
                    # Parse and validate
                    parsed = self.parse_deck(deck_data)
                    if not parsed:
                        continue
                    
                    total_cards = sum(card['quantity'] for card in parsed['cards'])
                    if total_cards < 98 or total_cards > 102:
                        continue
                    
                    # Extract tags for metadata
                    deck_tags = [tag['name'] for tag in deck_data.get('deckTags', [])]
                    parsed['metadata']['deck_tags'] = deck_tags
                    parsed['metadata']['bracket'] = bracket_num
                    
                    bracket_decks.append(parsed)
                    scraped_ids.add(deck_id)
                    all_decks.append(parsed)
                    
                    # Save incrementally after each deck
                    self._save_progress([parsed], append=True)
                    
                    print(f"  [{len(bracket_decks)}/{decks_per_bracket}] {parsed['name']} - Tags: {', '.join(deck_tags[:3])}")
                
                page += 1
            
            print(f"  ✓ Collected {len(bracket_decks)} decks for Bracket {bracket_num}\n")
        
        # Phase 2: Theme-specific scraping WITH TAG FILTERING (now available!)
        print(f"\n{'='*60}")
        print(f"PHASE 2: Theme+Bracket Collection")
        print(f"{'='*60}")
        print(f"Using Archidekt's deckTagName filter for targeted scraping")
        
        # Expanded theme list with strategies and tribal types
        priority_themes = [
            # Core strategies
            'Combo', 'Reanimator', 'Tokens', 'Aggro', 'Control', 'Stax',
            'Voltron', 'Aristocrats', 'Mill', 'Group Hug', 'Graveyard',
            'Spellslinger', '+1/+1 Counters', 'Budget', 'Cycling', 'Clones',
            'Artifacts', 'Lifegain', 'Modified Creatures', 'Self-Mill',
            'Flashback', 'Wheels', 'ETB Effects',
            
            # Tribal types (use exact Archidekt names)
            'Goblins', 'Elves', 'Birds', 'Nightmares', 'Spiders', 'Dragons',
            'Zombies', 'Vampires', 'Dinosaurs', 'Eldrazi', 'Humans', 'Angels',
            'Pirates', 'Merfolk', 'Cats', 'Wizards', 'Knights', 'Soldiers',
            'Slivers', 'Assassins', 'Faeries', 'Phyrexians', 'Demons',
            'Warlocks', 'Rats', 'Horrors', 'Spirits', 'Hydras', 'Fungus',
            'Myr', 'Rogues', 'Ninjas', 'Scouts', 'Insects', 'Plants',
            'Werewolves', 'Elementals', 'Warriors'
        ]
        
        decks_per_theme_bracket = 10  # 10 decks per theme/bracket (57 themes × 5 brackets × 10 = 2,850 total)
        
        for theme in priority_themes:
            for bracket_num in brackets.keys():
                theme_bracket_decks = []
                page = 1
                
                print(f"\n[{theme} @ Bracket {bracket_num}]")
                
                while len(theme_bracket_decks) < decks_per_theme_bracket and page <= 5:
                    results, _, _ = self.search_commander_decks(
                        page=page,
                        page_size=100,
                        edh_bracket=bracket_num,
                        deck_tag_name=theme
                    )
                    
                    if not results:
                        break
                    
                    for deck_summary in results:
                        if len(theme_bracket_decks) >= decks_per_theme_bracket:
                            break
                        
                        deck_id = deck_summary.get('id')
                        if deck_id in scraped_ids:
                            continue
                        
                        time.sleep(random.uniform(1.0, 2.0))
                        deck_data = self.get_deck_details(deck_id)
                        
                        if not deck_data:
                            continue
                        
                        if deck_data.get('viewCount', 0) < min_views:
                            continue
                        
                        parsed = self.parse_deck(deck_data)
                        if not parsed:
                            continue
                        
                        total_cards = sum(card['quantity'] for card in parsed['cards'])
                        if total_cards < 98 or total_cards > 102:
                            continue
                        
                        deck_tags = [tag['name'] for tag in deck_data.get('deckTags', [])]
                        parsed['metadata']['deck_tags'] = deck_tags
                        parsed['metadata']['bracket'] = bracket_num
                        
                        theme_bracket_decks.append(parsed)
                        scraped_ids.add(deck_id)
                        all_decks.append(parsed)
                        
                        self._save_progress([parsed], append=True)
                        print(f"  [{len(theme_bracket_decks)}/{decks_per_theme_bracket}] {parsed['name']}")
                    
                    page += 1
                
                print(f"  ✓ {len(theme_bracket_decks)} {theme} decks at Bracket {bracket_num}")
        
        # Summary
        print(f"\n{'='*60}")
        print(f"SCRAPING COMPLETE")
        print(f"{'='*60}")
        print(f"Total decks collected: {len(all_decks)}")
        print(f"Unique deck IDs: {len(scraped_ids)}")
        
        # Count by bracket
        bracket_counts = {}
        for deck in all_decks:
            bracket = deck['metadata'].get('bracket', 'Unknown')
            bracket_counts[bracket] = bracket_counts.get(bracket, 0) + 1
        
        print(f"\nDecks by bracket:")
        for bracket_num in sorted(bracket_counts.keys()):
            print(f"  Bracket {bracket_num}: {bracket_counts[bracket_num]} decks")
        
        # Count by tags
        tag_counts = {}
        for deck in all_decks:
            for tag in deck['metadata'].get('deck_tags', []):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        if tag_counts:
            print(f"\nTop 10 themes:")
            for tag, count in sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"  {tag}: {count} decks")
        
        return all_decks

if __name__ == '__main__':
    import sys
    
    scraper = ArchidektScraper()
    
    # Choose scraping mode
    mode = sys.argv[1] if len(sys.argv) > 1 else 'balanced'
    
    if mode == 'balanced':
        # RECOMMENDED: Scrape balanced across power brackets
        print("Mode: Balanced bracket scraping")
        decks = scraper.scrape_by_themes_and_brackets(
            decks_per_theme=50,  # 50 decks per theme
            min_views=50
        )
    elif mode == 'high-quality':
        # Alternative: Scrape only high-view decks
        print("Mode: High-quality deck scraping")
        decks = scraper.scrape_decks(num_decks=500, min_views=100)
    else:
        print(f"Unknown mode: {mode}")
        print("Usage: python scrape-archidekt-decks.py [balanced|high-quality]")
        sys.exit(1)
    
    print(f"\n✓ Scraping complete!")
    print(f"Total decks: {len(decks)}")
    
    # Show sample
    if decks:
        print(f"\nSample deck:")
        sample = decks[0]
        print(f"  Commander: {sample['commander']}")
        print(f"  Theme: {sample['theme']}")
        print(f"  Colors: {', '.join(sample['colors'])}")
        print(f"  Total cards: {sum(c['quantity'] for c in sample['cards'])}")
        print(f"  Views: {sample['metadata']['views']:,}")
        if 'bracket' in sample['metadata']:
            print(f"  Bracket: {sample['metadata']['bracket']}")
        if 'deck_tags' in sample['metadata']:
            print(f"  Tags: {', '.join(sample['metadata']['deck_tags'][:5])}")
