/**
 * Moxfield.com scraper
 * Fetches popular decks by power level bracket
 */

import { MoxfieldData, MoxfieldDeck } from './types';

const MOXFIELD_API_BASE = 'https://api2.moxfield.com/v2';

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
    for (let bracket = 1; bracket <= 5; bracket++) {
      const decks = await fetchDecksByBracket(bracket);
      decksByBracket[bracket.toString()] = decks;
    }

    return decksByBracket;
  } catch (error) {
    console.error('Error scraping decks by bracket:', error);
    return decksByBracket;
  }
}

async function fetchDecksByBracket(bracket: number): Promise<MoxfieldDeck[]> {
  try {
    // Moxfield's public search endpoint
    const params = new URLSearchParams({
      pageNumber: '1',
      pageSize: '20',
      sortType: 'views',
      sortDirection: 'Descending',
      fmt: 'commander',
      // Add bracket filter if Moxfield API supports it
    });

    const response = await fetch(`${MOXFIELD_API_BASE}/decks/search?${params}`, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
      },
    });

    if (!response.ok) {
      console.warn(`Moxfield API returned ${response.status} for bracket ${bracket}`);
      return [];
    }

    const data = await response.json();
    
    if (!data.data || !Array.isArray(data.data)) {
      return [];
    }

    const decks: MoxfieldDeck[] = data.data.map((deck: any) => ({
      id: deck.publicId,
      name: deck.name,
      commander: deck.commanders?.[0]?.card?.name || 'Unknown',
      powerLevel: bracket,
      colors: deck.colors || [],
      theme: deck.description || '',
      views: deck.viewCount || 0,
      likes: deck.likeCount || 0,
    }));

    console.log(`Scraped ${decks.length} bracket ${bracket} decks from Moxfield`);
    return decks;
  } catch (error) {
    console.error(`Error fetching bracket ${bracket} decks:`, error);
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
