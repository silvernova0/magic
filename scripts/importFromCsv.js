#!/usr/bin/env node

const { PrismaClient } = require('@prisma/client');
const fs = require('fs');
const path = require('path');
const { parse } = require('csv-parse/sync');

const prisma = new PrismaClient();

async function main() {
  // 1. Create a default user
  let user = await prisma.user.findUnique({ where: { email: 'default@example.com' } });
  if (!user) {
    user = await prisma.user.create({
      data: {
        email: 'default@example.com',
        password: 'password', // You should use a hashed password in a real app
      },
    });
  }
  console.log('Created default user:', user);

  // 2. Create a default collection for the user
  let collection = await prisma.collection.findFirst({ where: { userId: user.id, name: 'Default Collection' } });
  if (!collection) {
    collection = await prisma.collection.create({
      data: {
        name: 'Default Collection',
        userId: user.id,
      },
    });
  }
  console.log('Created default collection:', collection);

  // 3. Read and parse the CSV file
  const csvPath = path.join(__dirname, '..', 'collectionexport.csv');
  if (!fs.existsSync(csvPath)) {
    console.error('collectionexport.csv not found at', csvPath);
    process.exit(1);
  }
  const fileContent = fs.readFileSync(csvPath);
  const records = parse(fileContent, {
    columns: true,
    skip_empty_lines: true,
  });

  console.log(`Found ${records.length} records in CSV.`);

  // 4. Iterate and import cards
  let count = 0;
  for (const record of records) {
    const name = record['Card'];
    const setName = record['Set'];
    const quantity = parseInt(record['Quantity'], 10) || 1;
    const manaCost = record['Mana Cost'] || null;
    const cmc = parseFloat(record['Mana Value']) || 0;
    const colors = record['Color'] || '';
    const type_line = record['Type'] || '';
    const rarity = record['Rarity'] || 'unknown';
    const imageUrl = record['Image URL'] || null;
    const oracleText = record['Oracle Text'] || null;
    const power = record['Power'] || null;
    const toughness = record['Toughness'] || null;


    if (!name) {
      console.warn('Skipping record (no name):', record);
      continue;
    }

    // Upsert using findFirst + update/create to work with composite unique
    const existing = await prisma.card.findFirst({ where: { name: name, setName: setName, collectionId: collection.id } });
    if (existing) {
      await prisma.card.update({ where: { id: existing.id }, data: { quantity: existing.quantity + quantity } });
    } else {
      await prisma.card.create({
        data: {
          name,
          setName,
          quantity,
          manaCost,
          cmc,
          colors,
          type_line,
          rarity,
          imageUrl,
          oracleText,
          power,
          toughness,
          collectionId: collection.id,
        },
      });
    }

    count++;
    if (count % 100 === 0) {
      console.log(`Imported ${count}/${records.length} cards...`);
    }
  }

  console.log('Import complete. Total imported/updated:', count);
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
