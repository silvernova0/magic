#!/usr/bin/env python3
"""
Convert scraped deck data to v3 structured training format.

v3 Approach:
- Model generates structured JSON with filters/queries
- Database executes queries to get actual cards
- No card name generation = zero hallucinations

Input: All scraped deck JSONLs
Output: v3_structured_training.jsonl with instruction/output pairs

Example v3 output format:
{
  "instruction": "Build a Commander deck with The Ur-Dragon focused on tribal dragons at power level 7",
  "output": {
    "commander": "The Ur-Dragon",
    "strategy": "tribal",
    "tribe": "Dragon",
    "power_level": 7,
    "bracket": 3,
    "card_selection": {
      "lands": {
        "count": 37,
        "filters": [
          {"types": ["Land"], "colors_within": ["W", "U", "B", "R", "G"]},
          {"names": ["Command Tower", "Path of Ancestry"], "reason": "5-color staples"}
        ]
      },
      "ramp": {
        "count": 13,
        "filters": [
          {"tags": ["ramp"], "cmc_max": 3, "reason": "Fast mana to enable big dragons"},
          {"names": ["Urza's Incubator", "Dragon's Hoard"], "reason": "Tribal cost reduction"}
        ]
      },
      "creatures": {
        "count": 23,
        "filters": [
          {"types": ["Creature"], "subtypes": ["Dragon"], "reason": "Tribal synergy"},
          {"names": ["Dragonlord's Servant", "Dragonlord Kolaghan"], "reason": "Dragon support"}
        ]
      },
      "card_draw": {
        "count": 11,
        "filters": [{"tags": ["card_draw"], "cmc_max": 4}]
      },
      "removal": {
        "count": 8,
        "filters": [{"tags": ["removal"], "instant_speed": true}]
      },
      "board_wipes": {
        "count": 3,
        "filters": [{"tags": ["board_wipe"]}]
      },
      "tutors": {
        "count": 2,
        "filters": [{"tags": ["tutor"], "cmc_max": 5}]
      },
      "protection": {
        "count": 3,
        "filters": [{"tags": ["protection", "counterspell"]}]
      }
    },
    "priority_cards": [
      "The Ur-Dragon",
      "Scion of the Ur-Dragon",
      "Dragon Tempest",
      "Kindred Discovery",
      "Urza's Incubator"
    ],
    "combos": [],
    "notes": "Focus on dragon tribal synergy with cost reduction and card draw."
  }
}
"""

import json
import re
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Any, Set
import sys

# Load deck building rules
RULES_PATH = Path("data/training/deck_building_rules.json")
with open(RULES_PATH) as f:
    DECK_RULES = json.load(f)

# Card type keywords for categorization
CARD_CATEGORIES = {
    'ramp': ['sol ring', 'mana crypt', 'arcane signet', 'signet', 'talisman', 'mana vault',
             'chrome mox', 'mox', 'fellwar stone', 'thought vessel', 'commander sphere',
             'cultivate', 'kodama', 'rampant growth', 'three visits', 'nature\'s lore',
             'farseek', 'llanowar elves', 'birds of paradise', 'avacyn\'s pilgrim'],
    'card_draw': ['rhystic study', 'mystic remora', 'esper sentinel', 'phyrexian arena',
                  'sylvan library', 'treasure cruise', 'harmonize', 'night\'s whisper',
                  'sign in blood', 'read the bones', 'painful truths'],
    'removal': ['swords to plowshares', 'path to exile', 'beast within', 'generous gift',
                'chaos warp', 'nature\'s claim', 'assassin\'s trophy', 'anguished unmaking',
                'terminate', 'murder', 'go for the throat', 'reality shift'],
    'board_wipe': ['wrath of god', 'damnation', 'blasphemous act', 'toxic deluge',
                   'cyclonic rift', 'vandalblast', 'austere command', 'merciless eviction'],
    'tutor': ['demonic tutor', 'vampiric tutor', 'imperial seal', 'mystical tutor',
              'enlightened tutor', 'worldly tutor', 'diabolic tutor', 'beseech the queen'],
    'protection': ['lightning greaves', 'swiftfoot boots', 'heroic intervention',
                   'teferi\'s protection', 'counterspell', 'swan song', 'negate',
                   'force of will', 'pact of negation', 'fierce guardianship'],
    'land': ['command tower', 'path of ancestry', 'temple', 'shock land', 'fetch land',
             'triome', 'dual land', 'pain land', 'check land', 'bounce land']
}

