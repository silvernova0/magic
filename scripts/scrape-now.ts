#!/usr/bin/env node
/**
 * Manual scraper trigger
 * Run specific scraping jobs on demand for testing
 * 
 * Usage:
 *   npm run scrape:now -- edhrec
 *   npm run scrape:now -- mtgtop8
 *   npm run scrape:now -- moxfield
 *   npm run scrape:now -- all
 */

import { runJobNow, getJobStats } from '../src/lib/scheduled-scraper';

const jobType = process.argv[2];

async function main() {
  console.log('═══════════════════════════════════════════════════');
  console.log('     Manual Scraping Job Trigger');
  console.log('═══════════════════════════════════════════════════\n');

  if (!jobType || !['edhrec', 'mtgtop8', 'moxfield', 'all'].includes(jobType)) {
    console.error('❌ Invalid job type!\n');
    console.log('Usage:');
    console.log('  npm run scrape:now -- edhrec');
    console.log('  npm run scrape:now -- mtgtop8');
    console.log('  npm run scrape:now -- moxfield');
    console.log('  npm run scrape:now -- all\n');
    process.exit(1);
  }

  try {
    if (jobType === 'all') {
      console.log('🚀 Running all scraping jobs...\n');
      
      await runJobNow('edhrec');
      console.log('');
      
      await runJobNow('mtgtop8');
      console.log('');
      
      await runJobNow('moxfield');
      console.log('');
      
      console.log('✅ All jobs completed!\n');
    } else {
      console.log(`🚀 Running ${jobType} scraping job...\n`);
      await runJobNow(jobType as 'edhrec' | 'mtgtop8' | 'moxfield');
      console.log('');
    }

    // Show statistics
    console.log('📊 Job Statistics:\n');
    if (jobType === 'all') {
      const stats = await Promise.all([
        getJobStats('edhrec'),
        getJobStats('mtgtop8'),
        getJobStats('moxfield'),
      ]);
      
      stats.forEach(stat => {
        console.log(`${stat.jobType.toUpperCase()}:`);
        console.log(`  Total Runs: ${stat.totalRuns}`);
        console.log(`  Success Rate: ${stat.successRate}`);
        console.log(`  Avg Duration: ${stat.avgDuration}`);
        console.log(`  Last Status: ${stat.lastStatus}`);
        console.log('');
      });
    } else {
      const stats = await getJobStats(jobType);
      console.log(`Total Runs: ${stats.totalRuns}`);
      console.log(`Success Rate: ${stats.successRate}`);
      console.log(`Avg Duration: ${stats.avgDuration}`);
      console.log(`Total Items: ${stats.totalItemsScraped}`);
      console.log(`Last Status: ${stats.lastStatus}`);
      console.log('');
    }

    process.exit(0);
  } catch (error) {
    console.error('❌ Error running scrape job:', error);
    process.exit(1);
  }
}

main();
