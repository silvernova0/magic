// Debug script to see card structure in boards.commanders and boards.mainboard

async function debugCardStructure() {
  const testDeckId = 'FW1WWTKWC0Sg5ivZBMh_Ew';
  
  const response = await fetch(`https://api2.moxfield.com/v3/decks/all/${testDeckId}`, {
    headers: {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    },
  });

  const data = await response.json();
  
  console.log('=== COMMANDERS STRUCTURE ===');
  if (data.boards?.commanders?.cards) {
    const commandersObj = data.boards.commanders.cards;
    const commanderKeys = Object.keys(commandersObj);
    console.log('Number of commanders:', commanderKeys.length);
    console.log('Commander keys:', commanderKeys);
    
    if (commanderKeys.length > 0) {
      const firstCommander = commanderKeys[0];
      console.log(`\nFirst commander key: "${firstCommander}"`);
      console.log('First commander data:', JSON.stringify(commandersObj[firstCommander], null, 2).substring(0, 500));
    }
  }
  
  console.log('\n=== MAINBOARD STRUCTURE ===');
  if (data.boards?.mainboard?.cards) {
    const mainboardObj = data.boards.mainboard.cards;
    const mainboardKeys = Object.keys(mainboardObj);
    console.log('Number of unique cards:', mainboardKeys.length);
    console.log('First 5 card keys:', mainboardKeys.slice(0, 5));
    
    if (mainboardKeys.length > 0) {
      const firstCard = mainboardKeys[0];
      console.log(`\nFirst card key: "${firstCard}"`);
      console.log('First card data:', JSON.stringify(mainboardObj[firstCard], null, 2).substring(0, 800));
    }
  }
}

debugCardStructure().catch(console.error);
