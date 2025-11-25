#!/usr/bin/env python3
"""
Execute deck structure JSON into complete 100-card decklists
Uses Prisma database to find cards matching the filters
"""

import sys
import json
import re
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import Prisma client
from prisma import Prisma
import asyncio

async def execute_filters(prisma, filters, count, commander_colors):
    """
    Execute card filters against database
    Returns list of card objects matching the filters
    """
    cards = []
    
    for filter_obj in filters:
        # Build query conditions
        where_conditions = {
            "AND": []
        }
        
        # Types filter
        if "types" in filter_obj:
            type_conditions = []
            for card_type in filter_obj["types"]:
                type_conditions.append({
                    "typeLine": {
                        "contains": card_type
                    }
                })
            if type_conditions:
                where_conditions["AND"].append({"OR": type_conditions})
        
        # Subtypes filter
        if "subtypes" in filter_obj:
            subtype_conditions = []
            for subtype in filter_obj["subtypes"]:
                subtype_conditions.append({
                    "typeLine": {
                        "contains": subtype
                    }
                })
            if subtype_conditions:
                where_conditions["AND"].append({"OR": subtype_conditions})
        
        # Tags filter (check keywords or oracle text)
        if "tags" in filter_obj:
            tag_conditions = []
            for tag in filter_obj["tags"]:
                # Map common tags to searchable terms
                tag_map = {
                    "ramp": ["search", "land", "add", "mana"],
                    "removal": ["destroy", "exile", "remove"],
                    "card_draw": ["draw", "card"],
                    "board_wipe": ["destroy all", "exile all"],
                    "tutor": ["search your library"],
                    "protection": ["counter", "hexproof", "protection"],
                    "counterspell": ["counter target"]
                }
                
                if tag in tag_map:
                    for search_term in tag_map[tag]:
                        tag_conditions.append({
                            "oracleText": {
                                "contains": search_term,
                                "mode": "insensitive"
                            }
                        })
            
            if tag_conditions:
                where_conditions["AND"].append({"OR": tag_conditions})
        
        # CMC filter
        if "cmc_max" in filter_obj:
            where_conditions["AND"].append({
                "cmc": {
                    "lte": filter_obj["cmc_max"]
                }
            })
        
        if "cmc_min" in filter_obj:
            where_conditions["AND"].append({
                "cmc": {
                    "gte": filter_obj["cmc_min"]
                }
            })
        
        # Color identity filter - must be within commander colors
        if commander_colors:
            # Convert commander colors to array format
            color_array = list(commander_colors)
            # Cards must have color identity subset of commander
            where_conditions["AND"].append({
                "OR": [
                    {"colorIdentity": {"equals": ""}},  # Colorless
                    *[{"colorIdentity": {"contains": c}} for c in color_array]
                ]
            })
        
        # Instant speed filter
        if filter_obj.get("instant_speed"):
            where_conditions["AND"].append({
                "typeLine": {
                    "contains": "Instant"
                }
            })
        
        # Execute query
        try:
            results = await prisma.card.find_many(
                where=where_conditions if where_conditions["AND"] else {},
                take=count,
                order_by={"edhrecRank": "asc"}  # Prefer popular cards
            )
            cards.extend(results)
        except Exception as e:
            print(f"Warning: Filter query failed: {e}")
            continue
    
    return cards[:count]

