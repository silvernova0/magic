import { prisma } from './prisma';
import { removeBannedCards, isCardBanned } from './bannedCards';
import { scrapeCommanderDetails } from './scrapers/edhrec';
import type { DeckBuildRequest, DeckBuildResponse } from './gemini';

const OLLAMA_BASE_URL = process.env.OLLAMA_BASE_URL || 'http://host.docker.internal:11434';
const OLLAMA_MODEL = process.env.OLLAMA_MODEL || 'jankbuild-commander';

const BASIC_LAND_BY_COLOR: Record<string, string> = {
  W: 'Plains',
  U: 'Island',
  B: 'Swamp',
  R: 'Mountain',
  G: 'Forest',
};

const BASIC_LANDS = new Set(['Plains', 'Island', 'Swamp', 'Mountain', 'Forest', 'Wastes']);

const THEME_KEYWORDS: Record<string, string[]> = {
  aggro: ['haste', 'attack', 'combat damage', 'double strike', 'trample', 'menace', 'first strike', ' +1/+1 '],
  tempo: ['flash', 'flying', 'return target', 'counter target', 'draw a card', 'ward', 'unblockable'],
  control: ['counter target', 'destroy all', 'exile target', 'draw', 'each opponent', 'tap target', 'board'],
  stax: ['can\'t', 'doesn\'t untap', 'costs {', 'more to cast', 'each player sacrifices', 'opponents control enter tapped'],
  hatebears: ['can\'t', 'costs {', 'more to cast', 'opponents can\'t', 'spells cost', 'enter the battlefield tapped', 'enters tapped', 'noncreature spells', 'each player can\'t', 'abilities can\'t be activated', 'players can\'t', 'tax'],
  'hate bears': ['can\'t', 'costs {', 'more to cast', 'opponents can\'t', 'spells cost', 'enter the battlefield tapped', 'enters tapped', 'noncreature spells', 'each player can\'t', 'abilities can\'t be activated', 'players can\'t', 'tax'],
  '+1/+1 counters': ['+1/+1 counter', 'put a +1/+1', 'proliferate', 'support', 'modular', 'evolve', 'outlast', 'adapt', 'mentor', 'backup', 'modified'],
  counters: ['+1/+1 counter', 'counter on', 'proliferate', 'counters', 'modified'],
  combo: ['search your library', 'untap target', 'whenever you cast', 'infinite', 'copy target', 'graveyard to your hand', 'add {'],
  midrange: ['draw a card', 'enters', 'destroy target', 'search your library for a', 'graveyard', '+1/+1 counter'],
  voltron: ['equip', 'enchant creature', 'equipped creature', 'enchanted creature', 'hexproof', 'indestructible', 'double strike', 'aura', 'commander damage'],
  equipment: ['equip', 'equipped creature', 'equipment card', 'attach', 'whenever equipped creature deals combat damage'],
  tokens: ['create', 'token', 'populate', 'creatures you control get', 'whenever a creature enters', 'go wide', 'convoke'],
  aristocrats: ['sacrifice a creature', 'whenever a creature you control dies', 'whenever another creature dies', 'loses 1 life', 'you gain 1 life', 'blood', 'treasure'],
  reanimator: ['return target creature card from your graveyard', 'mill', 'discard', 'graveyard to the battlefield', 'entomb', 'reanimate'],
  'graveyard matters': ['graveyard', 'mill', 'cards in your graveyard', 'from your graveyard', 'flashback', 'underworld breach', 'delve', 'threshold', 'dredge'],
  graveyard: ['graveyard', 'mill', 'cards in your graveyard', 'from your graveyard', 'flashback', 'underworld breach', 'delve', 'threshold', 'dredge'],
  'blink / flicker': ['exile target', 'return it to the battlefield', 'return that card to the battlefield', 'enters the battlefield', 'exile another', 'flicker', 'blink'],
  blink: ['exile target', 'return it to the battlefield', 'return that card to the battlefield', 'enters the battlefield', 'exile another', 'flicker', 'blink'],
  flicker: ['exile target', 'return it to the battlefield', 'return that card to the battlefield', 'enters the battlefield', 'exile another', 'flicker', 'blink'],
  spellslinger: ['instant or sorcery', 'whenever you cast an instant', 'magecraft', 'prowess', 'copy target instant', 'storm'],
  artifacts: ['artifact', 'metalcraft', 'affinity for artifacts', 'treasure', 'clue', 'food', 'myr', 'thopter'],
  enchantments: ['enchantment', 'constellation', 'aura', 'shrine', 'saga', 'enchantress'],
  'enchantments / enchantress': ['enchantment', 'constellation', 'aura', 'shrine', 'saga', 'enchantress', 'whenever you cast an enchantment'],
  enchantress: ['enchantment', 'constellation', 'aura', 'shrine', 'saga', 'enchantress', 'whenever you cast an enchantment'],
  lands: ['landfall', 'whenever a land enters', 'play an additional land', 'search your library for a', 'land card'],
  'lands matter': ['landfall', 'whenever a land enters', 'play an additional land', 'search your library for a', 'land card'],
  'lands matter / landfall': ['landfall', 'whenever a land enters', 'play an additional land', 'search your library for a', 'land card'],
  landfall: ['landfall', 'whenever a land enters', 'play an additional land', 'search your library for a', 'land card'],
  lifegain: ['gain life', 'you gain', 'whenever you gain life', 'lifelink', 'life total', 'for each 1 life you gained'],
  mill: ['mill', 'put the top', 'cards of their library into their graveyard', 'library into their graveyard', 'whenever a card is put into an opponent\'s graveyard'],
  wheels: ['discard your hand and draw', 'each player discards', 'each player draws', 'whenever an opponent draws', 'wheel', 'windfall', 'draws a card, except the first'],
  chaos: ['coin', 'flip', 'random', 'chaos', 'whenever a player casts a spell', 'shuffle', 'roll a d20'],
  'group hug': ['each player draws', 'each player may', 'each opponent draws', 'all players', 'whenever a player', 'tempting offer'],
  'group slug': ['each player loses', 'whenever a player taps a land', 'deals damage to each', 'whenever an opponent casts', 'punish', 'pain'],
  superfriends: ['planeswalker', 'loyalty counter', 'proliferate', 'planeswalkers you control', 'activate an additional loyalty ability'],
  'infect / toxic': ['infect', 'toxic', 'poison counter', 'proliferate', 'corrupted', 'wither'],
  infect: ['infect', 'toxic', 'poison counter', 'proliferate', 'corrupted', 'wither'],
  'theft / clones': ['gain control of target', 'you control', 'as a copy', 'you may cast', 'from an opponent\'s graveyard', 'exile cards from the top of each opponent\'s library'],
  theft: ['gain control of target', 'you control', 'as a copy', 'you may cast', 'from an opponent\'s graveyard', 'exile cards from the top of each opponent\'s library'],
  'treasure / big mana': ['create a treasure token', 'treasure tokens', 'add {', 'untap all lands', 'mana doesn\'t empty', 'mana pool'],
  treasure: ['create a treasure token', 'treasure tokens', 'add {', 'untap all lands', 'mana doesn\'t empty', 'mana pool'],
};

