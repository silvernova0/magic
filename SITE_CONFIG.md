# JankBuild - Site Configuration

## Domain
- **Production**: https://jankbuild.com
- **Repository**: https://github.com/silvernova0/magic

## Branding
- **Name**: JankBuild
- **Tagline**: AI-Powered Commander Deck Builder
- **Theme**: Purple/Indigo gradient
- **Icon**: 🎴 (playing card emoji)

## Environment Variables

### Required for Production
```bash
# Database
DATABASE_URL="your-production-database-url"

# NextAuth
NEXTAUTH_URL="https://jankbuild.com"
NEXTAUTH_SECRET="your-secure-secret-key"

# Google Gemini AI
GOOGLE_GEMINI_API_KEY="your-gemini-api-key"

# Email (Optional)
EMAIL_SERVER_HOST="smtp.example.com"
EMAIL_SERVER_PORT="587"
EMAIL_SERVER_USER="noreply@jankbuild.com"
EMAIL_SERVER_PASSWORD="your-email-password"
EMAIL_FROM="JankBuild <noreply@jankbuild.com>"
```

## Deployment

### Vercel (Recommended)
1. Connect GitHub repository to Vercel
2. Add environment variables in Vercel dashboard
3. Deploy!

**Custom Domain Setup**:
- Add `jankbuild.com` as custom domain in Vercel
- Configure DNS:
  - A Record: `@` → Vercel IP
  - CNAME Record: `www` → `cname.vercel-dns.com`

### Alternative: Railway/Render
- Similar process: connect repo, add env vars, deploy
- Point domain DNS to their platform

## DNS Configuration

### Cloudflare (Recommended)
```
Type    Name    Content
A       @       76.76.21.21 (Vercel IP)
CNAME   www     cname.vercel-dns.com
```

### Other DNS Providers
Follow Vercel's DNS setup instructions in dashboard

## SSL/TLS
- Automatic via Vercel (Let's Encrypt)
- Force HTTPS enabled by default

## Features Live on Production

✅ **Core Features**:
- AI-powered deck generation (Gemini 2.0 Flash)
- Local card database (31,483 cards)
- User authentication (NextAuth.js)
- Deck saving and sharing
- Collection management
- Card preview system

✅ **Data Sources**:
- EDHREC synergies (21,817 synergies for 88 commanders)
- MTGTop8 tournament decks (26 decks)
- Moxfield community decks (20 unique decks)
- Scheduled scraping (daily/weekly updates)

✅ **Documentation**:
- Complete API documentation
- User guides and tutorials
- Developer setup instructions

## Monitoring & Analytics

### Recommended Tools
- **Vercel Analytics** - Built-in traffic and performance
- **Sentry** - Error tracking
- **Plausible/Umami** - Privacy-friendly analytics
- **Uptime Robot** - Uptime monitoring

## SEO Optimization

### Meta Tags (Already Configured)
- Title: "JankBuild - MTG Commander Deck Builder"
- Description: "AI-powered Commander/EDH deck builder with card collection management"

### Future Enhancements
- [ ] Add sitemap.xml
- [ ] Add robots.txt
- [ ] OpenGraph images for social sharing
- [ ] Structured data (JSON-LD)

## Social Media

### Suggested Accounts
- Twitter/X: @jankbuild
- Discord: JankBuild Server
- Reddit: r/JankBuild (or post in r/EDH, r/magicTCG)

## Branding Assets

### Logo Ideas
- Playing card emoji (🎴) - Currently used
- Custom logo with janky/playful aesthetic
- Purple/indigo color scheme

### Favicon
- Generate from logo
- Place in `public/favicon.ico`

## Marketing Copy

### Tagline Options
- "AI-Powered Commander Deck Builder" (current)
- "Build Better Jank"
- "Where Jank Meets Technology"
- "Commander Decks, Powered by AI"

### About Section
"JankBuild helps Magic: The Gathering players build creative Commander decks using AI. Whether you're brewing spicy jank or optimizing competitive lists, our tool combines the power of Google Gemini AI with comprehensive data from EDHREC, MTGTop8, and Moxfield to help you build better decks."

## Community Features (Future)

- [ ] Public deck sharing
- [ ] Deck ratings and comments
- [ ] User profiles
- [ ] Deck discovery feed
- [ ] Featured decks of the week
- [ ] Deck challenges/contests

## Legal

### Terms of Service
- [ ] Draft ToS
- [ ] Privacy Policy
- [ ] Cookie Policy

### Attribution
- MTG card data: © Wizards of the Coast
- Scryfall API for card images
- EDHREC for synergy data
- MTGTop8 for tournament data
- Moxfield for community decks

## Support

### Contact
- Email: support@jankbuild.com (recommended)
- GitHub Issues: For bug reports
- Discord: For community support

## Version
- Current: v1.0.0
- Launch Date: October 22, 2025
- Last Updated: October 22, 2025
