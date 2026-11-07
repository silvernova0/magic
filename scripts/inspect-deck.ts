import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function inspectDeck() {
  const deck = await prisma.commanderDeck.findFirst({
    where: { source: 'moxfield' }
  });

  if (deck) {
    console.log('Deck ID:', deck.id);
    console.log('Name:', deck.name);
    console.log('Commander:', deck.commander);
    console.log('Power Level:', deck.powerLevel);
    console.log('Source:', deck.source);
    console.log('\nDecklist type:', typeof deck.decklist);
    console.log('Decklist:', JSON.stringify(deck.decklist, null, 2).substring(0, 1000));
  }

  await prisma.$disconnect();
}

inspectDeck().catch(console.error);
