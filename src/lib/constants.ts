
export const POWER_LEVELS: string[] = ['Casual', 'Focused', 'Optimized', 'Competitive (cEDH)'];

// Moxfield Commander Brackets (1-5)
export const MOXFIELD_BRACKETS = [
  { value: '1', label: 'Bracket 1 - Precon Level', description: 'Unmodified precons, very casual' },
  { value: '2', label: 'Bracket 2 - Casual', description: 'Upgraded precons, basic synergies' },
  { value: '3', label: 'Bracket 3 - Focused', description: 'Tuned with good synergies and combos' },
  { value: '4', label: 'Bracket 4 - Optimized', description: 'Highly optimized, fast mana, tutors' },
  { value: '5', label: 'Bracket 5 - Competitive', description: 'cEDH level, turns 1-4 wins' },
];

// Deck archetypes/themes
export const DECK_THEMES = [
  'Aggro',
  'Tempo',
  'Control',
  'Stax',
  'Combo',
  'Midrange',
  'Tribal',
  'Voltron',
  'Tokens',
  'Aristocrats',
  'Reanimator',
  'Lifegain',
  'Mill',
  'Group Hug',
  'Group Slug',
  'Lands Matter',
  'Spellslinger',
  'Artifacts',
  'Enchantments',
  'Superfriends',
];

// MTG Color identities
export const MTG_COLORS = [
  { value: 'W', label: 'White', symbol: '⚪' },
  { value: 'U', label: 'Blue', symbol: '🔵' },
  { value: 'B', label: 'Black', symbol: '⚫' },
  { value: 'R', label: 'Red', symbol: '🔴' },
  { value: 'G', label: 'Green', symbol: '🟢' },
  { value: 'C', label: 'Colorless', symbol: '◇' },
];
