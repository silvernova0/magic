const { PrismaClient } = require('@prisma/client');

const prisma = new PrismaClient();

async function main() {
  console.log('Checking decks in database...\n');
  
  const decks = await prisma.deck.findMany({
    include: {
      user: {
        select: {
          email: true,
        },
      },
    },
  });

  console.log(`Total decks found: ${decks.length}\n`);

  decks.forEach((deck, index) => {
    console.log(`Deck ${index + 1}:`);
    console.log(`  ID: ${deck.id}`);
    console.log(`  Name: ${deck.name}`);
    console.log(`  Status: ${deck.status}`);
    console.log(`  Theme: ${deck.theme}`);
    console.log(`  Power Level: ${deck.powerLevel}`);
    console.log(`  User: ${deck.user.email}`);
    console.log(`  Created: ${deck.createdAt}`);
    console.log(`  Updated: ${deck.updatedAt}`);
    console.log('');
  });
}

main()
  .catch(console.error)
  .finally(() => prisma.$disconnect());
