/**
 * Enhanced EDHREC Synergy Importer
 * Scrapes commander pages for detailed synergy and combo data
 * Stores in CardSynergy and Combo tables
 */

import { prisma } from '../src/lib/prisma';
import { scrapeCommanderDetails } from '../src/lib/scrapers/edhrec';

const BATCH_SIZE = 10; // Process 10 commanders at a time
const DELAY_BETWEEN_BATCHES = 5000; // 5 seconds between batches

async function main() {
  console.log('🔍 Starting Enhanced EDHREC Synergy Import...\n');

  try {
    // Get top commanders from database (those with highest deck counts or lowest ranks)
    const commanders = await prisma.card.findMany({
      where: {
        isCommander: true,
        edhrecRank: { not: null, lt: 2000 }, // Top 2000 commanders
        NOT: {
          name: { startsWith: 'A-' } // Exclude Alchemy cards
        }
      },
      orderBy: {
        edhrecRank: 'asc',
      },
      take: 50, // Top 50 commanders
      select: {
        id: true,
        name: true,
        edhrecRank: true,
      },
    });

    console.log(`Found ${commanders.length} commanders to process\n`);

    let totalSynergies = 0;
    let totalCombos = 0;
    let processedCount = 0;

    // Process in batches
    for (let i = 0; i < commanders.length; i += BATCH_SIZE) {
      const batch = commanders.slice(i, i + BATCH_SIZE);
      console.log(`\n📦 Processing batch ${Math.floor(i / BATCH_SIZE) + 1}/${Math.ceil(commanders.length / BATCH_SIZE)}`);

      for (const commander of batch) {
        try {
          console.log(`  ⚙️  Processing: ${commander.name} (EDHREC Rank: ${commander.edhrecRank || 'N/A'})`);

          // Build EDHREC URL
          const commanderSlug = commander.name.toLowerCase()
            .replace(/[^a-z0-9]+/g, '-')
            .replace(/^-|-$/g, '');
          const url = `https://edhrec.com/commanders/${commanderSlug}`;

          // Scrape commander details
          const details = await scrapeCommanderDetails(url);

          // Store synergies
          if (details.synergies && details.synergies.length > 0) {
            for (const synergy of details.synergies) {
              // Find the synergy card
              const synergyCard = await prisma.card.findFirst({
                where: { name: synergy.cardName },
                select: { id: true },
              });

              if (synergyCard) {
                await prisma.cardSynergy.upsert({
                  where: {
                    cardId_synergyId_commander: {
                      cardId: commander.id,
                      synergyId: synergyCard.id,
                      commander: commander.name,
                    },
                  },
                  create: {
                    cardId: commander.id,
                    synergyId: synergyCard.id,
                    score: synergy.score,
                    source: 'edhrec',
                    commander: commander.name,
                  },
                  update: {
                    score: synergy.score,
                  },
                });

                totalSynergies++;
              }
            }
            console.log(`    ✅ Stored ${details.synergies.length} synergies`);
          }

          // Store combos
          if (details.combos && details.combos.length > 0) {
            for (const combo of details.combos) {
              // Create combo
              const createdCombo = await prisma.combo.create({
                data: {
                  name: combo.name,
                  description: combo.steps.join(' → '),
                  colors: JSON.stringify(combo.colors),
                  steps: JSON.stringify(combo.steps),
                  result: combo.result,
                  popularity: 0,
                  source: 'edhrec',
                  sourceUrl: url,
                },
              });

              // Link combo cards
              for (const cardName of combo.cards) {
                const card = await prisma.card.findFirst({
                  where: { name: cardName },
                  select: { id: true },
                });

                if (card) {
                  await prisma.comboCard.create({
                    data: {
                      comboId: createdCombo.id,
                      cardId: card.id,
                      quantity: 1,
                    },
                  });
                }
              }

              totalCombos++;
            }
            console.log(`    ✅ Stored ${details.combos.length} combos`);
          }

          processedCount++;
        } catch (error) {
          console.error(`    ❌ Error processing ${commander.name}:`, error);
        }

        // Small delay between commanders
        await new Promise(resolve => setTimeout(resolve, 1000));
      }

      // Delay between batches
      if (i + BATCH_SIZE < commanders.length) {
        console.log(`\n⏳ Waiting ${DELAY_BETWEEN_BATCHES / 1000}s before next batch...`);
        await new Promise(resolve => setTimeout(resolve, DELAY_BETWEEN_BATCHES));
      }
    }

    console.log('\n✅ Import Complete!');
    console.log(`📊 Statistics:`);
    console.log(`   - Commanders Processed: ${processedCount}`);
    console.log(`   - Total Synergies Stored: ${totalSynergies}`);
    console.log(`   - Total Combos Stored: ${totalCombos}`);
  } catch (error) {
    console.error('❌ Import failed:', error);
    throw error;
  } finally {
    await prisma.$disconnect();
  }
}

main()
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
