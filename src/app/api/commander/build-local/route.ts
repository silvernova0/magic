/**
 * API endpoint to build Commander decks using local Gemma 3 4B model
 * Calls localhost:8000 to generate deck structure, then executes with Python
 * 
 * POST /api/commander/build-local
 * Body: {
 *   commander?: string,
 *   strategy: string,
 *   powerLevel: number,
 *   bracket: number,
 *   useCollectionOnly?: boolean,
 *   colors?: string[]
 * }
 */

import { NextRequest, NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';
import { getCurrentUser } from '@/lib/user';
import { exec } from 'child_process';
import { promisify } from 'util';
import fs from 'fs/promises';
import path from 'path';

const execAsync = promisify(exec);

interface BuildRequest {
  commander?: string;
  strategy: string;
  powerLevel: number;
  bracket: number;
  useCollectionOnly?: boolean;
  colors?: string[];
  avoidSaltCards?: boolean;
  partner?: string; // NEW
}

/**
 * Call local Gemma 3 4B model to generate deck structure
 */
async function generateWithLocalModel(params: {
  commander?: string;
  strategy: string;
  colors?: string[];
  powerLevel: number;
  bracket: number;
}): Promise<any> {
  const response = await fetch('http://localhost:8000/api/deck/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      commander: params.commander || undefined,
      theme: params.strategy,
      colors: params.colors || [], // Default to empty array if not provided
      powerLevel: params.bracket.toString(), // Model expects "1"-"5"
    }),
    signal: AbortSignal.timeout(300000), // 5 minute timeout
  });
  // Read raw text so we can safely parse JSON or log partial HTML returned by the model
  const raw = await response.text();

  if (!response.ok) {
    // Try to parse JSON if it's present, otherwise log and throw with snippet
    try {
      const errObj = JSON.parse(raw);
      throw new Error(`Local model error: ${errObj.detail || errObj.error || response.statusText}`);
    } catch (_parseErr) {
      console.error('Local model returned non-OK body (first 4k chars):', raw.slice(0, 4096));
      throw new Error(`Local model error: ${response.status} ${response.statusText} (see server logs for response head)`);
    }
  }

  try {
    return JSON.parse(raw);
  } catch (err) {
    // Model sometimes appends conversational text. Log for debugging and return a helpful debug snippet.
    const head = raw ? raw.slice(0, 8192) : '';
    console.error('Local model returned non-JSON (first 8k chars):', head);
    // Return a safe debug snippet to the client for development; keep 2k char safe limit
    const debugHead = head.slice(0, 2048);
    // The top-level try/catch below will wrap this as a failure; we include the debug snippet so UI can display it
    throw new Error(`Local model returned invalid JSON: ${debugHead}`);
  }
}

