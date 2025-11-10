/**
 * Scheduled scraping service for automated data collection
 * Uses node-schedule for cron-like job scheduling
 */

import schedule from 'node-schedule';
import { PrismaClient } from '@prisma/client';
import { scrapeEDHREC } from './scrapers/edhrec';
import { scrapeMTGTop8 } from './scrapers/mtgtop8';
import { scrapeMoxfield } from './scrapers/moxfield';

const prisma = new PrismaClient();

interface ScrapeJobResult {
  success: boolean;
  itemsScraped: number;
  errors: string[];
  duration: number;
}

/**
 * Create a scrape job record in the database
 */
async function createScrapeJob(jobType: string) {
  return await prisma.scrapeJob.create({
    data: {
      jobType,
      status: 'running',
      startedAt: new Date(),
    },
  });
}

/**
 * Update scrape job with results
 */
async function updateScrapeJob(
  jobId: string,
  result: ScrapeJobResult
) {
  await prisma.scrapeJob.update({
    where: { id: jobId },
    data: {
      status: result.success ? 'completed' : 'failed',
      itemsScraped: result.itemsScraped,
      errors: result.errors.length > 0 ? JSON.stringify(result.errors) : null,
      completedAt: new Date(),
      duration: result.duration,
    },
  });
}

/**
 * EDHREC scraping job - runs weekly
 * Scrapes synergy data for top commanders
 */
async function runEDHRECJob() {
  console.log('\n🔄 [SCHEDULED] Starting EDHREC scraping job...');
  const startTime = Date.now();
  const job = await createScrapeJob('edhrec');
  
  try {
    const data = await scrapeEDHREC();
    
    // Count items scraped
    let itemsScraped = 0;
    if (data.topCommanders) {
      itemsScraped += data.topCommanders.length;
    }
    
    const duration = Date.now() - startTime;
    
    await updateScrapeJob(job.id, {
      success: true,
      itemsScraped,
      errors: [],
      duration,
    });
    
    console.log(`✅ [SCHEDULED] EDHREC job completed: ${itemsScraped} items in ${(duration / 1000).toFixed(1)}s`);
  } catch (error) {
    const duration = Date.now() - startTime;
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    
    await updateScrapeJob(job.id, {
      success: false,
      itemsScraped: 0,
      errors: [errorMessage],
      duration,
    });
    
    console.error(`❌ [SCHEDULED] EDHREC job failed:`, error);
  }
}

/**
 * MTGTop8 scraping job - runs every 3 days
 * Scrapes recent tournament decklists
 */
async function runMTGTop8Job() {
  console.log('\n🔄 [SCHEDULED] Starting MTGTop8 scraping job...');
  const startTime = Date.now();
  const job = await createScrapeJob('mtgtop8');
  
  try {
    const data = await scrapeMTGTop8();
    
    // Count items scraped
    const itemsScraped = data.recentDecks?.length || 0;
    const duration = Date.now() - startTime;
    
    await updateScrapeJob(job.id, {
      success: true,
      itemsScraped,
      errors: [],
      duration,
    });
    
    console.log(`✅ [SCHEDULED] MTGTop8 job completed: ${itemsScraped} items in ${(duration / 1000).toFixed(1)}s`);
  } catch (error) {
    const duration = Date.now() - startTime;
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    
    await updateScrapeJob(job.id, {
      success: false,
      itemsScraped: 0,
      errors: [errorMessage],
      duration,
    });
    
    console.error(`❌ [SCHEDULED] MTGTop8 job failed:`, error);
  }
}

/**
 * Moxfield scraping job - runs daily
 * Scrapes popular decks across all brackets
 */
