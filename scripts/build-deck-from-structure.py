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
import re
from synergy_engine import SynergyEngine
import sqlite3
import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Set
import random

# High power staples to ban in lower brackets (1-3)
HIGH_POWER_BANLIST = {
    'Mana Crypt', 'Mana Vault', 'Grim Monolith', 'Mox Diamond', 'Chrome Mox', 
    'Mox Opal', 'Jeweled Lotus', 'Lion\'s Eye Diamond', 'Gaea\'s Cradle',
    'Serra\'s Sanctum', 'Tolarian Academy', 'Timetwister', 'Wheel of Fortune',
    'Yawgmoth\'s Will', 'Necropotence', 'Ad Nauseam', 'Underworld Breach',
    'Thassa\'s Oracle', 'Demonic Consultation', 'Tainted Pact', 'Food Chain',
    'Dockside Extortionist', 'Rhystic Study', 'Mystic Remora', 'Cyclonic Rift',
    'Smothering Tithe', 'Teferi\'s Protection', 'Force of Will', 'Fierce Guardianship',
    'Deflecting Swat', 'Vampiric Tutor', 'Imperial Seal', 'Mana Drain',
    'Ancient Tomb', 'City of Traitors', 'Survival of the Fittest'
}

# Priority cards by bracket
PRIORITY_CARDS_BY_BRACKET = {
    '1': [ # Precon level - Budget staples
        'Sol Ring', 'Arcane Signet', 'Fellwar Stone', 'Commander\'s Sphere', 'Mind Stone',
        'Wayfarer\'s Bauble', 'Burnished Hart', 'Solemn Simulacrum',
        'Evolving Wilds', 'Terramorphic Expanse', 'Myriad Landscape',
        'Command Tower', 'Exotic Orchard', 'Path of Ancestry'
    ],
    '2': [ # Casual - Standard staples
        'Sol Ring', 'Arcane Signet', 'Fellwar Stone', 'Mind Stone',
        'Thought Vessel', 'Talisman of Progress', 'Talisman of Dominance', # Examples
        'Signet', # Generic check
        'Solemn Simulacrum', 'Burnished Hart', 'Swiftfoot Boots',
        'Lightning Greaves', 'Command Tower', 'Exotic Orchard'
    ],
    '3': [ # Optimized - Better rocks
        'Sol Ring', 'Arcane Signet', 'Fellwar Stone', 'Talisman', 'Signet',
        'Three Visits', 'Nature\'s Lore', 'Farseek', 'Cultivate', 'Kodama\'s Reach',
        'Lightning Greaves', 'Swiftfoot Boots', 'Skullclamp'
    ],
    '4': [ # High Power - Fast mana starts appearing
        'Sol Ring', 'Mana Crypt', 'Mana Vault', 'Chrome Mox', 'Mox Diamond',
        'Arcane Signet', 'Fellwar Stone', 'Dockside Extortionist',
        'Rhystic Study', 'Mystic Remora', 'Smothering Tithe', 'Esper Sentinel'
    ],
    '5': [ # cEDH - All the fast mana
        'Sol Ring', 'Mana Crypt', 'Mana Vault', 'Grim Monolith', 'Mox Diamond',
        'Chrome Mox', 'Mox Opal', 'Lotus Petal', 'Jeweled Lotus', 'Lion\'s Eye Diamond',
        'Gemstone Caverns', 'Ancient Tomb', 'City of Traitors', 'Arcane Signet', 'Fellwar Stone'
    ]
}


