# 🚀 JankBuild Quick Start Guide

This is a **quick reference** for self-hosting JankBuild. See `SELF_HOSTING.md` for comprehensive documentation.

## ⚡ Fastest Setup (5 minutes)

### Prerequisites
- Windows 10/11
- Docker Desktop **OR** Node.js 22.x
- Nginx Proxy Manager (running on ports 80, 81, 443)
- Domain DNS configured to point to your server

### Option 1: Docker (Recommended) 🐳

```powershell
# 1. Run setup script
.\setup.ps1

# 2. Select option 1 (Docker)

# 3. Configure Nginx Proxy Manager:
#    Domain: jankbuild.com
#    Forward: http://192.168.0.108:3002
#    Enable SSL

# Done! Access at https://jankbuild.com
```

### Option 2: Node.js Direct 🟢

```powershell
# 1. Install dependencies
npm ci

# 2. Build application
npm run build

# 3. Start server
npm run start

# 4. Access at http://localhost:3002
```

### Option 3: PM2 Process Manager ⚙️

```powershell
# 1. Install PM2
npm install -g pm2 pm2-windows-startup
pm2-startup install

# 2. Build and start
npm ci
npm run build
pm2 start npm --name jankbuild -- run start
pm2 save

# Done! Auto-starts on reboot
```

## 📝 Nginx Proxy Manager Configuration

### 1. Access NPM Admin
- URL: `http://192.168.0.108:81`
- Login with your credentials

### 2. Add Proxy Host
**Details Tab:**
- Domain Names: `jankbuild.com`, `www.jankbuild.com`
- Scheme: `http`
- Forward Hostname/IP: `192.168.0.108` (or `host.docker.internal` if NPM in Docker)
- Forward Port: `3002`
- ✅ Cache Assets
- ✅ Block Common Exploits  
- ✅ Websockets Support

**SSL Tab:**
- Request New SSL Certificate
- Email: your@email.com
- ✅ Force SSL
- ✅ HTTP/2 Support
- ✅ HSTS Enabled
- Agree to Terms → Save

### 3. Test
```powershell
curl http://localhost:3002    # Local access
curl https://jankbuild.com    # Via reverse proxy
```

## 🔧 Essential Commands

### Docker
```powershell
docker-compose up -d          # Start
docker-compose down           # Stop
docker-compose restart        # Restart
docker-compose logs -f        # View logs
docker-compose build          # Rebuild
```

### PM2
```powershell
pm2 status                    # Status
pm2 logs jankbuild           # Logs
pm2 restart jankbuild        # Restart
pm2 stop jankbuild           # Stop
pm2 monit                    # Monitor
```

### Native Node.js
```powershell
npm run start                # Start (foreground)
npm run build                # Rebuild
npx prisma generate          # Regenerate Prisma client
```

## 📊 Import Card Database (Optional)

```powershell
# 1. Download MTGJson files
# https://mtgjson.com/downloads/all-files/
# - AtomicCards.json (~50MB)

# 2. Place in data folder
C:\magicapp\data\mtgjson\AtomicCards.json

# 3. Import
npm run import:mtgjson:full

# Takes 2-3 minutes, imports ~31,000 cards
```

## 🔐 Create Admin User

```powershell
npm run create-admin

# Follow prompts to create admin account
```

## 🌐 Environment Configuration

Edit `.env` file:

```properties
# REQUIRED: Generate new secret
NEXTAUTH_SECRET=your-random-secret-here

# REQUIRED: Your production domain
NEXTAUTH_URL=https://jankbuild.com

# REQUIRED: Get from https://ai.google.dev/
GEMINI_API_KEY=your-api-key-here
```

**Generate secret:**
```powershell
# PowerShell
-join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | % {[char]$_})

# Or use online: https://generate-secret.vercel.app/32
```

## 🎯 Port Configuration

**Your System Ports (Occupied):**
- 80, 81, 443: Nginx Proxy Manager
- 8000, 8080, 8443: Other services
- 3389: RDP
- 5432: PostgreSQL

**JankBuild Configuration:**
- **Port 3002**: JankBuild (localhost only)
- **External Access**: Via Nginx Proxy Manager (ports 80/443)

**Change Port (if needed):**
```yaml
# docker-compose.yml
ports:
  - "3100:3000"  # Use 3100 instead
```

```json
// package.json
"start": "next start -p 3100"
```

## 🔍 Troubleshooting

### Port Already in Use
```powershell
# Find process
netstat -ano | findstr :3002

# Kill process
taskkill /PID <pid> /F
```

### Container Won't Start
```powershell
# Check logs
docker-compose logs jankbuild

# Rebuild
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### 502 Bad Gateway (NPM)
```powershell
# 1. Verify JankBuild running
curl http://localhost:3002

# 2. Check NPM forward settings:
#    IP: 192.168.0.108 or host.docker.internal
#    Port: 3002

# 3. Test from NPM container
docker exec -it npm curl http://host.docker.internal:3002
```

### Database Issues
```powershell
# Stop all instances
docker-compose down
pm2 stop all

# Wait and restart
Start-Sleep -Seconds 30
docker-compose up -d
```

## 📚 More Help

- **Full Documentation**: `SELF_HOSTING.md`
- **Deployment Checklist**: `DEPLOYMENT_CHECKLIST.md`
- **Site Configuration**: `SITE_CONFIG.md`
- **GitHub Issues**: https://github.com/silvernova0/magic/issues

## ✅ Post-Setup Checklist

- [ ] Application running on port 3002
- [ ] Nginx Proxy Manager configured
- [ ] SSL certificate installed
- [ ] Can access via https://jankbuild.com
- [ ] Card database imported (optional)
- [ ] Admin user created
- [ ] Scheduled scraping running (optional)

---

**Need help?** Check `SELF_HOSTING.md` for detailed troubleshooting and advanced configuration.
