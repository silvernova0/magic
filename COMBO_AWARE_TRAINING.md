# Combo-Aware Training for v3

## The Combo Problem

**Current v2 approach:**
- Model tries to memorize individual cards
- Might accidentally include combo pieces, but doesn't understand WHY
- No awareness of 2-card, 3-card, or 4-card combos

**v3 approach with combo awareness:**
- Model learns combo patterns: "infinite life combo" needs 2+ specific cards
- Database stores known combos with their pieces
- Model requests combos by strategy, database provides the cards

## EDHREC Combo Data Structure

From https://edhrec.com/combos, combos are structured like:

```json
{
  "combo_id": "exquisite-sanguine",
  "cards": ["Exquisite Blood", "Sanguine Bond"],
  "colors": ["B"],
  "result": "Infinite lifegain/lifeloss",
  "tags": ["infinite", "combo", "lifegain"],
  "popularity": 15234,  // Number of decks
  "power_level": 8,
  "requires": {
    "colors": ["B"],
    "cmc_total": 10,
    "setup": "Both must be on battlefield"
  }
}
```

## Implementation Steps

### 1. Scrape EDHREC Combo Data

```python
# scripts/scrape-edhrec-combos.py
import requests
from bs4 import BeautifulSoup
import json
import time

def scrape_combos_by_color():
    """Scrape all combos from EDHREC combo pages"""
    
    color_combos = [
        "w", "u", "b", "r", "g",
        "wu", "wb", "ub", "ur", "br", "bg", "rg", "gw", "gu", "rw",
        "wub", "ubr", "brg", "rgw", "gwu", "wbg", "urw", "bgu", "rwb", "gur",
        "wubr", "ubrg", "brgw", "rgwu", "gwub",
        "wubrg"
    ]
    
    all_combos = []
    
    for colors in color_combos:
        url = f"https://edhrec.com/combos/{colors}"
        print(f"Scraping {url}...")
        
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find combo sections
        combo_sections = soup.find_all('div', class_='combo-card')
        
        for combo in combo_sections:
            combo_data = {
                "combo_id": generate_combo_id(combo),
                "cards": extract_card_names(combo),
                "colors": list(colors.upper()),
                "result": extract_result(combo),
                "tags": extract_tags(combo),
                "popularity": extract_popularity(combo),
                "power_level": estimate_power_level(combo)
            }
            all_combos.append(combo_data)
        
        time.sleep(1)  # Rate limiting
    
    # Save to JSON
    with open('data/edhrec_combos.json', 'w') as f:
        json.dump(all_combos, f, indent=2)
    
    print(f"Scraped {len(all_combos)} combos")
    return all_combos

def extract_card_names(combo_element):
    """Extract card names from combo HTML"""
    cards = []
    card_links = combo_element.find_all('a', class_='card-link')
    for link in card_links:
        cards.append(link.text.strip())
    return cards

def extract_result(combo_element):
    """Extract what the combo does"""
    result_div = combo_element.find('div', class_='combo-result')
    if result_div:
        return result_div.text.strip()
    return "Unknown"

def extract_tags(combo_element):
    """Extract combo tags (infinite, token, etc)"""
    tags = []
    result_text = extract_result(combo_element).lower()
    
    if 'infinite' in result_text:
        tags.append('infinite')
    if 'win' in result_text or 'game' in result_text:
        tags.append('win_con')
    if 'token' in result_text:
        tags.append('tokens')
    if 'damage' in result_text:
        tags.append('damage')
    if 'life' in result_text:
        tags.append('lifegain')
    if 'mana' in result_text:
        tags.append('mana')
    if 'draw' in result_text:
        tags.append('draw')
    
    return tags

def extract_popularity(combo_element):
    """Extract number of decks using this combo"""
    popularity_span = combo_element.find('span', class_='combo-popularity')
    if popularity_span:
        return int(popularity_span.text.replace(',', ''))
    return 0
```

Run: `python3 scripts/scrape-edhrec-combos.py`

