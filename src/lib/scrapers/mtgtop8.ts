/**
 * MTGTop8.com scraper
 * Fetches tournament results and competitive meta data
 * Enhanced to scrape full decklists from individual deck pages
 */

import * as cheerio from 'cheerio';
import { MTGTop8Data, MTGTop8Deck } from './types';

const MTGTOP8_BASE_URL = 'https://www.mtgtop8.com';
const RATE_LIMIT_DELAY = 1000; // 1 second between requests to be respectful

// Sleep utility for rate limiting
function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

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

/**
 * Scrape a single deck page to get the full decklist
 */
export async function scrapeDeckDetails(deckUrl: string): Promise<{ mainboard: string[], sideboard: string[] } | null> {
  try {
    console.log(`Scraping deck details from: ${deckUrl}`);
    
    const fullUrl = deckUrl.startsWith('http') ? deckUrl : `${MTGTOP8_BASE_URL}${deckUrl}`;
    
    const response = await fetch(fullUrl, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
      },
    });

    if (!response.ok) {
      console.warn(`Failed to fetch deck details: ${response.status}`);
      return null;
    }

    const html = await response.text();
    const $ = cheerio.load(html);
    
    const mainboard: string[] = [];
    const sideboard: string[] = [];
    let inSideboard = false;

    // MTGTop8 uses different structures. Try multiple approaches:
    
    // Approach 1: Look for div.deck_line with quantity and card name
    $('div.deck_line').each((i, element) => {
      const text = $(element).text().trim();
      
      // Check if we're in sideboard section
      if (text.toLowerCase().includes('sideboard')) {
        inSideboard = true;
        return;
      }
      
      // Parse "1 Card Name" format
      const match = text.match(/^(\d+)\s+(.+)$/);
      if (match) {
        const quantity = parseInt(match[1]);
        const cardName = match[2].trim();
        
        const targetArray = inSideboard ? sideboard : mainboard;
        for (let i = 0; i < quantity; i++) {
          targetArray.push(cardName);
        }
      }
    });

    // Approach 2: Look for table rows with quantity in first cell
    if (mainboard.length === 0) {
      $('table tr').each((i, row) => {
        const cells = $(row).find('td');
        if (cells.length >= 2) {
          const quantityText = $(cells[0]).text().trim();
          const cardText = $(cells[1]).text().trim();
          
          // Check for sideboard header
          if (cardText.toLowerCase().includes('sideboard')) {
            inSideboard = true;
            return;
          }
          
          if (quantityText && cardText && !isNaN(parseInt(quantityText))) {
            const quantity = parseInt(quantityText);
            const targetArray = inSideboard ? sideboard : mainboard;
            
            for (let i = 0; i < quantity; i++) {
              targetArray.push(cardText);
            }
          }
        }
      });
    }

    // Approach 3: Look for plain text format in divs/spans
    if (mainboard.length === 0) {
      $('.S14, .S12').each((i, element) => {
        const text = $(element).text().trim();
        
        if (text.toLowerCase().includes('sideboard')) {
          inSideboard = true;
          return;
        }
        
        const match = text.match(/^(\d+)\s+(.+)$/);
        if (match) {
          const quantity = parseInt(match[1]);
          const cardName = match[2].trim();
          
          const targetArray = inSideboard ? sideboard : mainboard;
          for (let i = 0; i < quantity; i++) {
            targetArray.push(cardName);
          }
        }
      });
    }

    console.log(`Scraped ${mainboard.length} mainboard cards, ${sideboard.length} sideboard cards`);
    
    if (mainboard.length === 0) {
      console.warn('Could not find any cards in mainboard. Page structure may have changed.');
      return null;
    }
    
    return {
      mainboard,
      sideboard,
    };
  } catch (error) {
    console.error(`Error scraping deck details from ${deckUrl}:`, error);
    return null;
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

    // Debug: Let's see what we're getting
    console.log('Analyzing page structure...');
    
    // MTGTop8 uses different structures. Let's try multiple approaches:
    
    // Approach 1: Look for deck links in tables
    $('table tr').each((i, row) => {
      const $row = $(row);
      const link = $row.find('a[href*="event"]').first();
      
      if (link.length > 0) {
        const name = link.text().trim();
        const url = link.attr('href') || '';
        
        if (name && url && decks.length < 30) {
          // Extract commander from deck name
          const commander = extractCommanderFromDeckName(name);
          
          // Try to find placement and date from nearby cells
          const cells = $row.find('td');
          let placement = '';
          let date = '';
          let event = '';
          
          cells.each((j, cell) => {
            const text = $(cell).text().trim();
            // Look for date patterns (DD/MM/YYYY or similar)
            if (text.match(/\d{1,2}\/\d{1,2}\/\d{2,4}/)) {
              date = text;
            }
            // Look for placement (1st, 2nd, etc.)
            if (text.match(/\d+(st|nd|rd|th)/i)) {
              placement = text;
            }
          });
          
          event = name; // Use deck name as event for now
          
          decks.push({
            name,
            commander,
            placement: placement || 'Unknown',
            event,
            date: date || 'Recent',
            url: url.startsWith('http') ? url : `${MTGTOP8_BASE_URL}/${url}`,
          });
        }
      }
    });

    // Approach 2: Look for specific div structures
    if (decks.length === 0) {
      $('.S14 a[href*="event"], .S12 a[href*="event"]').each((i, element) => {
        if (i >= 30) return false;
        
        const name = $(element).text().trim();
        const url = $(element).attr('href') || '';
        
        if (name && url) {
          const commander = extractCommanderFromDeckName(name);
          
          decks.push({
            name,
            commander,
            placement: 'Unknown',
            event: name,
            date: 'Recent',
            url: url.startsWith('http') ? url : `${MTGTOP8_BASE_URL}/${url}`,
          });
        }
      });
    }

    console.log(`Scraped ${decks.length} decks from MTGTop8`);
    
    // Debug: Show first few deck names if found
    if (decks.length > 0) {
      console.log('Sample decks found:');
      decks.slice(0, 3).forEach(d => console.log(`  - ${d.name}`));
    }
    
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
