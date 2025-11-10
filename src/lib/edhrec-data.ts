import fs from 'fs';
import path from 'path';
import readline from 'readline';

export interface EDHRECDeckData {
  commander: string;
  slug: string;
  url: string;
  all_cards: string[];
  themes: string[];
  total_cards: number;
}

/**
 * Get popular cards for a commander from EDHREC average decks data
 * This provides AI-like suggestions based on what other players use
 */
export async function getEDHRECPopularCards(commanderName: string): Promise<string[]> {
  const dataPath = path.join(process.cwd(), 'data', 'training', 'edhrec_average_decks.jsonl');
  
  // Check if file exists
  if (!fs.existsSync(dataPath)) {
    console.log('EDHREC data file not found');
    return [];
  }

  try {
    const fileStream = fs.createReadStream(dataPath);
    const rl = readline.createInterface({
      input: fileStream,
      crlfDelay: Infinity
    });

    for await (const line of rl) {
      try {
        const data: EDHRECDeckData = JSON.parse(line);
        
        // Match commander name (case-insensitive)
        if (data.commander.toLowerCase() === commanderName.toLowerCase()) {
          // Filter out the commander itself and "As Card" placeholder
          const popularCards = data.all_cards.filter(
            card => card !== commanderName && card !== 'As Card'
          );
          
          console.log(`Found ${popularCards.length} popular cards for ${commanderName} from EDHREC`);
          return popularCards;
        }
      } catch (parseError) {
        // Skip malformed lines
        continue;
      }
    }

    console.log(`No EDHREC data found for commander: ${commanderName}`);
    return [];
  } catch (error) {
    console.error('Error reading EDHREC data:', error);
    return [];
  }
}

/**
 * Get the top N most popular cards for a commander
 */
export async function getTopEDHRECCards(commanderName: string, count: number = 30): Promise<string[]> {
  const allPopular = await getEDHRECPopularCards(commanderName);
  return allPopular.slice(0, count);
}