Expected result: `data/edhrec_combos.json` with ~500-1000 combos

### 2. Add Combos to Database Schema

```prisma
// prisma/schema.prisma

model Combo {
  id          String   @id @default(uuid())
  name        String   // "Exquisite Blood + Sanguine Bond"
  cards       String[] // Card IDs
  cardNames   String[] // For display
  colors      String[] // Color identity
  result      String   // "Infinite lifegain/lifeloss"
  tags        String[] // ["infinite", "lifegain", "combo"]
  popularity  Int      // Number of decks using it
  powerLevel  Int      // 1-10 scale
  cmc_total   Int      // Total CMC of combo pieces
  
  createdAt   DateTime @default(now())
  updatedAt   DateTime @updatedAt
}
```

Run: `npx prisma db push`

### 3. Import Combo Data to Database

```typescript
// scripts/import-combos.ts
import { PrismaClient } from '@prisma/client'
import combosData from '../data/edhrec_combos.json'

const prisma = new PrismaClient()

async function importCombos() {
  console.log(`Importing ${combosData.length} combos...`)
  
  for (const combo of combosData) {
    // Look up card IDs
    const cardIds = []
    for (const cardName of combo.cards) {
      const card = await prisma.card.findFirst({
        where: { name: cardName }
      })
      if (card) {
        cardIds.push(card.id)
      }
    }
    
    if (cardIds.length === combo.cards.length) {
      await prisma.combo.create({
        data: {
          name: combo.cards.join(' + '),
          cards: cardIds,
          cardNames: combo.cards,
          colors: combo.colors,
          result: combo.result,
          tags: combo.tags,
          popularity: combo.popularity,
          powerLevel: combo.power_level || 7,
          cmc_total: await calculateTotalCMC(cardIds)
        }
      })
    }
  }
  
  console.log('Combos imported!')
}

importCombos()
```

Run: `npx tsx scripts/import-combos.ts`

### 4. Enhanced Training Data with Combo Awareness

**New training format includes combo requests:**

```jsonl
{
  "instruction": "Build a Commander deck with Vito, Thorn of the Dusk Rose focused on lifegain combo. Power level 8/10. Colors: WB.",
  "output": {
    "strategy": {
      "primary": "lifegain_combo",
      "secondary": "aristocrats",
      "win_conditions": ["combo", "drain"]
    },
    "combos": [
      {
        "name": "Exquisite Blood + Sanguine Bond",
        "priority": "high",
        "filters": {
          "tags": ["infinite", "lifegain"],
          "colors": ["B"],
          "cmc_total_max": 12
        }
      },
      {
        "name": "Heliod + Walking Ballista", 
        "priority": "medium",
        "filters": {
          "tags": ["infinite", "damage"],
          "colors": ["W"],
          "cmc_total_max": 6
        }
      }
    ],
    "card_selection_rules": {
      "combo_pieces": {
        "count": 4,
        "method": "from_combos_above"
      },
      "tutors": {
        "count": 6,
        "filters": [{"tags": ["tutor"], "cmc_max": 4}],
        "reason": "Find combo pieces"
      },
      "protection": {
        "count": 8,
        "filters": [{"tags": ["protection", "counterspell"]}],
        "reason": "Protect combo"
      },
      "creatures": {
        "count": 20,
        "filters": [{"tags": ["lifegain"], "type": "Creature"}]
      },
      "removal": {
        "count": 10,
        "filters": [{"tags": ["removal"]}]
      },
      "ramp": {
        "count": 10,
        "filters": [{"tags": ["ramp"], "cmc_max": 3}]
      },
      "lands": {
        "count": 36,
        "filters": [{"type": "Land", "produces": ["W", "B"]}]
      }
    },
    "mana_curve": {"0-2": 18, "3-4": 24, "5-6": 12, "7+": 4}
  }
}
```

**What model learns:**
- "lifegain combo strategy" → Request combos with `tags: ["lifegain", "infinite"]`
- "power level 8" → Include 2-3 combos, not just value
- "Vito commander" → Synergizes with lifegain combos
- Always include tutors when requesting combos
- Always include protection for combo pieces

