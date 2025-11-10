import type { Card } from '@prisma/client';

export interface CardSummary {
  id: string;
  name: string;
  typeLine: string;
  oracleText: string | null;
  cmc: number;
  colors: string;
  colorIdentity: string;
  keywords: string | null;
  edhrecRank: number | null;
  isCommander: boolean;
}

const tribeTagMap: Record<string, string> = {
  Dragon: 'tribal_dragons',
  Goblin: 'tribal_goblins',
  Elf: 'tribal_elves',
  Zombie: 'tribal_zombies',
  Angel: 'tribal_angels',
  Sliver: 'tribal_slivers',
  Soldier: 'tribal_soldiers',
};

export function inferCardTags(card: CardSummary): Set<string> {
  const tags = new Set<string>();
  const text = (card.oracleText ?? '').toLowerCase();
  const keywords = (card.keywords ?? '').toLowerCase();
  const typeLine = card.typeLine.toLowerCase();

  const addTag = (tag: string) => {
    if (tag) tags.add(tag);
  };

  if (text.includes('add {') || text.includes('treasure token') || text.includes('search your library for a land')) {
    addTag('ramp');
  }
  if (text.includes('draw') || text.includes('investigate')) {
    addTag('card_draw');
  }
  if (text.includes('destroy target') || text.includes('exile target') || text.includes('deal') && text.includes('damage') && text.includes('target')) {
    addTag('removal');
  }
  if (text.includes('destroy all') || text.includes('each creature')) {
    addTag('board_wipe');
  }
  if (text.includes('search your library')) {
    addTag('tutor');
  }
  if (text.includes('hexproof') || text.includes('indestructible') || text.includes('protection from')) {
    addTag('protection');
  }
  if (text.includes('counter target')) {
    addTag('counterspell');
  }
  if (text.includes('token')) {
    addTag('tokens');
  }
  if (text.includes('graveyard') || text.includes('from your graveyard')) {
    addTag('graveyard');
  }
  if (text.includes('sacrifice')) {
    addTag('sacrifice');
  }
  if (text.includes('+1/+1 counter') || keywords.includes('proliferate')) {
    addTag('counters');
  }
  if (text.includes('haste')) {
    addTag('haste');
  }

  Object.entries(tribeTagMap).forEach(([subtype, tag]) => {
    if (card.typeLine.includes(subtype)) {
      addTag(tag);
    }
  });

  if (card.edhrecRank && card.edhrecRank < 200) {
    addTag('staple');
  }

  if (card.isCommander) {
    addTag('commander');
  }

  return tags;
}

export function parseColors(value: string | null | undefined): string[] {
  if (!value) return [];
  return value
    .split(',')
    .map((c) => c.trim().toUpperCase())
    .filter(Boolean);
}

