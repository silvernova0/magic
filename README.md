# Magic: The Gathering Commander Deck Builder

An intelligent Commander deck builder powered by Google Gemini AI with context from EDHREC, MTGTop8, and Moxfield.

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

## 🚀 Getting Started

### Prerequisites
- Node.js 20+
- npm or yarn

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/silvernova0/magic.git
cd magic
```

2. **Install dependencies**
```bash
npm install
```

3. **Set up environment variables**
Create a `.env` file:
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

4. **Set up database**
```bash
npx prisma generate
npx prisma db push

# Import Scryfall card database (25,000+ cards)
npm run import:scryfall
```

5. **Create admin user**
```bash
npm run create-admin
# Or with custom credentials:
npm run create-admin your@email.com password123 "Your Name"
```

6. **Run development server**
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
