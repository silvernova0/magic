import { prisma } from './prisma';

export interface LimitedPoolEntry {
  name: string;
  quantity: number;
}

export interface TaggedPoolCard {
  id: string;
  name: string;
  quantity: number;
  manaCost: string;
  cmc: number;
  colors: string[];
  colorIdentity: string[];
  typeLine: string;
  oracleText: string;
  rarity: string;
  power?: string | null;
  toughness?: string | null;
  edhrecRank: number;
  category: 'creatures' | 'instants' | 'sorceries' | 'artifacts' | 'enchantments' | 'planeswalkers' | 'lands';
  roles: string[];
  synergyTags: string[];
  baseQualityScore: number;
}

export interface LimitedDeckRecommendation {
  rank: number;
  guildName: string;
  colors: string[];
  archetypeTitle: string;
  primarySynergies: { tag: string; count: number }[];
  totalScore: number;
  summary: string;
  stats: {
    creatures: number;
    nonCreatures: number;
    lands: number;
    removalCount: number;
    bombCount: number;
    avgCmc: number;
    curve: Record<string, number>;
  };
  decklist: {
    creatures: string[];
    instants: string[];
    sorceries: string[];
    artifacts: string[];
    enchantments: string[];
    planeswalkers: string[];
    lands: string[];
  };
  keyCards: { name: string; reason: string; tags: string[] }[];
  sideboard: { name: string; quantity: number; colors: string[]; typeLine: string; tags: string[] }[];
}

export interface LimitedAnalysisResult {
  poolSize: number;
  uniqueCardsResolved: number;
  unresolvedNames: string[];
  poolTagSummary: { tag: string; count: number }[];
  recommendations: LimitedDeckRecommendation[];
  buildTimeMs: number;
}

const GUILDS: { colors: [string, string]; name: string }[] = [
  { colors: ['W', 'U'], name: 'Azorius (W/U)' },
  { colors: ['U', 'B'], name: 'Dimir (U/B)' },
  { colors: ['B', 'R'], name: 'Rakdos (B/R)' },
  { colors: ['R', 'G'], name: 'Gruul (R/G)' },
  { colors: ['G', 'W'], name: 'Selesnya (G/W)' },
  { colors: ['W', 'B'], name: 'Orzhov (W/B)' },
  { colors: ['U', 'R'], name: 'Izzet (U/R)' },
  { colors: ['B', 'G'], name: 'Golgari (B/G)' },
  { colors: ['R', 'W'], name: 'Boros (R/W)' },
  { colors: ['G', 'U'], name: 'Simic (G/U)' },
];

const BASIC_LAND_BY_COLOR: Record<string, string> = {
  W: 'Plains',
  U: 'Island',
  B: 'Swamp',
  R: 'Mountain',
  G: 'Forest',
};

const BASIC_LANDS = new Set(['Plains', 'Island', 'Swamp', 'Mountain', 'Forest', 'Wastes']);

const TRIBAL_TYPES = [
  'Elf',
  'Goblin',
  'Zombie',
  'Vampire',
  'Dragon',
  'Wizard',
  'Angel',
  'Human',
  'Soldier',
  'Knight',
  'Warrior',
  'Spirit',
  'Elemental',
  'Merfolk',
  'Dinosaur',
  'Cat',
  'Bird',
  'Rogue',
  'Pirate',
  'Sliver',
];

function parseColorArray(raw: string | null | undefined): string[] {
  if (!raw) return [];
  const trimmed = raw.trim();
  if (!trimmed) return [];
  if (trimmed.startsWith('[')) {
    try {
      const parsed = JSON.parse(trimmed);
      if (Array.isArray(parsed)) return parsed.map(String).filter(Boolean);
    } catch {
      // fall through
    }
  }
  return trimmed
    .split(',')
    .map((s) => s.trim().toUpperCase())
    .filter((s) => ['W', 'U', 'B', 'R', 'G'].includes(s));
}

function categorize(typeLine: string): TaggedPoolCard['category'] {
  const main = typeLine.split('//')[0].toLowerCase();
  if (main.includes('land')) return 'lands';
  if (main.includes('creature')) return 'creatures';
  if (main.includes('planeswalker')) return 'planeswalkers';
  if (main.includes('instant')) return 'instants';
  if (main.includes('sorcery')) return 'sorceries';
  if (main.includes('artifact')) return 'artifacts';
  if (main.includes('enchantment')) return 'enchantments';
  return 'artifacts';
}

