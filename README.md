# 🎴 JankBuild - MTG Commander Deck Builder

An AI-powered Commander/EDH deck builder with intelligent strategy-based card selection, comprehensive collection management, and user feedback system. Built with Next.js 15, React 19, and powered by Google Gemini AI + EDHREC data.

## 🎯 Core Features

### ✨ AI-Powered Deck Building
- **Google Gemini 2.5 Flash** - Primary AI engine for intelligent deck construction
- **EDHREC Integration** - 2,557 commanders with popularity data and card synergies
- **Strategy-Aware Selection** - 8 archetypes: Mill, Graveyard/Reanimator, Voltron/Equipment, Combo, Tokens, Control, Tribal, Default
- **Smart Card Deduplication** - 5x query multiplier ensures enough strategy cards
- **Priority Card System** - EDHREC-recommended cards intelligently replace similar cards
- **Universal Staples** - Auto-includes Sol Ring, Arcane Signet, Command Tower (color-dependent)
- **Salt Avoidance** - Optional filter for high-saltiness cards (Stasis, Winter Orb, etc.)

### 🎴 Deck Configuration
- **8 Strategy Archetypes** - Mill, Graveyard, Voltron, Combo, Tokens, Control, Tribal, Generic
- **Color Filtering** - Build within specific colors that intersect with commander identity
- **Power Level Brackets** - 1 (Precon) to 5 (cEDH) with randomized land counts for brackets 1-3
- **Collection Mode** - Build from owned cards only OR use entire database
- **Commander Selection** - Specify commander or use "Surprise Me!" for AI suggestions
- **Land Randomization** - Brackets 1-3 get 35-40 lands randomly, Brackets 4-5 get consistent 35

### 👥 User Features
- **Authentication** - Secure login/registration with NextAuth.js + bcrypt
- **Per-User Collections** - Import cards via CSV or bulk text (CSV export, Archidekt, Moxfield formats)
- **Collection Management** - Track quantities, search, filter by colors/types/rarity
- **Deck Saving** - Save generated decks with custom names
- **Role-Based Access** - USER and ADMIN roles with protected routes
- **Email Notifications** - Welcome emails (SMTP configurable, works with Mailcow)
- **Feedback System** - Users can submit bug reports, feature requests, and deck issues

### 📊 Admin Dashboard (`/admin`)
- **User Management** - View all users with card/deck counts
- **Role Control** - Promote users to ADMIN or demote to USER
- **Email Configuration** - Test SMTP settings and send test emails
- **Feedback Viewer** - Review all user-submitted feedback with type filtering
- **User Statistics** - Join dates, collection sizes, deck counts

### 🎴 Local Card Database (31,483 Cards)
- **MTGJson AtomicCards** - Complete unique card database with all printings
- **EDHREC Rankings** - Popularity rankings for 31k+ cards
- **Saltiness Scores** - Community-driven "feel bad" ratings (filters > 2.0)
- **Auto-Generated Tags** - 20+ tag types:
  - Strategy: `ramp`, `card_draw`, `removal`, `protection`, `board_wipe`, `tutor`
  - Archetype: `mill`, `lifegain`, `graveyard`, `tokens`, `sacrifice`
  - Impact: `game_changer`, `high_salt`, `combo_piece`
- **Power Level Scoring** - Automatic 0-10 calculation based on EDHREC + tags
- **Commander Validation** - Legal commander detection and format legalities
- **Advanced Filtering** - Search by name, oracle text, colors, color identity, types, keywords, CMC, rarity, EDHREC rank, saltiness
- **Python Deck Builder** - Smart card selection with type-matching replacement logic

## 🚀 Quick Start

### Prerequisites
- Node.js 18+ (project uses v18.19.1)
- Python 3.8+ (for deck builder script and training)
- SQLite3 (included with most systems)

