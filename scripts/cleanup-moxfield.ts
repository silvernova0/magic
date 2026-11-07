import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function cleanupMoxfieldDecks() {
  console.log('🧹 Cleaning up Moxfield decks from database...\n');

  const deleteResult = await prisma.commanderDeck.deleteMany({
    where: { source: 'moxfield' }
  });

  console.log(`✅ Deleted ${deleteResult.count} Moxfield decks\n`);
  
  await prisma.$disconnect();
}

cleanupMoxfieldDecks().catch(console.error);