export function parsePoolText(poolText: string): LimitedPoolEntry[] {
  const map = new Map<string, { name: string; quantity: number }>();
  const lines = poolText.split(/\r?\n/);

  for (const rawLine of lines) {
    let line = rawLine.trim();
    if (!line || line.startsWith('//') || line.startsWith('#') || /^deck$/i.test(line) || /^sideboard$/i.test(line)) {
      continue;
    }

    // Strip Arena set/collector suffix like "1 Lightning Bolt (STA) 42"
    line = line.replace(/\s+\([A-Z0-9]{2,5}\)\s*\d*.*$/i, '').trim();

    let qty = 1;
    let cardName = line;

    const match = line.match(/^(\d+)\s*x?\s+(.+)$/i);
    if (match) {
      qty = Math.max(1, Math.min(20, parseInt(match[1], 10) || 1));
      cardName = match[2].trim();
    }

    if (!cardName || BASIC_LANDS.has(cardName)) continue;

    const key = cardName.toLowerCase();
    const existing = map.get(key);
    if (existing) {
      existing.quantity += qty;
    } else {
      map.set(key, { name: cardName, quantity: qty });
    }
  }

  return Array.from(map.values());
}

function tagAndScoreCard(card: {
  id: string;
  name: string;
  manaCost: string | null;
  cmc: number;
  colors: string;
  colorIdentity: string;
  typeLine: string;
  oracleText: string | null;
  rarity: string;
  power: string | null;
  toughness: string | null;
  edhrecRank: number | null;
}, quantity: number): TaggedPoolCard {
  const text = (card.oracleText || '').toLowerCase();
  const typeLower = (card.typeLine || '').toLowerCase();
  const category = categorize(card.typeLine || '');
  const colors = parseColorArray(card.colors);
  const colorIdentity = parseColorArray(card.colorIdentity);
  const effectiveColors = colors.length > 0 ? colors : colorIdentity;
  const rank = card.edhrecRank ?? 20000;

  const roles: string[] = [];
  const synergyTags: string[] = [];

  // Functional Roles (BREAD)
  const isRemoval =
    text.includes('destroy target') ||
    text.includes('exile target') ||
    text.includes('destroy all') ||
    (text.includes('deals ') && text.includes('damage to any target')) ||
    (text.includes('deals ') && text.includes('damage to target creature')) ||
    text.includes('target creature gets -') ||
    text.includes('fights target') ||
    text.includes("enchanted creature can't attack or block");
  if (isRemoval) roles.push('Removal');

  const isDraw =
    text.includes('draw a card') ||
    text.includes('draw two cards') ||
    text.includes('draw cards') ||
    text.includes('investigate') ||
    text.includes('connive');
  if (isDraw) roles.push('Card Advantage');

  const isRampFixing =
    category !== 'lands' &&
    (text.includes('search your library for a basic land') ||
      text.includes('add one mana of any color') ||
      text.includes('create a treasure token') ||
      (text.includes('add {') && card.cmc <= 3));
  if (isRampFixing) roles.push('Ramp / Fixing');

  const isEvasion =
    text.includes('flying') ||
    text.includes('menace') ||
    text.includes('trample') ||
    text.includes("can't be blocked");
  if (isEvasion && category === 'creatures') roles.push('Evasion');

  // Synergy Archetype Tags
  if (text.includes('+1/+1 counter') || text.includes('proliferate') || text.includes('modified') || text.includes('adapt') || text.includes('bolster') || text.includes('outlast') || text.includes('evolve') || text.includes('mentor') || text.includes('training')) {
    synergyTags.push('+1/+1 Counters');
  }
  if (text.includes('token') || text.includes('populate') || text.includes('creatures you control get +')) {
    synergyTags.push('Tokens / Go-Wide');
  }
  if (text.includes('sacrifice') || text.includes('whenever a creature you control dies') || text.includes('whenever another creature dies') || text.includes('morbid')) {
    synergyTags.push('Sacrifice / Aristocrats');
  }
  if (text.includes('graveyard') || text.includes('mill') || text.includes('flashback') || text.includes('unearth') || text.includes('return target creature card from your graveyard')) {
    synergyTags.push('Graveyard Value');
  }
  if ((category === 'instants' || category === 'sorceries') || text.includes('instant or sorcery') || text.includes('prowess') || text.includes('magecraft')) {
    if (text.includes('instant or sorcery') || text.includes('prowess') || text.includes('magecraft') || text.includes('noncreature spell')) {
      synergyTags.push('Spellslinger');
    }
  }
  if (category === 'artifacts' || text.includes('artifact') || text.includes('treasure') || text.includes('metalcraft') || text.includes('affinity')) {
    if (text.includes('artifact') || category === 'artifacts') {
      synergyTags.push('Artifacts Matter');
    }
  }
  if (category === 'enchantments' || text.includes('enchantment') || text.includes('aura') || text.includes('constellation')) {
    if (text.includes('enchantment') || text.includes('aura') || category === 'enchantments') {
      synergyTags.push('Enchantments / Auras');
    }
  }
  if ((text.includes('exile target') && text.includes('return')) || text.includes('when this creature enters') || text.includes('enters the battlefield')) {
    synergyTags.push('ETB / Blink');
  }
  if (text.includes('gain life') || text.includes('lifelink') || text.includes('whenever you gain life')) {
    synergyTags.push('Lifegain');
  }
  if (text.includes('landfall') || text.includes('whenever a land enters') || text.includes('lands you control')) {
    synergyTags.push('Landfall / Lands');
  }
  if (category === 'creatures' && card.cmc <= 3 && (text.includes("can't") || text.includes('more to cast') || text.includes('enter tapped'))) {
    synergyTags.push('Hatebears / Tax');
  }

  for (const tribe of TRIBAL_TYPES) {
    if (typeLower.includes(tribe.toLowerCase()) || text.includes(tribe.toLowerCase())) {
      synergyTags.push(`Kindred: ${tribe}s`);
    }
  }

  // Base Limited Card Quality Score (0-100)
  let baseQualityScore = 40;
  const rarityLower = (card.rarity || '').toLowerCase();
  if (rarityLower === 'mythic') baseQualityScore += 28;
  else if (rarityLower === 'rare') baseQualityScore += 20;
  else if (rarityLower === 'uncommon') baseQualityScore += 10;

  if (rank <= 1500) baseQualityScore += 18;
  else if (rank <= 5000) baseQualityScore += 12;
  else if (rank <= 12000) baseQualityScore += 6;

  if (isRemoval) baseQualityScore += 22;
  if (isDraw) baseQualityScore += 12;
  if (isEvasion) baseQualityScore += 8;
  if (isRampFixing) baseQualityScore += 8;

  // Efficient curve bonus for Limited (2-4 drops are premium)
  if (category === 'creatures' && card.cmc >= 2 && card.cmc <= 4) {
    baseQualityScore += 8;
  }

  const isBomb =
    (rarityLower === 'mythic' || rarityLower === 'rare' || category === 'planeswalkers') &&
    baseQualityScore >= 65;
  if (isBomb) roles.push('Bomb');

  return {
    id: card.id,
    name: card.name,
    quantity,
    manaCost: card.manaCost || '',
    cmc: card.cmc,
    colors: effectiveColors,
    colorIdentity,
    typeLine: card.typeLine,
    oracleText: card.oracleText || '',
    rarity: card.rarity,
    power: card.power,
    toughness: card.toughness,
    edhrecRank: rank,
    category,
    roles,
    synergyTags,
    baseQualityScore,
  };
}

