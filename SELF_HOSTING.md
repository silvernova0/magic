# 🏠 Self-Hosting JankBuild

Complete guide for self-hosting JankBuild on Windows with Docker and Nginx Proxy Manager.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Port Configuration](#port-configuration)
- [Installation Methods](#installation-methods)
- [Nginx Proxy Manager Setup](#nginx-proxy-manager-setup)
- [Environment Configuration](#environment-configuration)
- [Database Setup](#database-setup)
- [Running the Application](#running-the-application)
- [SSL/TLS Configuration](#ssltls-configuration)
- [Maintenance](#maintenance)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Software
- **Docker Desktop for Windows** (latest version)
- **Nginx Proxy Manager** (running on ports 80, 81, 443)
- **Node.js 22.x** (for non-Docker deployment)
- **Git** (for repository management)

### System Requirements
- Windows 10/11 or Windows Server 2019+
- 4GB RAM minimum (8GB recommended)
- 10GB free disk space (for application + card database)
- Docker Desktop with WSL2 backend enabled

## Port Configuration

### Default Ports (from your netstat)
Your system currently uses these ports (occupied):
- **80, 81**: Nginx Proxy Manager (HTTP/Admin)
- **443**: Nginx Proxy Manager (HTTPS)
- **8000, 8080, 8083, 8443, 9443**: Other Docker services
- **3389**: RDP
- **5432**: PostgreSQL (localhost only)

### JankBuild Port Assignment
**Recommended configuration:**
- **External**: Access via Nginx Proxy Manager (ports 80/443)
- **Internal**: JankBuild runs on port **3050** (localhost only)
- **Alternative**: Port **3100** (if 3050 is needed elsewhere)

This configuration keeps JankBuild isolated and only accessible through your reverse proxy.

## Installation Methods

### Method 1: Docker Deployment (Recommended)

#### Step 1: Update Environment File
Edit `.env` file with production settings:

```properties
# Auth - Generate new secret with: openssl rand -base64 32
NEXTAUTH_SECRET=your-production-secret-here
NEXTAUTH_URL=https://jankbuild.com  # Your domain

# Gemini AI
GEMINI_API_KEY=your-gemini-api-key

# Email (optional)
EMAIL_HOST=localhost
EMAIL_PORT=2525
EMAIL_FROM="JankBuild <noreply@jankbuild.com>"
ADMIN_EMAIL=admin@jankbuild.com
```

#### Step 2: Build Docker Image
```powershell
cd C:\magicapp

# Build the Docker image
docker-compose build

# Or build without cache (for clean build)
docker-compose build --no-cache
```

#### Step 3: Start Container
```powershell
# Start in detached mode
docker-compose up -d

# View logs
docker-compose logs -f

# Check status
docker-compose ps
```

#### Step 4: Verify Application
```powershell
# Test internal access
curl http://localhost:3050

# Check container health
docker ps
```

### Method 2: Native Node.js Deployment

#### Step 1: Install Dependencies
```powershell
cd C:\magicapp
npm ci
```

#### Step 2: Build Production Bundle
```powershell
# Generate Prisma client
npx prisma generate

# Build Next.js application
npm run build
```

#### Step 3: Run Production Server
```powershell
# Set environment
$env:NODE_ENV="production"
$env:PORT="3050"

# Start server
npm run start
```

#### Step 4: Create Windows Service (Optional)
Use **NSSM** (Non-Sucking Service Manager) or **PM2** for Windows:

**Using PM2:**
```powershell
# Install PM2 globally
npm install -g pm2
npm install -g pm2-windows-startup

# Configure PM2 startup
pm2-startup install

# Start application
pm2 start npm --name "jankbuild" -- start
pm2 save

# Management commands
pm2 status
pm2 logs jankbuild
pm2 restart jankbuild
pm2 stop jankbuild
```

**Using NSSM:**
```powershell
# Download NSSM from https://nssm.cc/download
# Install as service
nssm install JankBuild "C:\Program Files\nodejs\node.exe" "C:\magicapp\node_modules\next\dist\bin\next start"

# Configure service
nssm set JankBuild AppDirectory C:\magicapp
nssm set JankBuild AppEnvironmentExtra PORT=3050 NODE_ENV=production
nssm set JankBuild Start SERVICE_AUTO_START

# Start service
nssm start JankBuild
```

## Nginx Proxy Manager Setup

### Step 1: Access NPM Admin Panel
1. Open browser: `http://192.168.0.108:81` (your NPM admin port)
2. Login with your credentials

### Step 2: Add Proxy Host

**Configuration:**
- **Domain Names**: `jankbuild.com`, `www.jankbuild.com`
- **Scheme**: `http`
- **Forward Hostname/IP**: `192.168.0.108` (or `host.docker.internal` if NPM is in Docker)
- **Forward Port**: `3050`
- **Cache Assets**: ✅ Enabled
- **Block Common Exploits**: ✅ Enabled
- **Websockets Support**: ✅ Enabled (for Next.js hot reload in dev)

**Custom Locations (Optional):**
```nginx
# API routes optimization
location /api/ {
    proxy_pass http://192.168.0.108:3050;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection 'upgrade';
    proxy_set_header Host $host;
    proxy_cache_bypass $http_upgrade;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

# Static assets caching
location /_next/static/ {
    proxy_pass http://192.168.0.108:3050;
    proxy_cache_valid 200 60d;
    add_header Cache-Control "public, immutable";
}
```

### Step 3: SSL Certificate

**Option A: Let's Encrypt (Recommended)**
1. In NPM, go to SSL tab
2. Select "Request a new SSL Certificate"
3. Enable "Force SSL" and "HTTP/2 Support"
4. Enter email address
5. Agree to Let's Encrypt ToS
6. Click "Save"

**Option B: Custom Certificate**
1. Upload your certificate files
2. Certificate: `your-cert.crt`
3. Certificate Key: `your-cert.key`
4. Intermediate Certificate: `chain.crt` (if applicable)

### Step 4: Test Configuration
```powershell
# Test internal access
curl http://localhost:3050

# Test reverse proxy (without SSL)
curl http://jankbuild.com

# Test HTTPS (after SSL setup)
curl https://jankbuild.com
```

## Environment Configuration

### Production .env Template
```properties
# ======================
# AUTH CONFIGURATION
# ======================
# Generate with: openssl rand -base64 32
NEXTAUTH_SECRET=CHANGE_THIS_TO_RANDOM_SECRET

# Your production domain
NEXTAUTH_URL=https://jankbuild.com

# ======================
# AI CONFIGURATION
# ======================
# Get from: https://ai.google.dev/
GEMINI_API_KEY=your-api-key-here

# ======================
# DATABASE
# ======================
# SQLite (default - no changes needed)
DATABASE_URL=file:./prisma/dev.db

# PostgreSQL (if migrating to production DB)
# DATABASE_URL=postgresql://user:password@localhost:5432/jankbuild

# ======================
# EMAIL (OPTIONAL)
# ======================
EMAIL_HOST=localhost
EMAIL_PORT=2525
EMAIL_FROM="JankBuild <noreply@jankbuild.com>"
ADMIN_EMAIL=admin@jankbuild.com

# ======================
# SECURITY
# ======================
# Disable telemetry
NEXT_TELEMETRY_DISABLED=1

# Node environment
NODE_ENV=production
```

### Update Environment in Docker
```powershell
# Method 1: Update .env file then restart
docker-compose down
docker-compose up -d

# Method 2: Pass environment variables directly
docker-compose up -d -e NEXTAUTH_URL=https://jankbuild.com
```

## Database Setup

### Initial Database Creation
```powershell
# Generate Prisma client
npx prisma generate

# Create database schema
npx prisma db push

# (Optional) Create admin user
npm run create-admin
```

### Import Card Database
```powershell
# Download MTGJson files first
# Place in: C:\magicapp\data\mtgjson\

# Import full card database (~31,000 cards)
npm run import:mtgjson:full

# Import EDHREC synergies (~21,000 synergies)
npm run import:edhrec:synergies

# Import tournament decks (optional)
npm run import:mtgtop8
npm run import:moxfield
```

### Database Location
- **Development**: `C:\magicapp\prisma\dev.db`
- **Docker Volume**: Persisted in named volume `jankbuild-data`
- **Backup Location**: (recommended) `C:\magicapp\backups\`

### Database Backups
```powershell
# Create backup script: backup-db.ps1
$timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$backupPath = "C:\magicapp\backups\dev_$timestamp.db"

# Create backups directory
New-Item -ItemType Directory -Force -Path "C:\magicapp\backups"

# Copy database
Copy-Item "C:\magicapp\prisma\dev.db" -Destination $backupPath

Write-Host "Database backed up to: $backupPath"

# Compress backup (optional)
Compress-Archive -Path $backupPath -DestinationPath "$backupPath.zip"
Remove-Item $backupPath
```

**Schedule with Task Scheduler:**
```powershell
# Create daily backup task
$action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-File C:\magicapp\backup-db.ps1"
$trigger = New-ScheduledTaskTrigger -Daily -At 3am
Register-ScheduledTask -TaskName "JankBuild-Backup" -Action $action -Trigger $trigger
```

## Running the Application

### Docker Management

**Start/Stop Commands:**
```powershell
# Start container
docker-compose up -d

# Stop container
docker-compose down

# Restart container
docker-compose restart

# View logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f jankbuild
```

**Update Application:**
```powershell
# Pull latest code
git pull origin main

# Rebuild and restart
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### PM2 Management (Native Deployment)

```powershell
# Start application
pm2 start npm --name "jankbuild" -- start

# Stop application
pm2 stop jankbuild

# Restart application
pm2 restart jankbuild

# View logs
pm2 logs jankbuild

# Monitor resources
pm2 monit

# Application status
pm2 status

# Remove from PM2
pm2 delete jankbuild
```

### Scheduled Scraping Service

**Run as separate service:**
```powershell
# Using PM2
pm2 start npm --name "jankbuild-scheduler" -- run scheduler

# Or create separate Docker container (add to docker-compose.yml)
```

**Add to docker-compose.yml:**
```yaml
scheduler:
  build:
    context: .
    dockerfile: Dockerfile
  container_name: jankbuild-scheduler
  command: npm run scheduler
  environment:
    - NODE_ENV=production
  volumes:
    - ./prisma:/app/prisma
    - ./data:/app/data
  restart: unless-stopped
```

## SSL/TLS Configuration

### Let's Encrypt with NPM (Automatic)
1. NPM handles certificate issuance automatically
2. Certificates renew automatically before expiration
3. No manual configuration needed

### Custom Certificate
```powershell
# Generate self-signed certificate (testing only)
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes

# Upload to NPM:
# - Certificate: cert.pem
# - Private Key: key.pem
```

### Force HTTPS Redirect
In NPM Proxy Host settings:
- ✅ Enable "Force SSL"
- ✅ Enable "HTTP/2 Support"
- ✅ Enable "HSTS Enabled"

## Maintenance

### Regular Tasks

**Daily:**
- Monitor container logs for errors
- Check disk space (database + card images)

**Weekly:**
- Review application performance
- Check for npm package updates
- Verify scheduled scraping is running

**Monthly:**
- Update Docker images: `docker-compose pull`
- Update dependencies: `npm outdated` → `npm update`
- Database backup verification
- Review Nginx access/error logs

### Update Checklist

**Application Updates:**
```powershell
# 1. Backup database
npm run backup  # (if script exists) or manual copy

# 2. Pull latest code
git pull origin main

# 3. Update dependencies
npm ci

# 4. Rebuild Prisma client
npx prisma generate

# 5. Run database migrations (if any)
npx prisma migrate deploy

# 6. Rebuild Docker image
docker-compose build --no-cache

# 7. Restart application
docker-compose up -d

# 8. Verify application
curl http://localhost:3050
curl https://jankbuild.com
```

### Log Management

**Docker Logs:**
```powershell
# Configure log rotation in docker-compose.yml
services:
  jankbuild:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

**PM2 Logs:**
```powershell
# Rotate logs manually
pm2 flush

# Configure automatic rotation
pm2 install pm2-logrotate
pm2 set pm2-logrotate:max_size 10M
pm2 set pm2-logrotate:retain 7
```

## Troubleshooting

### Common Issues

#### 1. Port Already in Use
**Error:** `Port 3050 is already in use`

**Solution:**
```powershell
# Find process using port
netstat -ano | findstr :3050

# Kill process (replace PID)
taskkill /PID <pid> /F

# Or change port in docker-compose.yml
ports:
  - "3100:3000"  # Use port 3100 instead
```

#### 2. Container Won't Start
**Check logs:**
```powershell
docker-compose logs jankbuild

# Common causes:
# - Missing .env file
# - Invalid environment variables
# - Database migration needed
```

**Solutions:**
```powershell
# Verify .env file exists
Get-Content .env

# Check Docker resources
docker system df

# Rebuild from scratch
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

#### 3. Nginx Proxy Manager 502 Bad Gateway
**Causes:**
- JankBuild not running
- Wrong forward port in NPM
- Firewall blocking connection

**Solutions:**
```powershell
# 1. Verify JankBuild is running
curl http://localhost:3050

# 2. Check NPM configuration
# Forward Port should be: 3050
# Forward IP should be: 192.168.0.108 or host.docker.internal

# 3. Test connectivity from NPM container
docker exec -it npm-container curl http://host.docker.internal:3050
```

#### 4. Database Locked
**Error:** `database is locked`

**Solution:**
```powershell
# Stop all applications accessing database
docker-compose down
pm2 stop all

# Wait 30 seconds
Start-Sleep -Seconds 30

# Restart
docker-compose up -d
```

#### 5. Out of Memory
**Symptoms:**
- Container crashes
- `ENOSPC` errors
- Slow performance

**Solutions:**
```powershell
# Increase Docker memory limit (Docker Desktop → Settings → Resources)

# Add memory limits to docker-compose.yml
services:
  jankbuild:
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 1G
```

### Performance Optimization

**Docker Compose:**
```yaml
services:
  jankbuild:
    environment:
      - NODE_ENV=production
      - NODE_OPTIONS=--max-old-space-size=2048  # 2GB heap
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
```

**Nginx Caching:**
```nginx
# Add to NPM Custom Configuration
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=jankbuild_cache:10m max_size=1g inactive=60m;
proxy_cache jankbuild_cache;
proxy_cache_valid 200 10m;
proxy_cache_bypass $http_upgrade;
```

### Monitoring

**Docker Stats:**
```powershell
# Real-time resource usage
docker stats jankbuild

# Continuous monitoring
docker stats --no-stream jankbuild
```

**Health Check:**
```powershell
# Application health
curl http://localhost:3050/api/health

# Database connection
docker exec jankbuild npx prisma db pull
```

### Getting Help

1. **Check Logs First:**
   ```powershell
   docker-compose logs -f --tail=100
   ```

2. **GitHub Issues**: https://github.com/silvernova0/magic/issues

3. **Documentation**: See other .md files in repository

4. **Community Discord**: (if available)

---

## Quick Reference

### Essential Commands
```powershell
# Start
docker-compose up -d

# Stop
docker-compose down

# Logs
docker-compose logs -f

# Restart
docker-compose restart

# Update
git pull && docker-compose build && docker-compose up -d

# Backup
Copy-Item prisma\dev.db backups\dev_backup.db

# Health Check
curl http://localhost:3050
```

### Port Summary
- **3050**: JankBuild application (localhost only)
- **80/443**: Nginx Proxy Manager → JankBuild
- **81**: NPM admin panel

### File Locations
- **Application**: `C:\magicapp\`
- **Database**: `C:\magicapp\prisma\dev.db`
- **Logs**: `docker logs jankbuild` or PM2 logs
- **Config**: `C:\magicapp\.env`
- **Data**: `C:\magicapp\data\mtgjson\`

---

**Last Updated:** {{ date }}  
**Version:** 1.0.0  
**Author:** JankBuild Team
