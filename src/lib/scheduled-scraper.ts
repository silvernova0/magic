/**
 * Scheduled scraping service for automated data collection
 * Includes Scryfall (new card releases), EDHREC, MTGTop8, and Moxfield
 */

import schedule from 'node-schedule';
import { prisma } from './prisma';
import { scrapeEDHREC, scrapeCommanderDetails } from './scrapers/edhrec';
import { scrapeMTGTop8 } from './scrapers/mtgtop8';
import { scrapeMoxfield } from './scrapers/moxfield';

interface ScrapeJobResult {
  success: boolean;
  itemsScraped: number;
  errors: string[];
  duration: number;
}

let schedulerInitialized = false;

async function createScrapeJob(jobType: string) {
  return await prisma.scrapeJob.create({
    data: {
      jobType,
      status: 'running',
      startedAt: new Date(),
    },
  });
}

async function updateScrapeJob(jobId: string, result: ScrapeJobResult) {
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
 * Scryfall New Card Releases job - runs daily at 4:00 AM
 * Fetches the newest paper Commander-legal card releases and updates local SQLite DB
 */
export async function runScryfallJob() {
  console.log('\n🔄 [SCRAPER] Starting Scryfall New Card Releases sync...');
  const startTime = Date.now();
  const job = await createScrapeJob('scryfall');

  try {
    let itemsScraped = 0;
    let nextUrl: string | null =
      'https://api.scryfall.com/cards/search?q=game:paper+legal:commander&order=released&dir=desc&unique=cards';
    let pagesFetched = 0;

    while (nextUrl && pagesFetched < 3) {
      const res = await fetch(nextUrl, {
        headers: {
          'User-Agent': 'JankBuild-MTG-DeckBuilder/1.0',
          Accept: 'application/json',
        },
      });

      if (!res.ok) {
        throw new Error(`Scryfall API returned HTTP ${res.status}`);
      }

      const data = await res.json();
      const cards = Array.isArray(data?.data) ? data.data : [];

      for (const card of cards) {
        if (!card?.id || !card?.name || !card?.type_line) continue;
        if (
          card.type_line.includes('Token') ||
          card.type_line.includes('Emblem') ||
          card.type_line.includes('Card')
        ) {
          continue;
        }

        const isCommander =
          (card.type_line.includes('Legendary') && card.type_line.includes('Creature')) ||
          (card.oracle_text || '').includes('can be your commander');

        const colorIdentityStr = Array.isArray(card.color_identity)
          ? [...card.color_identity].sort().join(',')
          : '';
        const colorsStr = Array.isArray(card.colors) ? [...card.colors].sort().join(',') : '';

        await prisma.card.upsert({
          where: { id: card.id },
          create: {
            id: card.id,
            oracleId: card.oracle_id || null,
            name: card.name,
            manaCost: card.mana_cost || '',
            cmc: typeof card.cmc === 'number' ? card.cmc : 0,
            colors: colorsStr,
            colorIdentity: colorIdentityStr,
            typeLine: card.type_line,
            oracleText: card.oracle_text || card.card_faces?.[0]?.oracle_text || null,
            power: card.power || null,
            toughness: card.toughness || null,
            loyalty: card.loyalty || null,
            keywords: JSON.stringify(card.keywords || []),
            legalities: JSON.stringify(card.legalities || {}),
            rarity: card.rarity || 'common',
            setCode: card.set || '',
            setName: card.set_name || '',
            collectorNumber: card.collector_number || '0',
            imageUris: card.image_uris
              ? JSON.stringify(card.image_uris)
              : card.card_faces?.[0]?.image_uris
              ? JSON.stringify(card.card_faces[0].image_uris)
              : null,
            prices: card.prices ? JSON.stringify(card.prices) : null,
            edhrecRank: card.edhrec_rank ?? null,
            artist: card.artist || null,
            flavorText: card.flavor_text || null,
            releasedAt: card.released_at ? new Date(card.released_at) : null,
            isCommander: Boolean(isCommander && card.legalities?.commander === 'legal'),
          },
          update: {
            name: card.name,
            manaCost: card.mana_cost || '',
            cmc: typeof card.cmc === 'number' ? card.cmc : 0,
            colors: colorsStr,
            colorIdentity: colorIdentityStr,
            typeLine: card.type_line,
            oracleText: card.oracle_text || card.card_faces?.[0]?.oracle_text || null,
            legalities: JSON.stringify(card.legalities || {}),
            prices: card.prices ? JSON.stringify(card.prices) : null,
            edhrecRank: card.edhrec_rank ?? null,
            isCommander: Boolean(isCommander && card.legalities?.commander === 'legal'),
            updatedAt: new Date(),
          },
        });
        itemsScraped++;
      }

      pagesFetched++;
      nextUrl = data.has_more && data.next_page ? data.next_page : null;
      if (nextUrl) {
        await new Promise((r) => setTimeout(r, 150));
      }
    }

    const duration = Date.now() - startTime;
    await updateScrapeJob(job.id, {
      success: true,
      itemsScraped,
      errors: [],
      duration,
    });
    console.log(`✅ [SCRAPER] Scryfall sync completed: ${itemsScraped} cards synced in ${(duration / 1000).toFixed(1)}s`);
  } catch (error) {
    const duration = Date.now() - startTime;
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    await updateScrapeJob(job.id, {
      success: false,
      itemsScraped: 0,
      errors: [errorMessage],
      duration,
    });
    console.error('❌ [SCRAPER] Scryfall sync failed:', error);
  }
}

/**
 * EDHREC scraping job - runs weekly
 * Scrapes top commanders and synergy data
 */
async function runEDHRECJob() {
  console.log('\n🔄 [SCRAPER] Starting EDHREC scraping job...');
  const startTime = Date.now();
  const job = await createScrapeJob('edhrec');

  try {
    const data = await scrapeEDHREC();
    let itemsScraped = data.topCommanders?.length || 0;

    // Also pull synergy details for top 5 commanders
    for (const cmd of (data.topCommanders || []).slice(0, 5)) {
      if (cmd.url) {
        const details = await scrapeCommanderDetails(cmd.url);
        itemsScraped += details.synergies?.length || 0;
      }
    }

    const duration = Date.now() - startTime;
    await updateScrapeJob(job.id, {
      success: true,
      itemsScraped,
      errors: [],
      duration,
    });
    console.log(`✅ [SCRAPER] EDHREC job completed: ${itemsScraped} items in ${(duration / 1000).toFixed(1)}s`);
  } catch (error) {
    const duration = Date.now() - startTime;
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    await updateScrapeJob(job.id, {
      success: false,
      itemsScraped: 0,
      errors: [errorMessage],
      duration,
    });
    console.error('❌ [SCRAPER] EDHREC job failed:', error);
  }
}

/**
 * MTGTop8 scraping job - runs every 3 days
 */
async function runMTGTop8Job() {
  console.log('\n🔄 [SCRAPER] Starting MTGTop8 scraping job...');
  const startTime = Date.now();
  const job = await createScrapeJob('mtgtop8');

  try {
    const data = await scrapeMTGTop8();
    const itemsScraped = data.recentDecks?.length || 0;
    const duration = Date.now() - startTime;

    await updateScrapeJob(job.id, {
      success: true,
      itemsScraped,
      errors: [],
      duration,
    });
    console.log(`✅ [SCRAPER] MTGTop8 job completed: ${itemsScraped} items in ${(duration / 1000).toFixed(1)}s`);
  } catch (error) {
    const duration = Date.now() - startTime;
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    await updateScrapeJob(job.id, {
      success: false,
      itemsScraped: 0,
      errors: [errorMessage],
      duration,
    });
    console.error('❌ [SCRAPER] MTGTop8 job failed:', error);
  }
}

/**
 * Moxfield scraping job - runs daily
 */
async function runMoxfieldJob() {
  console.log('\n🔄 [SCRAPER] Starting Moxfield scraping job...');
  const startTime = Date.now();
  const job = await createScrapeJob('moxfield');

  try {
    const data = await scrapeMoxfield();
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
    console.log(`✅ [SCRAPER] Moxfield job completed: ${itemsScraped} items in ${(duration / 1000).toFixed(1)}s`);
  } catch (error) {
    const duration = Date.now() - startTime;
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    await updateScrapeJob(job.id, {
      success: false,
      itemsScraped: 0,
      errors: [errorMessage],
      duration,
    });
    console.error('❌ [SCRAPER] Moxfield job failed:', error);
  }
}

export function initializeScheduledJobs() {
  if (schedulerInitialized) return {};
  schedulerInitialized = true;

  console.log('🚀 Initializing background scheduled scraping jobs...');

  // Scryfall New Releases: Every day at 4:00 AM
  const scryfallJob = schedule.scheduleJob('0 0 4 * * *', () => {
    runScryfallJob();
  });

  // EDHREC: Every Sunday at 3:00 AM
  const edhrecJob = schedule.scheduleJob('0 0 3 * * 0', () => {
    runEDHRECJob();
  });

  // MTGTop8: Every 3 days at 2:00 AM
  const mtgtop8Job = schedule.scheduleJob('0 0 2 */3 * *', () => {
    runMTGTop8Job();
  });

  // Moxfield: Every day at 1:00 AM
  const moxfieldJob = schedule.scheduleJob('0 0 1 * * *', () => {
    runMoxfieldJob();
  });

  console.log('✅ Scheduled jobs active: Scryfall (daily 4AM), Moxfield (daily 1AM), MTGTop8 (every 3d), EDHREC (Sun 3AM)');

  return {
    scryfall: scryfallJob,
    edhrec: edhrecJob,
    mtgtop8: mtgtop8Job,
    moxfield: moxfieldJob,
  };
}

export async function runJobNow(jobType: 'scryfall' | 'edhrec' | 'mtgtop8' | 'moxfield') {
  switch (jobType) {
    case 'scryfall':
      await runScryfallJob();
      break;
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

export async function getJobHistory(limit = 50) {
  return await prisma.scrapeJob.findMany({
    orderBy: { startedAt: 'desc' },
    take: limit,
  });
}

export async function getJobStats(jobType: string) {
  const jobs = await prisma.scrapeJob.findMany({
    where: { jobType },
    orderBy: { startedAt: 'desc' },
    take: 10,
  });

  const completed = jobs.filter((j) => j.status === 'completed').length;
  const failed = jobs.filter((j) => j.status === 'failed').length;
  const avgDuration =
    jobs.filter((j) => j.duration).reduce((sum, j) => sum + (j.duration || 0), 0) / jobs.length || 0;
  const totalItemsScraped = jobs.reduce((sum, j) => sum + j.itemsScraped, 0);

  return {
    jobType,
    totalRuns: jobs.length,
    completed,
    failed,
    successRate: jobs.length > 0 ? ((completed / jobs.length) * 100).toFixed(1) + '%' : '0%',
    avgDuration: `${(avgDuration / 1000).toFixed(1)}s`,
    totalItemsScraped,
    lastRun: jobs[0]?.startedAt,
    lastStatus: jobs[0]?.status,
  };
}
