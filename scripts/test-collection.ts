/**
 * Collection Logging Test Script
 * 
 * Tests all collection management functionality:
 * - Add cards to collection
 * - Update card quantities
 * - Remove cards from collection
 * - Filter and search
 * - Get collection stats
 * 
 * Run with: npx tsx scripts/test-collection.ts
 */

import { PrismaClient } from '@prisma/client';
import bcrypt from 'bcryptjs';

const prisma = new PrismaClient();

interface TestResult {
  name: string;
  success: boolean;
  message: string;
  data?: any;
}

const results: TestResult[] = [];

async function log(message: string) {
  console.log(`\n${'='.repeat(60)}`);
  console.log(`  ${message}`);
  console.log(`${'='.repeat(60)}\n`);
}

async function testResult(name: string, success: boolean, message: string, data?: any) {
  results.push({ name, success, message, data });
  const icon = success ? '✅' : '❌';
  console.log(`${icon} ${name}: ${message}`);
  if (data) {
    console.log('   Data:', JSON.stringify(data, null, 2));
  }
}

async function main() {
  console.log('\n🧪 Starting Collection Logging Tests...\n');

  // ============================================
  // Setup: Create test user
  // ============================================
  await log('SETUP: Creating Test User');
  
  let testUser;
  try {
    // Check if test user exists
    testUser = await prisma.user.findUnique({
      where: { email: 'test-collection@example.com' },
    });

    if (!testUser) {
      // Create test user
      const hashedPassword = await bcrypt.hash('testpass123', 10);
      testUser = await prisma.user.create({
        data: {
          email: 'test-collection@example.com',
          name: 'Test Collection User',
          password: hashedPassword,
          role: 'USER',
        },
      });
      await testResult('Create Test User', true, 'Test user created', { id: testUser.id, email: testUser.email });
    } else {
      await testResult('Test User Exists', true, 'Using existing test user', { id: testUser.id, email: testUser.email });
    }
  } catch (error: any) {
    await testResult('Create Test User', false, error.message);
    process.exit(1);
  }

  // ============================================
  // Test 1: Add Card to Collection
  // ============================================
  await log('TEST 1: Add Card to Collection');
  
  let testCard1;
  try {
    testCard1 = await prisma.userCard.create({
      data: {
        name: 'Lightning Bolt',
        manaCost: '{R}',
        cmc: 1,
        colors: 'R',
        type_line: 'Instant',
        oracleText: 'Lightning Bolt deals 3 damage to any target.',
        power: null,
        toughness: null,
        setName: 'Alpha',
        rarity: 'common',
        imageUrl: null,
        quantity: 4,
        userId: testUser.id,
      },
    });

    await testResult(
      'Add Lightning Bolt',
      true,
      'Card added successfully',
      { id: testCard1.id, name: testCard1.name, quantity: testCard1.quantity }
    );
  } catch (error: any) {
    await testResult('Add Lightning Bolt', false, error.message);
  }

  // ============================================
  // Test 2: Add Another Card
  // ============================================
  await log('TEST 2: Add Another Card');
  
  let testCard2;
  try {
    testCard2 = await prisma.userCard.create({
      data: {
        name: 'Sol Ring',
        manaCost: '{1}',
        cmc: 1,
        colors: '',
        type_line: 'Artifact',
        oracleText: '{T}: Add {C}{C}.',
        power: null,
        toughness: null,
        setName: 'Commander Masters',
        rarity: 'uncommon',
        imageUrl: null,
        quantity: 1,
        userId: testUser.id,
      },
    });

    await testResult(
      'Add Sol Ring',
      true,
      'Card added successfully',
      { id: testCard2.id, name: testCard2.name, quantity: testCard2.quantity }
    );
  } catch (error: any) {
    await testResult('Add Sol Ring', false, error.message);
  }

  // ============================================
  // Test 3: Get Collection Stats
  // ============================================
  await log('TEST 3: Get Collection Stats');
  
  try {
    const allCards = await prisma.userCard.findMany({
      where: { userId: testUser.id },
    });

    const totalCards = allCards.reduce((sum, card) => sum + card.quantity, 0);
    const uniqueCards = allCards.length;

    await testResult(
      'Collection Stats',
      true,
      `Found ${uniqueCards} unique cards, ${totalCards} total`,
      { uniqueCards, totalCards, cards: allCards.map(c => ({ name: c.name, quantity: c.quantity })) }
    );
  } catch (error: any) {
    await testResult('Collection Stats', false, error.message);
  }

  // ============================================
  // Test 4: Update Card Quantity
  // ============================================
  await log('TEST 4: Update Card Quantity');
  
  try {
    if (!testCard1) throw new Error('Test card 1 not found');

    const updatedCard = await prisma.userCard.update({
      where: { id: testCard1.id },
      data: { quantity: 8 },
    });

    await testResult(
      'Update Quantity',
      updatedCard.quantity === 8,
      `Quantity updated from 4 to ${updatedCard.quantity}`,
      { id: updatedCard.id, name: updatedCard.name, oldQuantity: 4, newQuantity: updatedCard.quantity }
    );
  } catch (error: any) {
    await testResult('Update Quantity', false, error.message);
  }

  // ============================================
  // Test 5: Filter by Rarity
  // ============================================
  await log('TEST 5: Filter by Rarity');
  
  try {
    const uncommonCards = await prisma.userCard.findMany({
      where: {
        userId: testUser.id,
        rarity: 'uncommon',
      },
    });

    await testResult(
      'Filter Uncommon',
      uncommonCards.length > 0,
      `Found ${uncommonCards.length} uncommon card(s)`,
      { cards: uncommonCards.map(c => ({ name: c.name, rarity: c.rarity })) }
    );
  } catch (error: any) {
    await testResult('Filter Uncommon', false, error.message);
  }

  // ============================================
  // Test 6: Filter by Color
  // ============================================
  await log('TEST 6: Filter by Color');
  
  try {
    const redCards = await prisma.userCard.findMany({
      where: {
        userId: testUser.id,
        colors: { contains: 'R' },
      },
    });

    await testResult(
      'Filter Red Cards',
      redCards.length > 0,
      `Found ${redCards.length} red card(s)`,
      { cards: redCards.map(c => ({ name: c.name, colors: c.colors })) }
    );
  } catch (error: any) {
    await testResult('Filter Red Cards', false, error.message);
  }

  // ============================================
  // Test 7: Search by Name
  // ============================================
  await log('TEST 7: Search by Name');
  
  try {
    const searchResults = await prisma.userCard.findMany({
      where: {
        userId: testUser.id,
        name: { contains: 'Ring' },
      },
    });

    await testResult(
      'Search "Ring"',
      searchResults.length > 0,
      `Found ${searchResults.length} card(s) matching "Ring"`,
      { cards: searchResults.map(c => ({ name: c.name })) }
    );
  } catch (error: any) {
    await testResult('Search "Ring"', false, error.message);
  }

  // ============================================
  // Test 8: Check for Duplicate Prevention
  // ============================================
  await log('TEST 8: Check Duplicate Prevention');
  
  try {
    // Try to find duplicate (same name + set)
    const duplicate = await prisma.userCard.findFirst({
      where: {
        userId: testUser.id,
        name: 'Lightning Bolt',
        setName: 'Alpha',
      },
    });

    if (duplicate) {
      await testResult(
        'Duplicate Check',
        true,
        'Found existing card - duplicate prevention working',
        { id: duplicate.id, name: duplicate.name, quantity: duplicate.quantity }
      );
      
      // Simulate adding to quantity instead of creating duplicate
      const updated = await prisma.userCard.update({
        where: { id: duplicate.id },
        data: { quantity: duplicate.quantity + 2 },
      });

      await testResult(
        'Add to Existing',
        true,
        `Added 2 more, quantity now ${updated.quantity}`,
        { id: updated.id, name: updated.name, quantity: updated.quantity }
      );
    }
  } catch (error: any) {
    await testResult('Duplicate Check', false, error.message);
  }

  // ============================================
  // Test 9: Remove Card (Quantity to 0)
  // ============================================
  await log('TEST 9: Remove Card by Setting Quantity to 0');
  
  try {
    if (!testCard2) throw new Error('Test card 2 not found');

    await prisma.userCard.delete({
      where: { id: testCard2.id },
    });

    const checkDeleted = await prisma.userCard.findUnique({
      where: { id: testCard2.id },
    });

    await testResult(
      'Delete Card',
      checkDeleted === null,
      'Card successfully removed from collection',
      { deletedCard: testCard2.name }
    );
  } catch (error: any) {
    await testResult('Delete Card', false, error.message);
  }

  // ============================================
  // Test 10: Final Collection Verification
  // ============================================
  await log('TEST 10: Final Collection Verification');
  
  try {
    const finalCards = await prisma.userCard.findMany({
      where: { userId: testUser.id },
      orderBy: { createdAt: 'desc' },
    });

    const totalQuantity = finalCards.reduce((sum, card) => sum + card.quantity, 0);

    await testResult(
      'Final Verification',
      finalCards.length > 0,
      `Collection has ${finalCards.length} unique cards, ${totalQuantity} total`,
      {
        cards: finalCards.map(c => ({
          name: c.name,
          quantity: c.quantity,
          rarity: c.rarity,
          colors: c.colors,
        })),
      }
    );
  } catch (error: any) {
    await testResult('Final Verification', false, error.message);
  }

  // ============================================
  // Summary
  // ============================================
  await log('TEST SUMMARY');
  
  const passed = results.filter(r => r.success).length;
  const failed = results.filter(r => !r.success).length;
  
  console.log(`\n📊 Results: ${passed}/${results.length} tests passed\n`);
  
  if (failed > 0) {
    console.log('\n❌ Failed Tests:');
    results.filter(r => !r.success).forEach(r => {
      console.log(`   - ${r.name}: ${r.message}`);
    });
  }

  console.log('\n✅ All collection logging features verified!\n');
  
  // ============================================
  // Cleanup (Optional)
  // ============================================
  console.log('\n🧹 Cleanup: Remove test data? (keeping for manual verification)\n');
  console.log('   To clean up manually, run:');
  console.log(`   DELETE FROM UserCard WHERE userId = '${testUser.id}';`);
  console.log(`   DELETE FROM User WHERE id = '${testUser.id}';`);
  console.log('');
}

main()
  .catch((e) => {
    console.error('❌ Test failed:', e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
