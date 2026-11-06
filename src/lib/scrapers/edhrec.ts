/**
 * EDHREC.com scraper - Enhanced JSON + HTML version
 * Fetches popular commanders, cards, synergies, and themes
 */

import * as cheerio from 'cheerio';
import { EDHRECData, CommanderStats, CardSynergy, TopCard, ComboInfo } from './types';

const EDHREC_BASE_URL = 'https://edhrec.com';
const EDHREC_JSON_BASE = 'https://json.edhrec.com/pages';

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

export async function scrapeTopCommanders(): Promise<CommanderStats[]> {
  try {
    // 1. Try EDHREC's JSON endpoint first (used by their Next.js frontend)
    const jsonRes = await fetch(`${EDHREC_JSON_BASE}/commanders/year.json`, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
        Accept: 'application/json',
      },
    });

    if (jsonRes.ok) {
      const data = await jsonRes.json();
      const cardlists = data?.container?.json_dict?.cardlists || [];
      const commanders: CommanderStats[] = [];

      for (const section of cardlists) {
        const views = section?.cardviews || [];
        for (const cv of views) {
          if (commanders.length >= 100) break;
          if (cv?.name) {
            commanders.push({
              name: cv.name,
              url: cv.url ? `${EDHREC_BASE_URL}${cv.url}` : `${EDHREC_BASE_URL}/commanders/${cv.sanitized || ''}`,
              deckCount: cv.num_decks || cv.inclusion || 0,
              colors: Array.isArray(cv.color_identity) ? cv.color_identity : [],
              rank: commanders.length + 1,
            });
          }
        }
      }

      if (commanders.length > 0) {
        console.log(`Scraped ${commanders.length} commanders from EDHREC JSON API`);
        return commanders;
      }
    }

    // 2. Fallback: scrape HTML / __NEXT_DATA__
    const response = await fetch(`${EDHREC_BASE_URL}/commanders`, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const html = await response.text();
    const $ = cheerio.load(html);
    const commanders: CommanderStats[] = [];

    const nextDataText = $('#__NEXT_DATA__').html();
    if (nextDataText) {
      try {
        const nextData = JSON.parse(nextDataText);
        const cardlists =
          nextData?.props?.pageProps?.data?.container?.json_dict?.cardlists || [];
        for (const section of cardlists) {
          for (const cv of section?.cardviews || []) {
            if (commanders.length >= 100) break;
            if (cv?.name) {
              commanders.push({
                name: cv.name,
                url: cv.url ? `${EDHREC_BASE_URL}${cv.url}` : `${EDHREC_BASE_URL}/commanders/${cv.sanitized || ''}`,
                deckCount: cv.num_decks || 0,
                colors: Array.isArray(cv.color_identity) ? cv.color_identity : [],
                rank: commanders.length + 1,
              });
            }
          }
        }
      } catch {
        // ignore JSON parse errors
      }
    }

    console.log(`Scraped ${commanders.length} commanders from EDHREC`);
    return commanders;
  } catch (error) {
    console.error('Error scraping top commanders:', error);
    return [];
  }
}

export async function scrapeCommanderDetails(commanderUrl: string): Promise<Partial<CommanderStats>> {
  try {
    let slug = commanderUrl.includes('/commanders/')
      ? commanderUrl.split('/commanders/')[1]?.replace(/\/$/, '') || ''
      : commanderUrl.replace(/^https?:\/\/[^\/]+\//, '').replace(/^\/+|\/+$/g, '');
    
    // For double-faced / transform cards, EDHREC typically indexes by the front-face slug
    if (slug.includes('--')) {
      slug = slug.split('--')[0];
    }
    if (slug) {
      const jsonRes = await fetch(`${EDHREC_JSON_BASE}/commanders/${slug}.json`, {
        headers: {
          'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
          Accept: 'application/json',
        },
      });
      if (jsonRes.ok) {
        const data = await jsonRes.json();
        const cardlists = data?.container?.json_dict?.cardlists || [];
        const synergies: CardSynergy[] = [];
        const topCards: TopCard[] = [];
        const combos: ComboInfo[] = [];

        for (const section of cardlists) {
          const category = section.tag || section.header || 'cards';
          for (const cv of section?.cardviews || []) {
            if (!cv?.name) continue;
            const synergy = typeof cv.synergy === 'number' ? Math.round(cv.synergy * 100) : 0;
            const inclusion = typeof cv.inclusion === 'number' ? cv.inclusion : 0;
            topCards.push({
              name: cv.name,
              inclusion,
              synergy,
              category,
            });
            if (synergy !== 0) {
              synergies.push({
                cardName: cv.name,
                score: Math.abs(synergy),
                inclusion,
                synType: Math.abs(synergy) >= 10 ? 'high-synergy' : 'top-card',
              });
            }
          }
        }
        return { synergies, topCards, combos };
      }
    }
    return {};
  } catch (error) {
    console.error('Error scraping commander details:', error);
    return {};
  }
}

async function scrapePopularCards(): Promise<EDHRECData['popularCards']> {
  return {};
}

async function scrapeThemes(): Promise<string[]> {
  return getDefaultThemes();
}

function getDefaultThemes(): string[] {
  return [
    'Aggro',
    'Tempo',
    'Control',
    'Midrange',
    'Combo',
    'Stax',
    'Hatebears',
    '+1/+1 Counters',
    'Tokens',
    'Aristocrats',
    'Voltron',
    'Equipment',
    'Enchantments / Enchantress',
    'Kindred',
    'Blink / Flicker',
    'Reanimator',
    'Graveyard Matters',
    'Spellslinger',
    'Lifegain',
    'Mill',
    'Wheels',
    'Lands Matter / Landfall',
    'Artifacts',
    'Superfriends',
    'Chaos',
    'Group Hug',
    'Group Slug',
    'Infect / Toxic',
    'Theft / Clones',
    'Treasure / Big Mana',
  ];
}
