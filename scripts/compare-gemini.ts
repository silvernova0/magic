#!/usr/bin/env tsx
/**
 * Compare Qwen 2.5 3B model vs Gemini 2.5 Flash
 * Generates decks with both models and compares quality
 */

import { buildCommanderDeckWithAI } from '../src/lib/gemini';
import { readFileSync, writeFileSync, mkdirSync } from 'fs';
import { join } from 'path';

interface TestCase {
  name: string;
  commander: string;
  theme: string;
  colors: string[];
  powerLevel: string;
}

const TEST_CASES: TestCase[] = [
  {
    name: 'atraxa-counters',
    commander: "Atraxa, Praetors' Voice",
    theme: 'Counters/Proliferate',
    colors: ['W', 'U', 'B', 'G'],
    powerLevel: '4', // Bracket 4 = high power
  },
  {
    name: 'ur-dragon-tribal',
    commander: 'The Ur-Dragon',
    theme: 'Dragon Tribal',
    colors: ['W', 'U', 'B', 'R', 'G'],
    powerLevel: '3', // Bracket 3 = optimized
  },
  {
    name: 'korvold-aristocrats',
    commander: 'Korvold, Fae-Cursed King',
    theme: 'Aristocrats/Sacrifice',
    colors: ['B', 'R', 'G'],
    powerLevel: '3',
  },
];

async function generateWithGemini(testCase: TestCase) {
  console.log(`\n${'='.repeat(70)}`);
  console.log(`GEMINI - ${testCase.name}`);
  console.log(`${'='.repeat(70)}`);

  const startTime = Date.now();

  try {
    const deck = await buildCommanderDeckWithAI({
      commander: testCase.commander,
      theme: testCase.theme,
      colors: testCase.colors,
      powerLevel: testCase.powerLevel,
      useCollectionOnly: false,
    });

    const duration = ((Date.now() - startTime) / 1000).toFixed(2);

    console.log(`✅ Generated in ${duration}s`);
    console.log(`Commander: ${deck.commander?.[0] || 'Unknown'}`);
    console.log(`Strategy: ${deck.strategy || 'Unknown'}`);

    // Count cards by type
    const cardCounts = {
      creatures: deck.creatures?.length || 0,
      instants: deck.instants?.length || 0,
      sorceries: deck.sorceries?.length || 0,
      enchantments: deck.enchantments?.length || 0,
      artifacts: deck.artifacts?.length || 0,
      planeswalkers: deck.planeswalkers?.length || 0,
      lands: deck.lands?.length || 0,
    };

    console.log('\nCard distribution:');
    for (const [type, count] of Object.entries(cardCounts)) {
      console.log(`  ${type}: ${count}`);
    }

    const total =
      cardCounts.creatures +
      cardCounts.instants +
      cardCounts.sorceries +
      cardCounts.enchantments +
      cardCounts.artifacts +
      cardCounts.planeswalkers +
      cardCounts.lands;

    console.log(`\nTotal: ${total} cards`);

    return {
      model: 'gemini-2.5-flash',
      test_case: testCase.name,
      duration_seconds: parseFloat(duration),
      deck,
      card_counts: cardCounts,
      total_cards: total,
      timestamp: new Date().toISOString(),
    };
  } catch (error) {
    console.error(`❌ Failed:`, error);
    return {
      model: 'gemini-2.5-flash',
      test_case: testCase.name,
      error: error instanceof Error ? error.message : String(error),
      timestamp: new Date().toISOString(),
    };
  }
}

async function main() {
  console.log('='.repeat(70));
  console.log('GEMINI VS QWEN COMPARISON TEST');
  console.log('='.repeat(70));
  console.log(`Test cases: ${TEST_CASES.length}\n`);

  const results = [];

  for (const testCase of TEST_CASES) {
    const geminiResult = await generateWithGemini(testCase);
    results.push(geminiResult);

    // Wait a bit between requests to avoid rate limiting
    await new Promise((resolve) => setTimeout(resolve, 2000));
  }

  // Save results
  const outputDir = 'generated_decks/comparison';
  mkdirSync(outputDir, { recursive: true });

  const summaryFile = join(outputDir, 'gemini_results.json');
  writeFileSync(summaryFile, JSON.stringify(results, null, 2));

  console.log(`\n${'='.repeat(70)}`);
  console.log('GEMINI SUMMARY');
  console.log(`${'='.repeat(70)}`);

  const successful = results.filter((r) => !r.error).length;
  const failed = results.filter((r) => r.error).length;

  console.log(`Total tests: ${results.length}`);
  console.log(`✅ Successful: ${successful}`);
  console.log(`❌ Failed: ${failed}`);

  if (successful > 0) {
    const avgDuration =
      results
        .filter((r) => r.duration_seconds)
        .reduce((sum, r) => sum + (r.duration_seconds || 0), 0) / successful;

    console.log(`Average generation time: ${avgDuration.toFixed(2)}s`);
  }

  console.log(`\n💾 Results saved to: ${summaryFile}`);

  console.log(`\n${'='.repeat(70)}`);
  console.log('NEXT STEP: Generate with Qwen model');
  console.log(`${'='.repeat(70)}`);
  console.log('\nRun the Qwen model test:');
  console.log('  cd /home/social/magicapp');
  console.log('  source ~/.virtualenvs/magicapp/bin/activate');
  console.log('  python3 scripts/compare-qwen-decks.py');
}

main().catch((error) => {
  console.error('Error:', error);
  process.exit(1);
});
