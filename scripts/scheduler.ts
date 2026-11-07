#!/usr/bin/env node
/**
 * Standalone scheduler service
 * Run this to start the scheduled scraping service
 * 
 * Usage:
 *   npm run scheduler
 *   or
 *   npx tsx scripts/scheduler.ts
 */

import { initializeScheduledJobs } from '../src/lib/scheduled-scraper';

console.log('═══════════════════════════════════════════════════');
console.log('     MTG AI Commander Deck Builder');
console.log('     Scheduled Scraping Service');
console.log('═══════════════════════════════════════════════════\n');

// Initialize scheduled jobs
const jobs = initializeScheduledJobs();

// Keep the process running
process.on('SIGINT', () => {
  console.log('\n\n🛑 Shutting down scheduler...');
  
  // Cancel all scheduled jobs
  Object.values(jobs).forEach(job => {
    if (job) {
      job.cancel();
    }
  });
  
  console.log('✅ All jobs cancelled. Goodbye!\n');
  process.exit(0);
});

console.log('🔄 Scheduler is running. Press Ctrl+C to stop.\n');

// Keep process alive
setInterval(() => {
  // Just keep the process running
}, 1000 * 60 * 60); // Check every hour
