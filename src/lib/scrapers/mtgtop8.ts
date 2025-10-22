/**
 * MTGTop8.com scraper
 * Fetches tournament results and competitive meta data
 */

import * as cheerio from 'cheerio';
import { MTGTop8Data, MTGTop8Deck } from './types';

const MTGTOP8_BASE_URL = 'https://www.mtgtop8.com';

export async function scrapeMTGTop8(): Promise<MTGTop8Data> {
  console.log('Scraping MTGTop8...');
  
  try {
    const recentDecks = await scrapeRecentCommanderDecks();
    const topCommanders = extractTopCommanders(recentDecks);
    const metaBreakdown = calculateMetaBreakdown(recentDecks);

    return {
      recentDecks,
      topCommanders,
      metaBreakdown,
      lastUpdated: new Date(),
    };
  } catch (error) {
    console.error('Error scraping MTGTop8:', error);
    throw new Error('Failed to scrape MTGTop8 data');
  }
}

async function scrapeRecentCommanderDecks(): Promise<MTGTop8Deck[]> {
  try {
    // MTGTop8 Commander format page
    const response = await fetch(`${MTGTOP8_BASE_URL}/format?f=EDH`, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
      },
    });

    if (!response.ok) {
      console.warn(`MTGTop8 returned ${response.status}, using fallback data`);
      return [];
    }

    const html = await response.text();
    const $ = cheerio.load(html);
    const decks: MTGTop8Deck[] = [];

    // Parse deck listings (adjust selectors based on actual MTGTop8 structure)
    $('.deck_line').each((i, element) => {
      if (i >= 30) return false; // Limit to 30 most recent

      const name = $(element).find('.deck_name').text().trim();
      const commander = extractCommanderFromDeckName(name);
      const placement = $(element).find('.placement').text().trim();
      const event = $(element).find('.event').text().trim();
      const date = $(element).find('.date').text().trim();
      const url = $(element).find('a').attr('href') || '';

      if (name && commander) {
        decks.push({
          name,
          commander,
          placement,
          event,
          date,
          url: url.startsWith('http') ? url : `${MTGTOP8_BASE_URL}${url}`,
        });
      }
    });

    console.log(`Scraped ${decks.length} decks from MTGTop8`);
    return decks;
  } catch (error) {
    console.error('Error scraping recent Commander decks:', error);
    return [];
  }
}

function extractCommanderFromDeckName(deckName: string): string {
  // Commander names are usually at the start or in brackets
  // Example: "Yuriko - Ninja Tribal" or "Cedh [Tivit]"
  
  const bracketMatch = deckName.match(/\[(.*?)\]/);
  if (bracketMatch) {
    return bracketMatch[1];
  }

  const dashSplit = deckName.split(' - ')[0];
  if (dashSplit) {
    return dashSplit.trim();
  }

  return deckName.split(' ')[0];
}

function extractTopCommanders(decks: MTGTop8Deck[]): string[] {
  const commanderCounts = new Map<string, number>();

  decks.forEach((deck) => {
    const count = commanderCounts.get(deck.commander) || 0;
    commanderCounts.set(deck.commander, count + 1);
  });

  return Array.from(commanderCounts.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, 20)
    .map(([commander]) => commander);
}

function calculateMetaBreakdown(decks: MTGTop8Deck[]): { [archetype: string]: number } {
  const breakdown: { [archetype: string]: number } = {};

  decks.forEach((deck) => {
    const archetype = inferArchetype(deck.name);
    breakdown[archetype] = (breakdown[archetype] || 0) + 1;
  });

  return breakdown;
}

function inferArchetype(deckName: string): string {
  const name = deckName.toLowerCase();

  if (name.includes('cedh') || name.includes('turbo')) return 'cEDH';
  if (name.includes('stax')) return 'Stax';
  if (name.includes('combo')) return 'Combo';
  if (name.includes('aggro') || name.includes('voltron')) return 'Aggro';
  if (name.includes('control')) return 'Control';
  if (name.includes('midrange') || name.includes('value')) return 'Midrange';
  if (name.includes('tribal')) return 'Tribal';
  
  return 'Other';
}
