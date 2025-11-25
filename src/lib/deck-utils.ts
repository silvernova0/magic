import { Deck } from "@prisma/client";

/**
 * Calculate the total number of cards in a deck, including commander(s).
 * Handles both string and array formats for commander.
 */
export function getDeckCardCount(deck: Deck): number {
    if (!deck || !deck.decklist) return 0;

    const decklist = deck.decklist as any;
    let count = 0;

    // Count commander(s)
    if (decklist.commander) {
        if (Array.isArray(decklist.commander)) {
            count += decklist.commander.length;
        } else if (typeof decklist.commander === 'string') {
            count += 1;
        }
    }

    // Count cards in categories
    const categories = [
        'creatures',
        'instants',
        'sorceries',
        'artifacts',
        'enchantments',
        'planeswalkers',
        'lands'
    ];

    for (const category of categories) {
        if (decklist[category] && Array.isArray(decklist[category])) {
            count += decklist[category].length;
        }
    }

    return count;
}

/**
 * Calculate the average CMC of the deck.
 * Ignores lands and cards without CMC data.
 */
export function calculateAverageCmc(decklist: any): string {
    if (!decklist) return "0.00";

    let totalCmc = 0;
    let cardCount = 0;

    const processCard = (card: any) => {
        // Skip if card is just a string (name only) or has no CMC
        if (typeof card === 'string' || typeof card.cmc !== 'number') return;

        // Skip lands (usually CMC 0, but we check type if available)
        if (card.type_line && card.type_line.toLowerCase().includes('land')) return;

        totalCmc += card.cmc;
        cardCount++;
    };

    // Iterate through all categories
    const categories = [
        'commander', 'creatures', 'instants', 'sorceries',
        'artifacts', 'enchantments', 'planeswalkers'
    ];

    for (const category of categories) {
        const items = decklist[category];
        if (items) {
            if (Array.isArray(items)) {
                items.forEach(processCard);
            } else if (category === 'commander') {
                processCard(items);
            }
        }
    }

    return cardCount > 0 ? (totalCmc / cardCount).toFixed(2) : "0.00";
}

/**
 * Calculate the mana curve (distribution of cards by CMC).
 * Returns an array of size 9 (0 to 8+).
 */
export function calculateManaCurve(decklist: any): number[] {
    const curve = new Array(9).fill(0);
    if (!decklist) return curve;

    const processCard = (card: any) => {
        if (typeof card === 'string' || typeof card.cmc !== 'number') return;

        // Include everything in curve, or exclude lands? Usually exclude lands.
        if (card.type_line && card.type_line.toLowerCase().includes('land')) return;

        const cmc = Math.floor(card.cmc);
        if (cmc >= 8) {
            curve[8]++;
        } else if (cmc >= 0) {
            curve[cmc]++;
        }
    };

    const categories = [
        'commander', 'creatures', 'instants', 'sorceries',
        'artifacts', 'enchantments', 'planeswalkers'
    ];

    for (const category of categories) {
        const items = decklist[category];
        if (items) {
            if (Array.isArray(items)) {
                items.forEach(processCard);
            } else if (category === 'commander') {
                processCard(items);
            }
        }
    }

    return curve;
}

/**
 * Calculate the distribution of card types.
 */
export function calculateTypeDistribution(decklist: any): Record<string, number> {
    const distribution: Record<string, number> = {
        Creatures: 0,
        Instants: 0,
        Sorceries: 0,
        Artifacts: 0,
        Enchantments: 0,
        Planeswalkers: 0,
        Lands: 0
    };

    if (!decklist) return distribution;

    // Helper to map category names to display names
    const categoryMap: Record<string, string> = {
        'creatures': 'Creatures',
        'instants': 'Instants',
        'sorceries': 'Sorceries',
        'artifacts': 'Artifacts',
        'enchantments': 'Enchantments',
        'planeswalkers': 'Planeswalkers',
        'lands': 'Lands'
    };

    for (const [key, label] of Object.entries(categoryMap)) {
        if (decklist[key] && Array.isArray(decklist[key])) {
            distribution[label] = decklist[key].length;
        }
    }

    // Handle commander(s) - usually creatures or planeswalkers
    if (decklist.commander) {
        const commanders = Array.isArray(decklist.commander) ? decklist.commander : [decklist.commander];
        commanders.forEach((cmd: any) => {
            // If we have type info, use it, otherwise assume Creature
            if (typeof cmd !== 'string' && cmd.type_line) {
                if (cmd.type_line.includes('Planeswalker')) distribution['Planeswalkers']++;
                else distribution['Creatures']++;
            } else {
                distribution['Creatures']++;
            }
        });
    }

    return distribution;
}

/**
 * Calculate color statistics based on mana costs.
 */
export function calculateColorStats(decklist: any): Record<string, number> {
    const stats: Record<string, number> = {
        W: 0, U: 0, B: 0, R: 0, G: 0, C: 0
    };

    if (!decklist) return stats;

    const processCard = (card: any) => {
        if (typeof card === 'string' || !card.mana_cost) return;

        const manaCost = card.mana_cost;
        // Simple regex counting for pips
        stats.W += (manaCost.match(/{W}/g) || []).length;
        stats.U += (manaCost.match(/{U}/g) || []).length;
        stats.B += (manaCost.match(/{B}/g) || []).length;
        stats.R += (manaCost.match(/{R}/g) || []).length;
        stats.G += (manaCost.match(/{G}/g) || []).length;
        stats.C += (manaCost.match(/{C}/g) || []).length;
    };

    const categories = [
        'commander', 'creatures', 'instants', 'sorceries',
        'artifacts', 'enchantments', 'planeswalkers'
    ];

    for (const category of categories) {
        const items = decklist[category];
        if (items) {
            if (Array.isArray(items)) {
                items.forEach(processCard);
            } else if (category === 'commander') {
                processCard(items);
            }
        }
    }

    return stats;
}
