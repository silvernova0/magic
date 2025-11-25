/**
 * EDHREC.com scraper - Enhanced version
 * Fetches popular commanders, cards, synergies, and combos
 */

import * as cheerio from 'cheerio';
import { EDHRECData, CommanderStats, CardSynergy, TopCard, ComboInfo } from './types';

const EDHREC_BASE_URL = 'https://edhrec.com';
const REQUEST_DELAY = 1000; // 1 second delay between requests to be respectful

// Helper function to delay between requests
const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

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

/**
 * Scrape detailed commander data including synergies and combos
 */
export async function scrapeCommanderDetails(commanderUrl: string): Promise<Partial<CommanderStats>> {
  try {
    console.log(`Scraping commander details from: ${commanderUrl}`);

    const response = await fetch(commanderUrl, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const html = await response.text();
    const $ = cheerio.load(html);

    // Extract synergy data
    const synergies: CardSynergy[] = [];
    const topCards: TopCard[] = [];
    const combos: ComboInfo[] = [];

    // EDHREC uses class names like Card_container__Ng56K
    // Find all card containers
    const cardContainers = $('[class*="Card_container"]');

    console.log(`Found ${cardContainers.length} cards on page`);

    cardContainers.each((i, cardEl) => {
      // Get card name - EDHREC may have the name in multiple child elements
      const cardNameEl = $(cardEl).find('[class*="Card_name"]');
      // Get only the first matching element's text to avoid duplication
      const cardName = cardNameEl.first().text().trim();

      if (!cardName) return;

      // Get CardLabel container with stats
      const labelContainer = $(cardEl).find('[class*="CardLabel_container"]');

      // Find inclusion percentage (23% inclusion)
      let inclusion = 0;
      const inclusionLine = labelContainer.find('[class*="CardLabel_line"]').first();
      const inclusionPercent = inclusionLine.find('[class*="CardLabel_stat"]').text().trim();
      const inclusionLabel = inclusionLine.find('[class*="CardLabel_label"]').text().trim();

      if (inclusionLabel.toLowerCase().includes('inclusion')) {
        inclusion = parseInt(inclusionPercent.replace('%', '')) || 0;
      }

      // Find synergy score (5% synergy or +5% synergy)
      let synergy = 0;
      const synergyLine = labelContainer.find('[class*="CardLabel_line"]').eq(1);
      const synergyPercent = synergyLine.find('[class*="CardLabel_stat"]').text().trim();
      const synergyLabel = synergyLine.find('[class*="CardLabel_label"]').text().trim();

      if (synergyLabel.toLowerCase().includes('synergy')) {
        const synergyText = synergyPercent.replace('%', '').trim();
        synergy = parseInt(synergyText) || 0;
      }

      // Determine category based on position in page
      // You could enhance this by tracking section headers
      let category = 'cards';

      if (cardName && (inclusion > 0 || synergy !== 0)) {
        // Add to top cards
        topCards.push({
          name: cardName,
          inclusion,
          synergy,
          category,
        });

        // Add to synergies if there's a meaningful synergy score
        if (synergy !== 0) {
          synergies.push({
            cardName,
            score: Math.abs(synergy),
            inclusion,
            synType: Math.abs(synergy) >= 10 ? 'high-synergy' : 'top-card',
          });
        }
      }
    });

    // Scrape combos - fetch the combos page
    const combosUrl = `${commanderUrl}/combos`;
    console.log(`Scraping combos from: ${combosUrl}`);

    try {
      const comboResponse = await fetch(combosUrl, {
        headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36' }
      });

      if (comboResponse.ok) {
        const comboHtml = await comboResponse.text();
        const $c = cheerio.load(comboHtml);

        // Find combo containers (usually .Combo_container or similar)
        // EDHREC structure varies, but often combos are in cards with specific layout
        const comboContainers = $c('[class*="Combo_container"]');

        comboContainers.each((i, el) => {
          const cards: string[] = [];
          // Extract card names in the combo
          $c(el).find('[class*="Card_name"]').each((_, nameEl) => {
            cards.push($c(nameEl).text().trim());
          });

          // Extract description/result
          const description = $c(el).find('[class*="Combo_description"]').text().trim() ||
            $c(el).find('[class*="CardLabel_label"]').text().trim();

          if (cards.length >= 2) {
            combos.push({
              name: cards.join(' + '),
              cards,
              colors: [], // We'd need to infer this
              steps: parseComboSteps(description),
              result: extractComboResult(description)
            });
          }
        });
      }
    } catch (e) {
      console.warn(`Failed to scrape combos for ${commanderUrl}: ${e}`);
    }

    console.log(`Scraped: ${synergies.length} synergies, ${topCards.length} top cards, ${combos.length} combos`);

    return {
      synergies,
      topCards,
      combos,
    };
  } catch (error) {
    console.error(`Error scraping commander details:`, error);
    return {};
  }
}

/**
 * Scrape top commanders with enhanced data
 */
export async function scrapeTopCommanders(): Promise<CommanderStats[]> {
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

    // Parse commander cards
    $('.Commander_list_item').each((i, element) => {
      if (i >= 100) return false; // Limit to top 100

      const name = $(element).find('.Commander_name').text().trim();
      const url = $(element).find('a').attr('href') || '';
      const deckCountText = $(element).find('.Commander_decks').text();
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

// ============================================
// HELPER FUNCTIONS
// ============================================

/**
 * Parse synergy score from EDHREC text
 * Example: "+15%" -> 15
 */
function parseSynergyScore(text: string): number {
  if (!text) return 0;
  const match = text.match(/([\d.]+)%?/);
  return match ? parseFloat(match[1]) : 0;
}

/**
 * Parse inclusion percentage from EDHREC text
 * Example: "45%" -> 45
 */
function parseInclusionScore(text: string): number {
  if (!text) return 0;
  const match = text.match(/([\d.]+)%?/);
  return match ? parseFloat(match[1]) : 0;
}

/**
 * Parse combo steps from description
 */
function parseComboSteps(description: string): string[] {
  if (!description) return [];

  // Split on common step indicators
  const steps = description.split(/\d+\.\s+|Step\s+\d+:?\s+/i).filter(s => s.trim());

  // If no numbered steps found, split on periods or line breaks
  if (steps.length <= 1) {
    return description.split(/[.\n]+/).filter(s => s.trim().length > 10);
  }

  return steps.map(s => s.trim()).filter(s => s.length > 0);
}

/**
 * Extract combo result from description
 */
function extractComboResult(description: string): string {
  if (!description) return 'Unknown result';

  // Look for result indicators
  const resultKeywords = ['result:', 'this creates', 'this generates', 'win the game', 'infinite'];
  const lower = description.toLowerCase();

  for (const keyword of resultKeywords) {
    const index = lower.indexOf(keyword);
    if (index !== -1) {
      // Extract the sentence containing the result
      const remaining = description.substring(index);
      const sentences = remaining.split(/[.!]/);
      if (sentences[0]) {
        return sentences[0].trim();
      }
    }
  }

  // Fallback: use first sentence if it mentions key terms
  const firstSentence = description.split(/[.!]/)[0];
  if (firstSentence && (
    firstSentence.toLowerCase().includes('infinite') ||
    firstSentence.toLowerCase().includes('win') ||
    firstSentence.toLowerCase().includes('damage') ||
    firstSentence.toLowerCase().includes('create')
  )) {
    return firstSentence.trim();
  }

  return 'See combo description for details';
}
