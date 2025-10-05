import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

// Simple rate limiter: allow one request per `intervalMs` by waiting between calls
let lastFetch = 0;
const intervalMs = 600; // ~100 requests per minute (adjustable)

async function rateLimitedFetch(url: string, options?: RequestInit) {
  const now = Date.now();
  const wait = Math.max(0, intervalMs - (now - lastFetch));
  if (wait > 0) await new Promise((r) => setTimeout(r, wait));
  lastFetch = Date.now();
  return fetch(url, options);
}

export async function fetchWithCache(url: string, source = 'unknown', ttlSeconds = 60 * 60 * 24) {
  // Check cache
  const cached = await prisma.deckCache.findUnique({ where: { url } });
  if (cached) {
    const age = (Date.now() - new Date(cached.fetchedAt).getTime()) / 1000;
    if (age < ttlSeconds) return cached.data;
  }

  // Fetch with rate limiting
  const res = await rateLimitedFetch(url);
  if (!res.ok) throw new Error(`Failed to fetch ${url}: ${res.status}`);
  const txt = await res.text();

  // Store in cache
  await prisma.deckCache.upsert({
    where: { url },
    update: { data: txt, fetchedAt: new Date() },
    create: { url, source, data: txt },
  });

  return txt;
}
