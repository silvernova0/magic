/**
 * Import Moxfield popular decks into database
 * Scrapes top decks across all power level brackets (1-5)
 */

import { PrismaClient } from '@prisma/client';
import { scrapeMoxfield, fetchDeckDetails } from '../src/lib/scrapers/moxfield';

const prisma = new PrismaClient({
  log: ['error', 'warn'],
});

const RATE_LIMIT_DELAY = 1000; // 1 second between deck detail requests
const DECKS_PER_BRACKET = 15; // Import top 15 decks per bracket

function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function importMoxfieldDecks() {
  console.log('🎯 Starting Moxfield deck import...\n');

  try {
    // Step 1: Scrape deck lists by bracket
    console.log('📥 Fetching popular decks by power level bracket...');
    const moxfieldData = await scrapeMoxfield();
    
    let totalDecks = 0;
    for (const [bracket, decks] of Object.entries(moxfieldData.topDecksByBracket)) {
      console.log(`  Bracket ${bracket}: ${decks.length} decks`);
      totalDecks += decks.length;
    }
    console.log(`\nTotal decks found: ${totalDecks}\n`);

    if (totalDecks === 0) {
      console.log('❌ No decks found. The API may have changed.');
      return;
    }

    let processedCount = 0;
    let successCount = 0;
    let errorCount = 0;
    let skippedCount = 0;

    // Step 2: Collect unique decks across all brackets
    console.log('\n🔍 Collecting unique decks across all brackets...');
    const uniqueDecksMap = new Map<string, any>();
    
    for (let bracket = 1; bracket <= 5; bracket++) {
      const decks = moxfieldData.topDecksByBracket[bracket.toString()] || [];
      for (const deck of decks) {
        // Use the Moxfield deck ID as the unique key
        if (!uniqueDecksMap.has(deck.id)) {
          uniqueDecksMap.set(deck.id, deck);
        }
      }
    }

    const uniqueDecks = Array.from(uniqueDecksMap.values());
    console.log(`Found ${uniqueDecks.length} unique decks to import\n`);

    // Step 3: Process unique decks
    console.log('📦 Processing Unique Decks');
    console.log('═'.repeat(50));

    // Limit total decks to import
    const decksToProcess = uniqueDecks.slice(0, 75);

    for (const deck of decksToProcess) {
      try {
        processedCount++;
        console.log(`\n  [${processedCount}/${decksToProcess.length}] ${deck.name}`);
        console.log(`     Commander: ${deck.commander}`);
        console.log(`     Views: ${deck.views.toLocaleString()} | Likes: ${deck.likes}`);

        // Fetch full deck details including decklist
        const deckDetails = await fetchDeckDetails(deck.id);
        
        if (!deckDetails || !deckDetails.mainboard || deckDetails.mainboard.length === 0) {
          console.log(`     ⚠️  No decklist found, skipping...`);
          skippedCount++;
          await sleep(RATE_LIMIT_DELAY);
          continue;
        }

        // Find commander card in database
        const commanderName = deckDetails.commanders[0] || deck.commander;
        const commanderCard = await prisma.card.findFirst({
          where: { name: commanderName },
          select: { id: true, colorIdentity: true },
        });

        // Extract colors
        let colors: string[] = deckDetails.colors || [];
        if (commanderCard && commanderCard.colorIdentity) {
          try {
            colors = JSON.parse(commanderCard.colorIdentity);
          } catch {
            colors = deckDetails.colors || [];
          }
        }

        // Determine theme from description and hubs
        const theme = inferTheme(deckDetails.description, deckDetails.hubs);

        // Create unique ID for this deck (without bracket to avoid duplicates)
        const deckId = `moxfield-${deck.id}`;

        // Store deck in database
        await prisma.commanderDeck.upsert({
          where: {
              id: deckId,
            },
            create: {
              id: deckId,
              name: deckDetails.name,
              commander: commanderName,
              commanderId: commanderCard?.id,
              colors: JSON.stringify(colors),
              theme,
              powerLevel: deckDetails.powerLevel || deck.powerLevel,
              source: 'moxfield',
              sourceUrl: `https://www.moxfield.com/decks/${deck.id}`,
              decklist: JSON.stringify({
                commanders: deckDetails.commanders,
                mainboard: deckDetails.mainboard,
                sideboard: deckDetails.sideboard || [],
                description: deckDetails.description,
                hubs: deckDetails.hubs,
                author: deckDetails.author,
              }),
              popularity: deckDetails.views,
              winRate: null,
              avgTurns: null,
            },
            update: {
              name: deckDetails.name,
              commander: commanderName,
              commanderId: commanderCard?.id,
              colors: JSON.stringify(colors),
              theme,
              powerLevel: deckDetails.powerLevel || deck.powerLevel,
              sourceUrl: `https://www.moxfield.com/decks/${deck.id}`,
              decklist: JSON.stringify({
                commanders: deckDetails.commanders,
                mainboard: deckDetails.mainboard,
                sideboard: deckDetails.sideboard || [],
                description: deckDetails.description,
                hubs: deckDetails.hubs,
                author: deckDetails.author,
              }),
              popularity: deckDetails.views,
              updatedAt: new Date(),
            },
          });

          console.log(`     ✅ Stored deck (${deckDetails.mainboard.length} cards, Power Level ${deckDetails.powerLevel || deck.powerLevel})`);
          successCount++;

          // Rate limiting
          await sleep(RATE_LIMIT_DELAY);
        } catch (error) {
          console.error(`     ❌ Error processing deck ${deck.name}:`, error);
          errorCount++;
        }
      }

    // Summary
    console.log('\n' + '='.repeat(50));
    console.log('✅ Import Complete!');
    console.log('📊 Statistics:');
    console.log(`   - Decks Processed: ${successCount + errorCount + skippedCount}`);
    console.log(`   - Successfully Stored: ${successCount}`);
    console.log(`   - Skipped (no decklist): ${skippedCount}`);
    console.log(`   - Errors: ${errorCount}`);
    console.log('='.repeat(50) + '\n');

  } catch (error) {
    console.error('❌ Fatal error during import:', error);
    throw error;
  } finally {
    await prisma.$disconnect();
  }
}

