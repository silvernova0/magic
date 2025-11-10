/**
 * Commander format banned cards list
 * Source: https://magic.wizards.com/en/banned-restricted-list
 * Last updated: October 2025
 */

export const COMMANDER_BANNED_CARDS = [
  // Power 9 and related
  'Ancestral Recall',
  'Black Lotus',
  'Mox Emerald',
  'Mox Jet',
  'Mox Pearl',
  'Mox Ruby',
  'Mox Sapphire',
  'Time Walk',
  'Time Vault',
  'Timetwister',
  
  // Fast mana
  'Jeweled Lotus',
  'Mana Crypt',
  'Dockside Extortionist',
  
  // Banned tutors/power cards
  'Channel',
  'Fastbond',
  'Flash',
  'Tinker',
  'Tolarian Academy',
  
  // Broken creatures
  'Emrakul, the Aeons Torn',
  'Griselbrand',
  'Iona, Shield of Emeria',
  'Leovold, Emissary of Trest',
  'Primeval Titan',
  'Rofellos, Llanowar Emissary',
  'Sundering Titan',
  'Sylvan Primordial',
  'Golos, Tireless Pilgrim',
  'Nadu, Winged Wisdom',
  
  // Oppressive cards
  'Balance',
  'Biorhythm',
  'Erayo, Soratami Ascendant',
  'Hullbreacher',
  'Karakas',
  'Limited Resources',
  'Lutri, the Spellchaser',
  'Paradox Engine',
  'Prophet of Kruphix',
  'Recurring Nightmare',
  'Shahrazad',
  'Trade Secrets',
  'Upheaval',
  'Yawgmoth\'s Bargain',
  
  // Ante cards
  'Library of Alexandria',
  
  // Un-set / Novelty
  'Chaos Orb',
  'Falling Star',
];

/**
 * Check if a card is banned in Commander
 */
export function isCardBanned(cardName: string): boolean {
  const normalizedName = cardName.trim().toLowerCase();
  return COMMANDER_BANNED_CARDS.some(
    banned => banned.toLowerCase() === normalizedName
  );
}

/**
 * Filter out banned cards from an array
 */
export function removeBannedCards(cards: string[]): string[] {
  return cards.filter(card => !isCardBanned(card));
}

/**
 * Find banned cards in an array
 */
export function findBannedCards(cards: string[]): string[] {
  return cards.filter(card => isCardBanned(card));
}
