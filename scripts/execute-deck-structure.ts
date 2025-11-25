#!/usr/bin/env ts-node
/**
 * Execute deck structure JSON into complete 100-card decklists
 * Uses Prisma database to find cards matching the filters
 */

import { PrismaClient, Prisma } from '@prisma/client';
import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'fs';
import { join } from 'path';

const prisma = new PrismaClient();

// Load land count reference data
function loadLandReference(): any {
  try {
    const refPath = join(process.cwd(), 'data', 'land_count_reference.json');
    if (existsSync(refPath)) {
      const data = readFileSync(refPath, 'utf-8');
      return JSON.parse(data);
    }
  } catch (error) {
    console.error('Warning: Could not load land reference data');
  }
  
  // Fallback defaults
  return {
    commanders: {},
    bracket_defaults: {
      '2': { min: 36, max: 38, avg: 36 },
      '3': { min: 34, max: 36, avg: 34 },
      '4': { min: 30, max: 34, avg: 30 },
      '5': { min: 28, max: 32, avg: 28 }
    },
    global_default: { min: 32, max: 38, avg: 35 }
  };
}

const landReference = loadLandReference();

function getLandRange(commander: string, bracket: number): { min: number; max: number } {
  const bracketStr = bracket.toString();
  
  // Try commander-specific data first
  if (landReference.commanders[commander]?.[bracketStr]) {
    const stats = landReference.commanders[commander][bracketStr];
    console.log(`📊 Using ${commander} training data (bracket ${bracket}): ${stats.min}-${stats.max} lands (avg: ${stats.avg}, ${stats.samples} samples)`);
    return { min: stats.min, max: stats.max };
  }
  
  // Fall back to bracket defaults
  if (landReference.bracket_defaults[bracketStr]) {
    const stats = landReference.bracket_defaults[bracketStr];
    console.log(`📊 Using bracket ${bracket} default: ${stats.min}-${stats.max} lands (avg: ${stats.avg}, ${stats.samples} samples)`);
    return { min: stats.min, max: stats.max };
  }
  
  // Last resort: global default
  const stats = landReference.global_default;
  console.log(`📊 Using global default: ${stats.min}-${stats.max} lands (avg: ${stats.avg})`);
  return { min: stats.min, max: stats.max };
}

interface DeckStructure {
  commander: string;
  strategy: string;
  power_level: number;
  bracket: number;
  card_selection: {
    [category: string]: {
      count: number;
      filters: Array<{
        types?: string[];
        subtypes?: string[];
        tags?: string[];
        cmc_max?: number;
        cmc_min?: number;
        instant_speed?: boolean;
        colors_within?: string[];
        reason?: string;
      }>;
    };
  };
  priority_cards?: string[];
  userId?: string;  // For collection filtering
  useCollectionOnly?: boolean;  // Whether to restrict to user's collection
}

interface DeckCard {
  name: string;
  category: string;
  cmc: number;
  type: string;
  colorIdentity?: string[];
  oracleText?: string | null;
}

