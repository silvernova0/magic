import type { Deck as PrismaDeck } from '@prisma/client';

export type CardCategory = 'commander' | 'creatures' | 'planeswalkers' | 'sorceries' | 'instants' | 'artifacts' | 'enchantments' | 'lands';

export type Decklist = {
  [key in CardCategory]?: string[];
};

export type Deck = PrismaDeck;