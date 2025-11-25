
import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function verifyAvatarCards() {
    console.log("🔍 Verifying Avatar cards in database...");

    // Search for cards from TLA or TLE sets
    const cards = await prisma.card.findMany({
        where: {
            OR: [
                { setCode: 'tla' },
                { setCode: 'tle' }
            ]
        },
        take: 10
    });

    if (cards.length === 0) {
        console.log("❌ No Avatar cards found in database yet.");
    } else {
        console.log(`✅ Found ${cards.length} Avatar cards (showing first 5):`);
        cards.slice(0, 5).forEach(c => {
            console.log(`- ${c.name} (${c.setCode.toUpperCase()})`);
        });
    }

    const count = await prisma.card.count({
        where: {
            OR: [
                { setCode: 'tla' },
                { setCode: 'tle' }
            ]
        }
    });
    console.log(`\nTotal Avatar cards in DB: ${count}`);
}

verifyAvatarCards()
    .catch(console.error)
    .finally(async () => await prisma.$disconnect());
