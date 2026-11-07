// Debug script to inspect Moxfield API response structure

async function debugMoxfieldAPI() {
  const testDeckId = 'FW1WWTKWC0Sg5ivZBMh_Ew'; // "Civ 6 Singularity"
  
  console.log('Fetching deck details from Moxfield API...\n');
  
  const response = await fetch(`https://api2.moxfield.com/v3/decks/all/${testDeckId}`, {
    headers: {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    },
  });

  const data = await response.json();
  
  console.log('=== FULL RESPONSE STRUCTURE ===');
  console.log(JSON.stringify(data, null, 2).substring(0, 3000)); // First 3000 chars
  
  console.log('\n=== BOARDS OBJECT ===');
  if (data.boards) {
    console.log('Available board types:', Object.keys(data.boards));
    
    if (data.boards.commanders) {
      console.log('\nCommanders:', Object.keys(data.boards.commanders));
    }
    
    if (data.boards.mainboard) {
      const mainboardKeys = Object.keys(data.boards.mainboard);
      console.log(`\nMainboard: ${mainboardKeys.length} unique cards`);
      console.log('First 5 cards:', mainboardKeys.slice(0, 5));
      
      // Show structure of first card
      const firstCard = mainboardKeys[0];
      console.log(`\nStructure of "${firstCard}":`, JSON.stringify(data.boards.mainboard[firstCard], null, 2));
    }
    
    if (data.boards.sideboard) {
      console.log('\nSideboard:', Object.keys(data.boards.sideboard).length, 'cards');
    }
  }
  
  console.log('\n=== OTHER DECK DATA ===');
  console.log('Name:', data.name);
  console.log('Format:', data.format);
  console.log('Colors:', data.colors);
  console.log('Power Level:', data.powerLevel);
  console.log('Views:', data.viewCount);
  console.log('Hubs type:', Array.isArray(data.hubs) ? 'array' : typeof data.hubs);
  if (data.hubs) {
    console.log('Hubs:', data.hubs);
  }
}

debugMoxfieldAPI().catch(console.error);
