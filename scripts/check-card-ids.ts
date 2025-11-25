import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function main() {
    const cards = await prisma.card.findMany({
        take: 5,
        select: {
            id: true,
            name: true
        }
    });

    console.log('Checking Card IDs:');
    for (const card of cards) {
        console.log(`Name: ${card.name}, ID: ${card.id}`);
    }
}

main()
    .catch(e => console.error(e))
    .finally(async () => await prisma.$disconnect());