### 5. Backend Combo-Aware Deck Builder

```typescript
// src/lib/deck-builder-v3.ts
import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

export async function buildDeckFromStructure(structure: any) {
  const deckCards = []
  
  // 1. Handle combo requests first
  if (structure.combos && structure.combos.length > 0) {
    for (const comboRequest of structure.combos) {
      // Find matching combos from database
      const combos = await prisma.combo.findMany({
        where: {
          tags: { hasSome: comboRequest.filters.tags },
          colors: { hasSome: structure.colors },
          cmc_total: { lte: comboRequest.filters.cmc_total_max || 20 }
        },
        orderBy: { popularity: 'desc' },
        take: 1
      })
      
      if (combos.length > 0) {
        // Add all combo pieces
        for (const cardId of combos[0].cards) {
          const card = await prisma.card.findUnique({ where: { id: cardId } })
          if (card) {
            deckCards.push(card)
          }
        }
      }
    }
  }
  
  // 2. Handle regular card selection
  for (const [category, rules] of Object.entries(structure.card_selection_rules)) {
    if (category === 'combo_pieces') {
      // Already handled above
      continue
    }
    
    const categoryCards = await prisma.card.findMany({
      where: buildWhereClause(rules.filters),
      orderBy: [
        { edhrecRank: 'asc' },
        { saltScore: 'asc' }
      ],
      take: rules.count
    })
    
    deckCards.push(...categoryCards)
  }
  
  // 3. Ensure exactly 100 cards
  return balanceTo100Cards(deckCards)
}
```

### 6. Training Data Examples with Real Combos

**Example 1: Lifegain Combo Deck**
```json
{
  "instruction": "Build a WB lifegain combo deck with Vito, Thorn of the Dusk Rose. Power level 8.",
  "output": {
    "strategy": {"primary": "lifegain_combo"},
    "combos": [
      {"filters": {"tags": ["lifegain", "infinite"], "colors": ["B"]}}
    ],
    "card_selection_rules": {
      "combo_pieces": {"count": 4},
      "tutors": {"count": 6, "filters": [{"tags": ["tutor"]}]},
      "creatures": {"count": 22, "filters": [{"tags": ["lifegain"]}]},
      "removal": {"count": 10},
      "ramp": {"count": 10},
      "lands": {"count": 36}
    }
  }
}
```

**Example 2: Infinite Mana Deck**
```json
{
  "instruction": "Build a Simic infinite mana deck with Kinnan, Bonder Prodigy. Power level 9.",
  "output": {
    "strategy": {"primary": "infinite_mana"},
    "combos": [
      {"filters": {"tags": ["mana", "infinite"], "colors": ["G", "U"]}}
    ],
    "card_selection_rules": {
      "combo_pieces": {"count": 6},
      "mana_dorks": {"count": 12, "filters": [{"tags": ["ramp"], "type": "Creature"}]},
      "protection": {"count": 8, "filters": [{"tags": ["counterspell", "protection"]}]},
      "tutors": {"count": 6},
      "win_cons": {"count": 4, "filters": [{"tags": ["win_con"]}, {"cmc_min": 6}]},
      "card_draw": {"count": 10},
      "lands": {"count": 32}
    }
  }
}
```

**Example 3: No Combos (Fair Deck)**
```json
{
  "instruction": "Build a Gruul stompy deck with Xenagos, God of Revels. Power level 6. No combos.",
  "output": {
    "strategy": {"primary": "stompy", "avoid_combos": true},
    "combos": [],
    "card_selection_rules": {
      "creatures": {"count": 32, "filters": [{"power_min": 4}]},
      "ramp": {"count": 12},
      "card_draw": {"count": 8},
      "removal": {"count": 8},
      "lands": {"count": 38}
    }
  }
}
```

### 7. Model Learns Combo Patterns

