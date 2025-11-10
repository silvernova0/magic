# Training v3: Rules-Based Deck Building with Pattern Learning

## The Complete Picture

You've identified the THREE key knowledge sources:

### 1. Deck Building Rules (Ratios & Constraints)
**Source:** Mythic Vault, Command Zone podcast, competitive wisdom
**What:** Universal deck building principles

```json
{
  "bracket_1_3": {
    "lands": {"min": 34, "max": 40},
    "ramp": {"min": 10, "max": 13},
    "card_draw": {"min": 10, "max": 10},
    "removal": {"min": 6, "max": 12},
    "board_wipes": {"min": 2, "max": 5},
    "graveyard_recursion": {"min": 2, "max": 2},
    "graveyard_hate": {"min": 1, "max": 2},
    "tutors": {"min": 1, "max": 2},
    "finishers": {"min": 1, "max": 2},
    "protection": {"min": 1, "max": 3}
  },
  "bracket_4_5": {
    "lands": {"min": 30, "max": 35},
    "ramp": {"min": 12, "max": 16},  // More fast mana
    "card_draw": {"min": 12, "max": 15},
    "removal": {"min": 8, "max": 15},
    "tutors": {"min": 6, "max": 12},  // Way more tutors!
    "combo_pieces": {"min": 4, "max": 8},
    "protection": {"min": 6, "max": 10}  // Protect combo
  }
}
```

### 2. Known Combos (EDHREC)
**Source:** https://edhrec.com/combos
**What:** Proven 2-card, 3-card, 4-card combos

Already covered in COMBO_AWARE_TRAINING.md

### 3. Commander-Specific Patterns (EDHREC Average Decks)
**Source:** https://edhrec.com/average-decks/{commander-name}
**What:** What cards/strategies work for EACH commander

**This is GOLD!** Example:
- https://edhrec.com/average-decks/shorikai-genesis-engine
- https://edhrec.com/average-decks/the-ur-dragon
- https://edhrec.com/average-decks/atraxa-praetors-voice

## Complete v3 Training Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    USER REQUEST                              │
│  "Build The Ur-Dragon deck, power level 7, tribal dragons"  │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                  TRAINED MODEL (3B)                          │
│                                                               │
│  Learns PATTERNS from 3 knowledge sources:                   │
│                                                               │
│  1. Deck Building Rules (ratios)                            │
│     → "Power 7 = bracket 3 → 10 ramp, 10 draw, 36 lands"    │
│                                                               │
│  2. Combo Patterns (when to use)                            │
│     → "Power 7 = 1 combo, Power 9 = 3+ combos"              │
│                                                               │
│  3. Commander Patterns (strategy)                           │
│     → "Ur-Dragon = tribal, 25+ dragons, 12 ramp, enablers"  │
│                                                               │
│  Output: Structured JSON with filters & counts              │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                  DATABASE EXECUTOR                           │
│                                                               │
│  Applies filters to card database:                           │
│  - 31,000+ cards with tags                                  │
│  - 500+ known combos                                        │
│  - Commander synergies                                       │
│  - EDHREC rankings                                          │
│                                                               │
│  Returns: Exactly 100 validated cards                       │
└─────────────────────────────────────────────────────────────┘
```

### Structured Deck Executor (NEW)

- Script: `scripts/build_deck_from_structure.py`
- Usage: `python3 scripts/build_deck_from_structure.py generated_decks/v3_test/ur-dragon-tribal.json`
- Requirements: `prisma/dev.db` populated (run imports first)
- Flow:
  1. Loads structured JSON (model output)
  2. Queries Prisma SQLite (via `sqlite3`) and infers tags (ramp, card_draw, removal, etc.)
  3. Picks cards per filter, fills remaining slots, enforces commander color identity
  4. Outputs `generated_decks/v3_executed/<name>-deck.json` with a 100-card list plus warnings/errors
- Notes:
  - Falls back to staples/basic lands if a filter runs dry (logging warnings)
  - Tag inference currently heuristics-based (oracle text keywords); extend as DB tagging improves
  - Designed to be called from Python validations now; Next.js API can port logic when node runtime available

## Implementation Plan

### Phase 1: Scrape EDHREC Average Decks (NEW!)

```python
# scripts/scrape-edhrec-average-decks.py
import requests
from bs4 import BeautifulSoup
import json
import time