const SYNERGY_MECHANICS = [
  'proliferate',
  '+1/+1 counter',
  '-1/-1 counter',
  'experience counter',
  'energy',
  'treasure',
  'clue',
  'food',
  'blood',
  'sacrifice',
  'dies',
  'graveyard',
  'exile',
  'equipment',
  'aura',
  'enchantment',
  'artifact',
  'token',
  'land',
  'draw',
  'discard',
  'mill',
  'lifelink',
  'gain life',
  'lose life',
  'flying',
  'attack',
  'combat damage',
  'instant or sorcery',
  'legendary',
  'dragon',
  'elf',
  'goblin',
  'zombie',
  'vampire',
  'angel',
  'demon',
  'wizard',
  'sliver',
  'dinosaur',
  'merfolk',
  'human',
  'knight',
  'soldier',
  'spirit',
  'faerie',
  'elemental',
  'eldrazi',
];

function parseColorIdentity(ci: string | null | undefined): string[] {
  if (!ci) return [];
  const trimmed = ci.trim();
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

function isColorSubset(cardColors: string[], allowedColors: Set<string>): boolean {
  for (const c of cardColors) {
    if (!allowedColors.has(c)) return false;
  }
  return true;
}

function isCommanderLegal(legalitiesJson: string | null | undefined): boolean {
  if (!legalitiesJson) return true;
  if (legalitiesJson.includes('"commander":"Banned"') || legalitiesJson.includes('"commander": "Banned"')) {
    return false;
  }
  return true;
}

function extractMechanicsFromText(oracleText: string, typeLine: string): string[] {
  const combined = `${oracleText} ${typeLine}`.toLowerCase();
  return SYNERGY_MECHANICS.filter((kw) => combined.includes(kw));
}

function categorizeCard(typeLine: string): keyof Pick<
  DeckBuildResponse,
  'creatures' | 'planeswalkers' | 'instants' | 'sorceries' | 'artifacts' | 'enchantments' | 'lands'
> {
  const mainType = typeLine.split('//')[0].toLowerCase();
  if (mainType.includes('land')) return 'lands';
  if (mainType.includes('creature')) return 'creatures';
  if (mainType.includes('planeswalker')) return 'planeswalkers';
  if (mainType.includes('instant')) return 'instants';
  if (mainType.includes('sorcery')) return 'sorceries';
  if (mainType.includes('artifact')) return 'artifacts';
  if (mainType.includes('enchantment')) return 'enchantments';
  return 'artifacts';
}

export async function isOllamaAvailable(): Promise<boolean> {
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 3000);
    const response = await fetch(`${OLLAMA_BASE_URL}/api/tags`, {
      method: 'GET',
      signal: controller.signal,
    });
    clearTimeout(timeout);
    return response.ok;
  } catch {
    return false;
  }
}

