export type Zone = 'LIBRARY' | 'HAND' | 'BATTLEFIELD' | 'GRAVEYARD' | 'EXILE' | 'COMMAND_ZONE';

export interface PlaytestCard {
    id: string; // Original card ID (scryfall ID)
    instanceId: string; // Unique ID for this specific card instance in the game
    name: string;
    manaCost: string;
    typeLine: string;
    imageUrl: string | null;
    zone: Zone;
    isTapped: boolean;
    isFlipped: boolean; // For transforming cards (future proofing)
    counters: number; // +1/+1 counters etc.
    x?: number; // For free positioning on battlefield (optional)
    y?: number;
}

export interface GameState {
    cards: PlaytestCard[];
    life: number;
    turn: number;
    poison: number;
    commanderDamage: number;
}
