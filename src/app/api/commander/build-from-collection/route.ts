/**
 * API endpoint to build Commander decks using the v3 Python deck builder
 * and the user's collection
 * 
 * POST /api/commander/build-from-collection
 * Body: {
 *   commander: string,
 *   strategy: string,
 *   powerLevel: number,
 *   bracket: number,
 *   useCollectionOnly?: boolean
 * }
 */

import { NextRequest, NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';
import { getCurrentUser } from '@/lib/user';
import { exec } from 'child_process';
import { promisify } from 'util';
import fs from 'fs/promises';
import path from 'path';
import { getTopEDHRECCards } from '@/lib/edhrec-data';

const execAsync = promisify(exec);

interface BuildRequest {
  commander: string;
  strategy: string;
  powerLevel: number;
  bracket: number;
  useCollectionOnly?: boolean;
  colors?: string[];  // Color restrictions from UI
  budgetConstraint?: number;  // Future: budget limit
  avoidSaltCards?: boolean;  // Future: avoid high-salt cards
}

export async function POST(req: NextRequest) {
  try {
    const user = await getCurrentUser();
    if (!user) {
      return NextResponse.json({ error: 'You must be logged in to build a deck.' }, { status: 401 });
    }

    const { commander, strategy, powerLevel, bracket, useCollectionOnly, avoidSaltCards, colors } = await req.json() as BuildRequest;

    if (!commander || !strategy || !powerLevel || !bracket) {
      return NextResponse.json({ 
        error: 'Missing required fields: commander, strategy, powerLevel, bracket' 
      }, { status: 400 });
    }

    // Fetch user's collection if useCollectionOnly is true
    let userCollection: string[] = [];
    if (useCollectionOnly) {
      const collectionCards = await prisma.userCard.findMany({
        where: { userId: user.id },
        select: { name: true, quantity: true },
      });

      // Flatten collection (include multiples of same card)
      userCollection = collectionCards.flatMap(card => 
        Array(card.quantity).fill(card.name)
      );

      if (userCollection.length === 0) {
        return NextResponse.json({ 
          error: 'Your collection is empty. Please add cards before building from collection.' 
        }, { status: 400 });
      }

      console.log(`Building deck from user collection (${userCollection.length} total cards, ${collectionCards.length} unique)`);
    } else {
      console.log('Building deck from all available cards (collection checkbox unchecked)');
    }

    // Create v3 structured JSON for deck builder
    // Build strategy-specific card selection based on deck theme
    const strategyLower = strategy.toLowerCase();
    
    // Get commander's color identity to determine which staples to include
    const commanderCard = await prisma.card.findFirst({
      where: { name: commander },
      select: { colorIdentity: true }
    });
    
    const hasColors = commanderCard?.colorIdentity && commanderCard.colorIdentity !== '';
    
    // Randomize land count for brackets 1-3 (casual to mid-power)
    // Higher brackets get consistent 35 lands for optimization
    let landCount = 35;
    if (bracket <= 3) {
      // Random between 35-40 lands for lower power/casual decks
      landCount = 35 + Math.floor(Math.random() * 6); // 35, 36, 37, 38, 39, or 40
      console.log(`🎲 Randomized land count for bracket ${bracket}: ${landCount} lands`);
    }
    
    // Base card selection (will be customized per strategy)
    // These categories apply to ALL decks regardless of strategy
    let cardSelection: any = {
      lands: {
        count: landCount,
        filters: [{ types: ["Land"] }]
      },
      staples: {
        count: hasColors ? 3 : 1,  // Sol Ring + Arcane Signet + Command Tower (if colored)
        filters: hasColors 
          ? [{ names: ["Sol Ring", "Arcane Signet", "Command Tower"] }]
          : [{ names: ["Sol Ring"] }]  // Colorless commanders only get Sol Ring
      },
      ramp: {
        count: hasColors ? 9 : 11,  // Reduced to account for Arcane Signet
        filters: [{ tags: ["ramp"], types_exclude: ["Land"] }]
      }
    };

    // Strategy-specific card selection
    if (strategyLower.includes('mill')) {
      // Mill strategy: focus on milling opponents and enabling mill synergies
      cardSelection = {
        ...cardSelection,
        mill_effects: {
          count: 15,
          filters: [{ oracle_text_includes: ["mill", "library into", "graveyard from their library"] }]
        },
        lifegain: {
          count: 12,
          filters: [{ oracle_text_includes: ["you gain", "gain life", "life equal"] }]
        },
        creatures: {
          count: 15,
          filters: [{ types: ["Creature"] }]
        },
        card_draw: {
          count: 8,
          filters: [{ tags: ["card_draw"] }]
        },
        protection: {
          count: 2,
          filters: [{ tags: ["protection"] }]
        }
      };
    } else if (strategyLower.includes('voltron') || strategyLower.includes('equipment') || strategyLower.includes('aura')) {
      // Voltron strategy: equipment, auras, combat-focused
      cardSelection = {
        ...cardSelection,
        voltron_equipment: {
          count: 15,
          filters: [{ types: ["Equipment", "Artifact"], oracle_text_includes: ["equipped", "attach"] }]
        },
        auras: {
          count: 8,
          filters: [{ types: ["Enchantment"], oracle_text_includes: ["enchant creature", "enchanted creature"] }]
        },
        creatures: {
          count: 18,
          filters: [{ types: ["Creature"] }]
        },
        protection: {
          count: 8,
          filters: [{ tags: ["protection"], oracle_text_includes: ["hexproof", "indestructible", "protection"] }]
        },
        card_draw: {
          count: 6,
          filters: [{ tags: ["card_draw"] }]
        }
      };
    } else if (strategyLower.includes('combo') || strategyLower.includes('infinite')) {
      // Combo strategy: tutors, combo pieces, card draw
      cardSelection = {
        ...cardSelection,
        combo_pieces: {
          count: 12,
          filters: [{ tags: ["combo"], oracle_text_includes: ["infinite", "untap", "goes infinite"] }]
        },
        tutors: {
          count: 8,
          filters: [{ tags: ["tutor"], oracle_text_includes: ["search your library", "search for a card"] }]
        },
        card_draw: {
          count: 12,
          filters: [{ tags: ["card_draw"] }]
        },
        creatures: {
          count: 20,
          filters: [{ types: ["Creature"] }]
        },
        protection: {
          count: 6,
          filters: [{ tags: ["protection"] }]
        }
      };
    } else if (strategyLower.includes('graveyard') || strategyLower.includes('reanimator')) {
      // Graveyard strategy: self-mill, reanimation, recursion
      cardSelection = {
        ...cardSelection,
        graveyard_fillers: {
          count: 10,
          filters: [{ oracle_text_includes: ["mill yourself", "put cards from your library into your graveyard", "discard"] }]
        },
        reanimation: {
          count: 12,
          filters: [{ oracle_text_includes: ["return", "from your graveyard", "reanimate"] }]
        },
        creatures: {
          count: 25,
          filters: [{ types: ["Creature"] }]
        },
        card_draw: {
          count: 8,
          filters: [{ tags: ["card_draw"] }]
        },
        removal: {
          count: 4,
          filters: [{ tags: ["removal"] }]
        }
      };
    } else if (strategyLower.includes('token') || strategyLower.includes('go-wide')) {
      // Token strategy: token generation, anthems, sacrifice outlets
      cardSelection = {
        ...cardSelection,
        token_makers: {
          count: 15,
          filters: [{ oracle_text_includes: ["create", "token", "tokens"] }]
        },
        anthems: {
          count: 10,
          filters: [{ oracle_text_includes: ["creatures you control get", "creatures get +"] }]
        },
        creatures: {
          count: 20,
          filters: [{ types: ["Creature"] }]
        },
        card_draw: {
          count: 8,
          filters: [{ tags: ["card_draw"] }]
        },
        removal: {
          count: 6,
          filters: [{ tags: ["removal"] }]
        }
      };
    } else if (strategyLower.includes('control')) {
      // Control strategy: removal, counterspells, board wipes
      cardSelection = {
        ...cardSelection,
        removal: {
          count: 15,
          filters: [{ tags: ["removal"] }]
        },
        counterspells: {
          count: 10,
          filters: [{ oracle_text_includes: ["counter target", "counter spell"] }]
        },
        board_wipes: {
          count: 6,
          filters: [{ oracle_text_includes: ["destroy all", "exile all", "all creatures"] }]
        },
        card_draw: {
          count: 12,
          filters: [{ tags: ["card_draw"] }]
        },
        creatures: {
          count: 12,
          filters: [{ types: ["Creature"] }]
        }
      };
    } else if (strategyLower.includes('tribal')) {
      // Tribal strategy: creature type synergies (commander's type will be in EDHREC cards)
      cardSelection = {
        ...cardSelection,
        creatures: {
          count: 35,
          filters: [{ types: ["Creature"] }]
        },
        tribal_support: {
          count: 8,
          filters: [{ oracle_text_includes: ["of the chosen type", "creature type", "share a creature type"] }]
        },
        card_draw: {
          count: 8,
          filters: [{ tags: ["card_draw"] }]
        },
        removal: {
          count: 6,
          filters: [{ tags: ["removal"] }]
        }
      };
    } else {
      // Default strategy (midrange, value, good stuff)
      cardSelection = {
        ...cardSelection,
        creatures: {
          count: 28,
          filters: [{ types: ["Creature"] }]
        },
        removal: {
          count: 12,
          filters: [{ tags: ["removal"] }]
        },
        card_draw: {
          count: 8,
          filters: [{ tags: ["card_draw"] }]
        },
        protection: {
          count: 4,
          filters: [{ tags: ["protection"] }]
        }
      };
    }

    // Adjust card counts if we have extra lands (brackets 1-3)
    // Reduce non-land categories proportionally to maintain 99 card total
    const extraLands = landCount - 35;
    if (extraLands > 0) {
      const nonLandCategories = Object.keys(cardSelection).filter(k => k !== 'lands');
      const totalNonLandCards = nonLandCategories.reduce((sum, key) => sum + (cardSelection[key]?.count || 0), 0);
      
      let landReduction = extraLands;
      
      // Reduce larger categories first (creatures, then others)
      for (const category of nonLandCategories) {
        if (landReduction <= 0) break;
        
        const currentCount = cardSelection[category]?.count || 0;
        if (currentCount > 0 && category !== 'staples') { // Don't reduce staples
          const reduction = Math.min(1, landReduction); // Reduce by 1 per category
          cardSelection[category].count = Math.max(1, currentCount - reduction);
          landReduction -= reduction;
        }
      }
      
      console.log(`📉 Adjusted card counts for ${extraLands} extra lands`);
    }

    // Get popular cards for this commander from EDHREC data
    // This acts as "AI suggestions" based on what other players use
    const popularCards = await getTopEDHRECCards(commander, 30);
    console.log(`Retrieved ${popularCards.length} popular cards for ${commander} from EDHREC`);

    const v3Structure = {
      commander,
      strategy,
      bracket,
      power_level: powerLevel,
      card_selection: cardSelection,
      ...(popularCards.length > 0 && { priority_cards: popularCards }), // AI-suggested cards
      ...(colors && colors.length > 0 && { color_restrictions: colors }), // UI color filters
      ...(useCollectionOnly && userCollection.length > 0 && { collection: userCollection }), // Only pass collection if checkbox is checked
      ...(avoidSaltCards && { avoid_salt_cards: true, salt_threshold: 2.0 }) // Filter out cards with saltiness > 2.0
    };

    // Write temporary input file
    const tempDir = path.join(process.cwd(), 'generated_decks', 'temp');
    await fs.mkdir(tempDir, { recursive: true });
    
    const inputFile = path.join(tempDir, `${user.id}-${Date.now()}.json`);
    await fs.writeFile(inputFile, JSON.stringify(v3Structure, null, 2));

    // Execute Python deck builder
    const scriptPath = path.join(process.cwd(), 'scripts', 'build-deck-from-structure.py');
    const command = `python3 ${scriptPath} ${inputFile}`;

    console.log(`Executing: ${command}`);
    const { stdout, stderr } = await execAsync(command);

    if (stderr && !stderr.includes('✅')) {
      console.error('Deck builder stderr:', stderr);
    }

    // Read generated deck from output
    const outputFile = inputFile.replace('.json', '_deck.json').replace('/temp/', '/v3_executed/');
    const deckData = JSON.parse(await fs.readFile(outputFile, 'utf-8'));

    // Clean up temp file
    await fs.unlink(inputFile).catch(() => {});

    // Save deck to database
    const newDeck = await prisma.deck.create({
      data: {
        name: `${commander} - ${strategy}`,
        description: `Power Level ${powerLevel}, Bracket ${bracket}`,
        theme: strategy,
        powerLevel: `Bracket ${bracket}`,
        decklist: deckData as any,
        userId: user.id,
        status: 'GENERATED',
      },
    });

    return NextResponse.json({ 
      success: true,
      deck: newDeck,
      decklist: deckData,
      message: useCollectionOnly 
        ? 'Deck built from your collection' 
        : 'Deck built successfully'
    });

  } catch (error) {
    console.error('Error building deck from collection:', error);
    
    const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
    
    return NextResponse.json({ 
      error: `Failed to build deck: ${errorMessage}` 
    }, { status: 500 });
  }
}
