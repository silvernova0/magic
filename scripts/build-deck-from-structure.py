#!/usr/bin/env python3
"""
Build actual Commander decks from v3 structured JSON using Prisma database

This script:
1. Reads v3 JSON structure (from test-v3-model.py output)
2. Queries Prisma SQLite database for cards matching filters
3. Builds a 100-card deck
4. Validates the final deck
5. Outputs in standard deck format

Usage:
    python3 scripts/build-deck-from-structure.py generated_decks/v3_test/ur-dragon-tribal.json
"""

import json
import sqlite3
import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Set
import random

class ColorIdentityChecker:
    """Helper class for color identity operations"""
    
    @staticmethod
    def parse_color_identity(color_identity_str: str) -> Set[str]:
        """Parse color identity from database string (comma-separated or JSON)"""
        if not color_identity_str:
            return set()
        
        # Try JSON first
        if color_identity_str.startswith('['):
            try:
                colors = json.loads(color_identity_str)
                return set(colors) if colors else set()
            except:
                pass
        
        # Otherwise treat as comma-separated
        colors = color_identity_str.split(',')
        return set(c.strip() for c in colors if c.strip())
    
    @staticmethod
    def is_within_identity(card_colors: Set[str], commander_colors: Set[str]) -> bool:
        """Check if card's color identity is within commander's identity"""
        # Empty set (colorless) is always valid
        if not card_colors:
            return True
        
        # Card colors must be subset of commander colors
        return card_colors.issubset(commander_colors)


