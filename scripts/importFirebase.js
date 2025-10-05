#!/usr/bin/env node
// Simple Firebase -> Prisma importer
// Usage: node scripts/importFirebase.js

const path = require('path');
const fs = require('fs');

// CLI args: --list  (list top-level collections)
//           --collection=<name>  (import this collection)
//           --path=<serviceAccountPath>  (path to service account JSON)
const argv = process.argv.slice(2);
const argMap = {};
for (const a of argv) {
  if (a.startsWith('--')) {
    const [k, v] = a.replace(/^--/, '').split('=');
    argMap[k] = v === undefined ? true : v;
  }
}

const serviceKeyPath = argMap.path
  ? path.resolve(process.cwd(), argMap.path)
  : path.join(__dirname, '..', '.github', 'newmagic-9deab-firebase-adminsdk-fbsvc-d8877cf21c.json');
if (!fs.existsSync(serviceKeyPath)) {
  console.error('Service account JSON not found at', serviceKeyPath);
  console.error('Place your Firebase service account JSON in .github and try again.');
  process.exit(1);
}

const admin = require('firebase-admin');
const { PrismaClient } = require('@prisma/client');

const prisma = new PrismaClient();

const serviceAccount = require(serviceKeyPath);

admin.initializeApp({ credential: admin.credential.cert(serviceAccount) });

const db = admin.firestore();

async function listCollections() {
  const cols = await db.listCollections();
  console.log('Top-level collections:');
  for (const c of cols) console.log('-', c.id);
}

async function listSubcollections(rootCollection, limit = 5) {
  console.log(`Listing subcollections for up to ${limit} docs in collection: ${rootCollection}`);
  const snapshot = await db.collection(rootCollection).limit(limit).get();
  if (snapshot.empty) {
    console.log('No documents found in', rootCollection);
    return;
  }
  const seen = new Set();
  for (const doc of snapshot.docs) {
    const subcols = await doc.ref.listCollections();
    for (const s of subcols) {
      seen.add(s.id);
    }
  }
  if (seen.size === 0) {
    console.log('No subcollections found under the sampled documents.');
  } else {
    console.log('Discovered subcollections:');
    for (const s of seen) console.log('-', s);
  }
}

async function importCollection(collectionName) {
  console.log('Importing collection:', collectionName);
  const snapshot = await db.collection(collectionName).get();
  console.log('Documents to import:', snapshot.size);

  let count = 0;
  for (const doc of snapshot.docs) {
    const data = doc.data();
    // Heuristic mapping: prefer explicit fields, fallback to generic ones
    const name = data.name || data.cardName || data.card || data.title;
    const setName = data.setName || data.set || data.set_code || data.setCode || 'unknown';
    const quantity = Number(data.quantity || data.qty || data.count || 1) || 1;
    const imageUrl = data.imageUrl || data.image || data.image_uri || null;
    const oracleText = data.oracleText || data.text || data.oracle || null;
    const manaCost = data.manaCost || data.mana || data.mana_cost || null;
    const cmc = Number(data.cmc ?? data.convertedManaCost ?? 0) || 0;
    const colors = Array.isArray(data.colors) ? data.colors.join(',') : (data.colors || data.color || '');
    const type_line = data.type_line || data.type || data.types || '';
    const rarity = data.rarity || data.r || 'unknown';

    if (!name) {
      console.warn('Skipping doc (no name):', doc.id);
      continue;
    }

    // Upsert using findFirst + update/create to work with composite unique
    const existing = await prisma.card.findFirst({ where: { name: name, setName: setName } });
    if (existing) {
      await prisma.card.update({ where: { id: existing.id }, data: { quantity: existing.quantity + quantity, imageUrl: imageUrl || existing.imageUrl } });
    } else {
      await prisma.card.create({ data: { name, setName, quantity, imageUrl, oracleText, manaCost, cmc, colors, type_line, rarity } });
    }

    count++;
    if (count % 50 === 0) console.log('Imported', count);
  }

  console.log('Import complete. Total imported/updated:', count);
}

async function scanCollections(limitPerCollection = 20) {
  console.log('Scanning top-level collections (sample up to', limitPerCollection, 'docs each)');
  const cols = await db.listCollections();
  for (const c of cols) {
    const snapshot = await db.collection(c.id).limit(limitPerCollection).get();
    console.log(`- ${c.id}: approx ${snapshot.size} documents (sampled up to ${limitPerCollection})`);
  }
}

async function run() {
  try {
    if (argMap.list) {
      await listCollections();
      process.exit(0);
    }

    if (argMap.scan) {
      await scanCollections(10);
      process.exit(0);
    }

    if (argMap['list-subcollections']) {
      const target = argMap['list-subcollections'] === true ? 'users' : argMap['list-subcollections'];
      await listSubcollections(target, 10);
      process.exit(0);
    }

    const collectionName = argMap.collection || null;
    if (!collectionName) {
      // Try common collection names
      const candidates = ['cards', 'collection', 'collections', 'mycards'];
      let found = null;
      for (const col of candidates) {
        const snapshot = await db.collection(col).limit(1).get();
        if (!snapshot.empty) {
          found = col;
          break;
        }
      }
      if (!found) {
        console.error('No candidate collection found. Run with --list to see top-level collections, or supply --collection=<name>.');
        process.exit(1);
      }
      await importCollection(found);
    } else {
      await importCollection(collectionName);
    }
  } catch (err) {
    console.error('Import failed:', err);
  } finally {
    await prisma.$disconnect();
    process.exit(0);
  }
}

run();
