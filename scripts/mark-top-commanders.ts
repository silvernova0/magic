/**
 * Mark Top Commanders in Database
 * Uses existing EDHREC rankings from MTGJson data to mark top 100 commanders
 */

import { prisma } from '../src/lib/prisma';

async function main() {
  console.log('🔍 Finding top 100 commanders by EDHREC rank...\n');

  try {
    // Find cards that could be commanders (legendary creatures + valid commander cards)
    // and have EDHREC rankings
    const potentialCommanders = await prisma.card.findMany({
      where: {
        edhrecRank: {
          not: null,
        },
        OR: [
          {
            typeLine: {
              contains: 'Legendary Creature',
            },
          },
          {
            typeLine: {
              contains: 'can be your commander',
            },
          },
          {
            // Planeswalkers that can be commanders
            AND: [
              {
                typeLine: {
                  contains: 'Planeswalker',
                },
              },
              {
                oracleText: {
                  contains: 'can be your commander',
                },
              },
            ],
          },
        ],
      },
      orderBy: {
        edhrecRank: 'asc',
      },
      take: 100,
      select: {
        id: true,
        name: true,
        edhrecRank: true,
        isCommander: true,
      },
    });

    console.log(`✅ Found ${potentialCommanders.length} top-ranked legendary creatures\n`);

    let updated = 0;
    let alreadyMarked = 0;

    // Mark these as commanders
    for (const commander of potentialCommanders) {
      try {
        if (commander.isCommander) {
          alreadyMarked++;
          console.log(`✓ Already marked: ${commander.name} (Rank: ${commander.edhrecRank})`);
        } else {
          await prisma.card.update({
            where: { id: commander.id },
            data: {
              isCommander: true,
            },
          });
          updated++;
          console.log(`✅ Marked: ${commander.name} (Rank: ${commander.edhrecRank})`);
        }
      } catch (error) {
        console.error(`❌ Error processing ${commander.name}:`, error);
      }
    }

    console.log(`\n📊 Summary:`);
    console.log(`   - Newly marked: ${updated} commanders`);
    console.log(`   - Already marked: ${alreadyMarked} commanders`);
    console.log(`   - Total: ${potentialCommanders.length} top commanders`);
    console.log(`\n✅ Database updated! Now run: npm run import:edhrec:synergies`);

  } catch (error) {
    console.error('❌ Error:', error);
    process.exit(1);
  } finally {
    await prisma.$disconnect();
  }
}

main();
