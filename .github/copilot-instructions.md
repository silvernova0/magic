<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

## Project Overview
**JankBuild** (jankbuild.com) - An AI-powered Commander/EDH deck builder with comprehensive collection management. A Next.js application that generates Commander decks using AI and local card database.

## Key Features
- **Local Card Database**: 31,483 cards from MTGJson with EDHREC rankings, saltiness scores, power levels (0-10), and 20+ auto-generated tags
- **AI Deck Builder**: Gemini-powered deck generation with EDHREC/MTGTop8/Moxfield context
- **Card Browser**: Advanced filtering by tags, type, color identity, power level, saltiness
- **Deck Display**: Shows power levels, saltiness warnings, game-changer badges for each card
- **Commander Autocomplete**: Local database search (replaces Scryfall)

## Tech Stack
- **Frontend**: Next.js 15.5.4 (App Router), React, TypeScript, TailwindCSS
- **Backend**: Prisma + SQLite, Next.js API Routes
- **AI**: Google Gemini 2.0 Flash Thinking Experimental
- **Data**: MTGJson 5.2.2, EDHREC integration
- **UI Components**: shadcn/ui, Radix UI, Lucide React

## Database Setup
1. Download MTGJson files from https://mtgjson.com/downloads/all-files/
2. Required: `AtomicCards.json` (~50MB)
3. Optional: `AllPrintings.json` (~500MB)
4. Place in `data/mtgjson/` directory
5. Run: `npm run import:mtgjson:full`
6. Import takes 2-3 minutes, creates 31,483 card records

## Project Structure
- `/src/app/` - Next.js App Router pages
- `/src/components/` - React components
- `/src/lib/` - Utilities (gemini.ts, prisma.ts)
- `/scripts/` - Import scripts
- `/prisma/` - Database schema
- `/data/mtgjson/` - Card data (gitignored)

## API Endpoints
- `GET /api/cards/search` - Advanced card search (15+ filters)
- `GET /api/cards/[nameOrId]` - Single card with metadata
- `POST /api/commander/build` - AI deck generation
- `POST /api/commander/suggest` - Commander suggestions

## Card Database Tags
**Mechanical**: card-draw, tutor, removal, ramp, counterspell, token, graveyard, sacrifice, extra-turns, copy, storm, cascade, exile
**Power Level**: game-changer, high-salt, top-100, top-500, top-1000, reserved-list
**Leadership**: commander, brawl
**Type**: creature, instant, sorcery, enchantment, artifact, planeswalker, land

## Power Level Scale (0-10)
- **8-10** (Red): cEDH staples (Mana Crypt, Timetwister, Gaea's Cradle)
- **6-7.9** (Orange): Optimized (Rhystic Study, Cyclonic Rift)
- **4-5.9** (Yellow): Focused (Arcane Signet, Cultivate)
- **0-3.9** (Green): Casual/Budget

## Saltiness Scale
- **≥2.0** (Red): Extremely salty (Armageddon, Winter Orb)
- **1.0-1.9** (Orange): High salt (Rhystic Study, Grand Arbiter)
- **0.5-0.9** (Yellow): Moderate salt (Cyclonic Rift)
- **<0.5** (Green): Low salt

## Development Commands
- `npm run dev` - Start dev server
- `npm run build` - Build for production
- `npm run import:mtgjson:full` - Import card database
- `npx prisma studio` - View database GUI
- `npx prisma migrate dev` - Run migrations

## Git Workflow
- JSON files in `data/mtgjson/` are gitignored (too large)
- Users download and import locally
- Keep commits focused and descriptive

## Documentation Files
- `CARD_DATABASE.md` - Card database features and API
- `LOCAL_CARDS_INTEGRATION.md` - Deck builder integration details
- `GEMINI_SETUP_COMPLETE.md` - AI deck builder setup
- `GEMINI_DECK_BUILDER.md` - Deck builder usage guide

## Next Steps
1. ✅ Local card database integrated into deck builder
2. Enhance EDHREC scraper (synergy data, combos)
3. Enhance MTGTop8 scraper (complete decklists)
4. Enhance Moxfield scraper (all brackets)
5. Scheduled scraping (cron jobs)
6. Research Intel OpenVINO for local AI (long-term)

## Code Style
- Use TypeScript strict mode
- Prefer async/await over promises
- Use Prisma for all database queries
- Keep components focused and reusable
- Document complex functions with JSDoc
- Use semantic HTML and ARIA labels

