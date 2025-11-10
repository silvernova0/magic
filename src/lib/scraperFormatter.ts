/**
 * Format scraped data for Gemini AI prompts
 */

import { ScrapedData } from './scrapers/types';

export function formatScrapedDataForPrompt(data: ScrapedData, theme: string, powerLevel: string): string {
  let context = '\n\n=== REAL-TIME COMMANDER META DATA ===\n\n';

  // EDHREC Data
  if (data.edhrec) {
    context += '📊 EDHREC POPULAR COMMANDERS:\n';
    const topCommanders = data.edhrec.topCommanders.slice(0, 20);
    topCommanders.forEach((cmd, i) => {
      context += `${i + 1}. ${cmd.name} (${cmd.deckCount || '?'} decks)\n`;
    });
    context += '\n';
  }

  // MTGTop8 Tournament Data
  if (data.mtgtop8) {
    context += '🏆 MTGTOP8 RECENT TOURNAMENT RESULTS:\n';
    
    if (data.mtgtop8.topCommanders.length > 0) {
      context += 'Top Performing Commanders:\n';
      data.mtgtop8.topCommanders.slice(0, 15).forEach((cmd, i) => {
        context += `${i + 1}. ${cmd}\n`;
      });
    }

    if (Object.keys(data.mtgtop8.metaBreakdown).length > 0) {
      context += '\nMeta Breakdown:\n';
      Object.entries(data.mtgtop8.metaBreakdown)
        .sort((a, b) => b[1] - a[1])
        .forEach(([archetype, count]) => {
          context += `- ${archetype}: ${count} decks\n`;
        });
    }
    context += '\n';
  }

  // Moxfield Bracket Data
  if (data.moxfield) {
    const bracket = powerLevel;
    context += `⚡ MOXFIELD BRACKET ${bracket} TOP DECKS:\n`;
    
    const bracketDecks = data.moxfield.topDecksByBracket[bracket] || [];
    if (bracketDecks.length > 0) {
      bracketDecks.slice(0, 10).forEach((deck, i) => {
        context += `${i + 1}. ${deck.commander} - ${deck.name} (${deck.views} views)\n`;
      });
    }

    // Popular commanders for this bracket
    const brackCommanders = data.moxfield.popularCommanders
      .filter(c => c.bracket === parseInt(bracket))
      .slice(0, 10);
    
    if (brackCommanders.length > 0) {
      context += `\nPopular Bracket ${bracket} Commanders:\n`;
      brackCommanders.forEach((cmd, i) => {
        context += `${i + 1}. ${cmd.name} (${cmd.deckCount} decks)\n`;
      });
    }
    context += '\n';
  }

  context += `\n📅 Data last updated: ${data.timestamp.toLocaleString()}\n`;
  context += `\n💡 USE THIS DATA: Reference these popular commanders and strategies when building the ${theme} deck at power level ${powerLevel}.\n`;
  context += `   Consider commanders and cards that are currently performing well in the meta.\n`;
  context += '=== END META DATA ===\n\n';

  return context;
}

export function getScraperSummary(data: ScrapedData): string {
  const parts: string[] = [];
  
  if (data.edhrec) {
    parts.push(`EDHREC: ${data.edhrec.topCommanders.length} commanders`);
  }
  
  if (data.mtgtop8) {
    parts.push(`MTGTop8: ${data.mtgtop8.recentDecks.length} tournament decks`);
  }
  
  if (data.moxfield) {
    const totalDecks = Object.values(data.moxfield.topDecksByBracket)
      .reduce((sum, decks) => sum + decks.length, 0);
    parts.push(`Moxfield: ${totalDecks} top decks across all brackets`);
  }

  return parts.join(' | ');
}
