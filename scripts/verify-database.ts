import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function verifyDatabase() {
  console.log('🔍 Verifying Database State\n');
  console.log('═══════════════════════════════════════════════════\n');

  // Count all records
  const cardCount = await prisma.card.count();
  const synergyCount = await prisma.cardSynergy.count();
  const deckCount = await prisma.commanderDeck.count();

  console.log('📊 Total Records:');
  console.log(`   Cards: ${cardCount.toLocaleString()}`);
  console.log(`   Synergies: ${synergyCount.toLocaleString()}`);
  console.log(`   Commander Decks: ${deckCount.toLocaleString()}`);
  console.log('');

  // Count decks by source
  const mtgtop8Decks = await prisma.commanderDeck.count({
    where: { source: 'mtgtop8' }
  });
  const moxfieldDecks = await prisma.commanderDeck.count({
    where: { source: 'moxfield' }
  });

  console.log('📦 Decks by Source:');
  console.log(`   MTGTop8: ${mtgtop8Decks}`);
  console.log(`   Moxfield: ${moxfieldDecks}`);
  console.log('');

  // Count decks by power level
  console.log('⚡ Decks by Power Level:');
  for (let level = 1; level <= 5; level++) {
    const count = await prisma.commanderDeck.count({
      where: { powerLevel: level }
    });
    console.log(`   Level ${level}: ${count} decks`);
  }
  console.log('');

  // Sample some Moxfield decks
  console.log('🎴 Sample Moxfield Decks:');
  const sampleDecks = await prisma.commanderDeck.findMany({
    where: { source: 'moxfield' },
    take: 5,
    select: {
      name: true,
      commander: true,
      theme: true,
      powerLevel: true,
      popularity: true,
      decklist: true,
    }
  });

  for (const deck of sampleDecks) {
    const decklist = deck.decklist as any;
    const cardCount = decklist.mainboard?.length || 0;
    console.log(`   • ${deck.name}`);
    console.log(`     Commander: ${deck.commander || 'Unknown'}`);
    console.log(`     Theme: ${deck.theme} | Power: ${deck.powerLevel} | Cards: ${cardCount}`);
    console.log(`     Popularity: ${deck.popularity || 0} views`);
  }
  console.log('');

  console.log('═══════════════════════════════════════════════════');
  console.log('✅ Database verification complete!\n');
  
  await prisma.$disconnect();
}

verifyDatabase().catch((error) => {
  console.error('Error:', error);
  process.exit(1);
});
