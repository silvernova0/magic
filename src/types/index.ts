import type { Deck, DeckStatus } from '@prisma/client';

export type { Deck, DeckStatus };


export interface Decklist {
  commander: string[];
  creatures: string[];
  sorceries: string[];
  instants: string[];
  artifacts: string[];
  enchantments: string[];
  planeswalkers: string[];
  lands: string[];
}

export type CardCategory = keyof Decklist;