export async function analyzeLimitedPool(poolText: string): Promise<LimitedAnalysisResult> {
  const startTime = Date.now();
  const entries = parsePoolText(poolText);

  if (entries.length === 0) {
    throw new Error('No valid card names found in pool. Paste one card per line (e.g., "2 Llanowar Elves" or "1x Swords to Plowshares").');
  }

  // Query SQLite database for matching cards
  const uniqueNames = entries.map((e) => e.name);
  const dbCards = await prisma.card.findMany({
    where: {
      name: { in: uniqueNames },
    },
    select: {
      id: true,
      name: true,
      manaCost: true,
      cmc: true,
      colors: true,
      colorIdentity: true,
      typeLine: true,
      oracleText: true,
      rarity: true,
      power: true,
      toughness: true,
      edhrecRank: true,
    },
  });

  const dbMap = new Map<string, (typeof dbCards)[0]>();
  for (const c of dbCards) {
    const existing = dbMap.get(c.name.toLowerCase());
    if (!existing || (c.edhrecRank ?? 99999) < (existing.edhrecRank ?? 99999)) {
      dbMap.set(c.name.toLowerCase(), c);
    }
  }

  // Case-insensitive fallback lookup for any cards that didn't match exact case
  const unresolvedNames: string[] = [];
  const taggedPool: TaggedPoolCard[] = [];

  for (const entry of entries) {
    let found = dbMap.get(entry.name.toLowerCase());
    if (!found) {
      const fuzzy = await prisma.card.findFirst({
        where: { name: { contains: entry.name } },
        orderBy: { edhrecRank: 'asc' },
        select: {
          id: true,
          name: true,
          manaCost: true,
          cmc: true,
          colors: true,
          colorIdentity: true,
          typeLine: true,
          oracleText: true,
          rarity: true,
          power: true,
          toughness: true,
          edhrecRank: true,
        },
      });
      if (fuzzy) found = fuzzy;
    }

    if (found) {
      taggedPool.push(tagAndScoreCard(found, entry.quantity));
    } else {
      unresolvedNames.push(entry.name);
    }
  }

  if (taggedPool.length === 0) {
    throw new Error('Could not match any of the provided card names in the local 31,483-card database.');
  }

  // Fetch pairwise CardSynergy rows for cards in this pool
  const cardIds = taggedPool.map((c) => c.id);
  const synergyRows = await prisma.cardSynergy.findMany({
    where: { cardId: { in: cardIds } },
    select: { cardId: true, synergyId: true, score: true },
    take: 500,
  });

  const poolSlugSet = new Set(
    taggedPool.map((c) => c.name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, ''))
  );
  const directSynergyBonusById = new Map<string, number>();
  for (const row of synergyRows) {
    if (poolSlugSet.has(row.synergyId.toLowerCase())) {
      directSynergyBonusById.set(row.cardId, (directSynergyBonusById.get(row.cardId) || 0) + Math.min(30, row.score));
    }
  }

  // Aggregate overall pool tags
  const globalTagCounts = new Map<string, number>();
  let totalPoolCards = 0;
  for (const card of taggedPool) {
    totalPoolCards += card.quantity;
    for (const tag of card.synergyTags) {
      globalTagCounts.set(tag, (globalTagCounts.get(tag) || 0) + card.quantity);
    }
  }

  const poolTagSummary = Array.from(globalTagCounts.entries())
    .map(([tag, count]) => ({ tag, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 12);

  // Evaluate all 10 Two-Color Guilds
  const guildEvaluations: LimitedDeckRecommendation[] = [];

  for (const guild of GUILDS) {
    const allowedSet = new Set<string>(guild.colors);

    // Filter pool cards playable in this two-color pair
    const eligibleNonLands = taggedPool.filter((c) => {
      if (c.category === 'lands') return false;
      if (c.colors.length === 0) return true; // Colorless artifacts/eldrazi playable in any pair
      return c.colors.every((col) => allowedSet.has(col));
    });

    const eligibleLands = taggedPool.filter((c) => {
      if (c.category !== 'lands') return false;
      if (c.colorIdentity.length === 0) return true;
      return c.colorIdentity.some((col) => allowedSet.has(col));
    });

    // Count tag frequencies inside this color pair
    const pairTagCounts = new Map<string, number>();
    for (const c of eligibleNonLands) {
      for (const tag of c.synergyTags) {
        pairTagCounts.set(tag, (pairTagCounts.get(tag) || 0) + c.quantity);
      }
    }

    const sortedPairTags = Array.from(pairTagCounts.entries())
      .map(([tag, count]) => ({ tag, count }))
      .sort((a, b) => b.count - a.count);

    const topSynergies = sortedPairTags.filter((t) => t.count >= 2).slice(0, 4);
    const primaryTheme = topSynergies[0]?.tag || 'Midrange Goodstuff';

    // Score each individual card copy in this guild context
    interface ExpandedCopy {
      card: TaggedPoolCard;
      score: number;
    }

    const expandedCopies: ExpandedCopy[] = [];
    for (const c of eligibleNonLands) {
      let score = c.baseQualityScore + (directSynergyBonusById.get(c.id) || 0);

      // Boost cards that participate in this color pair's densest synergy clusters
      for (const tag of c.synergyTags) {
        const clusterSize = pairTagCounts.get(tag) || 0;
        if (clusterSize >= 3) {
          score += clusterSize * 4.5;
        }
      }

      // Slight preference for colored spells over generic filler artifacts unless Artifacts Matter
      if (c.colors.length > 0) score += 6;
      if (c.colors.length === 2 && c.colors.every((col) => allowedSet.has(col))) {
        // Gold signpost uncommons/rares get a signpost bonus
        score += 14;
      }

      for (let i = 0; i < c.quantity; i++) {
        expandedCopies.push({ card: c, score });
      }
    }

    expandedCopies.sort((a, b) => b.score - a.score);

    // Select 23 non-land playables with curve & creature/spell balance
    const targetNonLands = Math.min(23, expandedCopies.length);
    const chosenCopies: ExpandedCopy[] = [];
    const usedCopyIndices = new Set<number>();

    // First pick up to 16 top creatures (prioritizing 2-4 CMC curve)
    for (let i = 0; i < expandedCopies.length; i++) {
      if (chosenCopies.length >= 15) break;
      if (expandedCopies[i].card.category === 'creatures') {
        chosenCopies.push(expandedCopies[i]);
        usedCopyIndices.add(i);
      }
    }

    // Next pick top removal & high-synergy non-creature spells up to 23 total non-lands
    for (let i = 0; i < expandedCopies.length; i++) {
      if (chosenCopies.length >= targetNonLands) break;
      if (!usedCopyIndices.has(i)) {
        chosenCopies.push(expandedCopies[i]);
        usedCopyIndices.add(i);
      }
    }

    // Assemble 17 Lands (on-color non-basics from pool + basic land split proportional to color pips)
    const targetLands = 40 - chosenCopies.length;
    const landsList: string[] = [];
    for (const l of eligibleLands) {
      for (let q = 0; q < l.quantity; q++) {
        if (landsList.length < Math.min(6, targetLands)) {
          landsList.push(l.name);
        }
      }
    }

    // Count mana pips of the two guild colors in chosenCopies
    const pipCounts: Record<string, number> = { [guild.colors[0]]: 1, [guild.colors[1]]: 1 };
    for (const item of chosenCopies) {
      for (const col of guild.colors) {
        const matches = (item.card.manaCost.match(new RegExp(`\\{${col}\\}`, 'g')) || []).length;
        pipCounts[col] += matches > 0 ? matches : item.card.colors.includes(col) ? 1 : 0;
      }
    }

    const remainingBasics = Math.max(0, targetLands - landsList.length);
    const totalPips = pipCounts[guild.colors[0]] + pipCounts[guild.colors[1]];
    const color1Count = Math.round((pipCounts[guild.colors[0]] / totalPips) * remainingBasics);
    const color2Count = remainingBasics - color1Count;

    for (let i = 0; i < color1Count; i++) landsList.push(BASIC_LAND_BY_COLOR[guild.colors[0]]);
    for (let i = 0; i < color2Count; i++) landsList.push(BASIC_LAND_BY_COLOR[guild.colors[1]]);

    // Calculate deck score & stats
    let totalScore = chosenCopies.reduce((sum, item) => sum + item.score, 0);
    // Penalize color pairs that don't even have 20 playables in the pool
    if (chosenCopies.length < 22) {
      totalScore -= (22 - chosenCopies.length) * 45;
    }

    const curve: Record<string, number> = { '1': 0, '2': 0, '3': 0, '4': 0, '5': 0, '6+': 0 };
    let totalCmc = 0;
    let creatureCount = 0;
    let removalCount = 0;
    let bombCount = 0;

    for (const item of chosenCopies) {
      const c = item.card;
      totalCmc += c.cmc;
      if (c.category === 'creatures') creatureCount++;
      if (c.roles.includes('Removal')) removalCount++;
      if (c.roles.includes('Bomb')) bombCount++;

      const bucket = c.cmc <= 1 ? '1' : c.cmc === 2 ? '2' : c.cmc === 3 ? '3' : c.cmc === 4 ? '4' : c.cmc === 5 ? '5' : '6+';
      curve[bucket] = (curve[bucket] || 0) + 1;
    }

    // Build key cards list (unique top 6 cards)
    const seenKey = new Set<string>();
    const keyCards: { name: string; reason: string; tags: string[] }[] = [];
    for (const item of chosenCopies) {
      if (seenKey.has(item.card.name)) continue;
      seenKey.add(item.card.name);
      const allTags = [...item.card.roles, ...item.card.synergyTags];
      keyCards.push({
        name: item.card.name,
        reason: item.card.roles.includes('Bomb')
          ? 'High-impact Bomb threat'
          : item.card.roles.includes('Removal')
          ? 'Key interaction / removal spell'
          : item.card.synergyTags.length > 0
          ? `Core ${item.card.synergyTags.slice(0, 2).join(' & ')} synergy piece`
          : 'Solid curve playable',
        tags: allTags.slice(0, 4),
      });
      if (keyCards.length >= 6) break;
    }

    // Remaining pool / sideboard
    const usedCountsByName = new Map<string, number>();
    for (const item of chosenCopies) {
      usedCountsByName.set(item.card.name, (usedCountsByName.get(item.card.name) || 0) + 1);
    }

    const sideboard = taggedPool
      .map((c) => {
        const used = usedCountsByName.get(c.name) || 0;
        const rem = c.quantity - used;
        return {
          name: c.name,
          quantity: rem,
          colors: c.colors,
          typeLine: c.typeLine,
          tags: [...c.roles, ...c.synergyTags].slice(0, 3),
        };
      })
      .filter((s) => s.quantity > 0);

    const avgCmc = chosenCopies.length > 0 ? Number((totalCmc / chosenCopies.length).toFixed(2)) : 0;
    const synergyDesc =
      topSynergies.length > 0
        ? topSynergies.map((s) => `${s.tag} (${s.count})`).join(', ')
        : 'balanced curve & interaction';

    guildEvaluations.push({
      rank: 0,
      guildName: guild.name,
      colors: guild.colors,
      archetypeTitle: `${guild.name} — ${primaryTheme}`,
      primarySynergies: topSynergies,
      totalScore: Math.round(totalScore),
      summary: `Recommended 40-card ${guild.name} build centered around ${synergyDesc}, featuring ${creatureCount} creatures, ${removalCount} removal/interaction pieces, and ${bombCount} bomb threat(s) with an average mana value of ${avgCmc}.`,
      stats: {
        creatures: creatureCount,
        nonCreatures: chosenCopies.length - creatureCount,
        lands: landsList.length,
        removalCount,
        bombCount,
        avgCmc,
        curve,
      },
      decklist: {
        creatures: chosenCopies.filter((x) => x.card.category === 'creatures').map((x) => x.card.name),
        instants: chosenCopies.filter((x) => x.card.category === 'instants').map((x) => x.card.name),
        sorceries: chosenCopies.filter((x) => x.card.category === 'sorceries').map((x) => x.card.name),
        artifacts: chosenCopies.filter((x) => x.card.category === 'artifacts').map((x) => x.card.name),
        enchantments: chosenCopies.filter((x) => x.card.category === 'enchantments').map((x) => x.card.name),
        planeswalkers: chosenCopies.filter((x) => x.card.category === 'planeswalkers').map((x) => x.card.name),
        lands: landsList,
      },
      keyCards,
      sideboard,
    });
  }

  guildEvaluations.sort((a, b) => b.totalScore - a.totalScore);
  const topRecommendations = guildEvaluations.slice(0, 3).map((rec, idx) => ({
    ...rec,
    rank: idx + 1,
  }));

  return {
    poolSize: totalPoolCards,
    uniqueCardsResolved: taggedPool.length,
    unresolvedNames,
    poolTagSummary,
    recommendations: topRecommendations,
    buildTimeMs: Date.now() - startTime,
  };
}