async function executeFilters(
  filters: any[],
  count: number,
  commanderColors: string,
  userId?: string,
  useCollectionOnly?: boolean
): Promise<DeckCard[]> {
  const cards: DeckCard[] = [];

  for (const filter of filters) {
    const whereConditions: Prisma.CardWhereInput[] = [];

    // Types filter
    if (filter.types) {
      const typeConditions = filter.types.map((type: string) => ({
        typeLine: { contains: type },
      }));
      whereConditions.push({ OR: typeConditions });
    }

    // Subtypes filter
    if (filter.subtypes) {
      const subtypeConditions = filter.subtypes.map((subtype: string) => ({
        typeLine: { contains: subtype },
      }));
      whereConditions.push({ OR: subtypeConditions });
    }

    // Tags filter
    if (filter.tags) {
      const tagMap: { [key: string]: string[] } = {
        ramp: ['search', 'land', 'add', 'mana'],
        removal: ['destroy', 'exile', 'remove'],
        card_draw: ['draw', 'card'],
        board_wipe: ['destroy all', 'exile all'],
        tutor: ['search your library'],
        protection: ['counter', 'hexproof', 'protection'],
        counterspell: ['counter target'],
      };

      const tagConditions: Prisma.CardWhereInput[] = [];
      for (const tag of filter.tags) {
        const searchTerms = tagMap[tag] || [tag];
        for (const term of searchTerms) {
          tagConditions.push({
            oracleText: { contains: term },
          });
        }
      }
      if (tagConditions.length > 0) {
        whereConditions.push({ OR: tagConditions });
      }
    }

    // CMC filters
    if (filter.cmc_max !== undefined) {
      whereConditions.push({ cmc: { lte: filter.cmc_max } });
    }
    if (filter.cmc_min !== undefined) {
      whereConditions.push({ cmc: { gte: filter.cmc_min } });
    }

    // NOTE: Color identity filtering is done in post-processing
    // because we need subset logic, not string contains
    // A card with colorIdentity "WUBRG" should NOT match a "W" commander
    // We'll filter by color identity after fetching candidates

    // Instant speed filter
    if (filter.instant_speed) {
      whereConditions.push({
        typeLine: { contains: 'Instant' },
      });
    }

    // Execute query
    try {
      // Add filter to exclude Arena-only cards (those starting with "A-")
      // Also exclude non-Commander-legal card types
      // CRITICAL: Filter for Commander legality
      const finalConditions = whereConditions.length > 0 ? { AND: whereConditions } : {};
      
      // Basic lands that are always available (unlimited in Commander)
      const basicLandNames = [
        'Plains', 'Island', 'Swamp', 'Mountain', 'Forest', 'Wastes',
        'Snow-Covered Plains', 'Snow-Covered Island', 'Snow-Covered Swamp',
        'Snow-Covered Mountain', 'Snow-Covered Forest', 'Snow-Covered Wastes'
      ];
      
      // If using collection only, we need to join with UserCard
      // BUT: Always allow basic lands (they're unlimited in Commander)
      const collectionFilter = userId && useCollectionOnly ? {
        OR: [
          // Either in user's collection
          {
            userCards: {
              some: {
                userId: userId,
                quantity: { gt: 0 }
              }
            }
          },
          // OR is a basic land (always available)
          {
            name: {
              in: basicLandNames
            }
          }
        ]
      } : {};
      
      const results = await prisma.card.findMany({
        where: {
          ...finalConditions,
          ...(userId && useCollectionOnly ? collectionFilter : {}),  // Add collection filter if specified
          name: {
            not: { startsWith: 'A-' }
          },
          // COMMANDER LEGALITY CHECK - legalities is stored as JSON string
          // Must contain "commander":"Legal" (case matters!)
          // Must NOT contain "commander":"Banned"
          legalities: {
            contains: '"commander":"Legal"'  // Capital L - exact match
          },
          NOT: {
            legalities: {
              contains: '"commander":"Banned"'  // Explicitly exclude banned cards
            }
          },
          // Exclude "atomic" set (meld card backs, transform card backs, etc.)
          setCode: {
            not: 'atomic'
          },
          // Exclude non-legal card types (must match exactly, not substring)
          AND: [
            { typeLine: { not: { contains: 'Plane —' } } },  // Planechase planes (not Planeswalker)
            { typeLine: { not: { contains: 'Scheme' } } },
            { typeLine: { not: { contains: 'Vanguard' } } },
            { typeLine: { not: { contains: 'Phenomenon' } } },
            { typeLine: { not: { contains: 'Conspiracy' } } },
            { typeLine: { not: { contains: 'Dungeon' } } },
            { typeLine: { not: { contains: 'Sticker' } } },
            // Also exclude weird card names
            { name: { not: { contains: 'Sticker' } } },
            { name: { not: { contains: '//' } } },  // Double-faced cards formatted wrong
          ]
        },
        take: count,
        orderBy: { edhrecRank: 'asc' }, // Prefer popular cards
      });

      cards.push(
        ...results.map((card) => ({
          name: card.name,
          category: 'filter',
          cmc: card.cmc,
          type: card.typeLine,
          colorIdentity: card.colorIdentity ? card.colorIdentity.split(',').filter(Boolean) : [],
          oracleText: card.oracleText,
        }))
      );
    } catch (error) {
      console.error(`Warning: Filter query failed:`, error);
      continue;
    }
  }

  // Post-process: filter by color identity (must be subset of commander colors)
  const commanderColorSet = new Set(commanderColors.split(',').filter(Boolean));
  const colorFilteredCards = cards.filter(card => {
    const cardColorSet = new Set(card.colorIdentity || []);
    // Colorless (empty) is always allowed
    if (cardColorSet.size === 0) return true;
    // Card colors must be subset of commander colors
    return Array.from(cardColorSet).every(color => commanderColorSet.has(color));
  });

  return colorFilteredCards.slice(0, count);
}

