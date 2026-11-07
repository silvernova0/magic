# 🚀 JankBuild Deployment Checklist

## ✅ Pre-Deployment (Completed)

- [x] ✅ Rebrand to JankBuild throughout codebase
- [x] ✅ Update package.json to v1.0.0
- [x] ✅ Create SITE_CONFIG.md with deployment instructions
- [x] ✅ Update README.md with new branding
- [x] ✅ Push all changes to GitHub

## 🔧 Deployment Steps

### 1. Vercel Setup (Recommended)
- [ ] Go to [vercel.com](https://vercel.com)
- [ ] Sign in with GitHub
- [ ] Click "Add New Project"
- [ ] Import `silvernova0/magic` repository
- [ ] Configure project:
  * Framework: Next.js
  * Root Directory: `./`
  * Build Command: `npm run build`
  * Output Directory: `.next`

### 2. Environment Variables
Add these in Vercel Dashboard → Settings → Environment Variables:

**Required:**
```
DATABASE_URL=file:./prisma/dev.db
NEXTAUTH_URL=https://jankbuild.com
NEXTAUTH_SECRET=<generate-with-openssl-rand-base64-32>
GOOGLE_GEMINI_API_KEY=<your-gemini-api-key>
```

**Optional (Email):**
```
EMAIL_SERVER_HOST=smtp.example.com
EMAIL_SERVER_PORT=587
EMAIL_SERVER_USER=noreply@jankbuild.com
EMAIL_SERVER_PASSWORD=<your-password>
EMAIL_FROM=JankBuild <noreply@jankbuild.com>
```

**Generate NEXTAUTH_SECRET:**
```bash
openssl rand -base64 32
```

### 3. Domain Configuration
- [ ] In Vercel Dashboard → Settings → Domains
- [ ] Add `jankbuild.com`
- [ ] Add `www.jankbuild.com` (optional)
- [ ] Copy the DNS records provided by Vercel

### 4. DNS Setup (Your Domain Registrar)
Configure these DNS records:

**For Cloudflare/Most Providers:**
```
Type    Name    Value                       TTL
A       @       76.76.21.21                 Auto
CNAME   www     cname.vercel-dns.com        Auto
```

Note: Vercel will provide exact DNS values after adding domain

### 5. Database Setup (Production)

**Option A: SQLite (Simple, for testing)**
- Already configured with `file:./prisma/dev.db`
- Vercel may have file system limitations
- OK for low traffic, single region

**Option B: PostgreSQL (Recommended for production)**
- Use [Neon](https://neon.tech) or [Supabase](https://supabase.com)
- Free tier available
- Update `DATABASE_URL` to PostgreSQL connection string
- Run migrations: `npx prisma migrate deploy`

**Option C: PlanetScale (MySQL)**
- Good for scaling
- Free tier available
- Update schema to MySQL format

### 6. Deploy!
- [ ] Click "Deploy" in Vercel
- [ ] Wait 2-3 minutes for build
- [ ] Visit https://jankbuild.com
- [ ] Test all features

## 🧪 Post-Deployment Testing

### Core Features
- [ ] Homepage loads correctly
- [ ] Login/Register works
- [ ] Deck builder generates decks
- [ ] Collection page loads
- [ ] Card search works
- [ ] Deck saving works
- [ ] Card preview works (hover/click)
- [ ] Deck sharing links work

### Performance
- [ ] Check page load times
- [ ] Verify images load
- [ ] Test on mobile devices
- [ ] Check Lighthouse scores

### SEO
- [ ] Verify meta tags
- [ ] Check OpenGraph preview (Twitter, Discord)
- [ ] Submit sitemap to Google Search Console
- [ ] Add site to Bing Webmaster Tools

## 📊 Monitoring Setup

### Vercel Analytics (Built-in)
- [ ] Enable in Vercel Dashboard
- [ ] Free for hobby projects

### Error Tracking (Recommended)
- [ ] [Sentry](https://sentry.io) - Error monitoring
- [ ] Add Sentry DSN to env vars

### Uptime Monitoring
- [ ] [UptimeRobot](https://uptimerobot.com) - Free
- [ ] Add https://jankbuild.com
- [ ] Set up email alerts

### Optional: Privacy-Friendly Analytics
- [ ] [Plausible](https://plausible.io)
- [ ] [Umami](https://umami.is)

## 🎨 Additional Setup

### Favicon
- [ ] Generate favicon from logo
- [ ] Add to `public/favicon.ico`
- [ ] Add Apple touch icon

### Social Media
- [ ] Create Twitter/X account
- [ ] Create Discord server
- [ ] Post to r/EDH announcing launch

### Legal
- [ ] Add Terms of Service page
- [ ] Add Privacy Policy page
- [ ] Add Cookie consent banner (if tracking)

## 🚨 Common Issues

### Build Fails
- Check Node.js version (20+)
- Verify all dependencies installed
- Check for TypeScript errors

### Database Connection
- Verify DATABASE_URL format
- For PostgreSQL: Include `?schema=public`
- Check firewall allows Vercel IPs

### Authentication Not Working
- Verify NEXTAUTH_URL matches domain
- Check NEXTAUTH_SECRET is set
- Clear browser cookies and retry

### Domain Not Resolving
- DNS propagation takes 24-48 hours
- Use [DNS Checker](https://dnschecker.org)
- Verify DNS records match Vercel instructions

### Images Not Loading
- Check Scryfall API is accessible
- Verify Next.js image domains configured
- Check browser console for errors

## 📝 Future Enhancements

### Phase 1 (Next 30 days)
- [ ] Add sitemap.xml
- [ ] Add robots.txt
- [ ] Improve mobile responsiveness
- [ ] Add loading states/skeletons
- [ ] Optimize images (lazy loading)

### Phase 2 (Next 90 days)
- [ ] Public deck sharing
- [ ] Deck discovery feed
- [ ] User profiles
- [ ] Deck ratings/comments
- [ ] Featured decks

### Phase 3 (Future)
- [ ] Premium features
- [ ] Deck analytics
- [ ] Tournament tracker
- [ ] Deck challenges
- [ ] Community features

## 💡 Marketing Ideas

### Launch Week
- [ ] Post on r/EDH
- [ ] Post on r/magicTCG
- [ ] Share on Twitter/X
- [ ] Post in MTG Discord servers
- [ ] Reach out to MTG content creators

### Content
- [ ] Write blog post about AI deck building
- [ ] Create video demo
- [ ] Share example decks
- [ ] Write about interesting synergies found

### Community
- [ ] Respond to feedback
- [ ] Add most requested features
- [ ] Create Discord server
- [ ] Host deck building challenges

## 🎉 Launch Checklist

**Ready to Go Live:**
- [x] ✅ Code complete and tested
- [x] ✅ Documentation complete
- [x] ✅ Branding finalized
- [ ] Vercel deployment configured
- [ ] Domain DNS pointing to Vercel
- [ ] Environment variables set
- [ ] SSL certificate active (auto via Vercel)
- [ ] All features tested in production
- [ ] Monitoring setup
- [ ] Marketing materials ready

**Launch Day:**
- [ ] Deploy to production
- [ ] Test all features
- [ ] Announce on social media
- [ ] Monitor for issues
- [ ] Respond to feedback

---

## 🆘 Need Help?

- **Vercel Docs**: https://vercel.com/docs
- **Next.js Docs**: https://nextjs.org/docs
- **Prisma Docs**: https://www.prisma.io/docs
- **Discord**: (create your support server)
- **GitHub Issues**: https://github.com/silvernova0/magic/issues

---

**Good luck with the launch! 🚀**