**What the model figures out:**
- Power level 7-8 → Usually includes 1-2 combos
- Power level 9-10 (cEDH) → Multiple combos + tutors + fast mana
- Power level 4-6 → Avoid combos
- "Combo" strategy → Need tutors (4-6), protection (6-8)
- Infinite mana combos → Need outlet cards (big X spells, draw engines)
- Lifegain combos → Synergize with lifegain matters cards

**What the model does NOT need to know:**
- Which specific cards form combos (database has this)
- How many combo pieces exist (database counts this)
- Which combos are popular (database ranks this)

## Training Dataset Preparation

```python
# scripts/prepare-combo-aware-dataset.py

def convert_deck_to_combo_aware_structure(deck):
    """Analyze deck and identify combos used"""
    
    deck_card_names = [card['name'] for card in deck['mainboard']]
    
    # Check against combo database
    combos_in_deck = []
    for combo in known_combos:
        if all(card in deck_card_names for card in combo['cards']):
            combos_in_deck.append({
                "name": combo['name'],
                "filters": {
                    "tags": combo['tags'],
                    "colors": combo['colors'],
                    "cmc_total_max": combo['cmc_total'] + 2
                }
            })
    
    # Build structure
    structure = {
        "strategy": infer_strategy(deck),
        "combos": combos_in_deck,
        "card_selection_rules": analyze_card_distribution(deck)
    }
    
    return structure
```

## Benefits of Combo-Aware Training

| Feature | v2 (Text Gen) | v3 (Structured) | v3 + Combos |
|---------|---------------|-----------------|-------------|
| Knows combos exist | Maybe | No | ✅ Yes |
| Includes combo pieces | Random | No | ✅ Intentional |
| Includes tutors for combos | Random | No | ✅ Automatic |
| Includes protection | Random | Maybe | ✅ Yes |
| Power level scaling | No | Maybe | ✅ Yes |
| Avoids combos when requested | No | No | ✅ Yes |
| Explains why cards included | No | Partial | ✅ Full |

## Example API Response

**Request:**
```json
{
  "commander": "Vito, Thorn of the Dusk Rose",
  "strategy": "lifegain combo",
  "power_level": 8
}
```

**Model generates structure, backend executes, response:**
```json
{
  "deck": {
    "commander": {"name": "Vito, Thorn of the Dusk Rose"},
    "combos_included": [
      {
        "name": "Exquisite Blood + Sanguine Bond",
        "result": "Infinite lifegain/lifeloss",
        "pieces": [
          {"name": "Exquisite Blood", "cmc": 5},
          {"name": "Sanguine Bond", "cmc": 5}
        ]
      }
    ],
    "mainboard": [
      // 100 cards including combo pieces, tutors, protection
    ],
    "explanation": {
      "combo_pieces": 2,
      "tutors": 6,
      "protection": 8,
      "lifegain_payoffs": 15,
      "win_conditions": ["Infinite combo", "Life drain"]
    }
  }
}
```

## Implementation Timeline

**Phase 1: Combo Data (4-6 hours)**
- Scrape EDHREC combos
- Add Combo model to schema
- Import to database

**Phase 2: Training Data Conversion (3-4 hours)**
- Analyze existing decks for combos
- Convert to combo-aware structure
- Generate training examples

**Phase 3: Training (5-8 hours)**
- Train model on combo-aware patterns
- Validate combo selection logic

**Phase 4: Backend Integration (3-4 hours)**
- Build combo-aware query executor
- Add combo explanation to responses

**Total: 15-22 hours** (2-3 days part-time)

## Conclusion

Combos are the **perfect example** of pattern learning vs memorization:

❌ **Bad (v2):** Model memorizes "Exquisite Blood goes with Sanguine Bond"
✅ **Good (v3):** Model learns "lifegain combo strategy needs infinite combos with lifegain tags"

The database knows which cards form combos. The model learns when to request combos and what kind.

**Next Steps:**
1. Scrape EDHREC combo data
2. Add Combo model to database
3. Convert training data to combo-aware format
4. Train on Arc B50 (no RTX needed!)

Want me to start with combo scraping?
