# Training Approach v3: Structured Output + Database Lookup

## Problem with v1 and v2

**Current training:** Model generates card names as text
```
Commander: The Ur-Dragon
Deck Name: Dragon Tribal

Commanders:
1x The Ur-Dragon

Creatures:
1x Dragonlord Dromoka
1x Ancient Silver Dragon
1x Aether Tunneler  ← HALLUCINATION (doesn't exist)
...
```

**Why it fails:**
- 3B/7B model tries to memorize 31,000+ card names
- Runs out of capacity, starts hallucinating
- No way to validate card existence during generation
- Can't enforce exactly 100 cards

## Solution: Generate Structured Queries

**New approach:** Model generates database queries, not card names

### Training Format v3

**Input:**
```
Build a Commander deck.
Commander: The Ur-Dragon
Strategy: Dragon tribal with ramp
Power level: 7
Budget: Moderate ($200-500)
Colors: WUBRG
```

**Output (JSON structure):**
```json
{
  "commander": {
    "query": {
      "name": "The Ur-Dragon",
      "type": "Legendary Creature"
    }
  },
  "strategy": {
    "primary": "tribal_dragons",
    "secondary": "ramp",
    "tertiary": "card_draw"
  },
  "card_selection_rules": {
    "creatures": {
      "count": 35,
      "filters": [
        {"type": "Dragon", "min": 20},
        {"type": "Creature", "cmc_max": 3, "tags": ["ramp"], "min": 8}
      ]
    },
    "ramp": {
      "count": 12,
      "filters": [
        {"tags": ["ramp"], "cmc_max": 3}
      ]
    },
    "card_draw": {
      "count": 10,
      "filters": [
        {"tags": ["card_draw"]}
      ]
    },
    "removal": {
      "count": 8,
      "filters": [
        {"tags": ["removal"]}
      ]
    },
    "lands": {
      "count": 35,
      "filters": [
        {"type": "Land", "produces": ["W","U","B","R","G"]}
      ]
    }
  },
  "mana_curve": {
    "0-2": 15,
    "3-4": 25,
    "5-6": 15,
    "7+": 10
  }
}
```

**Then:** Backend executes queries against card database to fill slots

### Benefits

1. **No hallucinations:** Model never generates card names
2. **Guaranteed 100 cards:** Structure enforces counts that sum to 100
3. **Validated queries:** All filters map to database fields
4. **Smaller model works:** 3B can learn patterns, database handles card lookup
5. **Explainable:** Can see why each card was selected
6. **Faster training:** No need to memorize 31,000 cards

## Implementation Plan

### Step 1: Enhance Card Database Schema

**Add query-friendly tags to cards table:**

```sql
-- Already have in prisma/schema.prisma:
model Card {
  id              String   @id
  name            String
  colors          String[] 
  colorIdentity   String[]
  types           String[]
  cmc             Int
  tags            String[]  // ["ramp", "removal", "card-draw", "tribal", etc]
  edhrecRank      Int?
  saltScore       Float?
  powerLevel      Int?
}
```

**Enhance with better tags (run import script with tag detection):**
- "ramp": Produces mana or reduces costs
- "card_draw": Draws cards
- "removal": Destroys/exiles permanents
- "wipe": Board wipes
- "tutor": Searches library
- "tribal_dragons": Benefits dragons
- "tribal_elves": Benefits elves
- etc.

### Step 2: Create New Training Dataset Format

**Convert existing decks to structured queries:**

```python
# scripts/convert-to-structured-training.py
import json
from collections import Counter

def analyze_deck(deck_cards):
    """Convert deck to structured query format"""
    
    # Analyze card types
    type_counts = Counter()
    tag_counts = Counter()
    cmc_distribution = {
        "0-2": 0, "3-4": 0, "5-6": 0, "7+": 0
    }
    
    for card in deck_cards:
        for card_type in card['types']:
            type_counts[card_type] += 1
        for tag in card['tags']:
            tag_counts[tag] += 1
        
        # CMC distribution
        cmc = card['cmc']
        if cmc <= 2:
            cmc_distribution["0-2"] += 1
        elif cmc <= 4:
            cmc_distribution["3-4"] += 1
        elif cmc <= 6:
            cmc_distribution["5-6"] += 1
        else:
            cmc_distribution["7+"] += 1
    
    # Build structured query
    return {
        "card_selection_rules": {
            "creatures": {
                "count": type_counts["Creature"],
                "filters": build_creature_filters(deck_cards)
            },
            "ramp": {
                "count": tag_counts["ramp"],
                "filters": [{"tags": ["ramp"], "cmc_max": 3}]
            },
            "card_draw": {
                "count": tag_counts["card_draw"],
                "filters": [{"tags": ["card_draw"]}]
            },
            "removal": {
                "count": tag_counts["removal"],
                "filters": [{"tags": ["removal"]}]
            },
            "lands": {
                "count": type_counts["Land"],
                "filters": build_land_filters(deck_cards)
            }
        },
        "mana_curve": cmc_distribution
    }

# Convert all 12,500 decks to this format
```

**New training example:**

```jsonl
{
  "instruction": "Build a Commander deck with The Ur-Dragon focused on dragon tribal with ramp and card draw. Power level 7/10. Colors: WUBRG.",
  "output": {
    "strategy": {"primary": "tribal_dragons", "secondary": "ramp"},
    "card_selection_rules": {
      "creatures": {
        "count": 32,
        "filters": [
          {"type": "Dragon", "min": 22},
          {"tags": ["ramp"], "type": "Creature", "cmc_max": 3, "min": 6}
        ]
      },
      "ramp": {"count": 12, "filters": [{"tags": ["ramp"], "cmc_max": 3}]},
      "card_draw": {"count": 10, "filters": [{"tags": ["card_draw"]}]},
      "removal": {"count": 8, "filters": [{"tags": ["removal"]}]},
      "lands": {"count": 38, "filters": [{"type": "Land", "produces": ["W","U","B","R","G"], "enters_tapped": "max_10"}]}
    },
    "mana_curve": {"0-2": 16, "3-4": 24, "5-6": 16, "7+": 6}
  }
}
```