export async function POST(req: NextRequest) {
  try {
    const user = await getCurrentUser();
    if (!user) {
      return NextResponse.json({ error: 'You must be logged in to build a deck.' }, { status: 401 });
    }

    const {
      commander,
      strategy,
      powerLevel,
      bracket,
      useCollectionOnly,
      avoidSaltCards,
      colors,
      partner // NEW
    } = await req.json() as BuildRequest;

    // Validate required fields
    if (!strategy || !powerLevel || !bracket) {
      return NextResponse.json({
        error: 'Missing required fields: strategy, powerLevel, bracket'
      }, { status: 400 });
    }

    // Normalize strategy
    let normalizedStrategy = strategy.toLowerCase();
    const strategyMap: Record<string, string> = {
      'kindred': 'tribal',
      'self mill': 'self_mill',
      'go wide': 'go_wide',
      'turbo fog': 'turbo_fog',
      'hate bears': 'hate_bears',
      'group hug': 'group_hug',
      'group slug': 'group_slug',
      'lands matter': 'lands_matter',
      'superfriends': 'superfriends',
    };
    normalizedStrategy = strategyMap[normalizedStrategy] || normalizedStrategy.replace(/\s+/g, '_');

    // Fetch user's collection if needed
    let userCollection: string[] = [];
    if (useCollectionOnly) {
      const collectionCards = await prisma.userCard.findMany({
        where: { userId: user.id },
        select: { name: true, quantity: true, type_line: true },
      });

      const totalCards = collectionCards.reduce((sum, card) => sum + card.quantity, 0);
      const uniqueCards = collectionCards.length;

      const legendaryCreatures = collectionCards.filter(card => {
        const typeLine = card.type_line?.toLowerCase() || '';
        return typeLine.includes('legendary') && typeLine.includes('creature');
      });
      const legendaryCount = legendaryCreatures.length;

      const MIN_LEGENDARY = 10;
      const MIN_TOTAL_CARDS = 500;

      if (legendaryCount < MIN_LEGENDARY) {
        return NextResponse.json({
          error: `Collection needs at least ${MIN_LEGENDARY} legendary creatures. You have ${legendaryCount}.`,
          details: { legendaryCreatures: legendaryCount, requiredLegendary: MIN_LEGENDARY, totalCards, uniqueCards }
        }, { status: 400 });
      }

      if (totalCards < MIN_TOTAL_CARDS) {
        return NextResponse.json({
          error: `Collection needs at least ${MIN_TOTAL_CARDS} total cards. You have ${totalCards}.`,
          details: { legendaryCreatures: legendaryCount, totalCards, requiredTotal: MIN_TOTAL_CARDS, uniqueCards }
        }, { status: 400 });
      }

      userCollection = collectionCards.flatMap(card =>
        Array(card.quantity).fill(card.name)
      );

      console.log(`🎯 Building from collection: ${totalCards} total, ${uniqueCards} unique, ${legendaryCount} legendary`);
    }

    // Select commander if not provided
    let finalCommander = commander;
    if (!finalCommander || finalCommander.trim() === '') {
      console.log('🎯 No commander specified, selecting one...');

      // Handle color identity - filter out 'C' if present (colorless is represented as empty string in DB)
      const filteredColors = colors && colors.length > 0 ? colors.filter(c => c !== 'C') : [];
      const colorIdentity = filteredColors.length > 0 ? filteredColors.sort().join(',') : '';

      // Commander selection criteria (as of recent rule changes):
      // 1. Any Legendary card with "Creature" in type line (covers Legendary Creature, 
      //    Legendary Artifact Creature, Legendary Enchantment Creature, etc.)
      // 2. Legendary Artifact — Vehicle
      // 3. Legendary Artifact — Spacecraft
      // Must be legal in Commander format
      // NOTE: Regular Legendary Artifact (Equipment, etc.) CANNOT be commanders
      // NOTE: Exclude meld results (back faces that can't be cast)
      const whereClause: any = {
        isCommander: true,
        OR: [
          {
            AND: [
              { typeLine: { contains: 'Legendary' } },
              { typeLine: { contains: 'Creature' } }
            ]
          }, // Any legendary creature (includes Artifact Creatures, Enchantment Creatures, etc.)
          { typeLine: { contains: 'Legendary Artifact — Vehicle' } }, // Vehicles
          { typeLine: { contains: 'Legendary Artifact — Spacecraft' } }, // Spacecraft
        ],
        legalities: { contains: '"commander":"Legal"' },
        colorIdentity: colorIdentity, // Always filter by colorIdentity (empty string for colorless)
        // Exclude meld results that cannot be cast (only exist as back faces)
        name: {
          notIn: [
            'Hanweir, the Writhing Township', // Meld of Hanweir Battlements + Garrison
            'Brisela, Voice of Nightmares', // Meld of Bruna + Gisela
            'Chittering Host', // Meld of Graf Rats + Midnight Scavengers
            'Ragnarok, Divine Deliverance', // Meld of Fang + Vanille
            'Urza, Planeswalker', // Meld of Urza pieces
            'Mishra, Lost to Phyrexia', // Back face only
            'The Unspeakable', // Back face only
            'Titania, Gaea Incarnate' // Back face only
          ]
        }
      };

      if (useCollectionOnly && userCollection.length > 0) {
        whereClause.name = { in: Array.from(new Set(userCollection)) };
      }

      const commanderOptions = await prisma.card.findMany({
        where: whereClause,
        orderBy: { edhrecRank: 'asc' },
        take: 10,
        select: { name: true, edhrecRank: true },
      });

      if (commanderOptions.length === 0) {
        return NextResponse.json({
          error: useCollectionOnly
            ? 'No suitable commanders found in your collection with those colors'
            : 'No commanders found matching your criteria'
        }, { status: 404 });
      }

      finalCommander = commanderOptions[0].name;
      console.log(`✅ Selected commander: ${finalCommander} (EDHREC rank: ${commanderOptions[0].edhrecRank})`);
    }

    // Get commander details
    const commanderCard = await prisma.card.findFirst({
      where: { name: finalCommander },
      select: {
        colorIdentity: true,
        oracleText: true,
        typeLine: true,
        name: true
      },
    });

    if (!commanderCard) {
      return NextResponse.json({
        error: `Commander "${finalCommander}" not found in database`
      }, { status: 404 });
    }

    let commanderColors = commanderCard.colorIdentity?.split(',').filter(Boolean) || [];
    // Handle Partner / Background Logic
    if (partner && partner.trim() !== '') {
      console.log(`🤝 Partner specified: ${partner}`);

      const partnerCard = await prisma.card.findFirst({
        where: { name: partner },
        select: {
          colorIdentity: true,
          oracleText: true,
          typeLine: true,
          name: true
        },
      });

      if (!partnerCard) {
        return NextResponse.json({
          error: `Partner "${partner}" not found in database`
        }, { status: 404 });
      }

      // VALIDATION LOGIC
      const cmdText = (commanderCard.oracleText || '').toLowerCase();
      const cmdType = (commanderCard.typeLine || '').toLowerCase();
      const partnerText = (partnerCard.oracleText || '').toLowerCase();
      const partnerType = (partnerCard.typeLine || '').toLowerCase();

      let isValidPair = false;
      let validationError = '';

      // 1. "Partner" keyword on both
      if (cmdText.includes('partner') && partnerText.includes('partner')) {
        // Exclude "Partner with" unless it matches
        const cmdPartnerWith = cmdText.match(/partner with ([^(\n]+)/);
        const partnerPartnerWith = partnerText.match(/partner with ([^(\n]+)/);

        if (cmdPartnerWith || partnerPartnerWith) {
          // One has "Partner with", so both must have it and name each other
          if (cmdPartnerWith && partnerPartnerWith) {
            if (cmdPartnerWith[1].toLowerCase().includes(partnerCard.name.toLowerCase()) &&
              partnerPartnerWith[1].toLowerCase().includes(commanderCard.name.toLowerCase())) {
              isValidPair = true;
            } else {
              validationError = `"${commanderCard.name}" must partner with "${cmdPartnerWith[1]}", not "${partnerCard.name}"`;
            }
          } else {
            validationError = 'Both cards must have "Partner with" and name each other.';
          }
        } else {
          // Generic Partner
          isValidPair = true;
        }
      }
      // 2. "Friends Forever" on both
      else if (cmdText.includes('friends forever') && partnerText.includes('friends forever')) {
        isValidPair = true;
      }
      // 3. "Choose a Background" + "Background" enchantment
      else if (cmdText.includes('choose a background') && partnerType.includes('background') && partnerType.includes('enchantment')) {
        isValidPair = true;
      }
      // 4. "Doctor's Companion" + "Time Lord Doctor"
      else if ((cmdText.includes("doctor's companion") && (partnerType.includes('time lord') && partnerType.includes('doctor'))) ||
        (partnerText.includes("doctor's companion") && (cmdType.includes('time lord') && cmdType.includes('doctor')))) {
        isValidPair = true;
      }

      if (!isValidPair) {
        return NextResponse.json({
          error: `Invalid Commander Pair: ${validationError || 'Commanders are not compatible partners.'}`
        }, { status: 400 });
      }

      // Merge Colors
      const partnerColors = partnerCard.colorIdentity?.split(',').filter(Boolean) || [];
      const mergedColors = new Set([...commanderColors, ...partnerColors]);
      commanderColors = Array.from(mergedColors);

      // Update final commander name for AI prompt
      finalCommander = `${commanderCard.name} + ${partnerCard.name}`;
      console.log(`✅ Valid Partner Pair: ${finalCommander} (Colors: ${commanderColors.join('')})`);
    }


    // Generate deck structure with local Gemma 3 4B model
    console.log('🤖 Generating deck structure with local Gemma 3 4B model...');

    let modelOutput: any;
    try {
      modelOutput = await generateWithLocalModel({
        commander: finalCommander,
        strategy: normalizedStrategy,
        colors: commanderColors,
        powerLevel,
        bracket,
      });
      console.log('✅ Local model generation complete');
    } catch (error: any) {
      console.error('❌ Local model failed:', error);
      return NextResponse.json({
        error: `Local model unavailable: ${error.message}`,
        details: 'Make sure the API server is running: python3 scripts/active/pipeline/api-server.py'
      }, { status: 503 });
    }

    // Build v3 structure for Python executor
    const v3Structure = {
      commander: finalCommander,
      strategy: normalizedStrategy,
      bracket,
      power_level: powerLevel,
      card_selection: modelOutput.card_selection || {},
    };

    // POST-PROCESSING: Fix tribal/kindred filters if AI didn't generate them correctly
    const themeLower = normalizedStrategy.toLowerCase();
    if ((themeLower.includes('tribal') || themeLower.includes('kindred')) && v3Structure.card_selection?.creatures) {
      // Extract creature type from theme (e.g., "Kindred - Cats" -> "Cat", "kindred_-_cats" -> "Cat")
      const typeMatch = themeLower.match(/(?:tribal|kindred)[-_\s]+(\w+)/);
      if (typeMatch) {
        let creatureType = typeMatch[1];

        // Handle irregular plurals
        const irregulars: Record<string, string> = {
          'elves': 'Elf',
          'wolves': 'Wolf',
          'dwarves': 'Dwarf',
          'fairies': 'Faerie',
          'merfolk': 'Merfolk' // Already singular/plural
        };

        if (irregulars[creatureType.toLowerCase()]) {
          creatureType = irregulars[creatureType.toLowerCase()];
        } else {
          // Standard de-pluralization
          creatureType = creatureType.replace(/s$/, '').replace(/^(.)/, (m: string) => m.toUpperCase());
        }

        // Check if filters are missing or incorrect
        const filters = v3Structure.card_selection.creatures.filters || [];
        const hasCorrectSubtype = filters.some((f: any) =>
          f.subtypes && Array.isArray(f.subtypes) && f.subtypes.includes(creatureType)
        );

        if (!hasCorrectSubtype) {
          console.log(`⚠️ Tribal theme detected but no ${creatureType} subtype filter found. Adding it.`);
          v3Structure.card_selection.creatures.filters = [
            { subtypes: [creatureType] },
            ...filters
          ];
        }
      }
    }

    // Continue building structure
    Object.assign(v3Structure, {
      ...(modelOutput.priority_cards && { priority_cards: modelOutput.priority_cards }),
      ...(colors && colors.length > 0 && { color_restrictions: colors }),
      ...(useCollectionOnly && userCollection.length > 0 && { collection: userCollection }),
      ...(avoidSaltCards && { avoid_salt_cards: true, salt_threshold: 2.0 }),
    });

    // Execute Python deck builder
    const tempDir = path.join(process.cwd(), 'generated_decks', 'temp');
    await fs.mkdir(tempDir, { recursive: true });

    const inputFile = path.join(tempDir, `${user.id}-${Date.now()}.json`);
    await fs.writeFile(inputFile, JSON.stringify(v3Structure, null, 2));

    const scriptPath = path.join(process.cwd(), 'scripts', 'build-deck-from-structure.py');
    const command = `python3 ${scriptPath} ${inputFile}`;

    console.log(`Executing: ${command}`);
    const { stdout, stderr } = await execAsync(command);

    if (stderr && !stderr.includes('✅')) {
      console.error('Deck builder stderr:', stderr);
    }

    // Read generated deck
    const outputFile = inputFile.replace('.json', '_deck.json').replace('/temp/', '/v3_executed/');
    const deckData = JSON.parse(await fs.readFile(outputFile, 'utf-8'));

    // Keep temp file for debugging (don't delete)
    // await fs.unlink(inputFile).catch(() => {});
    console.log(`📝 Structure saved to: ${inputFile} for debugging`);

    // Save to database
    const newDeck = await prisma.deck.create({
      data: {
        name: `${finalCommander} - ${strategy}`,
        description: `Power Level ${powerLevel}, Bracket ${bracket} (AI Generated)`,
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
      modelUsed: 'gemma-3-4b-local',
      message: `Deck generated with local AI model${useCollectionOnly ? ' from your collection' : ''}`
    });

  } catch (error) {
    console.error('Error building deck:', error);

    const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';

    console.error('Returning error to client:', errorMessage);
    const devDebug = (errorMessage || '').slice(0, 2000);
    return NextResponse.json({
      error: `Failed to build deck: ${errorMessage}`,
      debug: devDebug
    }, { status: 500 });
  }
}
