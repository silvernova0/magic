import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function main() {
    const cards = await prisma.card.findMany({
        take: 5,
        where: {
            prices: {
                not: null
            }
        },
        select: {
            name: true,
            prices: true
        }
    });

    console.log('Checking price data for 5 cards:');
    for (const card of cards) {
        console.log(`Card: ${card.name}`);
        console.log(`Prices Raw: ${card.prices}`);
        try {
            if (card.prices) {
                const parsed = JSON.parse(card.prices);
                console.log('Parsed:', parsed);
                console.log('USD:', parsed.usd);
            }
        } catch (e) {
            console.error('Failed to parse JSON');
        }
        console.log('---');
    }
}

main()
    .catch(e => console.error(e))
    .finally(async () => await prisma.$disconnect());