### Step 3: Train Model on Patterns, Not Cards

**What model learns:**
- Dragon tribal → 20+ dragons, tribal synergy
- Ramp strategy → 10-15 ramp cards, CMC ≤ 3
- WUBRG colors → 38-40 lands, multi-color focus
- Power level 7 → balanced mix, some expensive cards
- Card draw → ~10 sources

**What model does NOT learn:**
- Specific card names (database has these)
- Card text/abilities (database has these)
- Current prices (database updated separately)

### Step 4: Backend Deck Builder

**New API flow:**

```typescript
// src/app/api/deck/build-structured/route.ts
export async function POST(req: Request) {
  const { commander, strategy, powerLevel } = await req.json()
  
  // 1. Model generates structured query
  const structuredQuery = await generateStructuredQuery({
    commander,
    strategy,
    powerLevel
  })
  
  // 2. Execute queries against database
  const deck = await executeDeckQuery(structuredQuery)
  
  // 3. Validate and return
  return { deck, query: structuredQuery }
}

async function executeDeckQuery(query) {
  const cards = []
  
  // Execute each filter
  for (const [category, rules] of Object.entries(query.card_selection_rules)) {
    const categoryCards = await prisma.card.findMany({
      where: buildWhereClause(rules.filters),
      orderBy: [
        { edhrecRank: 'asc' },  // Prefer popular cards
        { saltScore: 'asc' }     // Avoid salty cards
      ],
      take: rules.count
    })
    cards.push(...categoryCards)
  }
  
  // Ensure exactly 100 cards
  if (cards.length < 100) {
    // Fill with basics
  } else if (cards.length > 100) {
    // Remove lowest EDHREC rank cards
  }
  
  return cards
}
```

### Step 5: Training Configuration

**Much simpler now:**

```bash
# Can train on smaller dataset (patterns, not cards)
# ~5,000 examples enough (vs 43,631 currently)

# Qwen 2.5 3B might be sufficient!
BATCH_SIZE=4 \
GRADIENT_ACCUMULATION_STEPS=8 \
MAX_SEQ_LENGTH=512 \  # Shorter! Just structure, not full decks
python3 scripts/train-structured-output.py
```

**Training time:** ~5-8 hours (vs 31 hours for v2)

## Comparison: v2 vs v3

| Aspect | v2 (Current) | v3 (Structured) | Winner |
|--------|--------------|-----------------|--------|
| Model task | Generate card names | Generate queries | v3 ✅ |
| Hallucinations | High (>10%) | Zero (no card names) | v3 ✅ |
| Card count | Variable (30-80) | Always 100 (enforced) | v3 ✅ |
| Model size | 7B needed | 3B sufficient | v3 ✅ |
| Training time | 31 hours (3B) | 5-8 hours | v3 ✅ |
| Sequence length | 675 tokens | 512 tokens | v3 ✅ |
| Dataset size | 43,631 examples | 5,000 examples | v3 ✅ |
| Explainability | Black box | Clear queries | v3 ✅ |
| Validation | Post-generation | Built-in | v3 ✅ |
| Flexibility | Hard to modify | Easy to adjust filters | v3 ✅ |

## Migration from v2 to v3

**You don't need RTX 5070 Ti for this!**

The Arc B50 with Qwen 2.5 3B can handle structured output training because:
1. Much simpler task (patterns, not memorization)
2. Shorter sequences (512 vs 675 tokens)
3. Smaller dataset needed (5k vs 43k examples)
4. JSON structure easier to learn than freeform text

**Steps:**
1. Enhance card database with tags (1-2 hours)
2. Convert existing decks to structured format (2-3 hours)
3. Modify training script for JSON output (1 hour)
4. Train on Arc B50 (5-8 hours)
5. Build query executor backend (3-4 hours)

**Total:** ~1-2 days vs ~4 hours RTX setup + 2.5 hours training

## Example Output Comparison

### v2 Output (Text generation - FAILS)
```
Commander: The Ur-Dragon

Creatures:
1x Aether Tunneler  ← Doesn't exist
1x Dragonlord Dromoka
1x Ancient Silver Dragon
... (only 45 cards generated)
```

### v3 Output (Structured queries - SUCCEEDS)
```json
{
  "creatures": {
    "count": 32,
    "filters": [
      {"type": "Dragon", "min": 22},
      {"tags": ["ramp"], "cmc_max": 3, "min": 6}
    ]
  }
}
```

**Backend executes:**
```sql
SELECT * FROM cards 
WHERE type LIKE '%Dragon%' 
  AND color_identity <= ['W','U','B','R','G']
ORDER BY edhrec_rank ASC
LIMIT 22
```

**Result:** 22 real, validated, popular dragons ✅

## Conclusion

**Your insight is 100% correct:** We're training on the wrong thing!

- ❌ Don't train model to memorize cards
- ✅ Train model to understand patterns
- ✅ Use database for card lookup
- ✅ Generate structured queries, not freeform text

**Recommendation:**
1. **Don't migrate to RTX yet** - try v3 on Arc B50 first
2. If v3 works (likely!), you have a working solution in 1-2 days
3. If v3 still needs improvement, RTX makes sense for larger pattern dataset
4. Either way, structured output is the correct approach

Want me to start implementing v3? I can:
1. Update card database schema with better tags
2. Create conversion script for existing decks → structured format
3. Modify training script for JSON output
4. Create backend query executor