async def build_complete_deck(structure_json):
    """
    Convert deck structure JSON into complete 100-card decklist
    """
    prisma = Prisma()
    await prisma.connect()
    
    try:
        # Parse input
        if isinstance(structure_json, str):
            structure = json.loads(structure_json)
        else:
            structure = structure_json
        
        commander_name = structure.get("commander", "Unknown")
        card_selection = structure.get("card_selection", {})
        priority_cards = structure.get("priority_cards", [])
        
        print(f"Building deck for: {commander_name}")
        print(f"Strategy: {structure.get('strategy', 'unknown')}")
        print(f"Power Level: {structure.get('power_level', 'unknown')}")
        print(f"Bracket: {structure.get('bracket', 'unknown')}\n")
        
        # Fetch commander to get color identity
        commander = await prisma.card.find_first(
            where={
                "name": {
                    "contains": commander_name.split(",")[0],  # Handle "Atraxa, Praetors' Voice"
                    "mode": "insensitive"
                }
            }
        )
        
        if not commander:
            print(f"Warning: Commander '{commander_name}' not found in database")
            commander_colors = ""
        else:
            commander_colors = commander.colorIdentity or ""
            print(f"Commander colors: {commander_colors or 'Colorless'}\n")
        
        # Build deck sections
        deck = {
            "commander": commander_name,
            "mainboard": [],
            "total_cards": 0
        }
        
        # Process each card category
        for category, data in card_selection.items():
            if not data or not isinstance(data, dict):
                continue
            
            count = data.get("count", 0)
            filters = data.get("filters", [])
            
            print(f"Fetching {count} {category}...")
            cards = await execute_filters(prisma, filters, count, commander_colors)
            
            print(f"  Found {len(cards)} cards")
            for card in cards:
                deck["mainboard"].append({
                    "name": card.name,
                    "category": category,
                    "cmc": card.cmc,
                    "type": card.typeLine
                })
            
            deck["total_cards"] += len(cards)
        
        # Add priority cards if we need more to reach 99
        needed = 99 - deck["total_cards"]
        if needed > 0 and priority_cards:
            print(f"\nAdding {needed} priority cards to reach 99...")
            
            # Deduplicate priority cards
            unique_priority = []
            seen = set([card["name"] for card in deck["mainboard"]])
            
            for card_name in priority_cards:
                if card_name not in seen:
                    unique_priority.append(card_name)
                    seen.add(card_name)
                if len(unique_priority) >= needed:
                    break
            
            # Fetch priority cards
            for card_name in unique_priority[:needed]:
                card = await prisma.card.find_first(
                    where={
                        "name": {
                            "equals": card_name,
                            "mode": "insensitive"
                        }
                    }
                )
                
                if card:
                    deck["mainboard"].append({
                        "name": card.name,
                        "category": "priority",
                        "cmc": card.cmc,
                        "type": card.typeLine
                    })
                    deck["total_cards"] += 1
        
        # Fill remaining slots with basics if still short
        needed = 99 - deck["total_cards"]
        if needed > 0:
            print(f"\nFilling {needed} remaining slots with basic lands...")
            
            # Determine which basics based on commander colors
            basic_types = []
            if 'W' in commander_colors:
                basic_types.append("Plains")
            if 'U' in commander_colors:
                basic_types.append("Island")
            if 'B' in commander_colors:
                basic_types.append("Swamp")
            if 'R' in commander_colors:
                basic_types.append("Mountain")
            if 'G' in commander_colors:
                basic_types.append("Forest")
            
            if not basic_types:
                basic_types = ["Wastes"]  # Colorless
            
            # Distribute evenly
            per_basic = needed // len(basic_types)
            remainder = needed % len(basic_types)
            
            for i, basic in enumerate(basic_types):
                count = per_basic + (1 if i < remainder else 0)
                for _ in range(count):
                    deck["mainboard"].append({
                        "name": basic,
                        "category": "basic_land",
                        "cmc": 0,
                        "type": "Basic Land"
                    })
                    deck["total_cards"] += 1
        
        print(f"\n{'='*70}")
        print(f"DECK COMPLETE: {deck['total_cards']} cards (99 mainboard + 1 commander)")
        print(f"{'='*70}\n")
        
        # Summary by category
        category_counts = {}
        for card in deck["mainboard"]:
            cat = card["category"]
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        print("Card distribution:")
        for cat, count in sorted(category_counts.items()):
            print(f"  {cat}: {count}")
        
        return deck
        
    finally:
        await prisma.disconnect()

async def main():
    """Main execution"""
    if len(sys.argv) < 2:
        print("Usage: python execute-deck-structure.py <json_file_or_string>")
        print("\nExample:")
        print('  python execute-deck-structure.py \'{"commander": "Atraxa", ...}\'')
        print("  python execute-deck-structure.py generated_decks/gemma_test/atraxa.json")
        sys.exit(1)
    
    input_arg = sys.argv[1]
    
    # Check if it's a file
    if Path(input_arg).exists():
        print(f"Reading from file: {input_arg}\n")
        with open(input_arg, 'r') as f:
            # Handle test output format
            data = json.load(f)
            if "raw_output" in data:
                # Extract from test output
                raw = data["raw_output"]
                if raw.startswith("model"):
                    raw = raw[5:].strip()
                # Try to parse truncated JSON
                json_start = raw.find('{')
                json_end = raw.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    structure_json = raw[json_start:json_end]
                else:
                    structure_json = raw
            else:
                structure_json = json.dumps(data)
    else:
        # Assume it's a JSON string
        structure_json = input_arg
    
    # Build the deck
    deck = await build_complete_deck(structure_json)
    
    # Save output
    output_file = "generated_decks/executed_deck.json"
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(deck, f, indent=2)
    
    print(f"\n💾 Complete deck saved to: {output_file}")
    
    # Also save as text decklist
    text_file = output_file.replace('.json', '.txt')
    with open(text_file, 'w') as f:
        f.write(f"Commander: {deck['commander']}\n\n")
        
        # Group by category
        by_category = {}
        for card in deck["mainboard"]:
            cat = card["category"]
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(card)
        
        for category, cards in sorted(by_category.items()):
            f.write(f"\n{category.upper()} ({len(cards)}):\n")
            for card in sorted(cards, key=lambda c: c["name"]):
                f.write(f"1x {card['name']}\n")
    
    print(f"💾 Text decklist saved to: {text_file}")

if __name__ == "__main__":
    asyncio.run(main())
