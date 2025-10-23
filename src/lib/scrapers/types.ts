/**
 * Types for web scraping data from MTG sources
 */

export interface CommanderStats {
  name: string;
  url: string;
  deckCount?: number;
  colors: string[];
  theme?: string;
  popularCards?: string[];
  rank?: number;
  // Enhanced synergy data
  synergies?: CardSynergy[];
  combos?: ComboInfo[];
  topCards?: TopCard[];
}

export interface CardSynergy {
  cardName: string;
  score: number; // 0-100
  inclusion: number; // Percentage of decks
  synType?: string; // 'high-synergy', 'signature', 'staple', 'creature', 'instant', etc.
}

export interface ComboInfo {
  name: string;
  cards: string[];
  steps: string[];
  result: string;
  colors: string[];
  source?: string;
}

export interface TopCard {
  name: string;
  inclusion: number; // Percentage
  synergy: number; // Synergy score
  category: string; // 'creature', 'instant', 'sorcery', etc.
}

export interface EDHRECData {
  topCommanders: CommanderStats[];
  popularCards: {
    [cardName: string]: {
      synergy: number;
      inclusion: number;
    };
  };
  themes: string[];
  lastUpdated: Date;
}

export interface MTGTop8Deck {
  name: string;
  commander: string;
  placement: string;
  event: string;
  date: string;
  url: string;
  mainboard?: string[];
  sideboard?: string[];
}

export interface MTGTop8Data {
  recentDecks: MTGTop8Deck[];
  topCommanders: string[];
  metaBreakdown: {
    [archetype: string]: number;
  };
  lastUpdated: Date;
}

export interface MoxfieldDeck {
  id: string;
  name: string;
  commander: string;
  powerLevel: number; // 1-5 bracket
  colors: string[];
  theme: string;
  views: number;
  likes: number;
}

export interface MoxfieldData {
  topDecksByBracket: {
    [bracket: string]: MoxfieldDeck[];
  };
  popularCommanders: {
    name: string;
    bracket: number;
    deckCount: number;
  }[];
  lastUpdated: Date;
}

export interface ScrapedData {
  edhrec?: EDHRECData;
  mtgtop8?: MTGTop8Data;
  moxfield?: MoxfieldData;
  timestamp: Date;
}