async function buildCompleteDeck(structure: DeckStructure) {
  const commanderName = structure.commander;
  const cardSelection = structure.card_selection || {};
  const priorityCards = structure.priority_cards || [];

  console.log(`Building deck for: ${commanderName}`);
  console.log(`Strategy: ${structure.strategy}`);
  console.log(`Power Level: ${structure.power_level}`);
  console.log(`Bracket: ${structure.bracket}\n`);

  // Fetch commander to get color identity
  const commander = await prisma.card.findFirst({
    where: {
      name: {
        contains: commanderName.split(',')[0],
      },
    },
  });

  const commanderColors = commander?.colorIdentity || '';
  console.log(`Commander colors: ${commanderColors || 'Colorless'}\n`);

  // Fetch the commander card from database
  const commanderCard = await prisma.card.findFirst({
    where: {
      name: { equals: commanderName },
    },
  });

  if (!commanderCard) {
    throw new Error(`Commander "${commanderName}" not found in database`);
  }

  // Validate commander is legendary
  if (!commanderCard.typeLine.includes('Legendary')) {
    console.warn(`⚠️  WARNING: "${commanderName}" is not legendary - may not be a valid commander`);
  }

  // Validate commander can be a commander (Creature or Planeswalker, unless special text)
  const isCreature = commanderCard.typeLine.includes('Creature');
  const isPlaneswalker = commanderCard.typeLine.includes('Planeswalker');
  const canBeCommander = commanderCard.oracleText?.includes('can be your commander') || false;
  
  if (!isCreature && !isPlaneswalker && !canBeCommander) {
    console.warn(`⚠️  WARNING: "${commanderName}" is not a creature/planeswalker and lacks "can be your commander" text`);
  }

  if (!commanderCard) {
    console.error(`ERROR: Commander "${commanderName}" not found in database`);
    process.exit(1);
  }

  const deck: {
    commander: string;
    commanders: DeckCard[];
    mainboard: DeckCard[];
    total_cards: number;
  } = {
    commander: commanderName,
    commanders: [
      {
        name: commanderCard.name,
        category: 'commander',
        cmc: commanderCard.cmc,
        type: commanderCard.typeLine,
        colorIdentity: commanderCard.colorIdentity ? commanderCard.colorIdentity.split('') : [],
      },
    ],
    mainboard: [],
    total_cards: 1, // Start at 1 for the commander
  };

  // Cards that are allowed to have multiple copies in Commander
  // Source: Cards with "A deck can have any number" or "A deck can have up to X" in oracle text
  const legalDuplicates = new Set([
    // "Any number" cards
    'Relentless Rats',
    'Rat Colony', 
    'Persistent Petitioners',
    'Shadowborn Apostle',
    'Dragon\'s Approach',
    'Slime Against Humanity',
    'Hare Apparent',
    'Tempest Hawk',
    'Templar Knight',
    'Cid, Timeless Artificer',
    // Limited quantity cards (but still allow duplicates)
    'Seven Dwarves', // up to 7
    'Nazgûl', // up to 9
    // Basic lands (always allowed)
    'Plains', 'Island', 'Swamp', 'Mountain', 'Forest', 'Wastes',
    'Snow-Covered Plains', 'Snow-Covered Island', 'Snow-Covered Swamp',
    'Snow-Covered Mountain', 'Snow-Covered Forest', 'Snow-Covered Wastes'
  ]);

  // Helper function to check if a card allows duplicates
  const allowsDuplicates = (cardName: string, oracleText?: string | null): boolean => {
    // Check hardcoded list first (fast path)
    if (legalDuplicates.has(cardName)) return true;
    
    // Check oracle text for "A deck can have any number of cards named" or "A deck can have up to"
    // This catches any new cards we might have missed in the hardcoded list
    if (oracleText) {
      if (oracleText.includes('A deck can have any number of cards named')) return true;
      if (oracleText.includes('A deck can have up to')) return true;
    }
    
    return false;
  };

  // Track cards already added to avoid duplicates (except legal duplicate cards)
  const seenCards = new Set<string>();
  // Add commander to seen cards so it doesn't appear in mainboard
  seenCards.add(commanderCard.name);

  // MINIMUM AND MAXIMUM LAND GUARANTEE: Use training data for realistic ranges
  const bracket = structure.bracket || 3;
  const landRange = getLandRange(commanderName, bracket);
  const MIN_LANDS = landRange.min;
  const MAX_LANDS = landRange.max;
  
  let landsAllocated = 0;
  
  // Check if 'lands' category exists and has enough count
  if (cardSelection.lands) {
    landsAllocated = cardSelection.lands.count || 0;
  }
  
  if (landsAllocated < MIN_LANDS) {
    console.log(`\n⚠️  Model only allocated ${landsAllocated} lands, enforcing minimum of ${MIN_LANDS}`);
    // Force set lands to minimum
    if (!cardSelection.lands) {
      cardSelection.lands = { count: MIN_LANDS, filters: [{ types: ['Land'] }] };
    } else {
      cardSelection.lands.count = MIN_LANDS;
    }
  } else if (landsAllocated > MAX_LANDS) {
    console.log(`\n⚠️  Model allocated ${landsAllocated} lands, capping at maximum of ${MAX_LANDS}`);
    // Cap lands at maximum
    if (cardSelection.lands) {
      cardSelection.lands.count = MAX_LANDS;
    }
  }

  // Process each card category
  for (const [category, data] of Object.entries(cardSelection)) {
    if (!data || typeof data !== 'object') continue;

    const count = data.count || 0;
    const filters = data.filters || [];

    console.log(`Fetching ${count} ${category}...`);
    const cards = await executeFilters(filters, count, commanderColors, structure.userId, structure.useCollectionOnly);

    let added = 0;
    console.log(`  Found ${cards.length} cards`);
    for (const card of cards) {
      // Skip duplicates (unless card allows multiple copies)
      if (seenCards.has(card.name) && !allowsDuplicates(card.name, card.oracleText || undefined)) {
        continue;
      }
      
      // Only track non-duplicate-allowed cards in seenCards
      if (!allowsDuplicates(card.name, card.oracleText || undefined)) {
        seenCards.add(card.name);
      }
      
      deck.mainboard.push({
        ...card,
        category,
      });
      added++;
    }

    console.log(`  Added ${added} unique cards`);
    deck.total_cards += added;
  }

  // Add priority cards if needed (mainboard should be 99 cards)
  const needed = 99 - deck.mainboard.length;
  if (needed > 0 && priorityCards.length > 0) {
    console.log(`\nAdding up to ${needed} priority cards to reach 99 mainboard...`);

    const uniquePriority: string[] = [];

    for (const cardName of priorityCards) {
      // Skip if already in deck (unless it allows duplicates)
      // Note: We need to fetch the card to check oracle text for duplicate-allowed cards
      if (!seenCards.has(cardName)) {
        uniquePriority.push(cardName);
        // Only track if it's not a duplicate-allowed card
        if (!legalDuplicates.has(cardName)) {
          seenCards.add(cardName);
        }
        if (uniquePriority.length >= needed) break;
      } else if (legalDuplicates.has(cardName)) {
        // Allow duplicate-allowed cards even if seen
        uniquePriority.push(cardName);
        if (uniquePriority.length >= needed) break;
      }
    }

    // Fetch priority cards (skip Arena-only cards)
    for (const cardName of uniquePriority.slice(0, needed)) {
      // Skip Arena-only cards
      if (cardName.startsWith('A-')) continue;
      
      // Build collection filter if needed
      const collectionWhere = structure.userId && structure.useCollectionOnly ? {
        userCards: {
          some: {
            userId: structure.userId,
            quantity: { gt: 0 }
          }
        }
      } : {};
      
      const card = await prisma.card.findFirst({
        where: {
          name: { equals: cardName },
          ...collectionWhere,  // Only fetch if in collection (if filtering)
        },
      });

      if (card) {
        deck.mainboard.push({
          name: card.name,
          category: 'priority',
          cmc: card.cmc,
          type: card.typeLine,
        });
        deck.total_cards++;
      } else if (structure.useCollectionOnly) {
        console.log(`⚠️  Priority card "${cardName}" not in collection, skipping`);
      }
    }
  }

  // Fill with basics if still short (mainboard should be 99 cards)
  const stillNeeded = 99 - deck.mainboard.length;
  if (stillNeeded > 0) {
    console.log(`\nFilling ${stillNeeded} remaining mainboard slots with basic lands...`);

    const basicTypes: string[] = [];
    if (commanderColors.includes('W')) basicTypes.push('Plains');
    if (commanderColors.includes('U')) basicTypes.push('Island');
    if (commanderColors.includes('B')) basicTypes.push('Swamp');
    if (commanderColors.includes('R')) basicTypes.push('Mountain');
    if (commanderColors.includes('G')) basicTypes.push('Forest');

    if (basicTypes.length === 0) basicTypes.push('Wastes');

    const perBasic = Math.floor(stillNeeded / basicTypes.length);
    const remainder = stillNeeded % basicTypes.length;

    for (let i = 0; i < basicTypes.length; i++) {
      const count = perBasic + (i < remainder ? 1 : 0);
      for (let j = 0; j < count; j++) {
        deck.mainboard.push({
          name: basicTypes[i],
          category: 'basic_land',
          cmc: 0,
          type: 'Basic Land',
        });
        deck.total_cards++;
      }
    }
  }

  console.log(`\n${'='.repeat(70)}`);
  console.log(
    `DECK COMPLETE: ${deck.total_cards} cards (1 commander + ${deck.mainboard.length} mainboard)`
  );
  console.log(`${'='.repeat(70)}\n`);

  // Summary by category
  const categoryCount: { [key: string]: number } = {};
  for (const card of deck.mainboard) {
    categoryCount[card.category] = (categoryCount[card.category] || 0) + 1;
  }

  console.log('Card distribution:');
  for (const [cat, count] of Object.entries(categoryCount).sort()) {
    console.log(`  ${cat}: ${count}`);
  }

  return deck;
}

