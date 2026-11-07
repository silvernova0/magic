/**
 * Check synergy import results
 */

import { prisma } from '../src/lib/prisma';

async function main() {
  console.log('📊 Checking EDHREC synergy import results...\n');

  try {
    // Count total synergies
    const synergyCount = await prisma.cardSynergy.count();
    console.log(`Total synergies: ${synergyCount.toLocaleString()}`);

    // Count unique commanders with synergies
    const commandersWithSynergies = await prisma.cardSynergy.groupBy({
      by: ['commander'],
      _count: true,
    });
    const uniqueCommanders = commandersWithSynergies.filter(c => c.commander !== null);
    console.log(`Commanders with synergies: ${uniqueCommanders.length}`);

    // Get average synergies per commander
    if (uniqueCommanders.length > 0) {
      const avgSynergies = synergyCount / uniqueCommanders.length;
      console.log(`Average synergies per commander: ${Math.round(avgSynergies)}`);
    }

    // Sample some synergies
    console.log('\n📋 Sample high-synergy cards:');
    const sampleSynergies = await prisma.cardSynergy.findMany({
      take: 10,
      include: {
        card: {
          select: { name: true },
        },
      },
      orderBy: {
        score: 'desc',
      },
      where: {
        commander: { not: null },
      },
    });

    sampleSynergies.forEach((syn) => {
      console.log(`   - ${syn.card.name} with ${syn.commander}: ${syn.score}% synergy (${syn.source})`);
    });

    console.log('\n✅ Import verification complete!');
  } catch (error) {
    console.error('❌ Error:', error);
    process.exit(1);
  } finally {
    await prisma.$disconnect();
  }
}

main();