def get_all_commanders():
    """Get list of all commanders from database"""
    # We already have 2,059+ commanders from previous scraping
    commanders = prisma.card.findMany({
        where: { types: { has: "Legendary" } }
    })
    return [cmd.name for cmd in commanders]

def scrape_average_deck(commander_name):
    """Scrape EDHREC average deck for a commander"""
    
    # Convert "The Ur-Dragon" → "the-ur-dragon"
    slug = commander_name.lower().replace(' ', '-').replace(',', '')
    url = f"https://edhrec.com/average-decks/{slug}"
    
    try:
        response = requests.get(url)
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract card categories and counts
        deck_data = {
            "commander": commander_name,
            "url": url,
            "categories": {},
            "top_cards": [],
            "themes": [],
            "avg_cmc": 0,
            "card_count": {}
        }
        
        # Parse card sections
        card_sections = soup.find_all('div', class_='card-container')
        for section in card_sections:
            category = section.find('h3').text.strip() if section.find('h3') else "Other"
            cards_in_category = section.find_all('a', class_='card-link')
            
            deck_data["categories"][category] = {
                "count": len(cards_in_category),
                "cards": [card.text.strip() for card in cards_in_category]
            }
        
        # Extract themes/tags
        theme_section = soup.find('div', class_='themes')
        if theme_section:
            deck_data["themes"] = [
                theme.text.strip() 
                for theme in theme_section.find_all('span', class_='theme-tag')
            ]
        
        # Get card type distribution
        type_dist = soup.find('div', class_='type-distribution')
        if type_dist:
            for type_item in type_dist.find_all('div', class_='type-item'):
                type_name = type_item.find('span', class_='type-name').text
                type_count = int(type_item.find('span', class_='type-count').text)
                deck_data["card_count"][type_name] = type_count
        
        return deck_data
        
    except Exception as e:
        print(f"Error scraping {commander_name}: {e}")
        return None

def scrape_all_average_decks():
    """Scrape average decks for all commanders"""
    
    commanders = get_all_commanders()
    average_decks = []
    
    print(f"Scraping average decks for {len(commanders)} commanders...")
    
    for i, commander in enumerate(commanders):
        if i % 100 == 0:
            print(f"Progress: {i}/{len(commanders)}")
        
        deck_data = scrape_average_deck(commander)
        if deck_data:
            average_decks.append(deck_data)
        
        time.sleep(0.5)  # Rate limiting
    
    # Save to JSON
    with open('data/edhrec_average_decks.json', 'w') as f:
        json.dump(average_decks, f, indent=2)
    
    print(f"Scraped {len(average_decks)} average decks")
    return average_decks
```

**Expected output:** `data/edhrec_average_decks.json` with ~2,000+ commander patterns

### Phase 2: Create Deck Building Rules Database

```python
# scripts/create-deck-rules.py
import json

