/**
 * Scraper orchestrator - coordinates all scrapers and manages caching
 */

import { promises as fs } from 'fs';
import path from 'path';
import { scrapeEDHREC } from './edhrec';
import { scrapeMTGTop8 } from './mtgtop8';
import { scrapeMoxfield } from './moxfield';
import { ScrapedData } from './types';

// Allow overriding cache root via env; default remains .cache in project root
const CACHE_ROOT = process.env.SCRAPER_CACHE_DIR || path.join(process.cwd(), '.cache');
const CACHE_DIR = path.join(CACHE_ROOT, 'scrapers');
const CACHE_FILE = path.join(CACHE_DIR, 'data.json');
const CACHE_TTL_HOURS = 6; // Refresh every 6 hours

/**
 * Get scraped data from cache or fetch fresh data
 */
export async function getScrapedData(forceRefresh = false): Promise<ScrapedData> {
  // Try to load from cache first
  if (!forceRefresh) {
    const cached = await loadFromCache();
    if (cached && !isCacheExpired(cached)) {
      console.log('Using cached scraper data');
      return cached;
    }
  }

  // Fetch fresh data
  console.log('Fetching fresh scraper data...');
  const data = await scrapeAllSources();
  
  // Save to cache
  await saveToCache(data);
  
  return data;
}

/**
 * Scrape all sources in parallel
 */
async function scrapeAllSources(): Promise<ScrapedData> {
  const results = await Promise.allSettled([
    scrapeEDHREC(),
    scrapeMTGTop8(),
    scrapeMoxfield(),
  ]);

  const data: ScrapedData = {
    timestamp: new Date(),
  };

  // EDHREC
  if (results[0].status === 'fulfilled') {
    data.edhrec = results[0].value;
  } else {
    console.error('EDHREC scraping failed:', results[0].reason);
  }

  // MTGTop8
  if (results[1].status === 'fulfilled') {
    data.mtgtop8 = results[1].value;
  } else {
    console.error('MTGTop8 scraping failed:', results[1].reason);
  }

  // Moxfield
  if (results[2].status === 'fulfilled') {
    data.moxfield = results[2].value;
  } else {
    console.error('Moxfield scraping failed:', results[2].reason);
  }

  return data;
}

/**
 * Load data from cache file
 */
async function loadFromCache(): Promise<ScrapedData | null> {
  try {
    const data = await fs.readFile(CACHE_FILE, 'utf-8');
    const parsed = JSON.parse(data);
    
    // Convert timestamp string back to Date
    parsed.timestamp = new Date(parsed.timestamp);
    if (parsed.edhrec) parsed.edhrec.lastUpdated = new Date(parsed.edhrec.lastUpdated);
    if (parsed.mtgtop8) parsed.mtgtop8.lastUpdated = new Date(parsed.mtgtop8.lastUpdated);
    if (parsed.moxfield) parsed.moxfield.lastUpdated = new Date(parsed.moxfield.lastUpdated);
    
    return parsed;
  } catch (error) {
    // Cache doesn't exist or is invalid
    return null;
  }
}

/**
 * Save data to cache file
 */
async function saveToCache(data: ScrapedData): Promise<void> {
  try {
    await fs.mkdir(CACHE_DIR, { recursive: true });
    await fs.writeFile(CACHE_FILE, JSON.stringify(data, null, 2));
    console.log('Scraper data cached successfully');
  } catch (error) {
    console.error('Error saving cache:', error);
  }
}

/**
 * Check if cache is expired
 */
function isCacheExpired(data: ScrapedData): boolean {
  const now = Date.now();
  const cacheAge = now - data.timestamp.getTime();
  const maxAge = CACHE_TTL_HOURS * 60 * 60 * 1000;
  
  return cacheAge > maxAge;
}

/**
 * Get cache status
 */
export async function getCacheStatus(): Promise<{
  exists: boolean;
  age?: number;
  expired?: boolean;
  lastUpdated?: Date;
}> {
  const cached = await loadFromCache();
  
  if (!cached) {
    return { exists: false };
  }

  const age = Date.now() - cached.timestamp.getTime();
  const expired = isCacheExpired(cached);

  return {
    exists: true,
    age,
    expired,
    lastUpdated: cached.timestamp,
  };
}

/**
 * Clear cache
 */
export async function clearCache(): Promise<void> {
  try {
    await fs.unlink(CACHE_FILE);
    console.log('Cache cleared');
  } catch (error) {
    // Cache file doesn't exist
  }
}
