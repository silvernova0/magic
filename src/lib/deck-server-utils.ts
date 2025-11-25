import { prisma } from '@/lib/prisma';

export async function hydrateDecklist(decklist: any) {
    if (!decklist) return decklist;

    const cardNames = new Set<string>();
    const categories = ['commander', 'creatures', 'instants', 'sorceries', 'artifacts', 'enchantments', 'planeswalkers', 'lands'];

    // Collect all card names
    for (const category of categories) {
        const items = decklist[category];
        if (items) {
            if (Array.isArray(items)) {
                items.forEach((item: any) => {
                    const name = typeof item === 'string' ? item : item.name;
                    if (name) cardNames.add(name);
                });
            } else if (category === 'commander') {
                const name = typeof items === 'string' ? items : items.name;
                if (name) cardNames.add(name);
            }
        }
    }

    // Fetch cards from DB
    const cards = await prisma.card.findMany({
        where: {
            name: { in: Array.from(cardNames) }
        },
        select: {
            name: true,
            manaCost: true,
            cmc: true,
            typeLine: true,
            colors: true,
            imageUris: true,
            prices: true,
            rarity: true,
            setName: true,
            collectorNumber: true
        }
    });

    const cardMap = new Map(cards.map(c => [c.name, c]));

    // Hydrate decklist
    const hydratedDecklist = { ...decklist };

    for (const category of categories) {
        const items = decklist[category];
        if (items) {
            if (Array.isArray(items)) {
                hydratedDecklist[category] = items.map((item: any) => {
                    const name = typeof item === 'string' ? item : item.name;
                    const cardData = cardMap.get(name);
                    if (cardData) {
                        return {
                            ...cardData,
                            // Parse JSON fields if necessary
                            image_uris: safeJsonParse(cardData.imageUris),
                            prices: safeJsonParse(cardData.prices),
                            colors: safeJsonParse(cardData.colors),
                            // Keep original quantity if it existed
                            quantity: typeof item === 'object' && item.quantity ? item.quantity : 1
                        };
                    }
                    // If card not found in DB, return original item (string or object)
                    return item;
                });
            } else if (category === 'commander') {
                const name = typeof items === 'string' ? items : items.name;
                const cardData = cardMap.get(name);
                if (cardData) {
                    hydratedDecklist[category] = {
                        ...cardData,
                        image_uris: safeJsonParse(cardData.imageUris),
                        prices: safeJsonParse(cardData.prices),
                        colors: safeJsonParse(cardData.colors),
                    };
                }
            }
        }
    }

    return hydratedDecklist;
}

function safeJsonParse(value: any) {
    if (!value) return undefined;
    if (typeof value === 'object') return value; // Already parsed
    try {
        return JSON.parse(value);
    } catch (e) {
        console.warn('Failed to parse JSON:', value);
        return undefined;
    }
}

export function calculateDeckPrice(decklist: any) {
    let total = 0;
    let missing = 0;
    const currency = 'USD';

    if (!decklist) return { total, currency, missing };

    const categories = ['commander', 'creatures', 'instants', 'sorceries', 'artifacts', 'enchantments', 'planeswalkers', 'lands'];

    const processCard = (card: any) => {
        if (!card || typeof card === 'string') {
            missing++;
            return;
        }

        // Check if prices exist (hydrated)
        if (card.prices && card.prices.usd) {
            const price = parseFloat(card.prices.usd);
            if (!isNaN(price)) {
                total += price * (card.quantity || 1);
            } else {
                missing++;
            }
        } else {
            missing++;
        }
    };

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

    return { total, currency, missing };
}
