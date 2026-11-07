/**
 * Test EDHREC Top Commanders Scraper
 * Tests scrapeTopCommanders() to see what HTML structure exists
 */

import * as cheerio from 'cheerio';

async function testTopCommandersScraper() {
  console.log('🔍 Testing EDHREC top commanders page...\n');

  try {
    const response = await fetch('https://edhrec.com/commanders', {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const html = await response.text();
    const $ = cheerio.load(html);

    console.log('Checking for commander elements...\n');

    // Check various possible selectors
    console.log('Selector: .Commander_list_item');
    console.log(`Found: ${$('.Commander_list_item').length} elements\n`);

    console.log('Selector: .Commander_name');
    console.log(`Found: ${$('.Commander_name').length} elements\n`);

    console.log('Selector: .Card-item');
    console.log(`Found: ${$('.Card-item').length} elements\n`);

    console.log('Selector: [class*="Commander"]');
    console.log(`Found: ${$('[class*="Commander"]').length} elements\n`);

    console.log('Selector: [class*="commander"]');
    console.log(`Found: ${$('[class*="commander"]').length} elements\n`);

    console.log('Selector: .Card');
    console.log(`Found: ${$('.Card').length} elements\n`);

    // Show a sample of classes found in the page
    console.log('Sample classes from page (Card/commander related):');
    $('[class]').slice(0, 50).each((i, el) => {
      const classes = $(el).attr('class');
      if (classes && (classes.includes('Card') || classes.includes('commander') || classes.includes('Commander'))) {
        console.log(`  - ${classes}`);
      }
    });

    // Check for any links to commander pages
    console.log('\nSample links to commander pages:');
    $('a[href*="/commanders/"]').slice(0, 10).each((i, el) => {
      const href = $(el).attr('href');
      const text = $(el).text().trim();
      if (text) {
        console.log(`  - ${text}: ${href}`);
      }
    });

    console.log('\n✅ Test complete');

  } catch (error) {
    console.error('❌ Error:', error);
  }
}

testTopCommandersScraper();