DECK_BUILDING_RULES = {
    "brackets": {
        "1": {
            "name": "Precon-level",
            "power_range": [1, 3],
            "rules": {
                "lands": {"min": 36, "max": 40, "reason": "Consistent mana"},
                "ramp": {"min": 8, "max": 10, "reason": "Catch up to higher brackets"},
                "card_draw": {"min": 8, "max": 10, "reason": "Keep hand full"},
                "removal": {"min": 4, "max": 8, "reason": "Answer threats"},
                "board_wipes": {"min": 1, "max": 3, "reason": "Reset board"},
                "tutors": {"min": 0, "max": 1, "reason": "Low power, no tutors"},
                "combos": {"min": 0, "max": 0, "reason": "Avoid combos"},
                "protection": {"min": 0, "max": 2, "reason": "Limited interaction"}
            }
        },
        "2": {
            "name": "Casual-optimized",
            "power_range": [4, 5],
            "rules": {
                "lands": {"min": 35, "max": 38, "reason": "Efficient mana base"},
                "ramp": {"min": 10, "max": 12, "reason": "Accelerate gameplan"},
                "card_draw": {"min": 10, "max": 12, "reason": "Card advantage"},
                "removal": {"min": 6, "max": 10, "reason": "Flexible answers"},
                "board_wipes": {"min": 2, "max": 4, "reason": "Reset when behind"},
                "graveyard_recursion": {"min": 2, "max": 3, "reason": "Value engine"},
                "tutors": {"min": 1, "max": 2, "reason": "Find key cards"},
                "combos": {"min": 0, "max": 1, "reason": "Optional combo finish"},
                "protection": {"min": 1, "max": 3, "reason": "Protect key pieces"}
            }
        },
        "3": {
            "name": "Focused-competitive",
            "power_range": [6, 7],
            "rules": {
                "lands": {"min": 34, "max": 36, "reason": "Optimized mana"},
                "ramp": {"min": 10, "max": 13, "reason": "Fast mana important"},
                "card_draw": {"min": 10, "max": 12, "reason": "Consistent card flow"},
                "removal": {"min": 8, "max": 12, "reason": "Interact heavily"},
                "board_wipes": {"min": 2, "max": 5, "reason": "Control board"},
                "graveyard_recursion": {"min": 2, "max": 4, "reason": "Recursion loops"},
                "graveyard_hate": {"min": 1, "max": 2, "reason": "Stop opponents GY"},
                "tutors": {"min": 2, "max": 4, "reason": "Find win cons"},
                "combos": {"min": 1, "max": 2, "reason": "Primary win con"},
                "protection": {"min": 2, "max": 4, "reason": "Protect combos"}
            }
        },
        "4": {
            "name": "High-power",
            "power_range": [8, 9],
            "rules": {
                "lands": {"min": 32, "max": 35, "reason": "Lower curve, fast mana"},
                "ramp": {"min": 12, "max": 15, "reason": "Explosive starts"},
                "card_draw": {"min": 12, "max": 15, "reason": "Draw into combo"},
                "removal": {"min": 10, "max": 15, "reason": "Stop other combos"},
                "board_wipes": {"min": 1, "max": 3, "reason": "Emergency resets"},
                "tutors": {"min": 6, "max": 10, "reason": "Find combo ASAP"},
                "combos": {"min": 2, "max": 4, "reason": "Multiple win paths"},
                "protection": {"min": 6, "max": 10, "reason": "Protect the win"},
                "fast_mana": {"min": 4, "max": 8, "reason": "Mana Crypt, Sol Ring, etc"}
            }
        },
        "5": {
            "name": "cEDH",
            "power_range": [9, 10],
            "rules": {
                "lands": {"min": 28, "max": 32, "reason": "Minimal lands, max efficiency"},
                "ramp": {"min": 14, "max": 18, "reason": "All fast mana"},
                "card_draw": {"min": 15, "max": 20, "reason": "Draw whole deck"},
                "removal": {"min": 12, "max": 18, "reason": "Stop all combo attempts"},
                "tutors": {"min": 8, "max": 15, "reason": "Tutor combo every game"},
                "combos": {"min": 3, "max": 6, "reason": "Redundant win cons"},
                "protection": {"min": 8, "max": 15, "reason": "Counter wars"},
                "fast_mana": {"min": 8, "max": 12, "reason": "Win turn 3-4"}
            }
        }
    },
    
    "strategy_modifiers": {
        "tribal": {
            "creatures": "+5 to +10",  // More creatures for tribal
            "lords": {"min": 3, "max": 6},  // Tribal anthem effects
            "tribal_payoffs": {"min": 4, "max": 8}
        },
        "combo": {
            "tutors": "+2 to +4",
            "protection": "+2 to +4",
            "combo_pieces": {"min": 4, "max": 8}
        },
        "aggro": {
            "creatures": "+8 to +12",
            "lands": "-2 to -3",  // Lower curve
            "ramp": "-2 to -4"
        },
        "control": {
            "removal": "+4 to +8",
            "board_wipes": "+2 to +4",
            "card_draw": "+2 to +4",
            "lands": "+1 to +2"
        },
        "stompy": {
            "creatures": "+5 to +10",
            "ramp": "+3 to +5",
            "big_creatures": {"min": 8, "max": 15}
        }
    }
}