def categorize_card(card_name: str) -> Set[str]:
    """Determine which categories a card belongs to based on name"""
    categories = set()
    card_lower = card_name.lower()
    
    for category, keywords in CARD_CATEGORIES.items():
        for keyword in keywords:
            if keyword in card_lower:
                categories.add(category)
                break
    
    # Default category based on card name patterns
    if not categories:
        if 'land' in card_lower or any(t in card_lower for t in ['tower', 'temple', 'grove', 'crag', 'plains', 'island', 'swamp', 'mountain', 'forest']):
            categories.add('land')
    
    return categories

def detect_strategy(deck_data: Dict) -> str:
    """Detect deck strategy from card names and themes"""
    all_cards = deck_data.get('all_cards', [])
    themes = deck_data.get('themes', [])
    
    # Check themes first
    themes_lower = ' '.join(themes).lower()
    
    if any(word in themes_lower for word in ['tribal', 'kindred', 'creature type']):
        return 'tribal'
    if any(word in themes_lower for word in ['combo', 'infinite']):
        return 'combo'
    if any(word in themes_lower for word in ['control', 'permission', 'counterspell']):
        return 'control'
    if any(word in themes_lower for word in ['aggro', 'weenie', 'go wide']):
        return 'aggro'
    if any(word in themes_lower for word in ['voltron', 'equipment', 'aura']):
        return 'voltron'
    if any(word in themes_lower for word in ['spell', 'instant', 'sorcery']):
        return 'spellslinger'
    if any(word in themes_lower for word in ['reanimator', 'graveyard']):
        return 'reanimator'
    if any(word in themes_lower for word in ['stax', 'lock', 'prison']):
        return 'stax'
    if any(word in themes_lower for word in ['aristocrats', 'sacrifice']):
        return 'aristocrats'
    if any(word in themes_lower for word in ['ramp', 'big creatures', 'stompy']):
        return 'stompy'
    
    # Analyze card composition
    card_names_lower = ' '.join(all_cards).lower()
    
    # Count strategy indicators
    strategy_score = defaultdict(int)
    
    # Tribal indicators
    creature_types = ['dragon', 'elf', 'goblin', 'zombie', 'vampire', 'angel', 'demon', 'wizard', 'soldier', 'merfolk']
    for ctype in creature_types:
        if card_names_lower.count(ctype) >= 5:
            strategy_score['tribal'] += 10
            break
    
    # Combo indicators
    if 'infinite' in themes_lower or any(combo in card_names_lower for combo in ['thassa\'s oracle', 'thoracle', 'consultation', 'worldgorger']):
        strategy_score['combo'] += 10
    
    # Default to balanced midrange
    if not strategy_score:
        return 'midrange'
    
    return max(strategy_score.items(), key=lambda x: x[1])[0]

def estimate_power_level(deck_data: Dict, strategy: str) -> tuple:
    """Estimate power level (1-10) and bracket (1-5) from deck composition"""
    all_cards = deck_data.get('all_cards', [])
    card_names_lower = ' '.join(all_cards).lower()
    
    power_score = 5  # Start at midrange
    
    # High power indicators (+1-2 each)
    high_power_cards = ['mana crypt', 'mana vault', 'chrome mox', 'mox diamond', 'mox opal',
                        'demonic tutor', 'vampiric tutor', 'imperial seal', 'mystical tutor',
                        'force of will', 'force of negation', 'pact of negation', 'fierce guardianship',
                        'cyclonic rift', 'rhystic study', 'mystic remora', 'esper sentinel',
                        'dockside extortionist', 'jeweled lotus', 'led', 'gaea\'s cradle']
    
    for card in high_power_cards:
        if card in card_names_lower:
            power_score += 0.5
    
    # cEDH indicators (+2-3)
    cedh_cards = ['thassa\'s oracle', 'thoracle', 'demonic consultation', 'tainted pact',
                  'ad nauseam', 'underworld breach', 'worldgorger dragon', 'necropotence']
    
    for card in cedh_cards:
        if card in card_names_lower:
            power_score += 1.5
    
    # Budget indicators (-1-2)
    budget_indicators = ['evolving wilds', 'terramorphic expanse', 'guildgate', 'gainland']
    for card in budget_indicators:
        if card in card_names_lower:
            power_score -= 0.5
    
    # Cap at 1-10
    power_score = max(1, min(10, power_score))
    
    # Convert to bracket (1-5)
    if power_score <= 3:
        bracket = 1
    elif power_score <= 5:
        bracket = 2
    elif power_score <= 7:
        bracket = 3
    elif power_score <= 8.5:
        bracket = 4
    else:
        bracket = 5
    
    return int(power_score), bracket

