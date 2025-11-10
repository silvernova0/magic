# 🎴 JankBuild - MTG Commander Deck Builder

**Website**: [jankbuild.com](https://jankbuild.com)

An AI-powered Commander/EDH deck builder with comprehensive card collection management, powered by Google Gemini AI with context from EDHREC, MTGTop8, and Moxfield.

## 🎯 Features

### ✨ AI-Powered Deck Building
- **Gemini AI Integration** - Intelligent deck building with context from popular EDH sources
- **EDHREC Data** - Uses most popular commanders and card synergies
- **MTGTop8 Meta** - References competitive tournament results
- **Moxfield Brackets** - Power level classification (1-5)

### 🎴 Deck Configuration
- **20+ Themes** - Aggro, Control, Stax, Combo, Kindred, and more
- **Color Identity** - Build in specific colors or let AI decide
- **Power Levels** - Bracket 1 (Precon) to Bracket 5 (cEDH)
- **Collection Mode** - Build from your cards OR use any cards
- **Commander Selection** - Specify commander or get AI suggestions

### 👥 User Features
- **Authentication** - Secure login with NextAuth.js
- **Per-User Collections** - Track your personal card collection
- **Role-Based Access** - USER and ADMIN roles
- **Email Notifications** - Welcome emails, password resets
- **Deck Management** - Save, edit, and organize your decks

### 📊 Admin Dashboard
- User management
- Role promotion/demotion
- Email configuration and testing
- User statistics

### 🎴 Local Card Database (31,000+ cards)
- **Comprehensive MTGJson Data** - Complete card database with EDHREC rankings
- **Advanced Filtering** - Search by name, colors, types, keywords, CMC, saltiness
- **Card Tags** - Auto-generated tags: game-changer, removal, tutor, card-draw, high-salt, etc.
- **EDHREC Integration** - Popularity rankings and saltiness scores
- **Power Level Scoring** - Automatic 0-10 power level calculation
- **Commander Validation** - Identifies legal commanders and format legalities
- **Price Data** - Purchase URLs for CardKingdom, TCGPlayer, Cardmarket

## 🚀 Quick Start

### Development Setup
```bash
# 1. Clone and install
git clone https://github.com/silvernova0/magic.git
cd magic
npm install

# 2. Setup environment
cp .env.production.template .env
# Edit .env with your settings (see below)

# 3. Generate Prisma client
npx prisma generate
npx prisma db push

# 4. Import card database (optional)
npm run import:mtgjson:full

# 5. Start development server
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

Required settings for production:
```env
# Auth
NEXTAUTH_SECRET=your_secret_here
NEXTAUTH_URL=http://localhost:3000

# Gemini AI
GEMINI_API_KEY=your_gemini_api_key

# Email (optional)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USER=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
EMAIL_FROM="Magic Deck Builder <your-email@gmail.com>"
ADMIN_EMAIL=admin@example.com
```

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

### Building a Deck

1. **Navigate to Deck Builder** (`/deckbuilder`)
2. **Configure your deck:**
   - Choose a theme (Aggro, Control, Stax, etc.)
   - Select colors or leave empty for AI choice
   - Pick power level (Bracket 1-5)
   - Optionally specify a commander
   - Toggle "Use Collection Only" if desired
3. **Click "Build My Commander Deck"**
4. **Review and save** your generated deck

### Managing Collection

1. **Go to Collection** (`/collection`)
2. **Import cards** via CSV or bulk text
3. **Search and filter** your collection
4. **Track quantities** and card details

### Admin Features

1. **Login as admin** (created via `npm run create-admin`)
2. **Access Admin Panel** (`/admin`)
3. **Manage users** - promote, demote, view stats
4. **Configure email** (`/admin/email`)
5. **Test SMTP** settings

## 📚 Documentation

- [**GEMINI_DECK_BUILDER.md**](./GEMINI_DECK_BUILDER.md) - Complete AI deck builder guide
- [**AUTHENTICATION_SETUP.md**](./AUTHENTICATION_SETUP.md) - Auth system documentation
- [**REGISTRATION_AND_ROLES.md**](./REGISTRATION_AND_ROLES.md) - User roles guide
- [**DATABASE_REFERENCE.md**](./DATABASE_REFERENCE.md) - Database schema reference

## 🛠️ Tech Stack

- **Frontend:** Next.js 15, React 19, TailwindCSS, Shadcn/UI
- **Backend:** Next.js API Routes, Server Actions
- **Database:** Prisma ORM + SQLite (local card database with 25,000+ cards)
- **AI:** Google Gemini 2.5 Flash (hybrid system with local scrapers)
- **Auth:** NextAuth.js with bcrypt
- **Email:** Nodemailer
- **External APIs:** Scryfall, EDHREC, MTGTop8, Moxfield
- **Scraping:** Cheerio, file-based cache (6-hour TTL)

## 📖 Documentation

### Getting Started
- **[QUICK_START.md](QUICK_START.md)** - Essential setup guide for development
- **[TRAINING_V2_QUICK_START.md](TRAINING_V2_QUICK_START.md)** - Complete AI model training guide (v2)
- **[TRAINING_GUIDE.md](TRAINING_GUIDE.md)** - Detailed training documentation

### AI Model Training
- **[START_TRAINING_V2.md](START_TRAINING_V2.md)** - v2 training startup guide
- **[.github/copilot-instructions.md](.github/copilot-instructions.md)** - Comprehensive AI assistant instructions
- **[TRAINING_PROGRESS.md](TRAINING_PROGRESS.md)** - Training progress tracking

### Features & Configuration
- **[GEMINI_DECK_BUILDER.md](GEMINI_DECK_BUILDER.md)** - Gemini AI integration details
- **[CARD_DATABASE.md](CARD_DATABASE.md)** - Card database reference
- **[AUTHENTICATION_SETUP.md](AUTHENTICATION_SETUP.md)** - User authentication guide
- **[DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)** - Production deployment

### Data Collection
- **[REAL_DATA_STRATEGY.md](REAL_DATA_STRATEGY.md)** - Data collection strategy
- **[SCHEDULED_SCRAPING.md](SCHEDULED_SCRAPING.md)** - Automated scraping setup

## 🤖 Local AI Model (Optional)

**Hybrid AI System**: Primary Gemini API + Optional local fine-tuned Qwen 2.5 3B model

### Training Status (v2)
- **Model**: Qwen 2.5 3B with LoRA fine-tuning
- **Dataset**: 43,631 examples (31k cards + 12.5k Commander decks)
- **Sources**: MTGGoldfish (12k), Archidekt (4k), Moxfield (4k)
- **Hardware**: Intel Arc B50 16GB VRAM
- **Training time**: ~32 hours

### Quick Start Training
```bash
# 1. Activate virtualenv (REQUIRED)
source ~/.virtualenvs/magicapp/bin/activate

# 2. Start training with optimal configuration
BATCH_SIZE=4 GRADIENT_ACCUMULATION_STEPS=8 MAX_SEQ_LENGTH=675 \
  nohup python3 scripts/train-commander-model-optimized.py > training_v2.log 2>&1 &

# 3. Monitor progress
tail -f training_v2.log

# 4. Check GPU usage
nvtop
```

See **[TRAINING_V2_QUICK_START.md](TRAINING_V2_QUICK_START.md)** for complete training guide.

## 📖 API Endpoints

### Deck Building
- `POST /api/commander/build` - Build a deck with AI
- `POST /api/commander/suggest` - Get commander suggestions
- `POST /api/commander/search` - Search EDHREC data

### Decks
- `GET /api/decks` - List user's decks
- `GET /api/decks/[id]` - Get specific deck
- `POST /api/decks` - Create deck
- `PATCH /api/decks/[id]` - Update deck
- `DELETE /api/decks/[id]` - Delete deck

### Card Database (31,000+ cards)
- `GET /api/cards/search` - Search and filter cards
  - Query params: `q` (name/text search), `colors`, `colorIdentity`, `types`, `keywords`, `minCmc`, `maxCmc`, `isCommander`, `minEdhrecRank`, `maxEdhrecRank`, `minSaltiness`, `maxSaltiness`, `rarity`, `sortBy`, `sortOrder`, `limit`, `offset`
- `GET /api/cards/[nameOrId]` - Get specific card with tags, saltiness, power level

### Admin
- `GET /api/admin/test-email` - Test email config
- `POST /api/admin/test-email` - Send test email

## 🧪 Development

### Run Tests
```bash
npm run lint
```

### Build for Production
```bash
npm run build
npm run start
```

### Database Management
```bash
# Open Prisma Studio
npx prisma studio

# Create migration
npx prisma migrate dev

# Reset database
npx prisma migrate reset

# Import Scryfall card database
npm run import:scryfall
```

## 📦 Project Structure

```
magic/
├── src/
│   ├── app/                 # Next.js app router
│   │   ├── api/            # API routes
│   │   ├── admin/          # Admin pages
│   │   ├── deckbuilder/    # Deck builder UI
│   │   └── ...
│   ├── components/         # React components
│   │   ├── ui/            # Shadcn UI components
│   │   └── deckbuilder/   # Deck builder components
│   ├── lib/               # Utilities
│   │   ├── gemini.ts      # AI integration
│   │   ├── auth.ts        # Authentication
│   │   ├── email.ts       # Email service
│   │   └── ...
│   └── types/             # TypeScript types
├── prisma/                # Database schema
├── public/                # Static assets
└── scripts/               # Utility scripts
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is open source and available under the MIT License.

## 🙏 Acknowledgments

- **EDHREC.com** - Commander statistics and data
- **MTGTop8.com** - Tournament meta information
- **Moxfield.com** - Power level bracket system
- **Scryfall** - Card database and API
- **Google Gemini** - AI deck building engine

## 📧 Support

For issues or questions:
- Check documentation files
- Open an issue on GitHub
- Contact: silvernova0@gmail.com

---

**Built with ❤️ for the Commander community**
