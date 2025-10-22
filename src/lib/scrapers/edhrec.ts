/**
 * EDHREC.com scraper
 * Fetches popular commanders, cards, and synergies
 */

import * as cheerio from 'cheerio';
import { EDHRECData, CommanderStats } from './types';

const EDHREC_BASE_URL = 'https://edhrec.com';

export async function scrapeEDHREC(): Promise<EDHRECData> {
  console.log('Scraping EDHREC...');
  
  try {
    const topCommanders = await scrapeTopCommanders();
    const popularCards = await scrapePopularCards();
    const themes = await scrapeThemes();

    return {
      topCommanders,
      popularCards,
      themes,
      lastUpdated: new Date(),
    };
  } catch (error) {
    console.error('Error scraping EDHREC:', error);
    throw new Error('Failed to scrape EDHREC data');
  }
}

async function scrapeTopCommanders(): Promise<CommanderStats[]> {
  try {
    const response = await fetch(`${EDHREC_BASE_URL}/commanders`, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const html = await response.text();
    const $ = cheerio.load(html);
    const commanders: CommanderStats[] = [];

    // Parse commander cards (adjust selectors based on actual EDHREC structure)
    $('.card-view').each((i, element) => {
      if (i >= 50) return false; // Limit to top 50

      const name = $(element).find('.card-name').text().trim();
      const url = $(element).find('a').attr('href') || '';
      const deckCountText = $(element).find('.deck-count').text();
      const deckCount = parseInt(deckCountText.replace(/\D/g, '')) || 0;

      if (name) {
        commanders.push({
          name,
          url: url.startsWith('http') ? url : `${EDHREC_BASE_URL}${url}`,
          deckCount,
          colors: extractColorsFromName(name),
          rank: i + 1,
        });
      }
    });

    console.log(`Scraped ${commanders.length} commanders from EDHREC`);
    return commanders;
  } catch (error) {
    console.error('Error scraping top commanders:', error);
    return [];
  }
}

async function scrapePopularCards(): Promise<EDHRECData['popularCards']> {
  try {
    // For now, return a structure that can be populated
    // In production, you'd scrape specific commander pages
    return {};
  } catch (error) {
    console.error('Error scraping popular cards:', error);
    return {};
  }
}

async function scrapeThemes(): Promise<string[]> {
  try {
    const response = await fetch(`${EDHREC_BASE_URL}/themes`, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
      },
    });

    if (!response.ok) {
      return getDefaultThemes();
    }

    const html = await response.text();
    const $ = cheerio.load(html);
    const themes: string[] = [];

    $('.theme-name').each((i, element) => {
      const theme = $(element).text().trim();
      if (theme) themes.push(theme);
    });

    return themes.length > 0 ? themes : getDefaultThemes();
  } catch (error) {
    console.error('Error scraping themes:', error);
    return getDefaultThemes();
  }
}

function extractColorsFromName(name: string): string[] {
  // Basic color extraction - can be enhanced
  const colors: string[] = [];
  const colorMap = {
    'White': 'W',
    'Blue': 'U',
    'Black': 'B',
    'Red': 'R',
    'Green': 'G',
  };

  Object.entries(colorMap).forEach(([colorName, symbol]) => {
    if (name.toLowerCase().includes(colorName.toLowerCase())) {
      colors.push(symbol);
    }
  });

  return colors;
}

function getDefaultThemes(): string[] {
  return [
    'Aggro',
    'Control',
    'Combo',
    'Stax',
    'Midrange',
    'Tempo',
    'Tokens',
    'Aristocrats',
    'Voltron',
    'Group Hug',
    'Chaos',
    'Tribal',
    'Lands',
    'Artifacts',
    'Enchantments',
    'Spellslinger',
    'Reanimator',
    'Graveyard',
    '+1/+1 Counters',
    'Wheels',
  ];
}