def analyze_deck_distribution(deck_data: Dict) -> Dict[str, int]:
    """Analyze card distribution by category"""
    all_cards = deck_data.get('all_cards', [])
    categories_dict = deck_data.get('categories', {})
    
    distribution = defaultdict(int)
    
    # Use EDHREC categories if available
    if categories_dict:
        for category, data in categories_dict.items():
            count = data.get('count', 0)
            category_lower = category.lower()
            
            if 'creature' in category_lower:
                distribution['creatures'] += count
            elif 'land' in category_lower:
                distribution['lands'] += count
            elif any(x in category_lower for x in ['ramp', 'mana']):
                distribution['ramp'] += count
            elif any(x in category_lower for x in ['draw', 'card advantage']):
                distribution['card_draw'] += count
            elif 'removal' in category_lower:
                distribution['removal'] += count
            elif any(x in category_lower for x in ['wipe', 'board clear']):
                distribution['board_wipes'] += count
            elif 'tutor' in category_lower:
                distribution['tutors'] += count
            elif any(x in category_lower for x in ['protection', 'counter']):
                distribution['protection'] += count
    
    # Fallback: categorize by card names
    if not distribution:
        for card in all_cards:
            categories = categorize_card(card)
            for cat in categories:
                distribution[cat] += 1
    
    # Estimate missing categories
    total_counted = sum(distribution.values())
    total_cards = len(all_cards)
    
    if total_cards > total_counted:
        # Remaining cards are likely creatures/spells
        distribution['creatures'] = distribution.get('creatures', 0) + (total_cards - total_counted) // 2
    
    return dict(distribution)

def extract_tribe_from_deck(deck_data: Dict) -> str:
    """Extract creature type for tribal decks"""
    themes = deck_data.get('themes', [])
    themes_str = ' '.join(themes).lower()
    
    tribes = ['dragon', 'elf', 'goblin', 'zombie', 'vampire', 'angel', 'demon', 'wizard',
              'soldier', 'merfolk', 'knight', 'cat', 'dog', 'bird', 'sphinx', 'hydra',
              'dinosaur', 'beast', 'elemental', 'spirit', 'artifact', 'phyrexian']
    
    for tribe in tribes:
        if tribe in themes_str:
            return tribe.capitalize()
    
    # Check card names
    all_cards = ' '.join(deck_data.get('all_cards', [])).lower()
    tribe_counts = Counter()
    
    for tribe in tribes:
        tribe_counts[tribe] = all_cards.count(tribe)
    
    if tribe_counts:
        most_common_tribe, count = tribe_counts.most_common(1)[0]
        if count >= 5:  # At least 5 cards of that type
            return most_common_tribe.capitalize()
    
    return None

