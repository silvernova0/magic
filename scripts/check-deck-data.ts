
import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function checkDeckData() {
    console.log("🔍 Checking deck data for CMC and Mana Cost...");

    const deck = await prisma.deck.findFirst({
        where: {
            status: 'GENERATED'
        },
        orderBy: {
            createdAt: 'desc'
        }
    });

    if (!deck) {
        console.log("❌ No generated decks found.");
        return;
    }

    console.log(`\nChecking deck: ${deck.name} (${deck.id})`);
    const decklist = deck.decklist as any;

    if (!decklist) {
        console.log("❌ Decklist is null/empty.");
        return;
    }

    // Check Commander
    if (decklist.commander) {
        const cmd = Array.isArray(decklist.commander) ? decklist.commander[0] : decklist.commander;
        console.log(`\nCommander: ${cmd.name || cmd}`);
        if (typeof cmd === 'object') {
            console.log(`  - CMC: ${cmd.cmc} (${typeof cmd.cmc})`);
            console.log(`  - Mana Cost: ${cmd.manaCost}`);
        } else {
            console.log("  ❌ Commander is a string, missing detailed data.");
        }
    }

    // Check a few creatures
    if (decklist.creatures && decklist.creatures.length > 0) {
        console.log("\nChecking first 3 creatures:");
        decklist.creatures.slice(0, 3).forEach((card: any, i: number) => {
            console.log(`  ${i + 1}. ${card.name || card}`);
            if (typeof card === 'object') {
                console.log(`     - CMC: ${card.cmc}`);
                console.log(`     - Mana Cost: ${card.manaCost}`);
            } else {
                console.log("     ❌ Card is a string, missing detailed data.");
            }
        });
    }
}

checkDeckData()
    .catch(e => console.error(e))
    .finally(async () => await prisma.$disconnect());