def normalize_card_name(card_name: str) -> str:
    """
    Normalize card names to handle split cards, MDFCs, and other variants.
    
    Examples:
        "Command Tower // Command Tower" -> "Command Tower"
        "Fire // Ice" -> "Fire // Ice" (keep split cards as-is)
        "Valki, God of Lies // Tibalt, Cosmic Impostor" -> "Valki, God of Lies // Tibalt, Cosmic Impostor"
    
    For cards where both sides are identical (like "Command Tower // Command Tower"),
    we normalize to just the front face.
    """
    if not card_name or '//' not in card_name:
        return card_name
    
    # Split on //
    parts = [p.strip() for p in card_name.split('//')]
    
    # If both sides are identical, use just one
    if len(parts) == 2 and parts[0] == parts[1]:
        return parts[0]
    
    # Otherwise keep the full name (for actual split cards)
    return card_name


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
                # Handle single quotes which aren't valid JSON
                json_str = color_identity_str.replace("'", '"')
                colors = json.loads(json_str)
                return set(colors) if colors else set()
            except:
                pass
        
        # Otherwise treat as comma-separated (and clean up)
        colors = color_identity_str.replace('[', '').replace(']', '').replace('"', '').replace("'", '').split(',')
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
    def __init__(self, db_path='/home/social/magicapp/prisma/dev.db', user_collection: List[str] = None, avoid_salt_cards: bool = False, salt_threshold: float = 2.0):

        if not os.path.exists(db_path):
            print(f"ERROR: DB file not found at {db_path}")
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
        self.synergy_engine = SynergyEngine(db_path=db_path)
        
        # Load deck stats if available
        self.deck_stats = {}
        try:
            if os.path.exists('data/deck_stats.json'):
                with open('data/deck_stats.json', 'r') as f:
                    self.deck_stats = json.load(f)
                print("📊 Loaded deck statistics from data/deck_stats.json")
        except Exception as e:
            print(f"⚠️ Failed to load deck stats: {e}")
        self.commander_colors = set()  # Will be set when building deck
        self.user_collection = set(user_collection) if user_collection else None
        self.avoid_salt_cards = avoid_salt_cards
        self.salt_threshold = salt_threshold
        self.tribal_type = None  # Store tribal type for strict filtering (e.g. "Spirit")
        
        # Load land count reference data
        self.land_reference = self._load_land_reference()
        
        if self.user_collection:
            print(f"✅ Connected to database: {db_path}")
            print(f"🎯 Building from collection: {len(self.user_collection)} cards available")
        else:
            print(f"✅ Connected to database: {db_path}")
        
        if self.avoid_salt_cards:
            print(f"🧂 Avoiding salty cards (saltiness > {salt_threshold})")
    
    def _load_land_reference(self) -> Dict:
        """Load land count reference data from training analysis"""
        ref_path = Path('data/land_count_reference.json')
        if ref_path.exists():
            try:
                with open(ref_path, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        # Fallback defaults if file doesn't exist
        return {
            'commanders': {},
            'bracket_defaults': {
                '2': {'min': 36, 'max': 38, 'avg': 36},
                '3': {'min': 34, 'max': 36, 'avg': 34},
                '4': {'min': 30, 'max': 34, 'avg': 30},
                '5': {'min': 28, 'max': 32, 'avg': 28}
            },
            'global_default': {'min': 32, 'max': 38, 'avg': 35}
        }
    
    def get_land_range(self, commander: str, bracket: int) -> tuple[int, int]:
        """Get recommended land count range for commander and bracket
        
        Returns (min, max) tuple based on:
        1. Commander-specific data from training (if available)
        2. Bracket-wide defaults from training
        3. Global defaults as last resort
        """
        bracket_str = str(bracket)
        
        # Try commander-specific data first
        if commander in self.land_reference['commanders']:
            commander_data = self.land_reference['commanders'][commander]
            if bracket_str in commander_data:
                stats = commander_data[bracket_str]
                print(f"📊 Using {commander} training data (bracket {bracket}): {stats['min']}-{stats['max']} lands (avg: {stats['avg']}, {stats['samples']} samples)")
                return (stats['min'], stats['max'])
        
        # Fall back to bracket defaults
        if bracket_str in self.land_reference['bracket_defaults']:
            stats = self.land_reference['bracket_defaults'][bracket_str]
            print(f"📊 Using bracket {bracket} default: {stats['min']}-{stats['max']} lands (avg: {stats['avg']}, {stats['samples']} samples)")
            return (stats['min'], stats['max'])
        
        # Last resort: global default
        stats = self.land_reference['global_default']
        print(f"📊 Using global default: {stats['min']}-{stats['max']} lands (avg: {stats['avg']})")
        return (stats['min'], stats['max'])
    
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
            SELECT colorIdentity, legalities, name, typeLine, oracleText
            FROM Card
            WHERE name = ?
            LIMIT 1
        """, (card_name,))
        
        row = cursor.fetchone()
        if not row:
            return (False, f"Card not found in database")
        
        row_dict = dict(row)
        
        # Check user collection if filtering by collection
        if self.user_collection:
            # Basic lands are always available (unlimited in Commander)
            basic_land_names = {
                'Plains', 'Island', 'Swamp', 'Mountain', 'Forest', 'Wastes',
                'Snow-Covered Plains', 'Snow-Covered Island', 'Snow-Covered Swamp',
                'Snow-Covered Mountain', 'Snow-Covered Forest', 'Snow-Covered Wastes'
            }
            
            if card_name not in self.user_collection and card_name not in basic_land_names:
                return (False, f"Card not in your collection")
        
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
            
        # Check land usability (fetches, etc.)
        if 'Land' in row_dict.get('typeLine', ''):
            if not self.is_land_usable(row_dict):
                return (False, "Land produces/fetches off-color mana")
        
        # Check tribal enforcement for priority creatures
        # If this is a tribal deck, priority creatures MUST match the tribe (unless it's the commander)
        if self.tribal_type and 'Creature' in row_dict.get('typeLine', ''):
            # Skip check for commander (handled elsewhere, and commander might be different type e.g. Human Advisor for Spirits)
            if normalize_card_name(card_name) != normalize_card_name(self.commander_name):
                type_line = row_dict.get('typeLine', '')
                # Check if type line contains the tribal type
                # Use word boundary check or simple inclusion? Simple inclusion is usually fine for Magic types
                if self.tribal_type not in type_line:
                    # Double check oracle text for "Changeling"
                    oracle_text = row_dict.get('oracleText', '')
                    if 'Changeling' not in oracle_text:
                        return (False, f"Creature does not match tribal type '{self.tribal_type}'")
        
        return (True, "")

    def is_card_budget_friendly(self, card_row: sqlite3.Row, bracket: int) -> bool:
        """Check if card fits budget constraints for the bracket"""
        # Bracket 1-2: Budget/Casual (Cap ~$20, strict cap ~$5 for Bracket 1)
        if bracket > 2:
            return True
            
        try:
            prices_str = card_row['prices']
            if not prices_str:
                return True # Assume okay if no price data (or maybe exclude?)
                
            prices = json.loads(prices_str)
            usd = float(prices.get('usd') or 0)
            
            # Bracket 1: Precon level - very strict
            if bracket == 1:
                return usd <= 5.0
            
            # Bracket 2: Casual - avoid very expensive cards
            if bracket == 2:
                return usd <= 20.0
                
            return True
        except:
            return True # Default to allow on error

    
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
    
    def query_cards(self, filters: List[Dict], limit: int = None, exclude_commander: str = None, bracket: int = 3) -> List[Dict]:
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
            if 'names' in filter_obj and filter_obj['names'] is not None:
                name_conditions = []
                for card_name in filter_obj['names']:
                    name_conditions.append("name = ?")
                    params.append(card_name)
                if name_conditions:
                    filter_conditions.append(f"({' OR '.join(name_conditions)})")
            
            # Type filtering
            if 'types' in filter_obj and filter_obj['types'] is not None:
                type_conditions = []
                for card_type in filter_obj['types']:
                    type_conditions.append("typeLine LIKE ?")
                    params.append(f"%{card_type}%")
                if type_conditions:
                    filter_conditions.append(f"({' OR '.join(type_conditions)})")
            
            # Type exclusion filtering (e.g., exclude lands from ramp)
            if 'types_exclude' in filter_obj and filter_obj['types_exclude'] is not None:
                for card_type in filter_obj['types_exclude']:
                    filter_conditions.append("typeLine NOT LIKE ?")
                    params.append(f"%{card_type}%")
            
            # Subtype filtering
            if 'subtypes' in filter_obj and filter_obj['subtypes'] is not None:
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
            if 'rarity_not' in filter_obj and filter_obj['rarity_not'] is not None:
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
            if 'tags' in filter_obj and filter_obj['tags'] is not None:
                tag_conditions = []
                for tag in filter_obj['tags']:
                    # Tags are stored as JSON array in database: ["ramp", "artifact"]
                    tag_conditions.append("tags LIKE ?")
                    params.append(f'%"{tag}"%')
                
                if tag_conditions:
                    # Use OR because card might have any of the requested tags
                    filter_conditions.append(f"({' OR '.join(tag_conditions)})")
            
            # Oracle text filtering (for strategy-specific cards like mill, lifegain)
            if 'oracle_text_includes' in filter_obj and filter_obj['oracle_text_includes'] is not None:
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
            SELECT DISTINCT name, manaCost, cmc, typeLine, oracleText, colorIdentity, tags, legalities, edhrecRank, edhrecSaltiness, prices
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

        # CRITICAL: Exclude duplicate card variants (e.g., "Command Tower // Command Tower")
        # These are separate database entries but represent the same card
        # Use TRIM() to handle whitespace around the // separator
        query += " AND (name NOT LIKE '%//%' OR (name LIKE '%//%' AND TRIM(SUBSTR(name, 1, INSTR(name, '//')-1)) != TRIM(SUBSTR(name, INSTR(name, '//')+2))))"
        
        # Add salt filtering if enabled
        if self.avoid_salt_cards:
            query += f" AND (edhrecSaltiness IS NULL OR edhrecSaltiness <= ?)"
            params.append(self.salt_threshold)
        
        # Exclude commander from appearing in the 99
        if exclude_commander:
            query += " AND name != ?"
            params.append(exclude_commander)
        
        # Priority ordering for quality cards (especially colorless ramp)
        # Select priority list based on bracket
        bracket_str = str(bracket)
        priority_cards = PRIORITY_CARDS_BY_BRACKET.get(bracket_str, PRIORITY_CARDS_BY_BRACKET['3'])
        
        # For Brackets 1-2, ensure we don't accidentally include high power cards via other filters
        if bracket <= 2:
            # Add exclusion for banlist
            placeholders = ','.join(['?'] * len(HIGH_POWER_BANLIST))
            query += f" AND name NOT IN ({placeholders})"
            params.extend(list(HIGH_POWER_BANLIST))
        
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
            
            # Basic lands are always available (unlimited in Commander)
            basic_land_names = {
                'Plains', 'Island', 'Swamp', 'Mountain', 'Forest', 'Wastes',
                'Snow-Covered Plains', 'Snow-Covered Island', 'Snow-Covered Swamp',
                'Snow-Covered Mountain', 'Snow-Covered Forest', 'Snow-Covered Wastes'
            }
            
            # Filter by user collection if provided (but always allow basic lands)
            if self.user_collection and card_name not in self.user_collection:
                # Exempt basic lands - they're unlimited in Commander
                if card_name not in basic_land_names:
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

            # Check budget/price constraints
            if not self.is_card_budget_friendly(row, bracket):
                # print(f"💰 Filtered expensive card: {card_name} (Bracket {bracket})")
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
            if color not in color_mapping:
                continue
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
                if color not in color_mapping:
                    continue
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

        # Explicit check for Urborg, Tomb of Yawgmoth
        if "urborg, tomb of yawgmoth" in name:
            # Only useful if deck includes Black (to make use of swamps) or has swampwalk
            # For general purpose, require Black identity
            return 'B' in self.commander_colors
            
        # Explicit check for Yavimaya, Cradle of Growth
        if "yavimaya, cradle of growth" in name:
            # Only useful if deck includes Green
            return 'G' in self.commander_colors
        
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
    
    def smart_color_sample(self, cards: List[Dict], count: int, commander_colors: set) -> List[Dict]:
        """
        Selects cards while attempting to balance color representation.
        """
        if not cards or count <= 0:
            return []
            
        if count >= len(cards):
            return cards
            
        # If mono-color, random is fine
        if len(commander_colors) <= 1:
            return random.sample(cards, count)
            
        # Bucket cards by color
        # We use a simplified bucketing: 
        # - One bucket per commander color
        # - One bucket for "Multicolor" (2+ colors)
        # - One bucket for "Colorless"
        buckets = {c: [] for c in commander_colors}
        buckets['Multi'] = []
        buckets['Colorless'] = []
        
        for card in cards:
            # Parse colors from JSON string or list
            c_colors = card.get('colors', [])
            if isinstance(c_colors, str):
                import json
                try:
                    c_colors = json.loads(c_colors)
                except:
                    c_colors = []
            
            if not c_colors:
                buckets['Colorless'].append(card)
            elif len(c_colors) > 1:
                buckets['Multi'].append(card)
            else:
                # Mono-color
                color = c_colors[0]
                if color in buckets:
                    buckets[color].append(card)
                else:
                    # Should not happen if filtered correctly, but fallback
                    buckets['Colorless'].append(card)
                    
        # Selection Strategy:
        # 1. Prioritize Multicolor cards (they are often strong/thematic)
        # 2. Evenly distribute among mono-colors
        # 3. Fill with Colorless
        
        selected = []
        
        # 1. Take some multicolor (up to 30% of target)
        multi_target = int(count * 0.3)
        if buckets['Multi']:
            taken = random.sample(buckets['Multi'], min(len(buckets['Multi']), multi_target))
            selected.extend(taken)
            
        # 2. Round-robin mono colors
        remaining_slots = count - len(selected)
        mono_colors = sorted(list(commander_colors))
        
        while remaining_slots > 0:
            added_this_round = False
            for color in mono_colors:
                if remaining_slots <= 0:
                    break
                
                if buckets[color]:
                    # Take one from this color
                    card = buckets[color].pop(random.randint(0, len(buckets[color]) - 1))
                    selected.append(card)
                    remaining_slots -= 1
                    added_this_round = True
            
            # If we went through all colors and didn't add anything, we are out of balanced mono cards
            if not added_this_round:
                break
                
        # 3. Fill remaining with anything left (Multi, Colorless, or remaining Mono)
        if remaining_slots > 0:
            pool = []
            pool.extend(buckets['Multi']) # Remaining multi
            pool.extend(buckets['Colorless'])
            for c in mono_colors:
                pool.extend(buckets[c])
            
            if pool:
                selected.extend(random.sample(pool, min(len(pool), remaining_slots)))
                
        return selected
    
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
        
        self.structure = structure
        self.commander_name = structure.get('commander', 'Unknown Commander')
        self.tribal_type = None
        
        # Detect tribal strategy
        strategy = structure.get('strategy', '').lower()
        tribal_match = re.search(r'(?:tribal|kindred)[-_\s]+(\w+)', strategy)
        if tribal_match:
            # Normalize type: "spirits" -> "Spirit", "elves" -> "Elf"
            raw_type = tribal_match.group(1)
            # Handle common irregular plurals
            irregular_plurals = {
                'elves': 'Elf',
                'wolves': 'Wolf',
                'dwarves': 'Dwarf',
                'merfolk': 'Merfolk' # Merfolk is same singular/plural
            }
            if raw_type in irregular_plurals:
                self.tribal_type = irregular_plurals[raw_type]
            else:
                # Standard de-pluralization
                self.tribal_type = raw_type.rstrip('s').capitalize()
            
            print(f"   ⚔️  Tribal Strategy Detected: Enforcing '{self.tribal_type}' for priority creatures")
        
        # 1. Analyze Commander Colors
        if 'color_restrictions' in structure:
            self.commander_colors = set(structure['color_restrictions'])
            print(f"🎨 Using provided color restrictions: {self.commander_colors}")
        else:
            # Fallback: Fetch from DB
            print(f"⚠️  No color restrictions provided, fetching from DB for {commander}...")
            self.commander_colors = self.get_commander_identity(commander)
            print(f"🎨 Fetched commander colors: {self.commander_colors}")
            
        # Determine bracket
        # Determine bracket
        self.bracket = structure.get('bracket', 2)
        
        color_names = [{'W': 'White', 'U': 'Blue', 'B': 'Black', 'R': 'Red', 'G': 'Green'}.get(c, c) for c in sorted(self.commander_colors)]
        color_display = ', '.join(color_names) if color_names else 'Colorless'
        print(f"🎨 Commander Color Identity: {color_display} ({'/'.join(sorted(self.commander_colors)) if self.commander_colors else 'C'})\n")
        
        deck_cards = []
        categories = {}
        final_cards_set = set()
        used_cards = final_cards_set  # Alias for backward compatibility
        lands_from_other_categories = 0  # Track lands that snuck into non-land categories
        
        # VALIDATE CARD ALLOCATION TOTALS TO 99
        total_allocated = sum(spec.get('count', 0) for spec in card_selection.values() if isinstance(spec, dict))
        print(f"📊 MODEL CARD ALLOCATION:")
        for category, spec in sorted(card_selection.items()):
            if isinstance(spec, dict):
                count = spec.get('count', 0)
                print(f"   {category}: {count} cards")
        print(f"   {'='*50}")
        print(f"   TOTAL: {total_allocated} cards (target: 99)\n")
        
        if total_allocated < 90:
            print(f"⚠️  WARNING: Model only allocated {total_allocated}/99 cards!")
            print(f"⚠️  This will cause {99 - total_allocated} basic lands to be added as filler\n")
        elif total_allocated > 99:
            print(f"⚠️  WARNING: Model allocated {total_allocated}/99 cards - will trim extras!\n")
        
        # PHASE 1: Query all non-land cards first to analyze mana requirements
        print(f"\n{'='*70}")
        print("PHASE 1: Querying non-land cards to analyze mana requirements")
        print(f"{'='*70}\n")
        
        # 1.5 Inject Tribal Filter into 'creatures' category
        if self.tribal_type and 'creatures' in card_selection:
            spec = card_selection['creatures']
            if isinstance(spec, dict):
                filters = spec.get('filters', [])
                # Check if we already have a subtype filter
                has_subtype = False
                for f in filters:
                    if 'subtypes' in f:
                        # Ensure our tribe is in there
                        if self.tribal_type not in f['subtypes']:
                            f['subtypes'].append(self.tribal_type)
                        has_subtype = True
                        break
                
                # If no subtype filter exists, add one
                if not has_subtype:
                    filters.append({'subtypes': [self.tribal_type]})
                    print(f"   🧬 Injected '{self.tribal_type}' subtype filter into 'creatures' category")
                
                spec['filters'] = filters

        # Track Planeswalkers to prevent flood
        planeswalker_count = 0
        max_planeswalkers = 3
        if 'superfriends' in strategy or 'planeswalker' in strategy:
            max_planeswalkers = 25
            print(f"   🦸 Superfriends strategy detected: allowing up to {max_planeswalkers} Planeswalkers")
        else:
            print(f"   🛡️  Standard strategy: capping Planeswalkers at {max_planeswalkers}")

        non_land_cards = []
        for category, spec in card_selection.items():
            if category == 'lands':
                continue  # Skip lands for now
            
            if spec is None or not isinstance(spec, dict):
                continue
            
            count = spec.get('count', 0)
            filters = spec.get('filters', [])
            print(f"   🔎 Processing {category} (count: {spec.get('count')}) with filters: {filters}")
            
            print(f"🔍 {category}: requesting {count} cards...")
            
            # Query more cards to account for deduplication
            # Use 5x multiplier for strategy-specific categories (mill_effects, lifegain, etc.)
            is_strategy_category = category in ['mill_effects', 'lifegain', 'voltron_equipment', 'combo_pieces', 'card_draw', 'removal']
            query_limit = count * 5 if is_strategy_category else count * 3
            
            cards = self.query_cards(filters, limit=query_limit, exclude_commander=commander, bracket=structure.get('bracket', 3))
            
            # FORCE exclude lands from non-land categories (safety check)
            cards = [c for c in cards if 'Land' not in c.get('typeLine', '')]
            
            available_cards = [c for c in cards if c['name'] not in used_cards]
            
            # Debug: Show dedup impact
            if len(cards) > len(available_cards):
                dedup_count = len(cards) - len(available_cards)
                print(f"   📊 Found {len(cards)} total, {dedup_count} already used, {len(available_cards)} available")
            
            # 1.6 Inject "Lords" (Tribal Anthems)
            if self.tribal_type and category == 'creatures':
                print(f"   👑 Searching for {self.tribal_type} Lords...")
                lord_filters = [{
                    'subtypes': [self.tribal_type],
                    'oracle_text_includes': [f"other {self.tribal_type}", f"other {self.tribal_type}s"]
                }]
                # Query for lords
                lords = self.query_cards(lord_filters, limit=20, exclude_commander=commander, bracket=structure.get('bracket', 3))
                lords = [c for c in lords if 'Creature' in c.get('typeLine', '') and c['name'] not in used_cards]
                
                # Take up to 6 lords
                num_lords = min(6, len(lords))
                selected_lords = self.smart_color_sample(lords, num_lords, self.commander_colors)
                
                if selected_lords:
                    print(f"   ✨ Found {len(selected_lords)} Lords: {[c['name'] for c in selected_lords]}")
                    # Add to deck immediately
                    for card in selected_lords:
                        deck_cards.append(card['name'])
                        final_cards_set.add(card['name'])
                        categories.setdefault('creatures', []).append(card['name'])
                        used_cards.add(card['name'])
                    
                    # Reduce the main creature count request
                    count = max(0, count - len(selected_lords))
                    print(f"   📉 Reduced generic creature count to {count}")

            # Smart Color Sampling instead of random
            selected = self.smart_color_sample(available_cards, min(count, len(available_cards)), self.commander_colors)
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
            
            used_cards.update([c['name'] for c in selected])
            # Filter for tribal compliance AND Planeswalker caps
            valid_cards = []
            for card in selected:
                # Enforce category-specific type restrictions
                if category == 'creatures' and 'Creature' not in card.get('typeLine', ''):
                    print(f"      ❌ Rejected {card['name']} (Not a Creature)")
                    continue
                
                # Check tribal enforcement for ANY creature (even in artifacts/enchantments)
                if self.tribal_type and 'Creature' in card.get('typeLine', ''):
                    if self.tribal_type not in card.get('typeLine', '') and 'Changeling' not in card.get('oracleText', ''):
                         print(f"      ❌ Rejected {card['name']} (Not a {self.tribal_type})")
                         continue

                # Check Planeswalker Cap
                if 'Planeswalker' in card.get('typeLine', ''):
                    if planeswalker_count >= max_planeswalkers:
                        print(f"      ❌ Rejected {card['name']} (Planeswalker limit reached)")
                        continue
                    planeswalker_count += 1

                valid_cards.append(card)

            # Add to deck (NAMES ONLY)
            card_names = [c['name'] for c in valid_cards]
            deck_cards.extend(card_names)
            for card in valid_cards:
                final_cards_set.add(card['name'])
                categories.setdefault(category, []).append(card['name'])
                
            print(f"   ✅ Added {len(valid_cards)} cards to {category}")

        
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
                
                # Get power level/bracket for mana base decisions
                bracket = structure.get('bracket', 3)
                power_level = structure.get('power_level', 5)
                num_colors = len(self.commander_colors)
                
                # GET RECOMMENDED LAND RANGE FROM TRAINING DATA
                commander_name = structure.get('commander', '')
                MIN_LANDS, MAX_LANDS = self.get_land_range(commander_name, bracket)
                
                # GLOBAL SAFETY FLOOR: Unless it's cEDH (Bracket 5), ensure at least 33 lands
                # This takes precedence over historical data to prevent mana screw
                if bracket < 5:
                    ABSOLUTE_MIN = 33
                    if MIN_LANDS < ABSOLUTE_MIN:
                        MIN_LANDS = ABSOLUTE_MIN
                    # Don't let MAX cap below the safety floor
                    if MAX_LANDS < ABSOLUTE_MIN:
                        MAX_LANDS = ABSOLUTE_MIN
                
                # Force minimum land count if model requests too few
                if total_lands_requested < MIN_LANDS:
                    print(f"⚠️  Model only allocated {total_lands_requested} lands, enforcing minimum of {MIN_LANDS}")
                    total_lands_requested = MIN_LANDS
                elif total_lands_requested > MAX_LANDS:
                    # Only cap if it's significantly over (allow some flexibility)
                    if total_lands_requested > MAX_LANDS + 2:
                        print(f"⚠️  Model allocated {total_lands_requested} lands, capping at {MAX_LANDS}")
                        total_lands_requested = MAX_LANDS
                    else:
                        print(f"ℹ️  Model allocated {total_lands_requested} lands (slightly above historical max {MAX_LANDS}, allowing)")

                
                # Adjust for lands already added to other categories (MDFCs)
                # BUT ensure we don't drop below a safe floor for DEDICATED lands
                if lands_from_other_categories > 0:
                    # If we have MDFCs, we can reduce dedicated lands, but not 1-for-1 if it drops us too low
                    # Example: 35 lands needed. 6 MDFCs found.
                    # Old logic: 35 - 6 = 29 dedicated lands. Total = 35.
                    # User complaint: "29 lands". They might not count MDFCs as lands.
                    # New logic: Only subtract half of MDFCs to be safe, or cap the reduction.
                    
                    reduction = min(lands_from_other_categories, 3)  # Max reduction of 3 lands
                    print(f"🔧 Adjusting land count: {total_lands_requested} requested - {reduction} (capped MDFC adjustment) = {total_lands_requested - reduction} to add")
                    total_lands_requested = max(0, total_lands_requested - reduction)
                
                # CRITICAL FIX: If model allocated a LOT of lands (e.g. Lands Matter deck), 
                # respect that allocation and don't let the "max cap" logic override it 
                # unless it's absurdly high (>60).
                if total_lands_requested > MAX_LANDS:
                    if structure.get('strategy', '') == 'lands_matter' or total_lands_requested < 60:
                        print(f"ℹ️  Respecting high land allocation ({total_lands_requested}) for strategy/preference")
                    else:
                        print(f"⚠️  Model allocated {total_lands_requested} lands, capping at 60 (safety limit)")
                        total_lands_requested = 60
                
                filters = spec.get('filters', [])
                
                # STRATEGY BLACKLIST: Filter out anti-synergistic cards
                strategy = structure.get('strategy', '').lower()
                blacklist = []
                
                if 'spellslinger' in strategy or 'storm' in strategy or 'cantrip' in strategy:
                    blacklist.extend([
                        "Trinisphere", "Sphere of Resistance", "Thalia, Guardian of Thraben", 
                        "Vryn Wingmare", "Thorn of Amethyst", "Damping Sphere", "Deafening Silence",
                        "Rule of Law", "Eidolon of Rhetoric", "Archon of Emeria", "Ethersworn Canonist"
                    ])
                
                if 'graveyard' in strategy or 'reanimator' in strategy:
                    blacklist.extend([
                        "Rest in Peace", "Leyline of the Void", "Dauthi Voidwalker", 
                        "Grafdigger's Cage", "Weathered Runestone"
                    ])
                
                if blacklist:
                    print(f"🚫 Blacklisting {len(blacklist)} anti-synergy cards for {strategy}")
                    filters.append({"names_exclude": blacklist})

                # URBORG CHECK: Exclude Urborg, Tomb of Yawgmoth if not useful
                if 'B' not in self.commander_colors:
                     filters.append({"names_exclude": ["Urborg, Tomb of Yawgmoth"]})
                
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
                    # Filter out off-color fetch lands/duals
                    # If deck is GW, exclude lands that mention Island/Swamp/Mountain/Blue/Black/Red
                    # unless they also mention a color we have (e.g. Windswept Heath fetches Forest/Plains)
                    
                    # Basic land types and their colors
                    basic_types = {
                        'Island': 'U', 'Swamp': 'B', 'Mountain': 'R', 'Plains': 'W', 'Forest': 'G'
                    }
                    
                    # Identify off-color types
                    off_color_types = []
                    for land_type, color in basic_types.items():
                        if color not in self.commander_colors:
                            off_color_types.append(land_type)
                    
                    # Filter candidates
                    valid_lands = []
                    for land in land_cards:
                        # Global Ban: Command Tower // Command Tower
                        if 'Command Tower // Command Tower' in land['name']:
                            continue
                            
                        # Check for off-color fetch/check lands
                        # If it mentions an off-color type but NOT an on-color type, it's bad
                        # (e.g. Polluted Delta mentions Island/Swamp, neither is in GW -> Bad)
                        # (e.g. Windswept Heath mentions Forest/Plains, both in GW -> Good)
                        # (e.g. Misty Rainforest mentions Forest/Island. Forest is in GW -> Good (fetchable))
                        
                        oracle_text = land.get('oracleText', '') or ''
                        name = land['name']
                        
                        # Skip this check for known 5-color lands
                        if name in ['Command Tower', 'City of Brass', 'Mana Confluence', 'Exotic Orchard', 'Path of Ancestry']:
                            valid_lands.append(land)
                            continue
                            
                        # Check mentions
                        mentions_off_color = False
                        mentions_on_color = False
                        
                        for off_type in off_color_types:
                            if off_type in oracle_text:
                                mentions_off_color = True
                        
                        # Check if it mentions ANY on-color type
                        # If it mentions off-color but NO on-color, it's definitely bad (e.g. Polluted Delta in GW)
                        # If it mentions off-color AND on-color, it's a fetch (e.g. Misty Rainforest in GW). This is acceptable but suboptimal.
                        # For now, let's be strict: if it mentions off-color types and no on-color types, exclude it.
                        
                        if mentions_off_color:
                            for on_type, color in basic_types.items():
                                if color in self.commander_colors and on_type in oracle_text:
                                    mentions_on_color = True
                                    break
                            
                            if not mentions_on_color:
                                # It mentions off-color types but no on-color types -> Exclude
                                continue
                        
                        valid_lands.append(land)
                    
                    # Use filtered list
                    land_cards = valid_lands
                    
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
        # Normalize card names to handle split cards (e.g., "Command Tower // Command Tower")
        seen = set()
        unique_cards = []
        for card in deck_cards:
            normalized = normalize_card_name(card)
            is_basic = normalized.lower() in ['plains', 'island', 'swamp', 'mountain', 'forest', 'wastes', 'snow-covered plains', 'snow-covered island', 'snow-covered swamp', 'snow-covered mountain', 'snow-covered forest']
            
            if is_basic or normalized not in seen:
                if not is_basic:
                    seen.add(normalized)
                unique_cards.append(card)  # Keep original name
        deck_cards = unique_cards
        
        # Adjust to exactly 99 cards
        if len(deck_cards) > 99:
            # Smart Trim: Prioritize removing non-land, non-priority cards
            print(f"\n⚠️  Deck has {len(deck_cards)} cards, trimming to 99...")
            
            # Identify safe-to-remove cards
            # 1. Must not be a Land
            # 2. Must not be in priority_cards (if any)
            
            priority_names = set()
            if 'priority_cards' in structure:
                p_list = structure['priority_cards']
                if isinstance(p_list, list):
                    priority_names = set(p_list)
            
            # We need to know which cards are lands. We can use the categories or query DB.
            # Since we just built the deck, we know which are lands from categories['lands']
            # But categories['lands'] might not be perfectly up to date if we did replacements?
            # Actually, replacements update deck_cards but maybe not categories.
            # Let's rely on a quick DB check or the 'lands' category if it's reliable.
            # Better: check if card is in categories['lands'] OR check DB type.
            
            land_names = set(categories.get('lands', []))
            
            # Also check DB for any cards not in that category (e.g. priority lands)
            # For speed, let's just assume anything NOT in land_names AND NOT in priority is fair game.
            # But wait, priority cards might be lands.
            
            candidates = []
            for i, card in enumerate(deck_cards):
                if card in priority_names:
                    continue
                if card in land_names:
                    continue
                
                # Double check it's not a land if we're unsure (e.g. MDFC added as spell)
                # We'll assume if it was added in Phase 1 (non-lands), it's removable.
                candidates.append(card)
            
            # If we still don't have enough candidates, we might have to cut lands or priority.
            # But usually we have plenty of spells.
            
            to_remove_count = len(deck_cards) - 99
            if len(candidates) >= to_remove_count:
                # Remove random candidates (or from end)
                # Let's remove from the end of the candidates list (likely added last)
                remove_set = set(candidates[-to_remove_count:])
                deck_cards = [c for c in deck_cards if c not in remove_set]
                print(f"   ✂️  Removed {to_remove_count} excess spells/non-key cards")
            else:
                # Fallback: Remove all candidates, then trim from end
                remove_set = set(candidates)
                deck_cards = [c for c in deck_cards if c not in remove_set]
                remaining_trim = len(deck_cards) - 99
                if remaining_trim > 0:
                    deck_cards = deck_cards[:99]
                    print(f"   ✂️  Removed {len(candidates)} spells and {remaining_trim} other cards (forced trim)")
            
            # Update categories to reflect trimmed cards
            final_cards_set = set(deck_cards)
            for category in categories:
                categories[category] = [c for c in categories[category] if c in final_cards_set]
            
        elif len(deck_cards) < 99:
            # Fill with basic lands ONLY if we are significantly under 99
            # If we are at 98 or 97, it might be fine, but let's stick to 99 standard.
            
            # Check current land count
            current_lands = len(categories.get('lands', []))
            # Also check if we have lands in other categories
            other_lands = sum(1 for c in deck_cards if c not in categories.get('lands', []) and 'Land' in c) # This check is hard without DB, assume categories is accurate enough or we trust the count
            
            total_current_lands = current_lands # Approximation
            
            lands_needed = 99 - len(deck_cards)
            
            # If we already have a ton of lands (e.g. >45), filling with MORE lands is bad.
            # But we need to reach 99 cards.
            # Ideally we'd add "filler" spells, but we don't have a "filler spell" list ready.
            # So we add basics, but warn if it gets excessive.
            
            if total_current_lands + lands_needed > 50:
                 print(f"⚠️  WARNING: Adding {lands_needed} basics will push land count to {total_current_lands + lands_needed}. Deck might be flooded.")
            
            print(f"\n⚠️  Deck has {len(deck_cards)} cards, need {lands_needed} more to reach 99")
            
            # SANITIZE DECK (Remove high power cards from low brackets)
            if self.bracket < 4:
                original_count = len(deck_cards)
                deck_cards = [c for c in deck_cards if c not in HIGH_POWER_BANLIST]
                if len(deck_cards) < original_count:
                    print(f"   🛡️  Removed {original_count - len(deck_cards)} high-power cards (Bracket {self.bracket})")
            
            final_cards_set = set(deck_cards)
            
            # ROBUST AUTO-FILL
            # We want to ensure we have enough SPELLS (non-lands) to avoid flooding with basics.
            # Target: ~63 non-land cards (leaving ~36 slots for lands)
            
            target_non_land_count = 63 
            
            # Count current non-lands (approximate by checking if not in 'lands' category or name check)
            # Since we don't have full DB data for AI cards easily, we'll assume AI cards are non-lands unless known otherwise.
            # Actually, we can use the categories dict if populated, or just assume for now.
            # Better: Check DB for types of existing cards to be sure.
            
            current_non_lands = 0
            cursor = self.conn.cursor()
            for card in deck_cards:
                # Quick check if it's a basic land
                if card in ['Plains', 'Island', 'Swamp', 'Mountain', 'Forest', 'Wastes']:
                    continue
                
                # Check DB for type
                cursor.execute("SELECT typeLine FROM Card WHERE name = ?", (card,))
                row = cursor.fetchone()
                if row and 'Land' in row['typeLine']:
                    continue
                current_non_lands += 1
            
            print(f"   📊 Current Non-Land Count: {current_non_lands}/{target_non_land_count}")
            
            if current_non_lands < target_non_land_count:
                needed = target_non_land_count - current_non_lands
                print(f"   🚑 Auto-filling {needed} cards to reach minimum spell count...")
                print(f"   🎨 Commander Colors for Auto-Fill: {self.commander_colors}")
                
                # Get top ranked cards from DB
                # Use GROUP BY name to avoid fetching 500 reprints of Sol Ring
                cursor = self.conn.cursor()
                cursor.execute("""
                    SELECT name, colorIdentity, typeLine, oracleText, MIN(edhrecRank) as rank
                    FROM Card
                    WHERE edhrecRank IS NOT NULL
                    AND typeLine NOT LIKE '%Land%'
                    GROUP BY name
                    ORDER BY rank ASC
                    LIMIT 2000
                """)
                
                candidates = cursor.fetchall()
                print(f"   📚 Fetched {len(candidates)} candidates from DB")
                
                added_count = 0
                rejection_reasons = {'color': 0, 'ban': 0, 'dupe': 0}
                
                for row in candidates:
                    if added_count >= needed:
                        break
                        
                    name = row['name']
                    # Normalize name to handle split cards/adventures (e.g. "Card // Card" -> "Card")
                    normalized_name = name.split(' // ')[0]
                    
                    if name in final_cards_set or normalized_name in final_cards_set:
                        rejection_reasons['dupe'] += 1
                        continue
                    
                    # Also check if we already have the "other half" in the deck
                    # (This is a bit expensive but safe)
                    is_dupe = False
                    for existing in final_cards_set:
                        if existing.split(' // ')[0] == normalized_name:
                            is_dupe = True
                            break
                    if is_dupe:
                        rejection_reasons['dupe'] += 1
                        continue
                        
                    # Check color identity
                    card_colors = self.color_checker.parse_color_identity(row['colorIdentity'])
                    if not self.color_checker.is_within_identity(card_colors, self.commander_colors):
                        rejection_reasons['color'] += 1
                        # Debug first few color rejections
                        if rejection_reasons['color'] <= 3:
                             print(f"      ❌ Rejected {name} (Color: {card_colors} vs Commander: {self.commander_colors})")
                        continue
                        
                    # Check legality/bans (simple check)
                    if name in HIGH_POWER_BANLIST and self.bracket < 4:
                        rejection_reasons['ban'] += 1
                        continue
                        
                    # Check tribal enforcement
                    if self.tribal_type and 'Creature' in row['typeLine']:
                        if self.tribal_type not in row['typeLine']:
                             oracle_text = row['oracleText'] or ''
                             if 'Changeling' not in oracle_text:
                                 # print(f"      ❌ Rejected {name} (Not a {self.tribal_type})")
                                 continue
                    
                    # CREATURE PRIORITY CHECK
                    # If we are low on creatures, try to skip non-creatures unless they are very high rank (staples)
                    # We want at least 22 creatures for most decks
                    # BUT: Skip this for Spellslinger, Superfriends, Control, etc.
                    
                    current_strategy = structure.get('strategy', '').lower() or structure.get('theme', '').lower()
                    low_creature_strategies = ['spellslinger', 'control', 'superfriends', 'planeswalkers', 'enchantress', 'voltron', 'artifacts', 'lands']
                    
                    should_enforce_creatures = True
                    for s in low_creature_strategies:
                        if s in current_strategy:
                            should_enforce_creatures = False
                            break
                    
                    # Determine target creature count from stats
                    target_creatures = 22 # Default
                    theme = structure.get('theme') or structure.get('strategy', 'Unknown')
                    
                    if self.deck_stats:
                        stats_source = self.deck_stats.get('by_theme', {}).get(theme)
                        if not stats_source:
                            stats_source = self.deck_stats.get('global')
                        
                        if stats_source and 'creatures' in stats_source:
                            # Use average - 1 standard deviation to be safe (minimum viable count)
                            # Or just use average? Let's use average but cap it reasonable.
                            avg = stats_source['creatures']['avg']
                            target_creatures = int(avg)
                            print(f"   📊 Using data-driven target for creatures: {target_creatures} (Theme: {theme})")

                    current_creatures = categories.get('creatures', [])
                    if should_enforce_creatures and len(current_creatures) < target_creatures:
                        is_creature = 'Creature' in row['typeLine']
                        # If it's not a creature, and we really need creatures, skip it
                        # UNLESS it's a top-tier staple (rank < 100) like Sol Ring
                        if not is_creature and row['rank'] > 100:
                             continue
                        
                    # Add to deck
                    deck_cards.append(name)
                    final_cards_set.add(name)
                    
                    # Add to category
                    type_line = row['typeLine'].lower()
                    if 'creature' in type_line:
                        categories.setdefault('creatures', []).append(name)
                    elif 'instant' in type_line:
                        categories.setdefault('instants', []).append(name)
                    elif 'sorcery' in type_line:
                        categories.setdefault('sorceries', []).append(name)
                    elif 'artifact' in type_line:
                        categories.setdefault('artifacts', []).append(name)
                    elif 'enchantment' in type_line:
                        categories.setdefault('enchantments', []).append(name)
                    elif 'planeswalker' in type_line:
                        categories.setdefault('planeswalkers', []).append(name)
                    
                    added_count += 1
                
                print(f"   ✅ Auto-filled {added_count} cards. New count: {len(deck_cards)}")
                print(f"   ❌ Rejections: {rejection_reasons}")

            # PHASE 4: SYNERGY INJECTION
            # Check for combos/synergies (e.g. Exquisite Blood -> Sanguine Bond)
            # This happens BEFORE land injection so we prioritize combo pieces over utility lands if space is tight
            print(f"\n{'='*70}")
            print("PHASE 4: Synergy Injection")
            print(f"{'='*70}\n")
            
            # Include commander in synergy check!
            cards_to_check = deck_cards + [commander] if commander else deck_cards
            synergy_suggestions = self.synergy_engine.find_synergies(cards_to_check, self.commander_colors)
            if synergy_suggestions:
                print(f"   💡 Found {len(synergy_suggestions)} potential synergy additions: {synergy_suggestions}")
                
                cursor = self.conn.cursor()
                synergy_added = 0
                
                for name in synergy_suggestions:
                    if len(deck_cards) >= 99: break
                    if name in final_cards_set: continue
                    
                    # Fetch card data to validate color/type
                    cursor.execute("SELECT name, colorIdentity, typeLine, oracleText FROM Card WHERE name = ?", (name,))
                    row = cursor.fetchone()
                    
                    if not row:
                        print(f"      ⚠️  Skipping {name} (Not found in DB)")
                        continue
                        
                    # Check color identity
                    card_colors = self.color_checker.parse_color_identity(row['colorIdentity'])
                    if not self.color_checker.is_within_identity(card_colors, self.commander_colors):
                        print(f"      ❌ Rejected {name} (Color mismatch)")
                        continue
                        
                    # Check bans
                    if name in HIGH_POWER_BANLIST and self.bracket < 4:
                        print(f"      ❌ Rejected {name} (Banned in this bracket)")
                        continue
                        
                    # Check tribal enforcement
                    if self.tribal_type and 'Creature' in row['typeLine']:
                        if self.tribal_type not in row['typeLine']:
                             oracle_text = row['oracleText'] or ''
                             if 'Changeling' not in oracle_text:
                                 print(f"      ❌ Rejected {name} (Not a {self.tribal_type})")
                                 continue
                        
                    # Add to deck
                    deck_cards.append(name)
                    final_cards_set.add(name)
                    
                    # Add to category
                    type_line = row['typeLine'].lower()
                    if 'land' in type_line:
                        categories.setdefault('lands', []).append(name)
                    elif 'creature' in type_line:
                        categories.setdefault('creatures', []).append(name)
                    elif 'instant' in type_line:
                        categories.setdefault('instants', []).append(name)
                    elif 'sorcery' in type_line:
                        categories.setdefault('sorceries', []).append(name)
                    elif 'artifact' in type_line:
                        categories.setdefault('artifacts', []).append(name)
                    elif 'enchantment' in type_line:
                        categories.setdefault('enchantments', []).append(name)
                    elif 'planeswalker' in type_line:
                        categories.setdefault('planeswalkers', []).append(name)
                        
                    synergy_added += 1
                    print(f"      ✨ Added synergy piece: {name}")
                    
                print(f"   ✅ Added {synergy_added} synergy cards")

            else:
                print("   🤷 No specific synergies found for current cards")

            # LAND BASE INJECTION
            
            # 1. Determine Target Land Count from Stats
            target_lands = 37 # Default fallback
            theme = structure.get('theme') or structure.get('strategy', 'Unknown')
            if self.deck_stats:
                stats_source = self.deck_stats.get('by_theme', {}).get(theme)
                if not stats_source:
                    stats_source = self.deck_stats.get('global')
                
                if stats_source and 'lands' in stats_source:
                    target_lands = int(stats_source['lands']['avg'])
                    print(f"   📊 Using data-driven target for lands: {target_lands} (Theme: {theme})")

            # 2. Analyze current deck state
            current_lands = 0
            current_non_basics = 0
            cursor = self.conn.cursor()
            
            # Helper to check if card is land
            for card in deck_cards:
                if card in ['Plains', 'Island', 'Swamp', 'Mountain', 'Forest', 'Wastes']: 
                    current_lands += 1
                    continue
                    
                cursor.execute("SELECT typeLine FROM Card WHERE name = ?", (card,))
                row = cursor.fetchone()
                if row and 'Land' in row['typeLine']:
                    current_lands += 1
                    if 'Basic' not in row['typeLine']:
                        current_non_basics += 1
            
            print(f"   📊 Current Lands: {current_lands} (Non-basics: {current_non_basics})")
            
            # 3. Calculate needs
            slots_remaining = 99 - len(deck_cards)
            lands_needed_for_target = target_lands - current_lands
            
            # We must fill slots_remaining to be legal.
            # If we need MORE lands to hit target than slots available, we are capped by slots.
            # If we need FEWER lands than slots available, we are forced to over-fill with lands (unless we add spells).
            
            total_lands_to_add = slots_remaining
            if lands_needed_for_target > slots_remaining:
                print(f"   ⚠️  Target lands {target_lands} exceeds available slots {slots_remaining + current_lands}. Capped.")
            elif lands_needed_for_target < slots_remaining:
                print(f"   ⚠️  Deck short on spells! Filling {slots_remaining} slots with lands (Target was {target_lands}).")
            
            # 4. Inject Non-Basics
            # We want a healthy amount of non-basics. Let's aim for ~40% of total lands being non-basic.
            target_total_non_basics = int(target_lands * 0.4)
            non_basics_to_add = max(0, target_total_non_basics - current_non_basics)
            
            # Don't add more non-basics than we have slots for
            non_basics_to_add = min(non_basics_to_add, total_lands_to_add)
            
            if non_basics_to_add > 0:
                print(f"   Build Land Base: Injecting {non_basics_to_add} non-basic lands...")
                
                cursor.execute("""
                    SELECT name, colorIdentity, typeLine, oracleText
                    FROM Card
                    WHERE typeLine LIKE '%Land%' 
                    AND typeLine NOT LIKE '%Basic%'
                    AND edhrecRank IS NOT NULL
                    ORDER BY edhrecRank ASC
                    LIMIT 500
                """)
                land_candidates = cursor.fetchall()
                
                # Setup for strict filtering
                basic_types = {
                    'Island': 'U', 'Swamp': 'B', 'Mountain': 'R', 'Plains': 'W', 'Forest': 'G',
                    'Blue': 'U', 'Black': 'B', 'Red': 'R', 'White': 'W', 'Green': 'G'
                }
                off_color_types = {k: v for k, v in basic_types.items() if v not in self.commander_colors}
                
                added_non_basics = 0
                for row in land_candidates:
                    if added_non_basics >= non_basics_to_add: break
                    if len(deck_cards) >= 99: break
                    
                    name = row['name']
                    if name in final_cards_set: continue
                    
                    # Check color identity
                    card_colors = self.color_checker.parse_color_identity(row['colorIdentity'])
                    if not self.color_checker.is_within_identity(card_colors, self.commander_colors):
                        continue
                        
                    # Strict Oracle Text Check (Fetch Lands & Off-Color Mana)
                    oracle_text = row['oracleText'] or ''
                    mentions_off_color = False
                    for type_name, color in off_color_types.items():
                        if type_name in oracle_text:
                            mentions_off_color = True
                            break
                    
                    if mentions_off_color:
                        # It mentions an off-color type -> Exclude
                        # This prevents off-color fetches (e.g. Polluted Delta in WU deck)
                        continue
                        
                    # Add land
                    deck_cards.append(name)
                    final_cards_set.add(name)
                    categories.setdefault('lands', []).append(name)
                    added_non_basics += 1
                
                print(f"   ✅ Injected {added_non_basics} non-basic lands")

                
            # 5. Fill remainder with Basics
            remaining_slots = 99 - len(deck_cards)
            if remaining_slots > 0:
                # Determine colors from commander - pick basics that match
                color_to_basic = {'W': 'Plains', 'U': 'Island', 'B': 'Swamp', 'R': 'Red', 'G': 'Forest'} # Error: R is Mountain
                # Fix R mapping
                color_to_basic = {'W': 'Plains', 'U': 'Island', 'B': 'Swamp', 'R': 'Mountain', 'G': 'Forest'}
                
                available_basics = [color_to_basic[c] for c in self.commander_colors if c in color_to_basic]
                
                if not available_basics:
                    available_basics = ["Wastes"]  # Colorless
                
                # Distribute basics evenly
                fill_lands = [available_basics[i % len(available_basics)] for i in range(remaining_slots)]
                deck_cards.extend(fill_lands)
                print(f"   ⚠️  Filled with {remaining_slots} basic lands to reach 99")
                
                # Add filled basics to categories
                if 'lands' not in categories:
                    categories['lands'] = []
                categories['lands'].extend(fill_lands)
        
        # FINAL SANITIZATION: Remove "Command Tower // Command Tower" if present
        # This is the nuclear option to ensure it never appears
        sanitized_cards = []
        has_command_tower = False
        
        for card in deck_cards:
            if 'Command Tower // Command Tower' in card:
                print(f"☢️  Removed {card} during final sanitization")
                continue
            
            if card == 'Command Tower':
                if has_command_tower:
                    print(f"☢️  Removed duplicate Command Tower during final sanitization")
                    continue
                has_command_tower = True
                
            sanitized_cards.append(card)
            
        deck_cards = sanitized_cards
        
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