def create_v3_training_example(deck_data: Dict, source: str) -> Dict:
    """Convert deck data to v3 structured training format"""
    
    commander = deck_data.get('commander', 'Unknown Commander')
    strategy = detect_strategy(deck_data)
    power_level, bracket = estimate_power_level(deck_data, strategy)
    distribution = analyze_deck_distribution(deck_data)
    tribe = extract_tribe_from_deck(deck_data) if strategy == 'tribal' else None
    
    # Build instruction
    instruction_parts = [f"Build a Commander deck with {commander}"]
    
    if tribe:
        instruction_parts.append(f"focused on tribal {tribe}s")
    else:
        instruction_parts.append(f"focused on {strategy}")
    
    instruction_parts.append(f"at power level {power_level}")
    instruction = ' '.join(instruction_parts)
    
    # Get base ratios for bracket
    bracket_key = str(bracket)
    base_ratios = DECK_RULES['brackets'][bracket_key]['base_ratios']
    
    # Build card selection filters
    card_selection = {}
    
    # Lands
    land_count = distribution.get('lands', base_ratios['lands']['min'])
    card_selection['lands'] = {
        'count': land_count,
        'filters': [
            {'types': ['Land'], 'colors_within': deck_data.get('colors', [])},
        ]
    }
    
    # Ramp
    ramp_count = distribution.get('ramp', base_ratios['ramp']['min'])
    card_selection['ramp'] = {
        'count': ramp_count,
        'filters': [
            {'tags': ['ramp'], 'cmc_max': 3 if bracket >= 3 else 4, 'reason': 'Accelerate gameplan'}
        ]
    }
    
    # Card draw
    draw_count = distribution.get('card_draw', base_ratios['card_draw']['min'])
    card_selection['card_draw'] = {
        'count': draw_count,
        'filters': [
            {'tags': ['card_draw'], 'reason': 'Card advantage'}
        ]
    }
    
    # Removal
    removal_count = distribution.get('removal', base_ratios['removal']['min'])
    card_selection['removal'] = {
        'count': removal_count,
        'filters': [
            {'tags': ['removal'], 'instant_speed': bracket >= 3, 'reason': 'Answer threats'}
        ]
    }
    
    # Board wipes
    wipe_count = distribution.get('board_wipes', base_ratios['board_wipes']['min'])
    if wipe_count > 0:
        card_selection['board_wipes'] = {
            'count': wipe_count,
            'filters': [
                {'tags': ['board_wipe'], 'reason': 'Reset board state'}
            ]
        }
    
    # Tutors
    tutor_count = distribution.get('tutors', base_ratios['tutors']['min'])
    if tutor_count > 0:
        card_selection['tutors'] = {
            'count': tutor_count,
            'filters': [
                {'tags': ['tutor'], 'cmc_max': 5 if bracket <= 3 else 3, 'reason': 'Find key pieces'}
            ]
        }
    
    # Protection
    protection_count = distribution.get('protection', base_ratios['protection']['min'])
    card_selection['protection'] = {
        'count': protection_count,
        'filters': [
            {'tags': ['protection', 'counterspell'], 'reason': 'Protect strategy'}
        ]
    }
    
    # Strategy-specific cards
    if strategy == 'tribal' and tribe:
        creature_count = distribution.get('creatures', 25)
        card_selection['creatures'] = {
            'count': creature_count,
            'filters': [
                {'types': ['Creature'], 'subtypes': [tribe], 'reason': f'{tribe} tribal synergy'}
            ]
        }
    
    # Priority cards (first 5-10 cards from deck)
    priority_cards = [commander]
    all_cards = deck_data.get('all_cards', [])
    if len(all_cards) > 1:
        priority_cards.extend(all_cards[1:min(6, len(all_cards))])
    
    # Build output structure
    output = {
        'commander': commander,
        'strategy': strategy,
        'power_level': power_level,
        'bracket': bracket,
        'card_selection': card_selection,
        'priority_cards': priority_cards,
        'combos': [],  # Will be populated from combo data later
        'notes': f"{strategy.capitalize()} deck at bracket {bracket}"
    }
    
    if tribe:
        output['tribe'] = tribe
    
    return {
        'instruction': instruction,
        'output': output,
        'source': source,
        'original_deck_size': len(all_cards)
    }

def parse_v2_decklist(output_text: str) -> List[str]:
    """Parse v2 text decklist format to extract card names"""
    cards = []
    lines = output_text.split('\n')
    
    for line in lines:
        line = line.strip()
        # Skip headers and empty lines
        if not line or line.startswith('Commander:') or line.startswith('Deck Name:') or line.startswith('Decklist:') or line.endswith(':'):
            continue
        
        # Parse "1x Card Name" format
        match = re.match(r'^\d+x\s+(.+)$', line)
        if match:
            card_name = match.group(1).strip()
            cards.append(card_name)
    
    return cards

