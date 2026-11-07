/**
 * Test if EDHREC card names match our database
 */

import { prisma } from '../src/lib/prisma';
import { scrapeCommanderDetails } from '../src/lib/scrapers/edhrec';

async function main() {
  console.log('🔍 Testing card name matching...\n');

  try {
    // Scrape a sample commander
    const testUrl = 'https://edhrec.com/commanders/syr-konrad-the-grim';
    console.log(`Scraping: ${testUrl}\n`);

    const details = await scrapeCommanderDetails(testUrl);

    if (details.synergies && details.synergies.length > 0) {
      console.log(`Found ${details.synergies.length} synergies from EDHREC\n`);

      // Test first 10 card names
      console.log('Testing first 10 card names:');
      for (let i = 0; i < Math.min(10, details.synergies.length); i++) {
        const synergy = details.synergies[i];
        
        // Try to find card in database
        const card = await prisma.card.findFirst({
          where: { name: synergy.cardName },
          select: { id: true, name: true },
        });

        if (card) {
          console.log(`   ✅ "${synergy.cardName}" - FOUND`);
        } else {
          console.log(`   ❌ "${synergy.cardName}" - NOT FOUND`);
          
          // Try to find similar cards
          const similarCards = await prisma.card.findMany({
            where: {
              name: {
                contains: synergy.cardName.substring(0, 10),
              },
            },
            select: { name: true },
            take: 3,
          });

          if (similarCards.length > 0) {
            console.log(`      Similar: ${similarCards.map(c => c.name).join(', ')}`);
          }
        }
      }
    }

  } catch (error) {
    console.error('❌ Error:', error);
  } finally {
    await prisma.$disconnect();
  }
}

main();
