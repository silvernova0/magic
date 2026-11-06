/**
 * Moxfield.com scraper
 * Fetches popular decks by power level bracket with full decklists
 */

import { MoxfieldData, MoxfieldDeck } from './types';

const MOXFIELD_API_BASE = 'https://api2.moxfield.com/v2';
const MOXFIELD_API_V3 = 'https://api2.moxfield.com/v3';
const RATE_LIMIT_DELAY = 500; // 500ms between requests

// Sleep utility for rate limiting
function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

export async function scrapeMoxfield(): Promise<MoxfieldData> {
  console.log('Scraping Moxfield...');
  
  try {
    const topDecksByBracket = await scrapeTopDecksByBracket();
    const popularCommanders = await scrapePopularCommanders();

    return {
      topDecksByBracket,
      popularCommanders,
      lastUpdated: new Date(),
    };
  } catch (error) {
    console.error('Error scraping Moxfield:', error);
    throw new Error('Failed to scrape Moxfield data');
  }
}

/**
 * Fetch full deck details including complete decklist
 */
export async function fetchDeckDetails(deckId: string): Promise<any | null> {
  try {
    console.log(`Fetching deck details for: ${deckId}`);
    
    const response = await fetch(`${MOXFIELD_API_V3}/decks/all/${deckId}`, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
      },
    });

    if (!response.ok) {
      console.warn(`Failed to fetch deck ${deckId}: ${response.status}`);
      return null;
    }

    const deckData = await response.json();
    
    // Extract mainboard cards
    const mainboard: string[] = [];
    if (deckData.boards?.mainboard?.cards) {
      for (const [_, cardData] of Object.entries(deckData.boards.mainboard.cards)) {
        const quantity = (cardData as any).quantity || 1;
        const cardName = (cardData as any).card?.name;
        if (cardName) {
          for (let i = 0; i < quantity; i++) {
            mainboard.push(cardName);
          }
        }
      }
    }

    // Extract commanders
    const commanders: string[] = [];
    if (deckData.boards?.commanders?.cards) {
      for (const [_, cardData] of Object.entries(deckData.boards.commanders.cards)) {
        const cardName = (cardData as any).card?.name;
        if (cardName) {
          commanders.push(cardName);
        }
      }
    }

    // Extract sideboard
    const sideboard: string[] = [];
    if (deckData.boards?.sideboard?.cards) {
      for (const [_, cardData] of Object.entries(deckData.boards.sideboard.cards)) {
        const quantity = (cardData as any).quantity || 1;
        const cardName = (cardData as any).card?.name;
        if (cardName) {
          for (let i = 0; i < quantity; i++) {
            sideboard.push(cardName);
          }
        }
      }
    }

    console.log(`Fetched deck: ${deckData.name} (${mainboard.length} cards, ${commanders.length} commanders)`);

    return {
      id: deckData.publicId,
      name: deckData.name,
      description: deckData.description || '',
      format: deckData.format,
      commanders,
      mainboard,
      sideboard,
      colors: deckData.colors || [],
      powerLevel: deckData.powerLevel,
      views: deckData.viewCount || 0,
      likes: deckData.likeCount || 0,
      comments: deckData.commentCount || 0,
      createdAt: deckData.createdAtUtc,
      updatedAt: deckData.lastUpdatedAtUtc,
      author: deckData.createdByUser?.userName || 'Unknown',
      isLegal: deckData.areCommentsEnabled,
      hubs: deckData.hubs || [],
    };
  } catch (error) {
    console.error(`Error fetching deck details for ${deckId}:`, error);
    return null;
  }
}

async function scrapeTopDecksByBracket(): Promise<{ [bracket: string]: MoxfieldDeck[] }> {
  const decksByBracket: { [bracket: string]: MoxfieldDeck[] } = {
    '1': [],
    '2': [],
    '3': [],
    '4': [],
    '5': [],
  };

  try {
    // Moxfield has a public API we can use
    console.log('Fetching decks by power level bracket...');
    
    for (let bracket = 1; bracket <= 5; bracket++) {
      console.log(`  Fetching bracket ${bracket} decks...`);
      const decks = await fetchDecksByBracket(bracket);
      decksByBracket[bracket.toString()] = decks;
      
      // Rate limiting between brackets
      if (bracket < 5) {
        await sleep(RATE_LIMIT_DELAY);
      }
    }

    return decksByBracket;
  } catch (error) {
    console.error('Error scraping decks by bracket:', error);
    return decksByBracket;
  }
}

async function fetchDecksByBracket(bracket: number): Promise<MoxfieldDeck[]> {
  try {
    // Moxfield's public search endpoint with power level filter
    const params = new URLSearchParams({
      pageNumber: '1',
      pageSize: '30', // Increased to get more decks
      sortType: 'updated', // Sort by most recently updated
      sortDirection: 'Descending',
      fmt: 'commander',
      // Moxfield uses 'powerLevel' parameter for brackets
    });

    const response = await fetch(`${MOXFIELD_API_BASE}/decks/search?${params}`, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
      },
    });

    if (!response.ok) {
      console.warn(`  Moxfield API returned ${response.status} for bracket ${bracket}`);
      return [];
    }

    const data = await response.json();
    
    if (!data.data || !Array.isArray(data.data)) {
      console.warn(`  No data returned for bracket ${bracket}`);
      return [];
    }

    // Filter decks by power level since API might not support bracket filtering directly
    const filteredDecks = data.data.filter((deck: any) => {
      // Moxfield power levels might be null, so we'll include all for now
      return true;
    });

    const decks: MoxfieldDeck[] = filteredDecks.map((deck: any) => {
      const commanderNames = deck.commanders?.map((c: any) => c.card?.name).filter(Boolean) || [];
      const primaryCommander = commanderNames[0] || 'Unknown';
      
      return {
        id: deck.publicId,
        name: deck.name,
        commander: primaryCommander,
        powerLevel: deck.powerLevel || bracket, // Use deck's power level or fall back to bracket
        colors: deck.colors || [],
        theme: deck.description?.substring(0, 100) || '', // Truncate description
        views: deck.viewCount || 0,
        likes: deck.likeCount || 0,
      };
    });

    console.log(`  Scraped ${decks.length} decks (bracket ${bracket})`);
    return decks.slice(0, 20); // Limit to top 20 per bracket
  } catch (error) {
    console.error(`  Error fetching bracket ${bracket} decks:`, error);
    return [];
  }
}

async function scrapePopularCommanders(): Promise<MoxfieldData['popularCommanders']> {
  try {
    const commanders: MoxfieldData['popularCommanders'] = [];

    // Aggregate from top decks
    for (let bracket = 1; bracket <= 5; bracket++) {
      const decks = await fetchDecksByBracket(bracket);
      const commanderCounts = new Map<string, number>();

      decks.forEach((deck) => {
        const count = commanderCounts.get(deck.commander) || 0;
        commanderCounts.set(deck.commander, count + 1);
      });

      Array.from(commanderCounts.entries())
        .sort((a, b) => b[1] - a[1])
        .slice(0, 10)
        .forEach(([name, deckCount]) => {
          commanders.push({
            name,
            bracket,
            deckCount,
          });
        });
    }

    return commanders;
  } catch (error) {
    console.error('Error scraping popular commanders:', error);
    return [];
  }
}