# Save rules
with open('data/deck_building_rules.json', 'w') as f:
    json.dump(DECK_BUILDING_RULES, f, indent=2)
```

### Phase 3: Training Data Format (Complete Example)

**Input:**
```
Build a Commander deck.
Commander: The Ur-Dragon
Strategy: Dragon tribal
Power level: 7
Bracket: 3
Colors: WUBRG
```

**Output (Model learns to generate this structure):**
```json
{
  "commander": "The Ur-Dragon",
  "bracket": 3,
  "power_level": 7,
  "strategy": {
    "primary": "tribal_dragons",
    "secondary": "ramp",
    "modifiers": ["big_creatures"]
  },
  
  "base_rules": {
    "from_bracket_3": {
      "lands": 35,
      "ramp": 12,
      "card_draw": 10,
      "removal": 10,
      "board_wipes": 3,
      "tutors": 3,
      "combos": 0,  // Power 7, no combo needed
      "protection": 3
    }
  },
  
  "strategy_adjustments": {
    "tribal_modifier": {
      "creatures": "+8",  // More dragons
      "tribal_lords": 4,
      "tribal_payoffs": 6
    }
  },
  
  "final_composition": {
    "lands": {
      "count": 35,
      "filters": [
        {"type": "Land", "produces": ["W","U","B","R","G"]},
        {"tags": ["five_color"], "priority": "high"}
      ]
    },
    "ramp": {
      "count": 12,
      "filters": [
        {"tags": ["ramp"], "cmc_max": 3},
        {"types": ["Artifact"], "priority": "high"}  // Ur-Dragon wants artifacts
      ],
      "reason": "Enable big dragons early"
    },
    "creatures": {
      "count": 30,  // Base 22 + tribal modifier +8
      "filters": [
        {"type": "Dragon", "min": 22, "reason": "Tribal core"},
        {"tags": ["tribal_dragons"], "min": 4, "reason": "Dragon lords"},
        {"tags": ["ramp"], "type": "Creature", "max": 4, "reason": "Mana dorks"}
      ],
      "commander_synergy": "the_ur_dragon_cheats_dragons"
    },
    "tribal_payoffs": {
      "count": 6,
      "filters": [
        {"tags": ["tribal_dragons", "anthem"], "reason": "Make dragons better"},
        {"tags": ["tribal_dragons", "card_draw"], "reason": "Draw off dragons"}
      ]
    },
    "card_draw": {
      "count": 10,
      "filters": [
        {"tags": ["card_draw"]},
        {"tags": ["tribal_dragons", "card_draw"], "priority": "high"}  // Temur Ascendancy
      ]
    },
    "removal": {
      "count": 10,
      "filters": [
        {"tags": ["removal"], "cmc_max": 4},
        {"colors": {"hasSome": ["W", "B"]}, "priority": "high"}  // Best removal colors
      ]
    },
    "board_wipes": {
      "count": 3,
      "filters": [{"tags": ["board_wipe"]}]
    },
    "tutors": {
      "count": 3,
      "filters": [{"tags": ["tutor"], "cmc_max": 4}]
    },
    "protection": {
      "count": 3,
      "filters": [{"tags": ["protection", "counterspell"]}]
    }
  },
  
  "commander_specific_patterns": {
    "from_edhrec_average": {
      "high_priority_cards": [
        "Scion of the Ur-Dragon",  // Top card for this commander
        "Dragon Tempest",
        "Rhythm of the Wild",
        "Temur Ascendancy"
      ],
      "themes": ["dragon_tribal", "ramp", "haste_enablers"]
    }
  },
  
  "validation": {
    "total_cards": 100,
    "breakdown": "35 lands + 12 ramp + 30 creatures + 6 tribal + 10 draw + 10 removal + 3 wipes + 3 tutors + 3 protection = 112 → adjust -12 from creatures"
  }
}
```

### Phase 4: Convert Existing Data to v3 Format

```python
# scripts/convert-to-v3-format.py
import json

