import { scrapeMoxfield, fetchDeckDetails } from '../src/lib/scrapers/moxfield';

async function testMoxfieldScraper() {
  console.log('🧪 Testing Moxfield scraper...\n');

  try {
    // Test 1: Fetch decks by bracket
    console.log('Test 1: Fetching decks for bracket 3 (focused)...');
    const moxfieldData = await scrapeMoxfield();
    const bracket3Decks = moxfieldData.topDecksByBracket['3'] || [];
    
    console.log(`✅ Found ${bracket3Decks.length} decks in bracket 3`);
    if (bracket3Decks.length > 0) {
      console.log('Sample deck:', {
        id: bracket3Decks[0].id,
        name: bracket3Decks[0].name,
        commander: bracket3Decks[0].commander,
        views: bracket3Decks[0].views,
        likes: bracket3Decks[0].likes
      });
    }
    console.log('');

    // Test 2: Fetch full deck details
    if (bracket3Decks.length > 0) {
      const testDeckId = bracket3Decks[0].id;
      console.log(`Test 2: Fetching full details for deck: ${testDeckId}...`);
      
      const deckDetails = await fetchDeckDetails(testDeckId);
      
      if (deckDetails) {
        console.log('✅ Successfully fetched deck details:');
        console.log(`  Name: ${deckDetails.name}`);
        console.log(`  Commanders: ${deckDetails.commanders.join(', ')}`);
        console.log(`  Mainboard cards: ${deckDetails.mainboard.length}`);
        console.log(`  Sideboard cards: ${deckDetails.sideboard.length}`);
        console.log(`  Colors: ${deckDetails.colors.join(', ')}`);
        console.log(`  Power level: ${deckDetails.powerLevel || 'N/A'}`);
        console.log(`  Views: ${deckDetails.views}`);
        console.log(`  Likes: ${deckDetails.likes}`);
        console.log(`  Hubs: ${deckDetails.hubs?.join(', ') || 'None'}`);
        console.log('  Sample cards:', deckDetails.mainboard.slice(0, 5).join(', '));
      } else {
        console.log('❌ Failed to fetch deck details');
      }
    }
    console.log('');

    // Test 3: Check all brackets
    console.log('Test 3: Checking all brackets...');
    for (let bracket = 1; bracket <= 5; bracket++) {
      const decks = moxfieldData.topDecksByBracket[bracket.toString()] || [];
      console.log(`  Bracket ${bracket}: ${decks.length} decks`);
    }
    console.log('');

    console.log('✅ All tests completed successfully!');
    console.log('\n📊 Summary:');
    const totalDecks = Object.values(moxfieldData.topDecksByBracket).flat().length;
    console.log(`  Total decks across all brackets: ${totalDecks}`);
    console.log('  Ready to run full import with: npm run import:moxfield');

  } catch (error) {
    console.error('❌ Test failed:', error);
    if (error instanceof Error) {
      console.error('Error details:', error.message);
      console.error('Stack:', error.stack);
    }
  }
}

testMoxfieldScraper();