/**
 * Suggest 5 Commanders using Local AI + Local 31k Card Database
 */
export async function suggestCommandersLocal(
  colors: string[],
  theme: string,
  powerLevel: string
): Promise<string[]> {
  const requestedColors = colors.map((c) => c.toUpperCase()).filter((c) => ['W', 'U', 'B', 'R', 'G'].includes(c));
  const sortedColorKey = [...requestedColors].sort().join(',');

  // Fetch commanders from local database
  const allCommanders = await prisma.card.findMany({
    where: {
      isCommander: true,
      ...(sortedColorKey ? { colorIdentity: sortedColorKey } : {}),
    },
    orderBy: [{ edhrecRank: 'asc' }],
    take: 150,
    select: {
      name: true,
      colorIdentity: true,
      typeLine: true,
      oracleText: true,
      edhrecRank: true,
      legalities: true,
    },
  });

  // If exact color match returned few commanders, broaden to commanders containing those colors
  let candidates = allCommanders.filter((c) => isCommanderLegal(c.legalities) && !isCardBanned(c.name));
  if (candidates.length < 5) {
    const broad = await prisma.card.findMany({
      where: { isCommander: true },
      orderBy: [{ edhrecRank: 'asc' }],
      take: 300,
      select: {
        name: true,
        colorIdentity: true,
        typeLine: true,
        oracleText: true,
        edhrecRank: true,
        legalities: true,
      },
    });
    candidates = broad.filter((c) => {
      if (!isCommanderLegal(c.legalities) || isCardBanned(c.name)) return false;
      if (requestedColors.length === 0) return true;
      const ci = parseColorIdentity(c.colorIdentity);
      return requestedColors.every((rc) => ci.includes(rc));
    });
  }

  // Deduplicate by clean card name, exclude Arena-only "A-" cards
  const seenCommanderNames = new Set<string>();
  const uniqueCandidates: typeof candidates = [];
  for (const c of candidates) {
    const cleanName = c.name.split('//')[0].trim();
    if (cleanName.startsWith('A-')) continue;
    if (!seenCommanderNames.has(cleanName)) {
      seenCommanderNames.add(cleanName);
      uniqueCandidates.push({ ...c, name: cleanName });
    }
  }

  // Score candidates by theme relevance + EDHREC rank
  const themeLower = theme.toLowerCase();
  const kindredMatch = themeLower.startsWith('kindred - ')
    ? themeLower.replace('kindred - ', '').trim().replace(/s$/, '')
    : '';
  const themeWords = THEME_KEYWORDS[themeLower] || [themeLower];

  const scored = uniqueCandidates.map((c, idx) => {
    const text = `${c.typeLine} ${c.oracleText || ''}`.toLowerCase();
    let score = Math.max(0, 150 - idx);
    if (kindredMatch && text.includes(kindredMatch)) score += 200;
    for (const kw of themeWords) {
      if (text.includes(kw)) score += 45;
    }
    return { ...c, score };
  });

  scored.sort((a, b) => b.score - a.score);
  const topPool = scored.slice(0, 20);

  // Ask Local Ollama to pick the best 5 from the top pool if available
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 15000);
    const candidateList = topPool
      .map((c) => `- ${c.name} (${c.typeLine}): ${(c.oracleText || '').replace(/\n/g, ' ').slice(0, 120)}`)
      .join('\n');

    const res = await fetch(`${OLLAMA_BASE_URL}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      signal: controller.signal,
      body: JSON.stringify({
        model: OLLAMA_MODEL,
        stream: false,
        format: 'json',
        options: { temperature: 0.4, num_predict: 256 },
        messages: [
          {
            role: 'system',
            content:
              'You are an expert MTG Commander deck builder. Pick the 5 best commanders from the candidate list for the requested theme and power level. Return JSON: {"suggestions": ["Name 1", "Name 2", "Name 3", "Name 4", "Name 5"]}',
          },
          {
            role: 'user',
            content: `Theme: ${theme}\nColors: ${requestedColors.join('/') || 'Any'}\nPower Bracket: ${powerLevel}/5\n\nCandidates:\n${candidateList}`,
          },
        ],
      }),
    });
    clearTimeout(timeout);

    if (res.ok) {
      const data = await res.json();
      const parsed = JSON.parse(data.message?.content || '{}');
      if (Array.isArray(parsed.suggestions) && parsed.suggestions.length > 0) {
        const validNames = new Set(topPool.map((c) => c.name));
        const uniqueSet = new Set<string>();
        for (const n of parsed.suggestions) {
          if (typeof n === 'string' && validNames.has(n)) {
            uniqueSet.add(n);
          }
        }
        for (const c of topPool) {
          if (uniqueSet.size >= 5) break;
          uniqueSet.add(c.name);
        }
        if (uniqueSet.size >= 3) {
          return Array.from(uniqueSet).slice(0, 5);
        }
      }
    }
  } catch (err) {
    console.warn('Local Ollama suggestion fallback to database ranking:', err);
  }

  return Array.from(new Set(topPool.map((c) => c.name))).slice(0, 5);
}

/**
 * Build a complete, 100-card legal Commander deck using Local AI + 31,483-Card SQLite Database
 */
export async function buildCommanderDeckWithOllama(
  request: DeckBuildRequest
): Promise<DeckBuildResponse> {
  const {
    commander: requestedCommander,
    theme,
    colors,
    powerLevel,
    useCollectionOnly,
    userCollection,
  } = request;

  const powerBracket = parseInt(String(powerLevel), 10) || 3;

  // 1. Resolve Commander from local Card database
  let commanderCard = null;
  if (requestedCommander && requestedCommander.trim()) {
    commanderCard = await prisma.card.findFirst({
      where: {
        name: { equals: requestedCommander.trim() },
      },
    });
    if (!commanderCard) {
      commanderCard = await prisma.card.findFirst({
        where: {
          name: { contains: requestedCommander.trim() },
          isCommander: true,
        },
        orderBy: { edhrecRank: 'asc' },
      });
    }
  }

  if (!commanderCard) {
    const suggestions = await suggestCommandersLocal(colors || [], theme, String(powerLevel));
    const chosenName = suggestions[0] || "Atraxa, Praetors' Voice";
    commanderCard = await prisma.card.findFirst({
      where: { name: chosenName },
    });
  }

  if (!commanderCard) {
    commanderCard = await prisma.card.findFirst({
      where: { isCommander: true },
      orderBy: { edhrecRank: 'asc' },
    });
  }

  const commanderName = commanderCard!.name;
  const commanderColors = parseColorIdentity(commanderCard!.colorIdentity);
  const allowedColors = new Set(commanderColors);
  const commanderMechanics = extractMechanicsFromText(
    commanderCard!.oracleText || '',
    commanderCard!.typeLine || ''
  );

  console.log(
    `[Local AI Builder] Commander: ${commanderName} | Colors: [${commanderColors.join(',')}] | Mechanics: [${commanderMechanics.join(', ')}]`
  );

  // 2. Fetch EDHREC Synergies for this Commander from CardSynergy table
  let synergyRows = await prisma.cardSynergy.findMany({
    where: {
      OR: [
        { commander: { contains: commanderName.split(',')[0] } },
        { cardId: commanderCard!.id },
      ],
    },
    orderBy: { score: 'desc' },
    take: 120,
  });

  // If no synergies in database yet for this commander, fetch on-demand from EDHREC API
  if (synergyRows.length === 0) {
    try {
      const frontName = commanderName.split('//')[0].trim();
      const commanderSlug = frontName
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/^-|-$/g, '');

      console.log(`[Local AI Builder] On-demand fetching EDHREC synergies for ${commanderSlug}...`);
      const details = await scrapeCommanderDetails(`https://edhrec.com/commanders/${commanderSlug}`);
      const newSynergies = details.synergies || [];

      if (newSynergies.length > 0) {
        console.log(`[Local AI Builder] Discovered ${newSynergies.length} EDHREC synergies for ${commanderName}`);
        for (const syn of newSynergies) {
          const synSlug = syn.cardName.toLowerCase().replace(/[^a-z0-9]+/g, '-');
          await prisma.cardSynergy.upsert({
            where: {
              cardId_synergyId_commander: {
                cardId: commanderCard!.id,
                synergyId: synSlug,
                commander: commanderName,
              },
            },
            create: {
              cardId: commanderCard!.id,
              synergyId: synSlug,
              score: syn.score,
              source: 'edhrec',
              commander: commanderName,
            },
            update: {
              score: syn.score,
            },
          }).catch(() => {});
        }

        synergyRows = await prisma.cardSynergy.findMany({
          where: {
            OR: [
              { commander: { contains: commanderName.split(',')[0] } },
              { cardId: commanderCard!.id },
            ],
          },
          orderBy: { score: 'desc' },
          take: 120,
        });
      }
    } catch (err) {
      console.warn('[Local AI Builder] On-demand synergy lookup failed, proceeding with heuristic scoring:', err);
    }
  }

  const synergyMap = new Map<string, number>();
  for (const row of synergyRows) {
    const normalized = row.synergyId.replace(/--/g, ' ').replace(/-/g, ' ').toLowerCase();
    synergyMap.set(normalized, Math.max(synergyMap.get(normalized) || 0, row.score));
  }

  // 3. Parse user collection if useCollectionOnly is enabled
  let allowedCollectionSet: Set<string> | null = null;
  if (useCollectionOnly && userCollection) {
    allowedCollectionSet = new Set(
      userCollection
        .split('\n')
        .map((line) => line.replace(/^\d+x?\s+/i, '').trim().toLowerCase())
        .filter(Boolean)
    );
  }

  // 4. Fetch all legal cards from SQLite and filter to Commander's color identity
  const allDbCards = await prisma.card.findMany({
    select: {
      id: true,
      name: true,
      cmc: true,
      colorIdentity: true,
      typeLine: true,
      oracleText: true,
      edhrecRank: true,
      legalities: true,
    },
    orderBy: { edhrecRank: 'asc' },
  });

  const themeLower = theme.toLowerCase();
  const kindredSubtype = themeLower.startsWith('kindred - ')
    ? themeLower.replace('kindred - ', '').trim().replace(/s$/, '')
    : '';
  const themeKeywords = THEME_KEYWORDS[themeLower] || [themeLower];

  interface ScoredCard {
    name: string;
    typeLine: string;
    oracleText: string;
    cmc: number;
    edhrecRank: number;
    category: ReturnType<typeof categorizeCard>;
    score: number;
    isRamp: boolean;
    isDraw: boolean;
    isRemoval: boolean;
  }

  const legalCandidates: ScoredCard[] = [];
  const seenNames = new Set<string>([commanderName.toLowerCase()]);

  for (const card of allDbCards) {
    const nameLower = card.name.toLowerCase();
    if (seenNames.has(nameLower)) continue;
    if (BASIC_LANDS.has(card.name)) continue;
    if (card.typeLine.includes('Conspiracy') || card.typeLine.includes('Phenomenon') || card.typeLine.includes('Plane ') || card.typeLine.includes('Vanguard') || card.typeLine.includes('Scheme') || card.typeLine.includes('Sticker') || card.typeLine.includes('Attraction')) {
      continue;
    }
    if (!isCommanderLegal(card.legalities) || isCardBanned(card.name)) continue;

    const cardCi = parseColorIdentity(card.colorIdentity);
    if (!isColorSubset(cardCi, allowedColors)) continue;

    if (allowedCollectionSet && !allowedCollectionSet.has(nameLower)) continue;

    seenNames.add(nameLower);

    const textLower = `${card.typeLine} ${card.oracleText || ''}`.toLowerCase();
    const oracleLower = (card.oracleText || '').toLowerCase();
    const category = categorizeCard(card.typeLine);
    const rank = card.edhrecRank ?? 25000;

    // Base score from EDHREC rank and target power level bracket
    let score = 0;
    if (powerBracket >= 4) {
      score += Math.max(0, 120 - rank / 40);
    } else if (powerBracket === 3) {
      score += Math.max(0, 100 - Math.abs(rank - 800) / 60);
    } else {
      score += Math.max(0, 90 - Math.abs(rank - 2500) / 80);
    }

    // Direct EDHREC synergy bonus
    const slug = nameLower.replace(/[^a-z0-9]+/g, ' ').trim();
    if (synergyMap.has(slug)) {
      score += 80 + (synergyMap.get(slug) || 0);
    }

    // Commander mechanical overlap bonus
    for (const mech of commanderMechanics) {
      if (textLower.includes(mech)) {
        score += 35;
      }
    }

    // Theme keyword bonus
    if (kindredSubtype && textLower.includes(kindredSubtype)) {
      score += 110;
    }
    for (const kw of themeKeywords) {
      if (textLower.includes(kw)) {
        score += 30;
      }
    }

    // Identify functional roles (Ramp, Card Draw, Removal)
    const isRamp =
      category !== 'lands' &&
      (oracleLower.includes('search your library for a basic land') ||
        oracleLower.includes('search your library for aforest') ||
        oracleLower.includes('search your library for up to two basic land') ||
        (oracleLower.includes('add {') && card.cmc <= 3) ||
        oracleLower.includes('add one mana of any color') ||
        oracleLower.includes('create a treasure token'));

    const isDraw =
      category !== 'lands' &&
      (oracleLower.includes('draw a card') ||
        oracleLower.includes('draw two cards') ||
        oracleLower.includes('draw cards') ||
        oracleLower.includes('draws a card'));

    const isRemoval =
      category !== 'lands' &&
      (oracleLower.includes('destroy target') ||
        oracleLower.includes('exile target') ||
        oracleLower.includes('counter target') ||
        oracleLower.includes('destroy all') ||
        (oracleLower.includes('deals ') && oracleLower.includes('damage to any target')));

    // Commander format universal staples bonus
    if (card.name === 'Sol Ring' || card.name === 'Arcane Signet' || card.name === 'Command Tower') {
      score += 200;
    }

    legalCandidates.push({
      name: card.name,
      typeLine: card.typeLine,
      oracleText: card.oracleText || '',
      cmc: card.cmc,
      edhrecRank: rank,
      category,
      score,
      isRamp,
      isDraw,
      isRemoval,
    });
  }

  legalCandidates.sort((a, b) => b.score - a.score);

  // 5. Consult Local Ollama AI for curated priority picks + deck strategy & description
  let aiPriorityCards = new Set<string>();
  let aiDescription = `A Bracket ${powerBracket} ${theme} Commander deck led by ${commanderName}, built using local EDHREC synergies and card database analysis.`;
  let aiStrategy = `Establish early mana with ramp pieces, deploy ${commanderName} to leverage its ${commanderMechanics.slice(0, 3).join(', ') || theme} synergies, and overwhelm opponents through cohesive ${theme.toLowerCase()} value engines.`;

  const topNonLandCandidates = legalCandidates
    .filter((c) => c.category !== 'lands')
    .slice(0, 90);

  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 45000);
    const candidateNames = topNonLandCandidates.slice(0, 60).map((c) => c.name).join(', ');

    console.log(`[Local AI Builder] Querying local Ollama (${OLLAMA_MODEL}) at ${OLLAMA_BASE_URL}...`);
    const response = await fetch(`${OLLAMA_BASE_URL}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      signal: controller.signal,
      body: JSON.stringify({
        model: OLLAMA_MODEL,
        stream: false,
        format: 'json',
        options: {
          temperature: 0.6,
          num_predict: 600,
        },
        messages: [
          {
            role: 'system',
            content:
              'You are JankBuild Local Commander AI, an expert Magic: The Gathering EDH deck builder. Given a Commander, its oracle text, theme, power bracket, and top synergy candidates from the local database, select 15 priority cards from the list and write a concise deck description and pilot strategy. Respond ONLY with valid JSON matching: {"priorityCards": ["Card 1", ...], "description": "2-3 sentence overview", "strategy": "3-4 sentence pilot guide"}',
          },
          {
            role: 'user',
            content: `Commander: ${commanderName} (${commanderCard!.typeLine})\nOracle Text: ${commanderCard!.oracleText || 'None'}\nColor Identity: ${commanderColors.join('/') || 'Colorless'}\nTheme: ${theme}\nPower Level: Bracket ${powerBracket}/5\n\nTop Synergy Candidates:\n${candidateNames}`,
          },
        ],
      }),
    });
    clearTimeout(timeout);

    if (response.ok) {
      const data = await response.json();
      const content = data.message?.content || '{}';
      const parsed = JSON.parse(content);
      if (Array.isArray(parsed.priorityCards)) {
        for (const name of parsed.priorityCards) {
          if (typeof name === 'string') aiPriorityCards.add(name.toLowerCase());
        }
      }
      if (typeof parsed.description === 'string' && parsed.description.trim().length > 15) {
        aiDescription = parsed.description.trim();
      }
      if (typeof parsed.strategy === 'string' && parsed.strategy.trim().length > 15) {
        aiStrategy = parsed.strategy.trim();
      }
      console.log(`[Local AI Builder] Ollama returned ${aiPriorityCards.size} priority picks and custom strategy.`);
    } else {
      console.warn(`[Local AI Builder] Ollama HTTP ${response.status}: using database synergy scoring.`);
    }
  } catch (err: any) {
    console.warn(`[Local AI Builder] Ollama call skipped/timed out (${err?.message || err}); using database synergy scoring.`);
  }

  // Boost cards selected by Local Ollama AI
  for (const c of legalCandidates) {
    if (aiPriorityCards.has(c.name.toLowerCase())) {
      c.score += 250;
    }
  }
  legalCandidates.sort((a, b) => b.score - a.score);

  // 6. Assemble balanced 62 non-land cards + 37 lands + 1 commander = 100 cards
  const chosenNonLands: ScoredCard[] = [];
  const chosenNames = new Set<string>([commanderName]);

  const addCandidate = (c: ScoredCard) => {
    if (c.category === 'lands') return false;
    if (chosenNames.has(c.name) || chosenNonLands.length >= 62) return false;
    chosenNames.add(c.name);
    chosenNonLands.push(c);
    return true;
  };

  // Ensure essential ramp (10), draw (10), and interaction/removal (8)
  for (const c of legalCandidates) {
    if (c.category !== 'lands' && c.isRamp && chosenNonLands.filter((x) => x.isRamp).length < 10) addCandidate(c);
  }
  for (const c of legalCandidates) {
    if (c.category !== 'lands' && c.isDraw && chosenNonLands.filter((x) => x.isDraw).length < 10) addCandidate(c);
  }
  for (const c of legalCandidates) {
    if (c.category !== 'lands' && c.isRemoval && chosenNonLands.filter((x) => x.isRemoval).length < 8) addCandidate(c);
  }

  // Target category quotas based on theme
  const isCreatureHeavyTheme =
    kindredSubtype ||
    ['aggro', 'tokens', 'hatebear', 'counter', 'aristocrat'].some((t) =>
      themeLower.includes(t)
    );
  const targetCreatures = isCreatureHeavyTheme ? 28 : 22;
  for (const c of legalCandidates) {
    if (c.category === 'creatures' && chosenNonLands.filter((x) => x.category === 'creatures').length < targetCreatures) {
      addCandidate(c);
    }
  }

  // Fill remaining up to 62 non-land cards with highest scoring synergy cards
  for (const c of legalCandidates) {
    if (c.category !== 'lands' && chosenNonLands.length < 62) {
      addCandidate(c);
    }
  }

  // Group non-land cards by category
  const creatures = chosenNonLands.filter((c) => c.category === 'creatures').map((c) => c.name);
  const instants = chosenNonLands.filter((c) => c.category === 'instants').map((c) => c.name);
  const sorceries = chosenNonLands.filter((c) => c.category === 'sorceries').map((c) => c.name);
  const artifacts = chosenNonLands.filter((c) => c.category === 'artifacts').map((c) => c.name);
  const enchantments = chosenNonLands.filter((c) => c.category === 'enchantments').map((c) => c.name);
  const planeswalkers = chosenNonLands.filter((c) => c.category === 'planeswalkers').map((c) => c.name);

  const nonLandTotal =
    creatures.length +
    instants.length +
    sorceries.length +
    artifacts.length +
    enchantments.length +
    planeswalkers.length;

  // 7. Assemble Lands (target: 100 - 1 commander - nonLandTotal = typically 37 lands)
  const targetLands = Math.max(0, 99 - nonLandTotal);
  const lands: string[] = [];

  // Pick top non-basic lands that match color identity
  const nonBasicLandCandidates = legalCandidates.filter((c) => {
    if (c.category !== 'lands') return false;
    // Avoid off-color taplands that have no color symbols but mention irrelevant basic land types
    const text = c.oracleText.toLowerCase();
    if (commanderColors.length === 0) return !text.includes('add {w}') && !text.includes('add {u}') && !text.includes('add {b}') && !text.includes('add {r}') && !text.includes('add {g}');
    return true;
  });

  const maxNonBasics = Math.min(commanderColors.length >= 2 ? 18 : 12, Math.max(0, targetLands - 5));
  for (const land of nonBasicLandCandidates) {
    if (lands.length >= maxNonBasics) break;
    if (!chosenNames.has(land.name)) {
      chosenNames.add(land.name);
      lands.push(land.name);
    }
  }

  // Fill remaining land slots with basic lands in the Commander's color identity
  while (lands.length < targetLands) {
    if (commanderColors.length === 0) {
      lands.push('Wastes');
    } else {
      const color = commanderColors[lands.length % commanderColors.length];
      lands.push(BASIC_LAND_BY_COLOR[color] || 'Plains');
    }
  }

  // Strict invariant: Ensure total count of commander + nonLands + lands is EXACTLY 100 cards
  const currentTotal = 1 + nonLandTotal + lands.length;
  if (currentTotal < 100) {
    const missing = 100 - currentTotal;
    for (let i = 0; i < missing; i++) {
      const color = commanderColors.length > 0 ? commanderColors[i % commanderColors.length] : 'C';
      lands.push(BASIC_LAND_BY_COLOR[color] || 'Wastes');
    }
  } else if (currentTotal > 100) {
    lands.splice(100 - 1 - nonLandTotal);
  }

  const responseDeck: DeckBuildResponse = {
    commander: [commanderName],
    creatures,
    instants,
    sorceries,
    artifacts,
    enchantments,
    planeswalkers,
    lands,
    description: `${aiDescription}\n\nStrategy: ${aiStrategy}`,
    strategy: aiStrategy,
  };

  return responseDeck;
}
