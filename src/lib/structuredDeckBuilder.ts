import { prisma } from './prisma';
import { Card } from '@prisma/client';
import { inferCardTags, parseColors, CardSummary } from './cardTagUtils';

export interface StructuredDeckPlan {
  commander?: string;
  commanders?: string[];
  strategy?: string;
  bracket?: number;
  power_level?: number;
  card_selection: Record<string, CardSelectionSection | null | undefined>;
}

export interface CardSelectionSection {
  count: number;
  filters: StructuredCardFilter[];
}

export interface StructuredCardFilter {
  types?: string[];
  subtypes?: string[];
  tags?: string[];
  colors_within?: string[];
  cmc_max?: number;
  cmc_min?: number;
  instant_speed?: boolean;
  reason?: string;
  priority?: 'high' | 'medium' | 'low';
}

export interface DeckCard {
  name: string;
  role: string;
  reason?: string;
}

export interface BuildResult {
  commander?: CardSummary;
  cards: DeckCard[];
  errors: string[];
  warnings: string[];
}

export async function buildDeckFromStructure(plan: StructuredDeckPlan): Promise<BuildResult> {
  const errors: string[] = [];
  const warnings: string[] = [];
  const cards: DeckCard[] = [];
  const used = new Set<string>();

  const cardPool = await prisma.card.findMany({
    select: {
      id: true,
      name: true,
      typeLine: true,
      oracleText: true,
      cmc: true,
      colors: true,
      colorIdentity: true,
      keywords: true,
      edhrecRank: true,
      isCommander: true,
    },
  });

  const commanderName = plan.commander || plan.commanders?.[0];
  let commanderCard: CardSummary | undefined;

  if (commanderName) {
    commanderCard = findCardByName(cardPool, commanderName);
    if (commanderCard) {
      cards.push({ name: commanderCard.name, role: 'commander' });
      used.add(commanderCard.name.toLowerCase());
    } else {
      errors.push(`Commander "${commanderName}" not found in card database.`);
    }
  } else {
    warnings.push('No commander specified in structured output.');
  }

  const categories = Object.entries(plan.card_selection || {});

  for (const [category, section] of categories) {
    if (!section || !section.count || section.count <= 0) continue;
    const filters = section.filters && section.filters.length > 0 ? section.filters : [{}];
    const countPerFilter = Math.max(1, Math.floor(section.count / filters.length));
    let collected = 0;

    for (const filter of filters) {
      const needed = Math.min(countPerFilter, section.count - collected);
      if (needed <= 0) break;

      const picked = pickCardsForFilter(cardPool, filter, needed, used);
      if (picked.length === 0) {
        warnings.push(`No cards found for category "${category}" with filter ${JSON.stringify(filter)}. Falling back to staples.`);
        const staples = pickStaples(cardPool, needed, used, commanderCard);
        cards.push(...staples.map((card) => ({ name: card.name, role: category, reason: filter.reason })));
        staples.forEach((card) => used.add(card.name.toLowerCase()));
        collected += staples.length;
      } else {
        cards.push(...picked.map((card) => ({ name: card.name, role: category, reason: filter.reason })));
        picked.forEach((card) => used.add(card.name.toLowerCase()));
        collected += picked.length;
      }
    }

    while (collected < section.count) {
      const filler = pickStaples(cardPool, 1, used, commanderCard);
      if (filler.length === 0) break;
      cards.push({ name: filler[0].name, role: category });
      used.add(filler[0].name.toLowerCase());
      collected += 1;
    }
  }

  const totalNeeded = 100 - cards.length;
  if (totalNeeded > 0) {
    const basicColor = commanderCard ? parseColors(commanderCard.colorIdentity) : [];
    const basics = generateBasicLands(totalNeeded, basicColor);
    basics.forEach((name) => {
      cards.push({ name, role: 'land', reason: 'Auto-filled to reach 100 cards' });
    });
    warnings.push(`Deck was short by ${totalNeeded} cards. Added basic lands as filler.`);
  }

  return {
    commander: commanderCard,
    cards,
    errors,
    warnings,
  };
}

function findCardByName(pool: CardSummary[], name: string): CardSummary | undefined {
  const lower = name.trim().toLowerCase();
  return pool.find((card) => card.name.toLowerCase() === lower);
}

function pickCardsForFilter(
  pool: CardSummary[],
  filter: StructuredCardFilter,
  needed: number,
  used: Set<string>
): CardSummary[] {
  let candidates = pool.filter((card) => !used.has(card.name.toLowerCase()));

  if (filter.types && filter.types.length > 0) {
    const needles = filter.types.map((t) => t.toLowerCase());
    candidates = candidates.filter((card) => needles.every((needle) => card.typeLine.toLowerCase().includes(needle)));
  }
  if (filter.subtypes && filter.subtypes.length > 0) {
    const needles = filter.subtypes.map((t) => t.toLowerCase());
    candidates = candidates.filter((card) => needles.every((needle) => card.typeLine.toLowerCase().includes(needle)));
  }
  if (filter.colors_within) {
    const allowed = filter.colors_within.map((c) => c.toUpperCase());
    candidates = candidates.filter((card) => isWithinColors(card, allowed));
  }
  if (typeof filter.cmc_max === 'number') {
    candidates = candidates.filter((card) => card.cmc <= filter.cmc_max!);
  }
  if (typeof filter.cmc_min === 'number') {
    candidates = candidates.filter((card) => card.cmc >= filter.cmc_min!);
  }
  if (filter.instant_speed) {
    candidates = candidates.filter((card) => card.typeLine.toLowerCase().includes('instant'));
  }
  if (filter.tags && filter.tags.length > 0) {
    candidates = candidates.filter((card) => {
      const tags = inferCardTags(card);
      return filter.tags!.every((tag) => tags.has(tag));
    });
  }

  if (candidates.length === 0) {
    return [];
  }

  const sorted = candidates.sort((a, b) => {
    const rankA = a.edhrecRank ?? Number.MAX_SAFE_INTEGER;
    const rankB = b.edhrecRank ?? Number.MAX_SAFE_INTEGER;
    return rankA - rankB;
  });

  return sorted.slice(0, needed);
}

function isWithinColors(card: CardSummary, allowed: string[]): boolean {
  if (allowed.length === 0) return true;
  const identity = parseColors(card.colorIdentity);
  return identity.every((color) => allowed.includes(color));
}

function pickStaples(
  pool: CardSummary[],
  count: number,
  used: Set<string>,
  commander?: CardSummary
): CardSummary[] {
  const commanderColors = commander ? parseColors(commander.colorIdentity) : [];
  const staples = pool.filter((card) => {
    if (used.has(card.name.toLowerCase())) return false;
    if (commanderColors.length > 0 && !isWithinColors(card, commanderColors)) return false;
    return (card.edhrecRank ?? Number.MAX_SAFE_INTEGER) < 5000;
  });

  return staples.sort((a, b) => (a.edhrecRank ?? 999999) - (b.edhrecRank ?? 999999)).slice(0, count);
}

function generateBasicLands(count: number, colors: string[]): string[] {
  if (colors.length === 0) {
    return Array(count).fill('Wastes');
  }
  const basicsMap: Record<string, string> = {
    W: 'Plains',
    U: 'Island',
    B: 'Swamp',
    R: 'Mountain',
    G: 'Forest',
  };
  const pool = colors.map((c) => basicsMap[c] ?? 'Wastes');
  const result: string[] = [];
  for (let i = 0; i < count; i++) {
    result.push(pool[i % pool.length]);
  }
  return result;
}

