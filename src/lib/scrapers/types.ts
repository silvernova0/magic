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
