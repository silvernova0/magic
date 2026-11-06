#!/usr/bin/env python3
"""
Fast MTGJson AtomicCards Importer for JankBuild
Directly streams and upserts cards into prisma/dev.db using SQLite transaction batching.
"""

import json
import os
import re
import sqlite3
import time
import uuid

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'prisma', 'dev.db')
ATOMIC_PATH = os.path.join(BASE_DIR, 'data', 'mtgjson', 'AtomicCards.json')

def slugify(text: str) -> str:
    slug = re.sub(r'[^a-z0-9]+', '-', text.lower())
    return slug.strip('-')

def main():
    print("🎴 Fast MTGJson AtomicCards Database Importer")
    print(f"📁 Database: {DB_PATH}")
    print(f"📄 AtomicCards: {ATOMIC_PATH}")

    if not os.path.exists(ATOMIC_PATH):
        raise FileNotFoundError(f"AtomicCards.json not found at {ATOMIC_PATH}")

    start_time = time.time()
    now_ms = int(time.time() * 1000)

    print("\n📖 Reading AtomicCards.json...")
    with open(ATOMIC_PATH, 'r', encoding='utf-8') as f:
        payload = json.load(f)

    meta = payload.get('meta', {})
    cards_dict = payload.get('data', {})
    print(f"ℹ️  MTGJson Version: {meta.get('version')} ({meta.get('date')})")
    print(f"ℹ️  Unique Card Names: {len(cards_dict):,}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Pre-optimize SQLite for bulk import
    cursor.execute("PRAGMA synchronous = NORMAL;")
    cursor.execute("PRAGMA journal_mode = WAL;")

    upsert_sql = """
    INSERT INTO Card (
        id, oracleId, name, manaCost, cmc, colors, colorIdentity,
        typeLine, oracleText, power, toughness, loyalty, keywords,
        legalities, rarity, setCode, setName, collectorNumber,
        imageUris, prices, edhrecRank, edhrecSaltiness, artist,
        flavorText, releasedAt, isCommander, createdAt, updatedAt
    ) VALUES (
        ?, ?, ?, ?, ?, ?, ?,
        ?, ?, ?, ?, ?, ?,
        ?, ?, ?, ?, ?,
        ?, ?, ?, ?, ?,
        ?, ?, ?, ?, ?
    )
    ON CONFLICT(id) DO UPDATE SET
        oracleId = COALESCE(excluded.oracleId, Card.oracleId),
        name = excluded.name,
        manaCost = excluded.manaCost,
        cmc = excluded.cmc,
        colors = excluded.colors,
        colorIdentity = excluded.colorIdentity,
        typeLine = excluded.typeLine,
        oracleText = excluded.oracleText,
        power = excluded.power,
        toughness = excluded.toughness,
        loyalty = excluded.loyalty,
        keywords = excluded.keywords,
        legalities = excluded.legalities,
        prices = COALESCE(excluded.prices, Card.prices),
        edhrecRank = COALESCE(excluded.edhrecRank, Card.edhrecRank),
        edhrecSaltiness = COALESCE(excluded.edhrecSaltiness, Card.edhrecSaltiness),
        isCommander = excluded.isCommander,
        updatedAt = excluded.updatedAt
    ;
    """

    records = []
    skipped_funny = 0
    commander_count = 0

    for name, printings in cards_dict.items():
        if not printings:
            continue
        c = printings[0]

        # Filter out funny / silver-border cards
        if c.get('isFunny'):
            skipped_funny += 1
            continue

        card_id = slugify(name)
        if not card_id:
            continue

        type_line = c.get('type') or ''
        text = c.get('text') or ''
        leadership = c.get('leadership') or {}

        is_commander = (
            leadership.get('commander') is True
            or c.get('isCommander') is True
            or ('Legendary' in type_line and 'Creature' in type_line)
            or ('can be your commander' in text.lower())
        )
        if is_commander:
            commander_count += 1

        identifiers = c.get('identifiers') or {}
        oracle_id = identifiers.get('scryfallOracleId')

        colors_str = ','.join(c.get('colors') or [])
        color_id_str = ','.join(c.get('colorIdentity') or [])
        keywords_str = ','.join(c.get('keywords') or []) if c.get('keywords') else None
        legalities_str = json.dumps(c.get('legalities') or {})
        prices_str = json.dumps(c.get('purchaseUrls')) if c.get('purchaseUrls') else None

        records.append((
            card_id,
            oracle_id,
            name,
            c.get('manaCost'),
            float(c.get('manaValue') or 0.0),
            colors_str,
            color_id_str,
            type_line,
            text if text else None,
            c.get('power'),
            c.get('toughness'),
            c.get('loyalty'),
            keywords_str,
            legalities_str,
            'common',
            'atomic',
            'Atomic',
            '1',
            None,
            prices_str,
            c.get('edhrecRank'),
            c.get('edhrecSaltiness'),
            None,
            None,
            None,
            1 if is_commander else 0,
            now_ms,
            now_ms
        ))

    print(f"📦 Prepared {len(records):,} cards for upsert (skipped {skipped_funny:,} funny cards)")
    print(f"👑 Legal / potential commanders identified: {commander_count:,}")

    print("💾 Executing SQLite transaction...")
    cursor.executemany(upsert_sql, records)

    duration_ms = int((time.time() - start_time) * 1000)

    # Record scrape job
    job_id = f"job-{uuid.uuid4().hex[:12]}"
    cursor.execute("""
    INSERT INTO ScrapeJob (id, jobType, status, itemsScraped, startedAt, completedAt, duration)
    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, ?)
    """, (job_id, 'mtgjson-atomic', 'completed', len(records), duration_ms))

    conn.commit()

    # Query statistics
    cursor.execute("SELECT count(*) FROM Card;")
    total_db_cards = cursor.fetchone()[0]

    cursor.execute("SELECT count(*) FROM Card WHERE isCommander = 1;")
    total_db_commanders = cursor.fetchone()[0]

    conn.close()

    elapsed = time.time() - start_time
    print(f"\n✅ Import completed in {elapsed:.2f}s!")
    print("📊 Final Database Statistics:")
    print(f"   Total cards in dev.db: {total_db_cards:,}")
    print(f"   Commanders in dev.db: {total_db_commanders:,}")

if __name__ == '__main__':
    main()
