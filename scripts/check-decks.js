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
    
    // Check decklist structure
    if (deck.decklist) {
      const decklist = typeof deck.decklist === 'string' ? JSON.parse(deck.decklist) : deck.decklist;
      console.log(`  Decklist structure:`);
      console.log(`    Commander: ${Array.isArray(decklist.commander) ? decklist.commander.length : 'N/A'} cards`);
      if (Array.isArray(decklist.commander) && decklist.commander.length > 0) {
        console.log(`      Example: ${decklist.commander.slice(0, 3).join(', ')}`);
      }
      console.log(`    Creatures: ${Array.isArray(decklist.creatures) ? decklist.creatures.length : 'N/A'} cards`);
      if (Array.isArray(decklist.creatures) && decklist.creatures.length > 0) {
        console.log(`      Example: ${decklist.creatures.slice(0, 5).join(', ')}`);
      }
      console.log(`    Instants: ${Array.isArray(decklist.instants) ? decklist.instants.length : 'N/A'} cards`);
      console.log(`    Sorceries: ${Array.isArray(decklist.sorceries) ? decklist.sorceries.length : 'N/A'} cards`);
      console.log(`    Artifacts: ${Array.isArray(decklist.artifacts) ? decklist.artifacts.length : 'N/A'} cards`);
      console.log(`    Enchantments: ${Array.isArray(decklist.enchantments) ? decklist.enchantments.length : 'N/A'} cards`);
      console.log(`    Planeswalkers: ${Array.isArray(decklist.planeswalkers) ? decklist.planeswalkers.length : 'N/A'} cards`);
      console.log(`    Lands: ${Array.isArray(decklist.lands) ? decklist.lands.length : 'N/A'} cards`);
      if (Array.isArray(decklist.lands) && decklist.lands.length > 0) {
        console.log(`      Example: ${decklist.lands.slice(0, 5).join(', ')}`);
      }
      
      const totalCards = (
        (Array.isArray(decklist.commander) ? decklist.commander.length : 0) +
        (Array.isArray(decklist.creatures) ? decklist.creatures.length : 0) +
        (Array.isArray(decklist.instants) ? decklist.instants.length : 0) +
        (Array.isArray(decklist.sorceries) ? decklist.sorceries.length : 0) +
        (Array.isArray(decklist.artifacts) ? decklist.artifacts.length : 0) +
        (Array.isArray(decklist.enchantments) ? decklist.enchantments.length : 0) +
        (Array.isArray(decklist.planeswalkers) ? decklist.planeswalkers.length : 0) +
        (Array.isArray(decklist.lands) ? decklist.lands.length : 0)
      );
      console.log(`    TOTAL: ${totalCards} cards`);
    } else {
      console.log(`  Decklist: NULL or EMPTY`);
    }
    console.log('');
  });
}

main()
  .catch(console.error)
  .finally(() => prisma.$disconnect());