### Development Setup
```bash
# 1. Clone repository
git clone https://github.com/silvernova0/magic.git
cd magic

# 2. Install dependencies
npm install

# 3. Setup environment variables
cp .env.example .env
# Edit .env with your settings (see Environment Variables section below)

# 4. Generate Prisma client and setup database
npx prisma generate
npx prisma db push

# 5. Import card database (REQUIRED - 31,483 cards)
npm run import:mtgjson:full
# Downloads AtomicCards.json, imports with EDHREC data, generates tags
# Takes ~2-3 minutes

# 6. Create admin user
npm run create-admin
# Or: npm run create-admin your@email.com YourPassword "Your Name"

# 7. Start development server
npm run dev
# Access at http://localhost:3000
```

### Production Deployment

#### 🏠 Self-Hosting (Recommended for full control)
**5-minute setup with Docker + Nginx Proxy Manager:**

```powershell
# Windows Quick Start
.\setup.ps1

# Or manually with Docker:
docker-compose build
docker-compose up -d
# Access at http://localhost:3050

# Or with Node.js:
npm ci && npm run build && npm run start
```

**📖 Complete Self-Hosting Guide:** See `QUICK_START.md` and `SELF_HOSTING.md`

#### ☁️ Cloud Hosting (Vercel)
```bash
# Deploy to Vercel
vercel deploy --prod
```

**📖 Cloud Deployment Guide:** See `DEPLOYMENT_CHECKLIST.md`

### Environment Variables (.env)

**Minimum required for development:**
```env
# Database
DATABASE_URL="file:./prisma/dev.db"

# Auth (generate secret with: openssl rand -base64 32)
NEXTAUTH_SECRET=your_random_secret_here
NEXTAUTH_URL=http://localhost:3000

# Google Gemini AI (REQUIRED for deck building)
GEMINI_API_KEY=your_gemini_api_key_here
```

**Optional - Email notifications (Mailcow, Gmail, etc.):**
```env
EMAIL_HOST=mail.yourdomain.com
EMAIL_PORT=587
EMAIL_SECURE=false  # false for 587 (STARTTLS), true for 465 (SSL)
EMAIL_USER=noreply@yourdomain.com
EMAIL_PASSWORD=your_smtp_password
EMAIL_FROM=noreply@yourdomain.com
```