class DeckBuilder:
    def __init__(self, db_path="prisma/dev.db", user_collection: List[str] = None, avoid_salt_cards: bool = False, salt_threshold: float = 2.0):
        """Initialize connection to Prisma SQLite database
        
        Args:
            db_path: Path to SQLite database
            user_collection: Optional list of card names from user's collection
            avoid_salt_cards: Whether to filter out high-salt cards
            salt_threshold: Saltiness score threshold (cards above this are excluded)
        """
        self.db_path = db_path
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"Database not found: {db_path}\nRun 'npm run import:mtgjson:full' first")
        
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row  # Return rows as dicts
        self.color_checker = ColorIdentityChecker()
        self.commander_colors = set()  # Will be set when building deck
        self.user_collection = set(user_collection) if user_collection else None
        self.avoid_salt_cards = avoid_salt_cards
        self.salt_threshold = salt_threshold
        
        if self.user_collection:
            print(f"✅ Connected to database: {db_path}")
            print(f"🎯 Building from collection: {len(self.user_collection)} cards available")
        else:
            print(f"✅ Connected to database: {db_path}")
        
        if self.avoid_salt_cards:
            print(f"🧂 Avoiding salty cards (saltiness > {salt_threshold})")
    
    def get_commander_identity(self, commander_name: str) -> Set[str]:
        """Get commander's color identity"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT colorIdentity
            FROM Card
            WHERE name = ?
            LIMIT 1
        """, (commander_name,))
        
        row = cursor.fetchone()
        if row and row['colorIdentity']:
            return self.color_checker.parse_color_identity(row['colorIdentity'])
        
        return set()
    
    def is_card_legal(self, card_name: str) -> tuple[bool, str]:
        """
        Check if a card is legal for this commander deck.
        Returns (is_legal, reason_if_illegal)
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT colorIdentity, legalities, name
            FROM Card
            WHERE name = ?
            LIMIT 1
        """, (card_name,))
        
        row = cursor.fetchone()
        if not row:
            return (False, f"Card not found in database")
        
        row_dict = dict(row)
        
        # Check color identity
        card_colors = self.color_checker.parse_color_identity(row_dict.get('colorIdentity', ''))
        if not self.color_checker.is_within_identity(card_colors, self.commander_colors):
            commander_color_str = ','.join(sorted(self.commander_colors)) if self.commander_colors else 'C'
            card_color_str = ','.join(sorted(card_colors)) if card_colors else 'C'
            return (False, f"Color identity {card_color_str} not in commander's {commander_color_str}")
        
        # Check if banned in commander
        legalities_str = row_dict.get('legalities', '')
        if '"commander":"Banned"' in legalities_str:
            return (False, "Banned in Commander format")
        
        return (True, "")
    
    def count_mana_symbols(self, card_names: List[str]) -> Dict[str, int]:
        """
        Count mana symbols across a list of cards to determine color requirements.
        Returns dict like {'W': 12, 'U': 5, 'B': 8, 'R': 15, 'G': 20}
        """
        import re
        
        symbol_counts = {'W': 0, 'U': 0, 'B': 0, 'R': 0, 'G': 0}
        
        cursor = self.conn.cursor()
        for card_name in card_names:
            cursor.execute('SELECT manaCost FROM Card WHERE name = ?', (card_name,))
            row = cursor.fetchone()
            if row and row['manaCost']:
                mana_cost = row['manaCost']
                
                # Count each color symbol (e.g., {W}, {U}, {2}{G}{G})
                for color in ['W', 'U', 'B', 'R', 'G']:
                    # Count occurrences of {W}, {U}, etc.
                    pattern = f'{{{color}}}'
                    symbol_counts[color] += mana_cost.count(pattern)
                    
                    # Also count hybrid symbols like {W/U}, {2/W}, etc.
                    # For hybrid, count as 0.5 for each color
                    hybrid_patterns = [
                        f'{{{color}/W}}', f'{{{color}/U}}', f'{{{color}/B}}', 
                        f'{{{color}/R}}', f'{{{color}/G}}',
                        f'{{W/{color}}}', f'{{U/{color}}}', f'{{B/{color}}}',
                        f'{{R/{color}}}', f'{{G/{color}}}',
                        f'{{2/{color}}}'  # Hybrid with generic
                    ]
                    for pattern in hybrid_patterns:
                        if pattern in mana_cost:
                            symbol_counts[color] += 0.5
        
        return symbol_counts
    
    def query_cards(self, filters: List[Dict], limit: int = None, exclude_commander: str = None) -> List[Dict]:
        """
        Query cards based on v3 filters
        
        Filter examples:
        - {"types": ["Land"], "colors_within": ["W", "U"]}
        - {"tags": ["ramp"], "cmc_max": 3}
        - {"subtypes": ["Dragon"]}
        
        Args:
            filters: List of filter dictionaries
            limit: Maximum number of results
            exclude_commander: Commander name to exclude from results
        """
        # Build SQL query from filters
        conditions = []
        params = []
        
        for filter_obj in filters:
            filter_conditions = []
            
            # Specific card names (for auto-includes like Sol Ring)
            if 'names' in filter_obj:
                name_conditions = []
                for card_name in filter_obj['names']:
                    name_conditions.append("name = ?")
                    params.append(card_name)
                if name_conditions:
                    filter_conditions.append(f"({' OR '.join(name_conditions)})")
            
            # Type filtering
            if 'types' in filter_obj:
                type_conditions = []
                for card_type in filter_obj['types']:
                    type_conditions.append("typeLine LIKE ?")
                    params.append(f"%{card_type}%")
                if type_conditions:
                    filter_conditions.append(f"({' OR '.join(type_conditions)})")
            
            # Type exclusion filtering (e.g., exclude lands from ramp)
            if 'types_exclude' in filter_obj:
                for card_type in filter_obj['types_exclude']:
                    filter_conditions.append("typeLine NOT LIKE ?")
                    params.append(f"%{card_type}%")
            
            # Subtype filtering
            if 'subtypes' in filter_obj:
                subtype_conditions = []
                for subtype in filter_obj['subtypes']:
                    subtype_conditions.append("typeLine LIKE ?")
                    params.append(f"%{subtype}%")
                if subtype_conditions:
                    filter_conditions.append(f"({' OR '.join(subtype_conditions)})")
            
            # CMC filtering
            if 'cmc_max' in filter_obj:
                filter_conditions.append("cmc <= ?")
                params.append(filter_obj['cmc_max'])
            
            if 'cmc_min' in filter_obj:
                filter_conditions.append("cmc >= ?")
                params.append(filter_obj['cmc_min'])
            
            # EDHREC rank filtering (lower rank = more popular/expensive)
            if 'edhrec_rank_min' in filter_obj:
                # NULL ranks are treated as 99999 (unpopular cards)
                filter_conditions.append("(edhrecRank IS NULL OR edhrecRank >= ?)")
                params.append(filter_obj['edhrec_rank_min'])
            
            if 'edhrec_rank_max' in filter_obj:
                filter_conditions.append("edhrecRank <= ?")
                params.append(filter_obj['edhrec_rank_max'])
            
            # Rarity filtering
            if 'rarity_not' in filter_obj:
                rarity_conditions = []
                for rarity in filter_obj['rarity_not']:
                    rarity_conditions.append("rarity != ?")
                    params.append(rarity)
                if rarity_conditions:
                    filter_conditions.append(f"({' AND '.join(rarity_conditions)})")
            
            # Color identity filtering
            if 'colors_within' in filter_obj:
                allowed_colors = filter_obj['colors_within']
                # This is handled post-query - see below
                pass
            
            # Tags filtering (NOW USING tags COLUMN!)
            if 'tags' in filter_obj:
                tag_conditions = []
                for tag in filter_obj['tags']:
                    # Tags are stored as JSON array in database: ["ramp", "artifact"]
                    tag_conditions.append("tags LIKE ?")
                    params.append(f'%"{tag}"%')
                
                if tag_conditions:
                    # Use OR because card might have any of the requested tags
                    filter_conditions.append(f"({' OR '.join(tag_conditions)})")
            
            # Oracle text filtering (for strategy-specific cards like mill, lifegain)
            if 'oracle_text_includes' in filter_obj:
                oracle_conditions = []
                for text in filter_obj['oracle_text_includes']:
                    oracle_conditions.append("oracleText LIKE ?")
                    params.append(f'%{text}%')
                
                if oracle_conditions:
                    # Use OR because card might have any of the requested text patterns
                    filter_conditions.append(f"({' OR '.join(oracle_conditions)})")
            
            if filter_conditions:
                conditions.append(f"({' AND '.join(filter_conditions)})")
        
        # Combine all filter conditions with OR (any filter can match)
        if not conditions:
            where_clause = "1=1"  # Match all
        else:
            where_clause = ' OR '.join(conditions)
        
        # Build query
        query = f"""
            SELECT DISTINCT name, manaCost, cmc, typeLine, oracleText, colorIdentity, tags, legalities, edhrecRank, edhrecSaltiness
            FROM Card
            WHERE {where_clause}
            AND name NOT LIKE 'A-%'  -- Exclude Arena rebalanced cards
            AND (
                legalities LIKE '%commander%' 
                OR legalities LIKE '%legacy%' 
                OR legalities LIKE '%vintage%'
            )  -- Only include paper-legal cards
            AND legalities NOT LIKE '%"commander":"Banned"%'  -- Exclude commander-banned cards
        """
        
        # Add salt filtering if enabled
        if self.avoid_salt_cards:
            query += f" AND (edhrecSaltiness IS NULL OR edhrecSaltiness <= ?)"
            params.append(self.salt_threshold)
        
        # Exclude commander from appearing in the 99
        if exclude_commander:
            query += " AND name != ?"
            params.append(exclude_commander)
        
        # Priority ordering for quality cards (especially colorless ramp)
        priority_cards = [
            'Sol Ring', 'Basalt Monolith', 'Solemn Simulacrum', 'Burnished Hart',
            'Palladium Myr', 'Worn Powerstone', 'Foundry Inspector', 'Metalworker',
            'Thran Dynamo', 'Gilded Lotus', 'Hedron Archive', 'Mind Stone',
            'Thought Vessel', 'Commander''s Sphere', 'Chromatic Lantern',
            'Fellwar Stone', 'Everflowing Chalice', 'Hedron Crawler'
        ]
        
        # Quality-based ordering:
        # 1. Priority cards first (hardcoded staples)
        # 2. EDHREC rank (lower is better)
        # 3. Random for variety
        case_statements = []
        for idx, card in enumerate(priority_cards):
            # Escape single quotes for SQL
            escaped_card = card.replace("'", "''")
            case_statements.append(f"WHEN name = '{escaped_card}' THEN {idx}")
        
        # Order by: priority cards, then EDHREC rank (nulls last), then random
        if case_statements:
            query += f"""
                ORDER BY 
                    CASE {' '.join(case_statements)} ELSE 999 END,
                    CASE WHEN edhrecRank IS NULL THEN 99999 ELSE edhrecRank END,
                    RANDOM()
            """
        else:
            query += " ORDER BY CASE WHEN edhrecRank IS NULL THEN 99999 ELSE edhrecRank END, RANDOM()"
        
        if limit:
            # For colorless commanders, need more results since most cards have colors
            multiplier = 10 if not self.commander_colors else 3
            query += f" LIMIT {limit * multiplier}"  # Get extra to account for color filtering
        
        # Execute
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # Post-query filter by color identity AND land usability AND collection
        filtered_rows = []
        for row in rows:
            row_dict = dict(row)
            card_colors = self.color_checker.parse_color_identity(row_dict.get('colorIdentity', ''))
            card_name = row_dict.get('name', '')
            
            # Filter by user collection if provided
            if self.user_collection and card_name not in self.user_collection:
                continue
            
            # Check if card's colors are within commander's identity
            if not self.color_checker.is_within_identity(card_colors, self.commander_colors):
                continue
            
            # For colorless commanders, exclude cards that only work with color identity
            if not self.commander_colors:  # Colorless commander
                oracle_text = (row_dict.get('oracleText') or '').lower()
                # Cards that depend on commander's color identity are useless in colorless
                if any(phrase in oracle_text for phrase in [
                    "color in your commander's color identity",
                    "colors in your commander's color identity",
                    "mana of any color in your commander's color identity"
                ]):
                    continue
            
            # Additional check for lands: ensure they can produce mana in our colors
            if 'Land' in row_dict.get('typeLine', ''):
                if not self.is_land_usable(row_dict):
                    continue
            
            filtered_rows.append(row_dict)
            if limit and len(filtered_rows) >= limit:
                break
        
        return filtered_rows
    
    def is_land_usable(self, card: Dict) -> bool:
        """
        Check if a land is usable in the commander's color identity.
        
        A land is usable if:
        1. It produces mana in our colors (e.g., {R}, {T}: Add {R})
        2. It fetches lands of our types (e.g., "search for a Mountain")
        3. It produces colorless/any mana
        4. It has utility beyond mana production
        """
        oracle = (card.get('oracleText') or '').lower()
        type_line = (card.get('typeLine') or '').lower()
        name = card.get('name', '').lower()
        
        # If no oracle text, assume it's a basic land
        if not oracle:
            # Basic lands are always usable if they match our colors
            basics = {
                'plains': 'W',
                'island': 'U', 
                'swamp': 'B',
                'mountain': 'R',
                'forest': 'G'
            }
            for basic, color in basics.items():
                if basic in name:
                    return color in self.commander_colors
            return True  # Unknown land, allow it
        
        # Map color symbols and land types to colors
        color_mapping = {
            'W': {'symbols': ['{w}', 'white'], 'land_type': 'plains'},
            'U': {'symbols': ['{u}', 'blue'], 'land_type': 'island'},
            'B': {'symbols': ['{b}', 'black'], 'land_type': 'swamp'},
            'R': {'symbols': ['{r}', 'red'], 'land_type': 'mountain'},
            'G': {'symbols': ['{g}', 'green'], 'land_type': 'forest'}
        }
        
        # Check if land produces mana in our colors
        can_produce_our_colors = False
        for color in self.commander_colors:
            mapping = color_mapping[color]
            for symbol in mapping['symbols']:
                if f'add {symbol}' in oracle:
                    can_produce_our_colors = True
                    break
            if can_produce_our_colors:
                break
        
        # Check for fetch lands - must be able to fetch a land type we can use
        if 'search' in oracle and ('land' in oracle or 'card' in oracle):
            can_fetch_useful_land = False
            
            # Check if it can fetch any of our land types
            for color in self.commander_colors:
                land_type = color_mapping[color]['land_type']
                if land_type in oracle:
                    can_fetch_useful_land = True
                    break
            
            # If it's a fetch land but can't fetch our types, it's useless
            if not can_fetch_useful_land:
                # Check if it's a generic fetcher (any basic, any land, etc.)
                if 'basic land' not in oracle and 'any land' not in oracle and 'land card' not in oracle:
                    return False  # Specific fetch that doesn't fetch our types
        
        # Check for conditional lands that require specific card types
        # These are bad unless the deck has many of that type
        conditional_lands = {
            "serra's sanctum": 'enchantment',  # Taps for W per enchantment
            'gaea\'s cradle': 'creature',  # Taps for G per creature
            'tolarian academy': 'artifact',  # Taps for U per artifact (also banned)
            'cabal coffers': 'swamp',  # Based on swamps
            'nykthos': 'devotion',  # Based on devotion to colors
        }
        
        for land_name, card_type in conditional_lands.items():
            if land_name in name:
                # These lands need significant support - skip them for now
                # TODO: Could check deck composition to see if we have enough support
                return False
        
        # Check for lands that require synergy with specific other lands
        # These are useless without their companion cards
        # NOTE: These lands are handled by smart package inclusion in build_deck()
        # and should NOT be included individually
        synergy_land_sets = {
            # Urza's lands (Tron) - need all 3 to be good
            "urza's mine": ["urza's power plant", "urza's tower"],
            "urza's power plant": ["urza's mine", "urza's tower"],
            "urza's tower": ["urza's mine", "urza's power plant"],
            # Cloudpost lands - need multiples
            "cloudpost": ["glimmerpost", "vesuva"],
            "glimmerpost": ["cloudpost"],
            "vesuva": ["cloudpost"],  # Vesuva is best with Cloudpost
        }
        
        for trigger_land, required_lands in synergy_land_sets.items():
            if trigger_land in name:
                # Skip lands that require synergy pieces
                # These will be added as complete packages if strategy supports them
                return False
        
        # Additional pattern matching for conditional lands
        conditional_patterns = [
            ('for each enchantment', 'enchantment'),
            ('for each artifact', 'artifact'),
            ('equal to the number of artifacts', 'artifact'),
            ('equal to the number of enchantments', 'enchantment'),
            ('equal to the number of creatures', 'creature'),
            ('equal to your devotion', 'devotion'),
        ]
        
        for pattern, card_type in conditional_patterns:
            if pattern in oracle:
                # Skip conditional mana producers unless we can verify deck support
                # For now, conservatively exclude them
                return False
        
        # Colorless/utility lands
        utility_keywords = [
            'add {c}',
            'add one mana of any color',
            'add one mana of any type',
            'mana of any color',
            'draw a card',
            'scry',
            'surveil',
            'create',
            'token'
        ]
        
        has_utility = any(keyword in oracle for keyword in utility_keywords)
        
        # Land is usable if it produces our colors OR has utility OR produces colorless
        if can_produce_our_colors or has_utility:
            return True
        
        # If it only produces colors we can't use, exclude it
        for color in set(['W', 'U', 'B', 'R', 'G']) - self.commander_colors:
            mapping = color_mapping[color]
            produces_wrong_color = False
            for symbol in mapping['symbols']:
                if f'add {symbol}' in oracle:
                    produces_wrong_color = True
                    break
            
            if produces_wrong_color and not can_produce_our_colors and not has_utility:
                return False
        
        # Check for lands that reference specific land types we don't have
        # e.g., "Each land is a Forest" is useless if we can't run Forests
        land_type_references = {
            'plains': 'W',
            'island': 'U',
            'swamp': 'B',
            'mountain': 'R',
            'forest': 'G'
        }
        
        for land_type, color in land_type_references.items():
            if land_type in oracle and color not in self.commander_colors:
                # References a land type we can't use (e.g., Yavimaya in non-green deck)
                return False
        
        # Default to DISALLOWING unclear lands (conservative approach)
        # Only allow lands we explicitly understand
        return False
    
    def build_deck(self, structure: Dict) -> Dict:
        """
        Build a 100-card deck from v3 structure
        
        Returns:
            {
                'commander': str,
                'cards': List[str],  # 99 card names
                'categories': Dict[str, List[str]],  # Organized by category
                'total': int
            }
        """
        print(f"\n{'='*70}")
        print(f"Building deck: {structure.get('commander', 'Unknown')}")
        print(f"Strategy: {structure.get('strategy', 'Unknown')}")
        print(f"Power Level: {structure.get('power_level', '?')}")
        print(f"{'='*70}\n")
        
        commander = structure.get('commander')
        card_selection = structure.get('card_selection', {})
        
        # Get commander's color identity
        self.commander_colors = self.get_commander_identity(commander)
        
        # Apply additional color restrictions from UI if provided
        if 'color_restrictions' in structure:
            ui_colors = set(structure['color_restrictions'])
            if ui_colors:
                # Intersect with commander colors (can only restrict further, not expand)
                original_colors = self.commander_colors.copy()
                self.commander_colors = self.commander_colors.intersection(ui_colors)
                if self.commander_colors != original_colors:
                    print(f"⚠️  Color restrictions applied: {sorted(ui_colors)} → using intersection with commander identity")
        
        color_names = [{'W': 'White', 'U': 'Blue', 'B': 'Black', 'R': 'Red', 'G': 'Green'}.get(c, c) for c in sorted(self.commander_colors)]
        color_display = ', '.join(color_names) if color_names else 'Colorless'
        print(f"🎨 Commander Color Identity: {color_display} ({'/'.join(sorted(self.commander_colors)) if self.commander_colors else 'C'})\n")
        
        deck_cards = []
        categories = {}
        used_cards = set()  # Track cards already added to avoid duplicates across categories
        lands_from_other_categories = 0  # Track lands that snuck into non-land categories
        
        # PHASE 1: Query all non-land cards first to analyze mana requirements
        print(f"\n{'='*70}")
        print("PHASE 1: Querying non-land cards to analyze mana requirements")
        print(f"{'='*70}\n")
        
        non_land_cards = []
        for category, spec in card_selection.items():
            if category == 'lands':
                continue  # Skip lands for now
            
            if spec is None or not isinstance(spec, dict):
                continue
            
            count = spec.get('count', 0)
            filters = spec.get('filters', [])
            
            print(f"🔍 {category}: requesting {count} cards...")
            
            # Query more cards to account for deduplication
            # Use 5x multiplier for strategy-specific categories (mill_effects, lifegain, etc.)
            is_strategy_category = category in ['mill_effects', 'lifegain', 'voltron_equipment', 'combo_pieces', 'card_draw', 'removal']
            query_limit = count * 5 if is_strategy_category else count * 3
            
            cards = self.query_cards(filters, limit=query_limit, exclude_commander=commander)
            
            # FORCE exclude lands from non-land categories (safety check)
            cards = [c for c in cards if 'Land' not in c.get('typeLine', '')]
            
            available_cards = [c for c in cards if c['name'] not in used_cards]
            
            # Debug: Show dedup impact
            if len(cards) > len(available_cards):
                dedup_count = len(cards) - len(available_cards)
                print(f"   📊 Found {len(cards)} total, {dedup_count} already used, {len(available_cards)} available")
            
            selected = random.sample(available_cards, min(count, len(available_cards)))
            card_names = [c['name'] for c in selected]
            
            # Debug: Check if any lands snuck into non-land categories
            land_count = sum(1 for c in selected if 'Land' in c.get('typeLine', ''))
            if land_count > 0:
                lands_from_other_categories += land_count
                print(f"   ⚠️  WARNING: {land_count} lands found in {category} category!")
                for c in selected:
                    if 'Land' in c.get('typeLine', ''):
                        print(f"      - {c['name']} ({c.get('typeLine', 'Unknown type')})")
                print(f"      → Will reduce land count by {land_count}")
            
            used_cards.update(card_names)
            non_land_cards.extend(card_names)
            categories[category] = card_names
            
            print(f"   ✅ Found {len(selected)}/{count} cards")
        
        # PHASE 2: Analyze mana symbols for land distribution
        print(f"\n{'='*70}")
        print("PHASE 2: Analyzing mana requirements")
        print(f"{'='*70}\n")
        
        symbol_counts = self.count_mana_symbols(non_land_cards)
        total_symbols = sum(symbol_counts.values())
        
        if total_symbols > 0:
            print("Mana symbol distribution:")
            for color in ['W', 'U', 'B', 'R', 'G']:
                if color in self.commander_colors and symbol_counts[color] > 0:
                    pct = (symbol_counts[color] / total_symbols) * 100
                    color_name = {'W': 'White', 'U': 'Blue', 'B': 'Black', 'R': 'Red', 'G': 'Green'}[color]
                    print(f"  {color_name}: {symbol_counts[color]:.1f} symbols ({pct:.1f}%)")
        
        # Add all non-land cards to deck
        deck_cards.extend(non_land_cards)
        
        # PHASE 3: Build land package (basics + non-basics)
        print(f"\n{'='*70}")
        print("PHASE 3: Building mana base")
        print(f"{'='*70}\n")

        # Process lands from API request
        if 'lands' in card_selection:
            spec = card_selection['lands']
            if spec and isinstance(spec, dict):
                total_lands_requested = spec.get('count', 0)
                
                # Adjust for lands already added to other categories
                if lands_from_other_categories > 0:
                    print(f"🔧 Adjusting land count: {total_lands_requested} requested - {lands_from_other_categories} already added = {total_lands_requested - lands_from_other_categories} to add")
                    total_lands_requested = max(0, total_lands_requested - lands_from_other_categories)
                
                filters = spec.get('filters', [])
                
                # Get power level/bracket for mana base decisions
                bracket = structure.get('bracket', 3)
                power_level = structure.get('power_level', 5)
                num_colors = len(self.commander_colors)
                
                # Determine basic land ratio based on power level
                # High-power decks run very few basics (fetch lands + duals)
                # Budget/casual decks run more basics
                if bracket >= 4 or power_level >= 7:
                    # High-power/cEDH: minimal basics
                    if num_colors == 0:
                        basic_count = 10  # Colorless cEDH still needs some
                    elif num_colors == 1:
                        basic_count = 6   # Mono-color cEDH
                    elif num_colors == 2:
                        basic_count = 3   # 2-color cEDH
                    else:
                        basic_count = 2   # 3+ color cEDH (fetch targets only)
                    print(f"⚡ High-power deck (bracket {bracket}, power {power_level}) - {basic_count} basics, rest non-basics")
                elif bracket <= 2 or power_level <= 3:
                    # Budget decks: many basics, limited non-basics
                    if num_colors == 0:
                        basic_count = min(20, total_lands_requested - 10)
                    elif num_colors == 1:
                        basic_count = min(26, total_lands_requested - 9)
                    else:
                        basic_count = min(15, total_lands_requested - 10)
                    print(f"💰 Budget deck (bracket {bracket}, power {power_level}) - {basic_count} basics, ~10 non-basics")
                else:
                    # Mid-power: balanced mix
                    if num_colors == 0:
                        basic_count = min(15, total_lands_requested - 15)
                    elif num_colors == 1:
                        basic_count = min(18, total_lands_requested - 15)
                    else:
                        basic_count = min(12, total_lands_requested - 15)
                    print(f"⚖️  Mid-power deck (bracket {bracket}, power {power_level}) - {basic_count} basics, ~15 non-basics")
                
                # Calculate non-basic count
                non_basic_count = max(0, total_lands_requested - basic_count)
                
                # Build basic lands list
                color_to_basic = {'W': 'Plains', 'U': 'Island', 'B': 'Swamp', 'R': 'Mountain', 'G': 'Forest'}
                basic_lands = []
                
                if num_colors <= 1:
                    # Mono or colorless: all same basic
                    if num_colors == 0:
                        basic_lands = ["Wastes"] * basic_count
                    else:
                        basic_name = color_to_basic[list(self.commander_colors)[0]]
                        basic_lands = [basic_name] * basic_count
                    print(f"💎 {basic_count}x {basic_lands[0] if basic_lands else 'none'}")
                else:
                    # Multi-color: distribute based on mana symbol counts
                    if total_symbols > 0:
                        # Weight by actual mana requirements
                        for color in self.commander_colors:
                            if color in color_to_basic:
                                ratio = symbol_counts.get(color, 0) / total_symbols
                                count = round(basic_count * ratio)
                                basic_lands.extend([color_to_basic[color]] * count)
                        
                        # Adjust if rounding caused wrong total
                        while len(basic_lands) < basic_count:
                            max_color = max(self.commander_colors, key=lambda c: symbol_counts.get(c, 0))
                            basic_lands.append(color_to_basic[max_color])
                        
                        while len(basic_lands) > basic_count:
                            min_color = min(self.commander_colors, key=lambda c: symbol_counts.get(c, 0))
                            if color_to_basic[min_color] in basic_lands:
                                basic_lands.remove(color_to_basic[min_color])
                        
                        from collections import Counter
                        dist = Counter(basic_lands)
                        dist_str = ', '.join([f"{count}x {land}" for land, count in sorted(dist.items())])
                        print(f"💎 {dist_str}")
                    else:
                        # No mana symbols found, distribute evenly
                        basics = [color_to_basic[c] for c in self.commander_colors if c in color_to_basic]
                        basic_lands = [basics[i % len(basics)] for i in range(basic_count)]
                        print(f"💎 {basic_count} basics (even distribution)")
                
                # Add basics to deck
                deck_cards.extend(basic_lands)
                categories['lands'] = basic_lands.copy()
                
                # Query for non-basic lands
                print(f"🔍 Requesting {non_basic_count} non-basic lands...")
                if non_basic_count > 0:
                    land_cards = self.query_cards(filters, limit=non_basic_count * 3, exclude_commander=commander)
                    available_lands = [c for c in land_cards if c['name'] not in used_cards]
                    selected_lands = random.sample(available_lands, min(non_basic_count, len(available_lands)))
                    land_names = [c['name'] for c in selected_lands]
                    
                    used_cards.update(land_names)
                    deck_cards.extend(land_names)
                    categories['lands'].extend(land_names)
                    
                    print(f"   ✅ Added {len(selected_lands)}/{non_basic_count} non-basic lands")
                    print(f"   📊 Total lands: {len(categories['lands'])} ({basic_count} basics + {len(land_names)} non-basics)")
                else:
                    print(f"   ℹ️  No non-basic lands needed")
                    print(f"   📊 Total lands: {len(categories['lands'])} (all basics)")
        
        # All categories have been processed at this point
        # Phase 1 handled all non-land categories
        # Phase 3 added basic lands
        # Phase 4 added non-basic lands
        
        # Add priority cards if specified
        if 'priority_cards' in structure:
            priority = structure['priority_cards']
            if isinstance(priority, list):
                # Don't add commander to main deck
                priority_filtered = [c for c in priority if c != commander]
                print(f"\n🌟 Validating {len(priority_filtered)} priority cards...")
                
                # Validate each priority card for color identity and legality
                valid_priority = []
                for card in priority_filtered:
                    is_legal, reason = self.is_card_legal(card)
                    if is_legal:
                        valid_priority.append(card)
                    else:
                        print(f"   ⚠️  Rejected {card}: {reason}")
                
                # Smart insertion: Replace similar cards instead of just prepending
                existing_cards = set(deck_cards)
                new_priority = [c for c in valid_priority if c not in existing_cards]
                
                if new_priority:
                    print(f"   ✅ Intelligently inserting {len(new_priority)} priority cards...")
                    
                    # Get card details for priority cards to categorize them
                    priority_cards_data = {}
                    for card_name in new_priority:
                        cursor = self.conn.cursor()
                        cursor.execute("SELECT name, typeLine, tags FROM Card WHERE name = ?", (card_name,))
                        row = cursor.fetchone()
                        if row:
                            priority_cards_data[card_name] = dict(row)
                    
                    # Try to replace similar cards, otherwise add to deck
                    cards_inserted = 0
                    cards_replaced = 0
                    
                    for priority_card in new_priority:
                        if priority_card not in priority_cards_data:
                            continue
                        
                        p_data = priority_cards_data[priority_card]
                        p_type = p_data.get('typeLine', '')
                        p_tags = p_data.get('tags', '[]')
                        
                        # Determine card category
                        is_land = 'Land' in p_type
                        is_creature = 'Creature' in p_type
                        is_artifact = 'Artifact' in p_type
                        is_enchantment = 'Enchantment' in p_type
                        
                        # Try to find a similar card to replace (prefer non-priority cards)
                        replaced = False
                        
                        # Protect staples from being replaced
                        staples = ['Sol Ring', 'Arcane Signet', 'Command Tower']
                        
                        for i, existing_card in enumerate(deck_cards):
                            # Don't replace other priority cards or staples
                            if existing_card in valid_priority or existing_card in staples:
                                continue
                            
                            # Get existing card data
                            cursor = self.conn.cursor()
                            cursor.execute("SELECT name, typeLine, tags FROM Card WHERE name = ?", (existing_card,))
                            row = cursor.fetchone()
                            if not row:
                                continue
                            
                            e_data = dict(row)
                            e_type = e_data.get('typeLine', '')
                            
                            # Check if types match
                            type_match = False
                            if is_land and 'Land' in e_type:
                                type_match = True
                            elif is_creature and 'Creature' in e_type and 'Land' not in e_type:
                                type_match = True
                            elif is_artifact and 'Artifact' in e_type and 'Creature' not in e_type and 'Land' not in e_type:
                                type_match = True
                            elif is_enchantment and 'Enchantment' in e_type and 'Creature' not in e_type and 'Land' not in e_type:
                                type_match = True
                            elif not is_land and not is_creature and not is_artifact and not is_enchantment:
                                # Instant/Sorcery/Planeswalker
                                if 'Land' not in e_type and 'Creature' not in e_type and 'Artifact' not in e_type and 'Enchantment' not in e_type:
                                    type_match = True
                            
                            if type_match:
                                # Replace this card
                                print(f"      🔄 Replacing {existing_card} with {priority_card}")
                                deck_cards[i] = priority_card
                                cards_replaced += 1
                                replaced = True
                                break
                        
                        if not replaced:
                            # No suitable replacement found, add to deck
                            deck_cards.append(priority_card)
                            cards_inserted += 1
                    
                    print(f"   📊 {cards_replaced} cards replaced, {cards_inserted} cards added")
                else:
                    print(f"   ℹ️  All priority cards already in deck or invalid")
        
        # Ensure commander is not in the 99
        deck_cards = [c for c in deck_cards if c != commander]
        
        # Remove duplicates (keep first occurrence)
        seen = set()
        unique_cards = []
        for card in deck_cards:
            if card not in seen:
                seen.add(card)
                unique_cards.append(card)
        deck_cards = unique_cards
        
        # Adjust to exactly 99 cards
        if len(deck_cards) > 99:
            # Trim to 99
            trimmed_count = len(deck_cards)
            deck_cards = deck_cards[:99]
            print(f"\n⚠️  Trimmed to 99 cards (had {trimmed_count})")
            
            # Update categories to reflect trimmed cards
            final_cards_set = set(deck_cards)
            for category in categories:
                categories[category] = [c for c in categories[category] if c in final_cards_set]
            
        elif len(deck_cards) < 99:
            # Fill with basic lands
            lands_needed = 99 - len(deck_cards)
            print(f"\n⚠️  Deck has {len(deck_cards)} cards, need {lands_needed} more to reach 99")
            # Determine colors from commander - pick basics that match
            color_to_basic = {'W': 'Plains', 'U': 'Island', 'B': 'Swamp', 'R': 'Mountain', 'G': 'Forest'}
            available_basics = [color_to_basic[c] for c in self.commander_colors if c in color_to_basic]
            
            if not available_basics:
                available_basics = ["Wastes"]  # Colorless
            
            fill_lands = [available_basics[i % len(available_basics)] for i in range(lands_needed)]
            deck_cards.extend(fill_lands)
            print(f"⚠️  Filled with {lands_needed} basic lands to reach 99")
            
            # Add filled basics to categories (ungrouped will be shown as "Other")
        
        return {
            'commander': commander,
            'cards': deck_cards,
            'categories': categories,
            'total': len(deck_cards) + 1  # +1 for commander
        }
    
    def categorize_by_type(self, deck: Dict) -> Dict:
        """Categorize cards by their Magic card types for frontend display
        
        Returns a dict with:
        - commander: str
        - creatures: List[str]
        - instants: List[str]
        - sorceries: List[str]
        - artifacts: List[str]
        - enchantments: List[str]
        - planeswalkers: List[str]
        - lands: List[str]
        """
        commander = deck['commander']
        cards = deck['cards']
        
        categorized = {
            'commander': commander,
            'creatures': [],
            'instants': [],
            'sorceries': [],
            'artifacts': [],
            'enchantments': [],
            'planeswalkers': [],
            'lands': []
        }
        
        # Query each card's type from database
        cursor = self.conn.cursor()
        for card_name in cards:
            cursor.execute('SELECT typeLine FROM Card WHERE name = ?', (card_name,))
            row = cursor.fetchone()
            if not row:
                continue
            
            type_line = row['typeLine'].lower()
            
            # Categorize by primary type
            # Handle multiple types by priority (Artifact Creature goes to creatures, etc.)
            if 'creature' in type_line:
                categorized['creatures'].append(card_name)
            elif 'planeswalker' in type_line:
                categorized['planeswalkers'].append(card_name)
            elif 'instant' in type_line:
                categorized['instants'].append(card_name)
            elif 'sorcery' in type_line:
                categorized['sorceries'].append(card_name)
            elif 'enchantment' in type_line:
                categorized['enchantments'].append(card_name)
            elif 'artifact' in type_line:
                categorized['artifacts'].append(card_name)
            elif 'land' in type_line:
                categorized['lands'].append(card_name)
        
        return categorized
    
    def format_deck_output(self, deck: Dict, structure: Dict) -> str:
        """Format deck in standard Commander format without categories
        
        Outputs a simple list format easy to import into other tools.
        Basic lands can appear multiple times and should be counted together.
        Most other cards follow singleton rules (1x each).
        """
        from collections import Counter
        
        commander = deck['commander']
        cards = deck['cards']
        
        # Define basic lands
        basic_lands = {'Plains', 'Island', 'Swamp', 'Mountain', 'Forest', 'Wastes'}
        
        output = []
        output.append(f"Commander: {commander}\n")
        output.append(f"Deck Name: {structure.get('strategy', 'Commander')} - {commander}")
        output.append(f"Strategy: {structure.get('strategy', 'Unknown')}")
        output.append(f"Power Level: {structure.get('power_level', '?')}")
        output.append(f"Bracket: {structure.get('bracket', '?')}")
        output.append(f"\nDecklist:\n")
        
        # Count all cards (basics can appear multiple times)
        card_counts = Counter(cards)
        
        # Sort alphabetically for easy import
        for card in sorted(card_counts.keys()):
            count = card_counts[card]
            output.append(f"{count}x {card}")
        
        output.append(f"\nTotal: {deck['total']} cards")
        
        return '\n'.join(output)
    
    def close(self):
        """Close database connection"""
        self.conn.close()


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/build-deck-from-structure.py <v3_json_file>")
        print("\nExample:")
        print("  python3 scripts/build-deck-from-structure.py generated_decks/v3_test/ur-dragon-tribal.json")
        sys.exit(1)
    
    input_file = Path(sys.argv[1])
    
    if not input_file.exists():
        print(f"❌ File not found: {input_file}")
        sys.exit(1)
    
    # Load structure
    print(f"Loading structure from {input_file}...")
    with open(input_file) as f:
        structure = json.load(f)
    
    # Extract user collection if provided
    user_collection = structure.get('collection', None)
    if user_collection:
        print(f"📋 User collection detected: {len(user_collection)} cards")
    
    # Extract salt avoidance settings
    avoid_salt_cards = structure.get('avoid_salt_cards', False)
    salt_threshold = structure.get('salt_threshold', 2.0)
    
    # Build deck
    builder = DeckBuilder(
        user_collection=user_collection,
        avoid_salt_cards=avoid_salt_cards,
        salt_threshold=salt_threshold
    )
    
    try:
        deck = builder.build_deck(structure)
        
        # Format output
        deck_text = builder.format_deck_output(deck, structure)
        
        print(f"\n{'='*70}")
        print("FINAL DECK:")
        print(f"{'='*70}\n")
        print(deck_text)
        
        # Save output
        output_dir = Path('generated_decks/v3_executed')
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / f"{input_file.stem}_deck.txt"
        with open(output_file, 'w') as f:
            f.write(deck_text)
        
        print(f"\n💾 Deck saved to: {output_file}")
        
        # Categorize by card type for frontend display
        categorized_deck = builder.categorize_by_type(deck)
        
        # Print category summary
        print(f"\n{'='*70}")
        print("DECK BREAKDOWN BY TYPE:")
        print(f"{'='*70}")
        print(f"Commander: 1x {categorized_deck['commander']}")
        for category in ['creatures', 'instants', 'sorceries', 'artifacts', 'enchantments', 'planeswalkers', 'lands']:
            count = len(categorized_deck[category])
            if count > 0:
                print(f"{category.capitalize()}: {count}")
        total_categorized = sum(len(categorized_deck[cat]) for cat in ['creatures', 'instants', 'sorceries', 'artifacts', 'enchantments', 'planeswalkers', 'lands'])
        print(f"Total: {total_categorized + 1} cards (including commander)")
        print(f"{'='*70}\n")
        
        # Also save as JSON
        json_output = output_dir / f"{input_file.stem}_deck.json"
        with open(json_output, 'w') as f:
            json.dump(categorized_deck, f, indent=2)
        
        print(f"💾 JSON saved to: {json_output}")
        
    finally:
        builder.close()


if __name__ == '__main__':
    main()