def process_deck_file(file_path: Path, source_name: str) -> List[Dict]:
    """Process a single JSONL deck file"""
    examples = []
    
    print(f"Processing {source_name}: {file_path.name}")
    
    try:
        with open(file_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    deck_data = json.loads(line.strip())
                    
                    # Handle v2 format (instruction/output text)
                    if 'output' in deck_data and isinstance(deck_data['output'], str):
                        # Parse text decklist
                        cards = parse_v2_decklist(deck_data['output'])
                        
                        if not cards:
                            continue
                        
                        # Extract commander from output text
                        commander_match = re.search(r'Commander:\s*(.+)', deck_data['output'])
                        commander = commander_match.group(1).strip() if commander_match else 'Unknown Commander'
                        
                        # Convert to EDHREC-style format
                        deck_data = {
                            'commander': commander,
                            'all_cards': cards,
                            'themes': [],
                            'categories': {}
                        }
                    
                    # Skip if no cards
                    if not deck_data.get('all_cards') and not deck_data.get('cards'):
                        continue
                    
                    # Normalize format
                    if 'cards' in deck_data and 'all_cards' not in deck_data:
                        deck_data['all_cards'] = [card['name'] for card in deck_data['cards']]
                    
                    example = create_v3_training_example(deck_data, source_name)
                    examples.append(example)
                    
                    if line_num % 500 == 0:
                        print(f"  Processed {line_num} decks...")
                        
                except json.JSONDecodeError as e:
                    print(f"  ⚠️  Line {line_num}: Invalid JSON - {e}")
                    continue
                except Exception as e:
                    print(f"  ⚠️  Line {line_num}: Error - {e}")
                    continue
        
        print(f"  ✅ Generated {len(examples)} training examples from {source_name}")
        
    except FileNotFoundError:
        print(f"  ⚠️  File not found: {file_path}")
    except Exception as e:
        print(f"  ❌ Error processing {source_name}: {e}")
    
    return examples

def main():
    """Convert all deck data to v3 training format"""
    
    print("=" * 60)
    print("Converting deck data to v3 structured training format")
    print("=" * 60)
    print()
    
    training_dir = Path("data/training")
    output_path = training_dir / "v3_structured_training.jsonl"
    
    # Deck sources to process (in priority order)
    deck_sources = [
        ("edhrec_average_decks.jsonl", "EDHREC Average Decks"),
        ("mtggoldfish_by_commander_decks.jsonl", "MTGGoldfish Commander Decks"),
        ("moxfield_decks.jsonl", "Moxfield Theme Decks"),
        ("archidekt_decks.jsonl", "Archidekt Popular Decks"),
        ("moxfield_decks_diverse.jsonl", "Moxfield Diverse Decks"),
        ("mtggoldfish_decks.jsonl", "MTGGoldfish Archetype Decks"),
    ]
    
    all_examples = []
    
    for filename, source_name in deck_sources:
        file_path = training_dir / filename
        if file_path.exists() and file_path.stat().st_size > 0:
            examples = process_deck_file(file_path, source_name)
            all_examples.extend(examples)
        else:
            print(f"⏭️  Skipping {source_name} (file empty or missing)")
    
    print()
    print("=" * 60)
    print(f"Total training examples generated: {len(all_examples)}")
    print("=" * 60)
    print()
    
    # Save to output file
    print(f"Saving to {output_path}...")
    with open(output_path, 'w') as f:
        for example in all_examples:
            f.write(json.dumps(example) + '\n')
    
    print(f"✅ Saved {len(all_examples)} examples to {output_path}")
    print()
    
    # Statistics
    print("=" * 60)
    print("Dataset Statistics:")
    print("=" * 60)
    
    strategies = Counter(ex['output']['strategy'] for ex in all_examples)
    brackets = Counter(ex['output']['bracket'] for ex in all_examples)
    power_levels = Counter(ex['output']['power_level'] for ex in all_examples)
    
    print("\nStrategies:")
    for strategy, count in strategies.most_common():
        print(f"  {strategy}: {count} ({count/len(all_examples)*100:.1f}%)")
    
    print("\nBrackets:")
    for bracket in sorted(brackets.keys()):
        count = brackets[bracket]
        print(f"  Bracket {bracket}: {count} ({count/len(all_examples)*100:.1f}%)")
    
    print("\nPower Levels:")
    for power in sorted(power_levels.keys()):
        count = power_levels[power]
        print(f"  Level {power}: {count} ({count/len(all_examples)*100:.1f}%)")
    
    print()
    print("=" * 60)
    print("✅ v3 training data ready!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Train v3 model: python scripts/train-v3-structured.py")
    print("2. Test with: python scripts/test-v3-model.py")
    print()

if __name__ == '__main__':
    main()