**Getting a Gemini API Key:**
1. Visit [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Click "Get API Key"
3. Create new key or use existing project
4. Copy key to `.env` file

4. **Download MTGJson card data**

Visit [https://mtgjson.com/downloads/all-files/](https://mtgjson.com/downloads/all-files/) and download:
- `AtomicCards.json` (Required - ~50MB, unique cards only)
- `AllPrintings.json` (Optional - ~500MB, all printings)

Place the downloaded files in `data/mtgjson/` directory:
```bash
mkdir -p data/mtgjson
# Move downloaded JSON files to data/mtgjson/
```

5. **Set up database**
```bash
npx prisma generate
npx prisma db push

# Import MTGJson card database (31,000+ cards with EDHREC data)
npm run import:mtgjson:full

# This will:
# - Import 31,483 unique cards from AtomicCards.json
# - Add EDHREC rankings and saltiness scores
# - Generate 20+ tag types (game-changer, removal, tutor, etc.)
# - Calculate power levels (0-10 scale)
# - Takes ~2-3 minutes
```

6. **Create admin user**
```bash
npm run create-admin
# Or with custom credentials:
npm run create-admin your@email.com password123 "Your Name"
```

7. **Run development server**
```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser.

## 🎮 Usage

### Building Your First Deck

1. **Navigate to Deck Builder** - Click "Deck Builder" in sidebar or visit `/deckbuilder`

2. **Configure Deck Settings:**
   - **Commander**: Type commander name or click "Surprise Me!" for AI suggestion
   - **Strategy**: Select from 8 archetypes (Mill, Graveyard, Voltron, Combo, Tokens, Control, Tribal, or Default)
   - **Colors**: Choose specific colors to filter cards (intersects with commander identity)
   - **Power Level**: Select bracket 1-5 (affects land count, card selection, combo density)
   - **Collection Mode**: ☐ Use only cards from your collection
   - **Salt Avoidance**: ☐ Avoid high-saltiness cards (Stasis, Winter Orb, etc.)

3. **Build Deck** - Click "Build My Commander Deck"
   - AI processes your request with EDHREC context
   - Python script selects cards with strategy-aware filters
   - Staples auto-included (Sol Ring + color-dependent Arcane Signet/Command Tower)
   - Priority EDHREC cards replace similar non-staples

4. **Review Generated Deck:**
   - 100 cards total (99 + commander OR 98 + 2 commanders)
   - Lands: 35-40 (randomized for brackets 1-3), 35 (fixed for brackets 4-5)
   - Strategy cards: Mill effects, lifegain, removal, ramp, card draw, etc.
   - Organized by card type with quantities

5. **Save Deck** (optional):
   - Click "Save Deck"
   - Enter custom name
   - View in "My Decks" section

### Managing Your Collection

1. **Go to Collection** - Click "Collection" in sidebar or visit `/collection`

2. **Import Cards** - Three methods:
   - **CSV Upload**: Export from Archidekt, Moxfield, Deckbox, or custom format
   - **Bulk Text**: Paste deck list with quantities (e.g., "2x Sol Ring")
   - **Manual Entry**: Search and add individual cards

3. **CSV Format Support:**
   ```csv
   Count,Name,Edition,Condition,Language,Foil
   1,Sol Ring,Commander 2021,Near Mint,English,Normal
   3,Island,Foundations,Near Mint,English,Normal
   ```

4. **View and Filter:**
   - Search by card name or text
   - Filter by colors (W/U/B/R/G)
   - Filter by card types (Creature, Instant, etc.)
   - Filter by rarity (Common, Uncommon, Rare, Mythic)
   - View total card count and collection value

5. **Build from Collection:**
   - Enable "Use Collection Only" in Deck Builder
   - Deck will only use cards you own
   - Preserves collection quantities

### Providing Feedback

1. **Click "Provide Feedback"** - Floating button at bottom-center of any page

2. **Select Feedback Type:**
   - 🐛 Bug Report - Report issues or errors
   - 💡 Feature Request - Suggest new features
   - 🎴 Deck Issue - Report deck building problems
   - 💬 General Feedback - Other comments

3. **Write Message** - Describe your feedback in detail

4. **Optional Email** - Provide email if you want a response

5. **Submit** - Feedback sent to admin dashboard

### Admin Functions (Admin Users Only)

1. **Access Admin Panel** - Visit `/admin` (requires ADMIN role)

2. **User Management:**
   - View all registered users
   - See card/deck counts per user
   - Promote USER → ADMIN
   - Demote ADMIN → USER

3. **Email Configuration** (`/admin/email`):
   - Configure SMTP settings
   - Send test emails
   - Verify email delivery

4. **View Feedback:**
   - See all user submissions
   - Filtered by type (Bug, Feature, Deck Issue, General)
   - Track submitter (user account, email, or anonymous)
   - View submission timestamps and page context

## �️ Tech Stack

### Frontend
- **Next.js 15.5.4** - React framework with App Router
- **React 19** - UI library with Server Components
- **TailwindCSS 4** - Utility-first CSS framework
- **Shadcn/UI** - Component library (Button, Card, Dialog, Select, Input, Textarea, Tabs, Label, Alert, Badge)
- **TypeScript 5** - Type safety

### Backend
- **Next.js API Routes** - RESTful API endpoints
- **Server Actions** - Form handling and mutations
- **Prisma 6.16** - ORM with type-safe queries
- **SQLite** - Local database (31,483 cards, ~39MB)
- **NextAuth.js** - Authentication with session management
- **bcrypt** - Password hashing

### AI & Data
- **Google Gemini 2.5 Flash** - Primary AI engine for deck generation
- **Python 3** - Deck builder script (`scripts/build-deck-from-structure.py`)
- **EDHREC Data** - 2,557 commanders with synergies (cached JSON)
- **MTGJson AtomicCards** - Complete card database with all printings

### External Integrations
- **Nodemailer** - Email service (SMTP support for Mailcow, Gmail, etc.)
- **CSV Parsing** - Bulk import support (Archidekt, Moxfield formats)

### Development Tools
- **ESLint** - Code linting
- **Prettier** (via Tailwind) - Code formatting
- **Git** - Version control

## 📖 Documentation

### Getting Started
- **[QUICK_START.md](QUICK_START.md)** - Fast setup for development
- **[.github/copilot-instructions.md](.github/copilot-instructions.md)** - Complete project architecture and workflows
- **[DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)** - Production deployment guide

### Features & Configuration
- **[GEMINI_DECK_BUILDER.md](GEMINI_DECK_BUILDER.md)** - Gemini AI integration details
- **[CARD_DATABASE.md](CARD_DATABASE.md)** - Card database schema and tagging system
- **[AUTHENTICATION_SETUP.md](AUTHENTICATION_SETUP.md)** - User authentication guide
- **[REGISTRATION_AND_ROLES.md](REGISTRATION_AND_ROLES.md)** - User roles and permissions

### AI Model Training (Optional)
- **[TRAINING_GUIDE.md](TRAINING_GUIDE.md)** - Complete v3 training documentation
- **[TRAINING_PROGRESS.md](TRAINING_PROGRESS.md)** - Training status and results
- **Local Model**: Fine-tuned Qwen 2.5 3B with LoRA adapters (optional alternative to Gemini API)

### Data Collection
- **[REAL_DATA_STRATEGY.md](REAL_DATA_STRATEGY.md)** - Data collection strategy
- **[SCHEDULED_SCRAPING.md](SCHEDULED_SCRAPING.md)** - Automated scraping (EDHREC, MTGGoldfish, Moxfield, Archidekt)

## 🤖 Local AI Model (Optional)

**Note**: The app works great with just the Gemini API. Local model training is **completely optional** for advanced users who want to experiment with custom AI models.

### v3 Training System (Current)
- **Model**: Qwen 2.5 3B Instruct with LoRA fine-tuning
- **Approach**: Structured JSON output (no card memorization)
- **Dataset**: 23,405 deck-derived examples
  - EDHREC average decks (2,557)
  - MTGGoldfish commander decks (12,334)
  - Moxfield theme decks (3,759)
  - Archidekt popular decks (4,289)
- **Training Time**: ~4-6 hours on Intel Arc B50 16GB
- **Status**: In testing - model learns deck-building patterns, database provides cards

### Quick Start Training (Advanced Users Only)
```bash
# 1. Activate virtualenv (REQUIRED)
source ~/.virtualenvs/magicapp/bin/activate

# 2. Set environment variables for Intel Arc GPU
export ACCELERATE_USE_XPU=1
export USE_XPU=1
export ONEAPI_DEVICE_SELECTOR=level_zero:*

# 3. Start v3 training
BATCH_SIZE=4 GRADIENT_ACCUMULATION_STEPS=8 MAX_SEQ_LENGTH=600 \
  nohup python3 scripts/train-v3-structured.py > training_v3.log 2>&1 &

# 4. Monitor progress
tail -f training_v3.log

# 5. Check GPU usage
sudo intel_gpu_top -J -s 200 | head -40
```

See **[TRAINING_GUIDE.md](TRAINING_GUIDE.md)** for complete training documentation and v2 legacy info.

## 📖 API Endpoints

### Deck Building
- `POST /api/commander/build-from-collection` - Build deck with AI (supports collection-only mode)
  - Body: `{ commander, strategy, colors, powerLevel, useCollectionOnly, avoidSaltCards }`
  - Returns: Complete 100-card deck with organized card types
- `GET /api/commander/search` - Search EDHREC commander database
  - Query: `q` (name search)
  - Returns: Matching commanders with colors and popularity
- `POST /api/commander/suggest` - Get AI commander suggestions
  - Body: `{ colors, strategy, powerLevel }`
  - Returns: Recommended commanders with explanations

### Decks
- `GET /api/decks` - List all public decks (12 most recent per category)
- `GET /api/user/decks` - List current user's decks
- `GET /api/decks/[id]` - Get specific deck details
- `POST /api/user/decks` - Save new deck
  - Body: `{ name, commanderName, decklist, theme, colors, powerLevel }`
- `DELETE /api/decks/[id]` - Delete user's deck
- `PATCH /api/decks/[id]` - Update deck details

### Card Database (31,483 Cards)
- `GET /api/cards/search` - Advanced card search with filters
  - Query params:
    - `q` - Name or oracle text search
    - `colors` - Exact color match (e.g., "WU" for Azorius)
    - `colorIdentity` - Color identity match
    - `types` - Card types (Creature, Instant, etc.)
    - `keywords` - Keyword abilities
    - `minCmc`, `maxCmc` - Mana cost range
    - `isCommander` - Legal commanders only
    - `minEdhrecRank`, `maxEdhrecRank` - Popularity range
    - `minSaltiness`, `maxSaltiness` - Saltiness range (0-4)
    - `rarity` - Common, Uncommon, Rare, Mythic
    - `sortBy` - name, cmc, edhrecRank, edhrecSaltiness
    - `sortOrder` - asc, desc
    - `limit`, `offset` - Pagination
  - Returns: Cards with tags, saltiness, power levels
- `GET /api/cards/[nameOrId]` - Get specific card
  - Returns: Full card details including tags array
- `GET /api/cards/lookup` - Lookup card by exact name
  - Query: `name` (exact match)

### Collection Management
- `GET /api/collection` - Get user's collection
- `POST /api/collection/add` - Add cards to collection
  - Body: `{ cardName, quantity }`
- `POST /api/import/collection` - Bulk import from CSV/text
  - Body: `{ format: 'csv' | 'text', data: string }`
- `DELETE /api/collection/[id]` - Remove card from collection

### Feedback System
- `POST /api/feedback` - Submit user feedback (public or authenticated)
  - Body: `{ type: 'BUG' | 'FEATURE_REQUEST' | 'DECK_ISSUE' | 'GENERAL', message, email?, page }`
- `GET /api/feedback` - Get all feedback (admin only)
  - Returns: All submissions with user info and timestamps

### Admin (Admin Role Required)
- `GET /api/admin/test-email` - Get current email config
- `POST /api/admin/test-email` - Send test email
  - Body: `{ to, subject, message }`
- `POST /api/admin/scrape` - Trigger manual scraping job

## 🧪 Development

### Available Commands
```bash
# Development
npm run dev              # Start dev server (http://localhost:3000)
npm run build            # Build for production
npm run start            # Start production server
npm run lint             # Run ESLint

# Database
npx prisma studio        # Open database GUI (http://localhost:5555)
npx prisma generate      # Regenerate Prisma client
npx prisma db push       # Push schema changes to database
npx prisma migrate dev   # Create migration

# Data Import
npm run import:mtgjson:full    # Import 31k cards with EDHREC data + tags

# Admin
npm run create-admin     # Create admin user interactively
npm run reset-password   # Reset user password
```

### Database Schema Overview
```prisma
model User {
  id        String      @id @default(cuid())
  email     String      @unique
  password  String
  name      String?
  role      Role        @default(USER)  // USER or ADMIN
  cards     UserCard[]  // Collection
  decks     Deck[]      // Saved decks
  feedback  Feedback[]  // Submitted feedback
}

model Card {
  id              String   @id @default(cuid())
  name            String
  oracleText      String?
  colors          String?  // JSON array ["W","U","B","R","G"]
  colorIdentity   String?  // JSON array
  types           String?  // JSON array ["Creature"]
  keywords        String?  // JSON array ["Flying","Haste"]
  cmc             Float?
  edhrecRank      Int?
  edhrecSaltiness Float?
  tags            String?  // JSON array ["ramp","card_draw","removal"]
  isCommander     Boolean  @default(false)
  // ... more fields
}

model Deck {
  id            String   @id @default(cuid())
  userId        String
  name          String
  commanderName String
  decklist      String   // Full deck text
  theme         String?
  colors        String?
  powerLevel    Int?
  user          User     @relation(fields: [userId], references: [id])
}

model Feedback {
  id        String        @id @default(cuid())
  userId    String?       // Optional - can be anonymous
  email     String?       // Optional contact email
  type      FeedbackType  // BUG, FEATURE_REQUEST, DECK_ISSUE, GENERAL
  message   String
  page      String?       // Page where submitted
  createdAt DateTime      @default(now())
  user      User?         @relation(fields: [userId], references: [id])
}
```

## 📦 Project Structure

```
magicapp/
├── .github/
│   └── copilot-instructions.md    # Complete project documentation
├── src/
│   ├── app/                        # Next.js App Router
│   │   ├── api/                   # API endpoints
│   │   │   ├── commander/        # Deck building APIs
│   │   │   ├── cards/            # Card search/lookup
│   │   │   ├── decks/            # Deck management
│   │   │   ├── collection/       # Collection management
│   │   │   ├── feedback/         # User feedback system
│   │   │   └── admin/            # Admin-only endpoints
│   │   ├── deckbuilder/          # Deck builder page
│   │   ├── collection/           # Collection management page
│   │   ├── decks/                # Deck viewing pages
│   │   ├── admin/                # Admin dashboard
│   │   ├── login/                # Login page
│   │   ├── register/             # Registration page
│   │   └── layout.tsx            # Root layout with nav + feedback button
│   ├── components/                # React components
│   │   ├── ui/                   # Shadcn/UI components
│   │   ├── deckbuilder/          # Deck builder UI
│   │   ├── collection/           # Collection UI
│   │   ├── FeedbackButton.tsx    # Global feedback button
│   │   └── UserNav.tsx           # User authentication nav
│   ├── lib/                       # Utilities
│   │   ├── gemini.ts             # Gemini AI integration
│   │   ├── edhrec-data.ts        # EDHREC commander data (2,557 commanders)
│   │   ├── auth.ts               # NextAuth configuration
│   │   ├── email.ts              # Email service (Nodemailer)
│   │   └── prisma.ts             # Prisma client
│   └── types/                     # TypeScript type definitions
├── scripts/                        # Python utilities
│   ├── build-deck-from-structure.py  # Main deck builder (strategy-aware)
│   ├── tag-cards.py              # Card tagging system
│   ├── train-v3-structured.py    # v3 model training (optional)
│   ├── scrape-*.py               # Data collection scripts
│   └── test-*.py                 # Testing utilities
├── prisma/
│   ├── schema.prisma             # Database schema
│   │                             # Models: User, Card, Deck, UserCard, Feedback
│   └── dev.db                    # SQLite database (31,483 cards, ~39MB)
├── data/
│   ├── mtgjson/                  # Card data
│   │   ├── AtomicCards.json     # 31k unique cards
│   │   └── AllSetFiles/         # Set-specific data
│   └── training/                 # AI training data (optional)
│       ├── v3_structured_training.jsonl  # 23k deck examples
│       └── deck_building_rules.json      # Strategy definitions
├── public/                        # Static assets
└── .env                          # Environment variables (gitignored)
```

## 🚀 Deployment

### Production Checklist
1. Set production environment variables in `.env`
2. Generate secure `NEXTAUTH_SECRET`: `openssl rand -base64 32`
3. Configure production `NEXTAUTH_URL` (your domain)
4. Add Gemini API key
5. Configure SMTP for email (optional but recommended)
6. Run `npm run build`
7. Import card database: `npm run import:mtgjson:full`
8. Create admin user: `npm run create-admin`
9. Start server: `npm run start`

### Self-Hosting (Docker)
```bash
# Build and run with Docker Compose
docker-compose up -d

# Access at http://localhost:3050
```

### Cloud Hosting (Vercel)
```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel deploy --prod

# Note: SQLite won't work on Vercel
# Need to migrate to PostgreSQL or other cloud database
```

See **[DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)** for detailed production guide.

## 🙏 Acknowledgments

- **EDHREC.com** - Commander statistics, popularity data, and saltiness scores
- **MTGJson.com** - Comprehensive card database (AtomicCards.json)
- **Scryfall** - Card imagery and additional data
- **Google Gemini** - AI deck building engine
- **Shadcn/UI** - Beautiful component library
- **Commander Community** - Feedback and testing

## 📧 Support & Contributing

**Issues & Bugs**: Open an issue on [GitHub](https://github.com/silvernova0/magic/issues)

**Feature Requests**: Use the in-app feedback button or GitHub issues

**Contributing**:
1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open Pull Request

**Contact**: jeffbuildsabase@gmail.com

## 📄 License

This project is open source and available under the MIT License.

---

**Built with ❤️ for the Commander/EDH community**

*Last Updated: November 2025*
