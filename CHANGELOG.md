# Changelog

All notable changes to the JankBuild (`magicapp`) MTG Commander Deck Builder + Local AI project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-11-04

### Added
- **Version Numbering & UI Badge**: Introduced project versioning (`v0.1.0`) with visual indicators across desktop and mobile navigation headers and `APP_VERSION` in `src/lib/constants.ts`.
- **Restored & Expanded Theme Archetypes**: Restored and expanded the full suite of 30 Commander themes in the deck builder dropdown, including:
  - `Hatebears` (taxing and disruptive low-curve creatures like Grand Abolisher, Yasharn, Thalia, Drannith Magistrate)
  - `+1/+1 Counters` (counter placement, proliferate, modular, and mentor value engines)
  - `Blink / Flicker` (ETB value engines, flicker recursion, and exile triggers)
  - `Graveyard Matters` (self-mill, dredge, delve, and flashback)
  - `Wheels` (windfall and wheel punishment)
  - `Equipment` (Voltron attachments and combat triggers)
  - `Enchantments / Enchantress` (constellation, auras, and enchantress card-draw engines)
  - `Lands Matter / Landfall` (landfall and land sacrifice triggers)
  - `Infect / Toxic` (poison counters and proliferation)
  - `Theft / Clones` (graveyard theft and copy effects)
  - `Treasure / Big Mana` (treasure generation and high-cost spells)
  - `Chaos`, `Mill`, `Lifegain`, `Superfriends`, `Group Hug`, `Group Slug`
- **Dynamic Creature Quotas**: Added adaptive creature targets in `ollama.ts` to ensure creature-heavy strategies (Hatebears, +1/+1 Counters, Aggro, Tokens) build with 28+ creatures.
- **High-Performance Card Importer (`scripts/import-mtgjson-fast.py`)**: Batched SQLite transactions importing MTGJSON card databases in under 3 seconds.
- **Card Database Expansion**: Upgraded database to MTGJSON 5.3.0 (`2026-11-04`) containing **37,756 cards** and **6,264 commanders** (supporting new sets including *Vraska, Soul of Stone*).
- **On-Demand EDHREC Synergy Fetching & Caching**: Added automatic on-the-fly fetching from `json.edhrec.com` whenever a commander with 0 synergies is queried, persisting positive synergy ratings directly to `prisma.cardSynergy`.

### Changed
- **Ollama Commander Recommendation Deduplication**:
  - Deduplicated commander recommendation candidates so all 5 suggestions are distinct.
  - Excluded digital-only Arena variants (`A-*`) and cleaned split-card names (`//`) for paper Commander legality.
- **Local AI Inference Endpoint**: Updated local AI connectivity to point to the dedicated Vulkan-accelerated Intel Arc A380 LXC (`ai-arc-01`, `192.168.0.228:11434`).

### Fixed
- **Strict 100-Card Deck Guarantee**:
  - Fixed a bug where dual lands and multi-color utility lands were misclassified as non-land ramp pieces, consuming non-land slots and subsequently being dropped during category grouping (resulting in 99-card deck builds).
  - Enforced strict category isolation (`category !== 'lands'`) across all role extractors and candidate selection loops.
  - Implemented dynamic land count calculation (`targetLands = 100 - 1 - nonLandTotal`) and a hard invariant top-up/trim mechanism ensuring every generated decklist has exactly 100 cards.
- **Docker Compose Health Check**: Changed health check target from `localhost:3000` to `127.0.0.1:3000` to prevent Alpine IPv6 connection refused false positives.