/**
 * Infer theme from description and hubs
 */
function inferTheme(description: string, hubs: string[]): string {
  // Check hubs first (these are user-assigned tags)
  if (hubs && hubs.length > 0) {
    // Common hub themes
    const themeMap: { [key: string]: string } = {
      'cEDH': 'cEDH',
      'Competitive': 'cEDH',
      'Stax': 'Stax',
      'Combo': 'Combo',
      'Aggro': 'Aggro',
      'Voltron': 'Voltron',
      'Control': 'Control',
      'Midrange': 'Midrange',
      'Tribal': 'Tribal',
      'Tokens': 'Tokens',
      'Aristocrats': 'Aristocrats',
      'Landfall': 'Lands Matter',
      'Reanimator': 'Reanimator',
      'Graveyard': 'Graveyard',
      'Spellslinger': 'Spellslinger',
      'Group Hug': 'Group Hug',
      'Chaos': 'Chaos',
    };

    for (const hub of hubs) {
      // Ensure hub is a string
      if (typeof hub !== 'string') continue;
      
      const hubLower = hub.toLowerCase();
      for (const [key, value] of Object.entries(themeMap)) {
        if (hubLower.includes(key.toLowerCase())) {
          return value;
        }
      }
    }

    // Return first hub if no match (ensure it's a string)
    const firstHub = hubs.find(h => typeof h === 'string');
    if (firstHub) {
      return firstHub.substring(0, 50);
    }
  }

  // Fall back to description analysis
  if (description) {
    const desc = description.toLowerCase();
    
    if (desc.includes('cedh') || desc.includes('competitive')) return 'cEDH';
    if (desc.includes('stax')) return 'Stax';
    if (desc.includes('combo')) return 'Combo';
    if (desc.includes('aggro') || desc.includes('voltron')) return 'Aggro';
    if (desc.includes('control')) return 'Control';
    if (desc.includes('tribal')) return 'Tribal';
    if (desc.includes('token')) return 'Tokens';
    if (desc.includes('aristocrat')) return 'Aristocrats';
    if (desc.includes('land')) return 'Lands Matter';
    if (desc.includes('graveyard') || desc.includes('reanimate')) return 'Graveyard';
    if (desc.includes('spellslinger') || desc.includes('storm')) return 'Spellslinger';
  }

  return 'Midrange'; // Default
}

// Run the import
importMoxfieldDecks()
  .then(() => {
    console.log('Import script completed successfully');
    process.exit(0);
  })
  .catch((error) => {
    console.error('Import script failed:', error);
    process.exit(1);
  });
