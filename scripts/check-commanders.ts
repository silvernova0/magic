import { prisma } from '../src/lib/prisma';

async function main() {
  const count = await prisma.card.count({
    where: { isCommander: true }
  });
  
  console.log(`Total commanders in database: ${count}`);
  
  // Show some examples
  const commanders = await prisma.card.findMany({
    where: { isCommander: true },
    orderBy: { edhrecRank: 'asc' },
    take: 10,
    select: { name: true, edhrecRank: true }
  });
  
  console.log('\nTop 10 commanders:');
  commanders.forEach(c => {
    console.log(`  - ${c.name} (Rank: ${c.edhrecRank})`);
  });
  
  await prisma.$disconnect();
}

main().catch(console.error);