def convert_deck_to_v3(deck, edhrec_average, deck_rules):
    """Convert scraped deck to v3 training format"""
    
    commander = deck['commander']
    strategy = infer_strategy(deck)
    power_level = deck.get('power_level', 7)
    bracket = get_bracket_from_power(power_level)
    
    # Get base rules for bracket
    base_rules = deck_rules['brackets'][str(bracket)]['rules']
    
    # Apply strategy modifiers
    strategy_mods = deck_rules['strategy_modifiers'].get(strategy['primary'], {})
    
    # Analyze actual deck composition
    actual_composition = analyze_deck_categories(deck)
    
    # Get EDHREC average deck patterns for this commander
    edhrec_patterns = edhrec_average.get(commander, {})
    
    return {
        "instruction": f"Build a Commander deck with {commander} focused on {strategy['primary']}. Power level {power_level}.",
        "output": {
            "commander": commander,
            "bracket": bracket,
            "power_level": power_level,
            "strategy": strategy,
            "base_rules": base_rules,
            "strategy_adjustments": strategy_mods,
            "final_composition": actual_composition,
            "commander_specific_patterns": edhrec_patterns
        }
    }

def analyze_deck_categories(deck):
    """Categorize cards in deck"""
    categories = {
        "lands": [],
        "ramp": [],
        "creatures": [],
        "removal": [],
        "card_draw": [],
        "board_wipes": [],
        "tutors": [],
        "combo_pieces": [],
        "protection": [],
        "tribal_payoffs": []
    }
    
    for card in deck['mainboard']:
        # Check card tags (from our enhanced database)
        if 'Land' in card['types']:
            categories['lands'].append(card)
        if 'ramp' in card.get('tags', []):
            categories['ramp'].append(card)
        if 'Creature' in card['types']:
            categories['creatures'].append(card)
        # ... etc for all categories
    
    # Build filter rules from analysis
    composition = {}
    for category, cards in categories.items():
        if len(cards) > 0:
            composition[category] = {
                "count": len(cards),
                "filters": infer_filters_from_cards(cards)
            }
    
    return composition
```

### Phase 5: Enhanced Database Schema

```prisma
// prisma/schema.prisma

model Card {
  id              String   @id
  name            String
  colors          String[]
  colorIdentity   String[]
  types           String[]
  subtypes        String[]  // NEW: For tribal (Dragon, Elf, etc)
  cmc             Int
  power           Int?
  toughness       Int?
  
  // Enhanced tagging
  tags            String[]  // ramp, removal, card_draw, tutor, etc
  edhrecRank      Int?
  saltScore       Float?
  powerLevel      Int?
  
  // NEW: Commander-specific synergy
  commanderSynergies String[]  // List of commander names this synergizes with
  
  // NEW: Combo associations
  comboPieces     Combo[]   @relation("ComboCards")
}

model Combo {
  id          String   @id @default(uuid())
  name        String
  cards       Card[]   @relation("ComboCards")
  cardNames   String[]
  colors      String[]
  result      String
  tags        String[]
  popularity  Int
  powerLevel  Int
  cmc_total   Int
}

model DeckBuildingRule {
  id          String @id @default(uuid())
  bracket     Int
  category    String  // "ramp", "removal", etc
  min         Int
  max         Int
  reason      String
  
  // Strategy modifiers
  strategy    String?  // "tribal", "combo", etc
  modifier    String?  // "+2", "-3", etc
}

model CommanderPattern {
  id              String @id @default(uuid())
  commanderName   String @unique
  themes          String[]
  topCards        String[]  // Most popular cards for this commander
  cardDistribution Json   // Type/category breakdown
  avgCMC          Float
  edhrecUrl       String
}
```

### Phase 6: Model Training Configuration

**Simplified training (learns patterns, not cards):**

```python
# scripts/train-v3-structured.py

