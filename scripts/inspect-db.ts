/**
 * Direct database inspection
 */

import { prisma } from '../src/lib/prisma';

async function main() {
  try {
    // Check all tables
    const cardCount = await prisma.card.count();
    const synergyCount = await prisma.cardSynergy.count();
    const comboCount = await prisma.combo.count();
    const deckCount = await prisma.commanderDeck.count();

    console.log('📊 Database Row Counts:');
    console.log(`   Cards: ${cardCount.toLocaleString()}`);
    console.log(`   Card Synergies: ${synergyCount.toLocaleString()}`);
    console.log(`   Combos: ${comboCount.toLocaleString()}`);
    console.log(`   Commander Decks: ${deckCount.toLocaleString()}`);

    // Check if there are any synergies at all
    const anySynergy = await prisma.cardSynergy.findFirst();
    console.log(`\nFirst synergy record: ${anySynergy ? 'EXISTS' : 'NONE'}`);
    if (anySynergy) {
      console.log('Sample:', JSON.stringify(anySynergy, null, 2));
    }

  } catch (error) {
    console.error('❌ Error:', error);
  } finally {
    await prisma.$disconnect();
  }
}

main();
