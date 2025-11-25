import { PrismaClient } from '@prisma/client';
import { getDeckCardCount } from '../src/lib/deck-utils';

const prisma = new PrismaClient();

async function main() {
    // 1. Get or Create User
    let user = await prisma.user.findFirst();
    if (!user) {
        user = await prisma.user.create({
            data: {
                id: "test_user_" + Date.now(),
                name: "Test User",
                email: "test@example.com"
            }
        });
        console.log(`Created test user: ${user.id}`);
    } else {
        console.log(`Using existing user: ${user.id}`);
    }

    const decklist = {
        commander: "Atraxa, Praetors' Voice",
        creatures: Array(20).fill("Llanowar Elves"),
        instants: Array(20).fill("Lightning Bolt"),
        sorceries: Array(20).fill("Divination"),
        artifacts: Array(10).fill("Sol Ring"),
        enchantments: Array(10).fill("Rancor"),
        planeswalkers: Array(5).fill("Jace Beleren"),
        lands: Array(14).fill("Forest")
    };

    // Total: 1 (Cmdr) + 20 + 20 + 20 + 10 + 10 + 5 + 14 = 100

    const deck = await prisma.deck.create({
        data: {
            name: "Test Card Count Deck",
            description: "A deck to verify card counting logic",
            theme: "Test",
            powerLevel: "7",
            status: "GENERATED",
            userId: user.id,
            decklist: decklist
        }
    });

    console.log(`Created deck with ID: ${deck.id}`);

    // Verify count
    const count = getDeckCardCount(deck);
    console.log(`Card Count: ${count}`);

    if (count === 100) {
        console.log("✅ VERIFICATION PASSED: Count is 100");
    } else {
        console.error(`❌ VERIFICATION FAILED: Count is ${count}, expected 100`);
        process.exit(1);
    }
}

main()
    .catch(e => {
        console.error(e);
        process.exit(1);
    })
    .finally(async () => {
        await prisma.$disconnect();
    });