MAX_SEQ_LENGTH = 768  # JSON structure + filters
BATCH_SIZE = 4
GRADIENT_ACCUMULATION_STEPS = 8
EPOCHS = 3

# Training data: ~5,000 examples
# - 2,000 from EDHREC average decks
# - 2,000 from MTGGoldfish decks  
# - 1,000 from Moxfield decks

# Each example: Instruction → Structured JSON output
# Model learns to:
# 1. Map power level → bracket rules
# 2. Map strategy → category adjustments
# 3. Map commander → EDHREC patterns
# 4. Generate valid filters for database queries
```

**Training time on Arc B50:** ~4-6 hours (vs 31 hours for v2!)

### Phase 7: Backend Query Executor

```typescript
// src/lib/deck-builder-v3-complete.ts

export async function buildDeck(request: DeckRequest) {
  // 1. Model generates structured output
  const structure = await model.generate(request)
  
  // 2. Execute each category query
  const deck = {
    commander: await getCommander(structure.commander),
    mainboard: []
  }
  
  for (const [category, spec] of Object.entries(structure.final_composition)) {
    const cards = await executeCardQuery({
      filters: spec.filters,
      count: spec.count,
      colorIdentity: request.colors,
      excludeIds: deck.mainboard.map(c => c.id)  // No duplicates
    })
    
    deck.mainboard.push(...cards)
  }
  
  // 3. Add high-priority commander-specific cards
  if (structure.commander_specific_patterns?.high_priority_cards) {
    const priorityCards = await prisma.card.findMany({
      where: {
        name: { in: structure.commander_specific_patterns.high_priority_cards }
      }
    })
    // Swap out lower-priority cards
    deck.mainboard = integratePriorityCards(deck.mainboard, priorityCards)
  }
  
  // 4. Validate exactly 100 cards
  deck.mainboard = balanceTo100(deck.mainboard)
  
  return deck
}
```

## Training Data Statistics

**v2 (Failed):**
- 43,631 examples
- 675 tokens per example
- Model task: Generate 100 card names
- Result: Hallucinations, wrong counts

**v3 (New):**
- ~5,000 examples (8.7x fewer!)
- 768 tokens per example
- Model task: Generate structure with filters
- Expected result: 0% hallucinations, always 100 cards

## Benefits Summary

| Feature | v2 | v3 |
|---------|----|----|
| Hallucinations | High | Zero ✅ |
| Card count accuracy | Variable | Always 100 ✅ |
| Training data needed | 43k | 5k ✅ |
| Training time | 31 hours | 4-6 hours ✅ |
| Model size needed | 7B | 3B ✅ |
| Explainability | None | Full ✅ |
| Uses deck building rules | No | Yes ✅ |
| Uses combo knowledge | No | Yes ✅ |
| Uses commander patterns | No | Yes ✅ |
| Validates against database | No | Yes ✅ |

## Implementation Timeline

**Week 1:**
- Day 1-2: Scrape EDHREC average decks (2,000+)
- Day 3: Create deck building rules database
- Day 4-5: Convert existing training data to v3 format
- Day 6: Enhance card database with better tags

**Week 2:**
- Day 1-2: Train model on Arc B50 (4-6 hours train time)
- Day 3: Build backend query executor
- Day 4-5: Test and validate
- Day 6: Integrate into Next.js app

**Total: ~2 weeks**

## Next Steps

Want me to start with:
1. **EDHREC average deck scraper** - Gets commander-specific patterns
2. **Deck building rules database** - Codifies the Mythic Vault wisdom
3. **Data conversion script** - Convert existing 12k decks to v3 format

This approach combines:
- ✅ Deck building fundamentals (Mythic Vault ratios)
- ✅ Combo knowledge (EDHREC combos)  
- ✅ Commander patterns (EDHREC average decks)
- ✅ Database lookup (no hallucinations)
- ✅ Pattern learning (not memorization)

**Much more productive path indeed!** 🎯
