/**
 * Test MTGTop8 deck detail scraper
 */

import { scrapeMTGTop8, scrapeDeckDetails } from '../src/lib/scrapers/mtgtop8';

async function testMTGTop8Scraper() {
  console.log('🧪 Testing MTGTop8 scraper...\n');

  try {
    // Test 1: Scrape recent decks list
    console.log('Test 1: Scraping recent Commander decks list...');
    const data = await scrapeMTGTop8();
    
    console.log(`✅ Found ${data.recentDecks.length} decks`);
    console.log(`✅ Top commanders: ${data.topCommanders.slice(0, 5).join(', ')}`);
    console.log(`✅ Meta breakdown:`, data.metaBreakdown);
    
    if (data.recentDecks.length > 0) {
      console.log('\n📋 First deck:');
      const firstDeck = data.recentDecks[0];
      console.log(`   Name: ${firstDeck.name}`);
      console.log(`   Commander: ${firstDeck.commander}`);
      console.log(`   Event: ${firstDeck.event}`);
      console.log(`   Placement: ${firstDeck.placement}`);
      console.log(`   URL: ${firstDeck.url}`);

      // Test 2: Scrape deck details
      console.log('\nTest 2: Scraping deck details from first deck...');
      const deckDetails = await scrapeDeckDetails(firstDeck.url);
      
      if (deckDetails) {
        console.log(`✅ Mainboard: ${deckDetails.mainboard.length} cards`);
        console.log(`✅ Sideboard: ${deckDetails.sideboard.length} cards`);
        
        if (deckDetails.mainboard.length > 0) {
          console.log('\n📋 Sample cards:');
          deckDetails.mainboard.slice(0, 10).forEach(card => {
            console.log(`   - ${card}`);
          });
        }
      } else {
        console.log('⚠️  Could not scrape deck details (page structure may have changed)');
      }
    }

    console.log('\n✅ All tests completed!');
  } catch (error) {
    console.error('❌ Test failed:', error);
    throw error;
  }
}

testMTGTop8Scraper()
  .then(() => {
    console.log('\nTest script completed');
    process.exit(0);
  })
  .catch((error) => {
    console.error('\nTest script failed:', error);
    process.exit(1);
  });