async function main() {
  const args = process.argv.slice(2);

  if (args.length === 0) {
    console.log('Usage: ts-node execute-deck-structure.ts <json_file>');
    console.log('\nExample:');
    console.log('  ts-node execute-deck-structure.ts generated_decks/gemma_test/atraxa.json');
    process.exit(1);
  }

  const inputFile = args[0];

  console.log(`Reading from file: ${inputFile}\n`);
  const fileContent = readFileSync(inputFile, 'utf-8');
  const data = JSON.parse(fileContent);

  let structure: DeckStructure;

  // Handle test output format
  if (data.raw_output) {
    let raw = data.raw_output as string;
    if (raw.startsWith('model')) {
      raw = raw.slice(5).trim();
    }

    // Try to parse truncated JSON
    const jsonStart = raw.indexOf('{');
    const jsonEnd = raw.lastIndexOf('}') + 1;

    if (jsonStart >= 0 && jsonEnd > jsonStart) {
      const jsonStr = raw.slice(jsonStart, jsonEnd);
      try {
        structure = JSON.parse(jsonStr);
      } catch {
        console.error('Failed to parse truncated JSON from raw_output');
        process.exit(1);
      }
    } else {
      console.error('Could not find JSON in raw_output');
      process.exit(1);
    }
  } else {
    structure = data as DeckStructure;
  }

  // Build the deck
  const deck = await buildCompleteDeck(structure);

  // Save output
  const outputDir = 'generated_decks/executed';
  mkdirSync(outputDir, { recursive: true });

  const outputFile = join(outputDir, 'deck.json');
  writeFileSync(outputFile, JSON.stringify(deck, null, 2));

  console.log(`\n💾 Complete deck saved to: ${outputFile}`);

  // Save as text decklist
  const textFile = outputFile.replace('.json', '.txt');
  const lines: string[] = [];

  lines.push(`Commander: ${deck.commander}\n`);

  // Group by category and consolidate duplicates
  const byCategory: { [key: string]: Map<string, number> } = {};
  for (const card of deck.mainboard) {
    if (!byCategory[card.category]) {
      byCategory[card.category] = new Map();
    }
    const currentCount = byCategory[card.category].get(card.name) || 0;
    byCategory[card.category].set(card.name, currentCount + 1);
  }

  for (const [category, cardMap] of Object.entries(byCategory).sort()) {
    const totalCards = Array.from(cardMap.values()).reduce((sum, count) => sum + count, 0);
    lines.push(`\n${category.toUpperCase()} (${totalCards}):`);
    
    // Sort by card name and write with quantities
    const sortedCards = Array.from(cardMap.entries()).sort((a, b) => a[0].localeCompare(b[0]));
    for (const [cardName, quantity] of sortedCards) {
      lines.push(`${quantity}x ${cardName}`);
    }
  }

  writeFileSync(textFile, lines.join('\n'));
  console.log(`💾 Text decklist saved to: ${textFile}`);

  await prisma.$disconnect();
}

main().catch((error) => {
  console.error('Error:', error);
  prisma.$disconnect();
  process.exit(1);
});
