#!/usr/bin/env tsx

import { readFileSync, existsSync, mkdirSync, writeFileSync } from 'fs';
import { basename, join } from 'path';
import { buildDeckFromStructure, StructuredDeckPlan } from '../src/lib/structuredDeckBuilder';

async function main() {
  const inputPath = process.argv[2];
  if (!inputPath) {
    console.error('Usage: npx tsx scripts/build-deck-from-structure.ts <structured-json> [output-dir]');
    process.exit(1);
  }

  const outputDir = process.argv[3] ?? 'generated_decks/v3_executed';

  if (!existsSync(inputPath)) {
    console.error(`Input file not found: ${inputPath}`);
    process.exit(1);
  }

  const raw = readFileSync(inputPath, 'utf-8');
  const plan: StructuredDeckPlan = JSON.parse(raw);

  const result = await buildDeckFromStructure(plan);

  console.log('Commander:', result.commander?.name ?? 'Unknown');
  console.log('Cards generated:', result.cards.length);
  if (result.errors.length) {
    console.warn('Errors:');
    result.errors.forEach((err) => console.warn(`  - ${err}`));
  }
  if (result.warnings.length) {
    console.warn('Warnings:');
    result.warnings.forEach((warn) => console.warn(`  - ${warn}`));
  }

  mkdirSync(outputDir, { recursive: true });
  const fileName = basename(inputPath).replace(/\.json$/i, '') + '-deck.json';
  const outPath = join(outputDir, fileName);
  writeFileSync(
    outPath,
    JSON.stringify(
      {
        commander: result.commander?.name,
        cards: result.cards,
        errors: result.errors,
        warnings: result.warnings,
      },
      null,
      2
    )
  );

  console.log(`\nDeck saved to ${outPath}`);
  process.exit(result.errors.length ? 1 : 0);
}

main().catch((err) => {
  console.error('Failed to build deck:', err);
  process.exit(1);
});

