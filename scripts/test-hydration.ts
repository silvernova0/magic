
import { hydrateDecklist } from '@/lib/deck-utils';
import { prisma } from '@/lib/prisma';

async function testHydration() {
    console.log("🧪 Testing Decklist Hydration...");

    // 1. Get a real deck from DB
    const deck = await prisma.deck.findFirst({
        where: { status: 'GENERATED' },
        orderBy: { createdAt: 'desc' }
    });

    if (!deck) {
        console.log("❌ No generated decks found.");
        return;
    }

    console.log(`\nOriginal Deck: ${deck.name}`);
    const originalList = deck.decklist as any;

    // Check original state (should be strings)
    if (originalList.creatures && originalList.creatures.length > 0) {
        console.log(`Original Creature 1: ${JSON.stringify(originalList.creatures[0])}`);
    }

    // 2. Hydrate
    console.log("\n💧 Hydrating...");
    const hydratedList = await hydrateDecklist(originalList);

    // 3. Check hydrated state (should be objects with cmc)
    if (hydratedList.creatures && hydratedList.creatures.length > 0) {
        const c1 = hydratedList.creatures[0];
        console.log(`Hydrated Creature 1: ${JSON.stringify(c1, null, 2)}`);

        if (typeof c1 === 'object' && typeof c1.cmc === 'number') {
            console.log("✅ Hydration SUCCESS: CMC found.");
        } else {
            console.log("❌ Hydration FAILED: CMC missing.");
        }
    }
}

testHydration()
    .catch(console.error)
    .finally(async () => await prisma.$disconnect());
