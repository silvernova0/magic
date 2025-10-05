import * as cheerio from 'cheerio';
import { fetchWithCache } from './cache';

export type ParsedDeck = {
  title: string;
  url: string;
  cards: { name: string; qty: number }[];
};

export async function fetchEdhrecCommanderPage(commanderName: string): Promise<string | null> {
  const slug = commanderName.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
  const url = `https://edhrec.com/commanders/${encodeURIComponent(slug)}`;
  try {
    const txt = await fetchWithCache(url, 'edhrec', 60 * 60 * 24);
    return String(txt);
  } catch (err) {
    return null;
  }
}

export function parseEdhrecCommanderPage(html: string): string[] {
  const $ = cheerio.load(html);
  const links: string[] = [];

  $('a').each((i: number, el: any) => {
    const href = $(el).attr('href');
    if (!href) return;
    if (/tappedout\.net|mtggoldfish\.com|archidekt\.com|deckstats\.net|moxfield\.com/.test(href)) {
      if (href.startsWith('http')) links.push(href);
      else links.push(new URL(href, 'https://edhrec.com').toString());
    }
  });

  return Array.from(new Set(links));
}

export async function fetchDeckFromUrl(url: string): Promise<ParsedDeck | null> {
  try {
    const html = String(await fetchWithCache(url, 'decksource', 60 * 60 * 24));
    if (url.includes('tappedout.net')) return parseTappedOut(html, url);
    if (url.includes('mtggoldfish.com')) return parseMTGGoldfish(html, url);
    if (url.includes('archidekt.com')) return parseArchidekt(html, url);
    if (url.includes('moxfield.com')) return parseMoxfield(html, url);

    const cards: { name: string; qty: number }[] = [];
    const lines = html.split(/\r?\n/);
    for (const line of lines) {
      const match = line.replace(/<[^>]*>/g, '').match(/^(\d+)\s+([A-Za-z0-9'",. \-\(\)]+)/);
      if (match) {
        cards.push({ qty: parseInt(match[1]), name: match[2].trim() });
      }
    }
    return { title: url, url, cards };
  } catch (err) {
    return null;
  }
}

function parseTappedOut(html: string, url: string): ParsedDeck | null {
  const $ = cheerio.load(html);
  const title = $('title').text() || url;
  const cards: { name: string; qty: number }[] = [];
  // tappedout places decklists in elements with class 'deck-list' or 'card'...
  $('li.card').each((i: number, el: any) => {
    const qty = parseInt($(el).find('.qty').text()) || 1;
    const name = $(el).find('.cardname').text().trim();
    if (name) cards.push({ name, qty });
  });
  // fallback search for lines
  if (!cards.length) {
    $('pre').each((i: number, el: any) => {
      const text = $(el).text();
      const lines = text.split(/\r?\n/);
      for (const line of lines) {
        const m = line.match(/^(\d+)\s+(.+)$/);
        if (m) cards.push({ qty: parseInt(m[1]), name: m[2].trim() });
      }
    });
  }

  return { title, url, cards };
}

function parseMTGGoldfish(html: string, url: string): ParsedDeck | null {
  const $ = cheerio.load(html);
  const title = $('h1').first().text() || url;
  const cards: { name: string; qty: number }[] = [];
  // mtggoldfish decklists usually have tables with class 'deck-view-deck-table'
  $('table').each((i: number, table: any) => {
    const header = $(table).prev('h3').text() || '';
    $(table).find('tr').each((j: number, tr: any) => {
      const qtyText = $(tr).find('td').first().text().trim();
      const name = $(tr).find('td').eq(1).text().trim();
      if (qtyText && name) {
        const qty = parseInt(qtyText) || 1;
        cards.push({ name, qty });
      }
    });
  });
  return { title, url, cards };
}

function parseArchidekt(html: string, url: string): ParsedDeck | null {
  const $ = cheerio.load(html);
  const title = $('title').text() || url;
  const cards: { name: string; qty: number }[] = [];
  // Archidekt often embeds JSON with deck data in a script tag
  const script = $('script[type="application/ld+json"]').text();
  if (script) {
    try {
      const json = JSON.parse(script);
      if (json && json.deck && Array.isArray(json.deck.cards)) {
        for (const c of json.deck.cards) {
          cards.push({ name: c.name, qty: c.qty || 1 });
        }
        return { title, url, cards };
      }
    } catch (err) {
      // ignore
    }
  }
  // fallback
  $('li.deck-card').each((i: number, el: any) => {
    const qty = parseInt($(el).find('.count').text()) || 1;
    const name = $(el).find('.card-name').text().trim();
    if (name) cards.push({ name, qty });
  });
  return { title, url, cards };
}

function parseMoxfield(html: string, url: string): ParsedDeck | null {
  const $ = cheerio.load(html);
  const title = $('title').text() || url;
  const cards: { name: string; qty: number }[] = [];
  // Moxfield often contains a script with window.__INITIAL_STATE__ containing deck data
  $('script').each((i: number, el: any) => {
    const text = $(el).html() || '';
    const match = text.match(/window\.__INITIAL_STATE__\s*=\s*(\{[\s\S]+\});/);
    if (match) {
      try {
        const obj = JSON.parse(match[1]);
        // attempt to find deck cards
        const deck = obj?.deck || obj?.currentDeck;
        if (deck && deck.cards) {
          for (const c of deck.cards) cards.push({ name: c.name, qty: c.qty || 1 });
        }
      } catch (err) {
        // ignore
      }
    }
  });
  return { title, url, cards };
}