async function runMoxfieldJob() {
  console.log('\n🔄 [SCHEDULED] Starting Moxfield scraping job...');
  const startTime = Date.now();
  const job = await createScrapeJob('moxfield');
  
  try {
    const data = await scrapeMoxfield();
    
    // Count items scraped
    let itemsScraped = 0;
    if (data.topDecksByBracket) {
      itemsScraped = Object.values(data.topDecksByBracket).flat().length;
    }
    
    const duration = Date.now() - startTime;
    
    await updateScrapeJob(job.id, {
      success: true,
      itemsScraped,
      errors: [],
      duration,
    });
    
    console.log(`✅ [SCHEDULED] Moxfield job completed: ${itemsScraped} items in ${(duration / 1000).toFixed(1)}s`);
  } catch (error) {
    const duration = Date.now() - startTime;
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    
    await updateScrapeJob(job.id, {
      success: false,
      itemsScraped: 0,
      errors: [errorMessage],
      duration,
    });
    
    console.error(`❌ [SCHEDULED] Moxfield job failed:`, error);
  }
}

/**
 * Initialize scheduled jobs
 * 
 * Schedule format (cron-like):
 * - Second (0-59)
 * - Minute (0-59)
 * - Hour (0-23)
 * - Day of Month (1-31)
 * - Month (0-11)
 * - Day of Week (0-6, Sunday=0)
 */
export function initializeScheduledJobs() {
  console.log('🚀 Initializing scheduled scraping jobs...\n');
  
  // EDHREC: Every Sunday at 3:00 AM
  // Synergy data changes slowly, weekly updates are sufficient
  const edhrecJob = schedule.scheduleJob('0 0 3 * * 0', () => {
    runEDHRECJob();
  });
  console.log('📅 EDHREC job scheduled: Every Sunday at 3:00 AM');
  
  // MTGTop8: Every 3 days at 2:00 AM
  // Tournament data updates regularly but not daily
  const mtgtop8Job = schedule.scheduleJob('0 0 2 */3 * *', () => {
    runMTGTop8Job();
  });
  console.log('📅 MTGTop8 job scheduled: Every 3 days at 2:00 AM');
  
  // Moxfield: Every day at 1:00 AM
  // Community decks update frequently, daily scraping keeps data fresh
  const moxfieldJob = schedule.scheduleJob('0 0 1 * * *', () => {
    runMoxfieldJob();
  });
  console.log('📅 Moxfield job scheduled: Every day at 1:00 AM');
  
  console.log('\n✅ All scheduled jobs initialized!');
  console.log('📊 Use GET /api/scrape/jobs to view job history\n');
  
  return {
    edhrec: edhrecJob,
    mtgtop8: mtgtop8Job,
    moxfield: moxfieldJob,
  };
}

/**
 * Run a job immediately (for testing or manual triggers)
 */
export async function runJobNow(jobType: 'edhrec' | 'mtgtop8' | 'moxfield') {
  switch (jobType) {
    case 'edhrec':
      await runEDHRECJob();
      break;
    case 'mtgtop8':
      await runMTGTop8Job();
      break;
    case 'moxfield':
      await runMoxfieldJob();
      break;
    default:
      throw new Error(`Unknown job type: ${jobType}`);
  }
}

/**
 * Get recent scrape job history
 */
export async function getJobHistory(limit = 50) {
  return await prisma.scrapeJob.findMany({
    orderBy: { startedAt: 'desc' },
    take: limit,
  });
}

/**
 * Get statistics for a specific job type
 */
export async function getJobStats(jobType: string) {
  const jobs = await prisma.scrapeJob.findMany({
    where: { jobType },
    orderBy: { startedAt: 'desc' },
    take: 10,
  });
  
  const completed = jobs.filter(j => j.status === 'completed').length;
  const failed = jobs.filter(j => j.status === 'failed').length;
  const avgDuration = jobs
    .filter(j => j.duration)
    .reduce((sum, j) => sum + (j.duration || 0), 0) / jobs.length || 0;
  const totalItemsScraped = jobs.reduce((sum, j) => sum + j.itemsScraped, 0);
  
  return {
    jobType,
    totalRuns: jobs.length,
    completed,
    failed,
    successRate: jobs.length > 0 ? (completed / jobs.length * 100).toFixed(1) + '%' : '0%',
    avgDuration: `${(avgDuration / 1000).toFixed(1)}s`,
    totalItemsScraped,
    lastRun: jobs[0]?.startedAt,
    lastStatus: jobs[0]?.status,
  };
}
