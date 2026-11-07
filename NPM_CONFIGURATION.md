# 🔧 Nginx Proxy Manager - JankBuild Configuration

Quick reference for configuring JankBuild with Nginx Proxy Manager on your Windows system.

## Your System Configuration

**IP Address:** `192.168.0.108`  
**JankBuild Port:** `3050` (localhost only)  
**Domain:** `jankbuild.com`

**Occupied Ports (from your netstat):**
- 80, 81, 443: Nginx Proxy Manager
- 8000, 8080, 8083, 8443, 9443: Other Docker services
- 3389: RDP
- 5432: PostgreSQL (localhost)
- **3050: JankBuild** ✅ (configured)

## Step 1: Start JankBuild

Choose one method:

### Option A: Docker (Recommended)
```powershell
cd C:\magicapp
.\setup.ps1
# Select option 1 (Docker)
```

### Option B: Quick Docker
```powershell
docker-compose up -d
```

### Option C: Node.js
```powershell
npm run start
```

Verify it's running:
```powershell
curl http://localhost:3050
```

## Step 2: Configure Nginx Proxy Manager

### Access NPM
1. Open browser: `http://192.168.0.108:81`
2. Login with your admin credentials

### Add Proxy Host

Click **"Proxy Hosts"** → **"Add Proxy Host"**

#### Details Tab
```
Domain Names:
  jankbuild.com
  www.jankbuild.com

Scheme: http
Forward Hostname/IP: 192.168.0.108
Forward Port: 3050

[✓] Cache Assets
[✓] Block Common Exploits
[✓] Websockets Support
```

**Alternative Forward Hostname** (if NPM is in Docker):
- Use: `host.docker.internal` instead of `192.168.0.108`

#### SSL Tab
```
SSL Certificate: [Request a new SSL Certificate]

Email Address: your@email.com

[✓] Force SSL
[✓] HTTP/2 Support
[✓] HSTS Enabled
[✓] I Agree to the Let's Encrypt Terms of Service
```

Click **"Save"**

## Step 3: DNS Configuration

Ensure your domain DNS points to your server:

```
A Record:
  Host: @
  Value: <your-public-ip>
  TTL: 300

A Record (optional www):
  Host: www
  Value: <your-public-ip>
  TTL: 300
```

**If using internal DNS:**
```
A Record:
  Host: jankbuild.com
  Value: 192.168.0.108
```

## Step 4: Test Configuration

### Test Local Access
```powershell
curl http://localhost:3050
# Should return HTML
```

### Test HTTP Access (before SSL)
```powershell
curl http://jankbuild.com
# Should redirect to HTTPS or return content
```

### Test HTTPS Access (after SSL setup)
```powershell
curl https://jankbuild.com
# Should return HTML with valid certificate
```

### Test in Browser
1. Open: `https://jankbuild.com`
2. Should show JankBuild homepage
3. Check browser padlock (SSL certificate valid)

## Advanced Configuration (Optional)

### Custom Nginx Configuration

In NPM → Proxy Host → "Advanced" tab:

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

# Static assets caching (30 days)
location /_next/static/ {
    proxy_pass http://192.168.0.108:3050;
    proxy_cache_valid 200 30d;
    add_header Cache-Control "public, immutable";
}

# Enable gzip compression
gzip on;
gzip_vary on;
gzip_proxied any;
gzip_comp_level 6;
gzip_types text/plain text/css text/xml text/javascript application/json application/javascript application/xml+rss application/rss+xml font/truetype font/opentype application/vnd.ms-fontobject image/svg+xml;
```

### Access Lists (Security)

Create access list in NPM:
1. Go to "Access Lists" → "Add Access List"
2. Name: "Internal Network Only"
3. Add: `192.168.0.0/24` (Allow)
4. Apply to JankBuild proxy host

### Rate Limiting

In "Advanced" tab:
```nginx
# Limit API requests to 10/second per IP
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
limit_req zone=api_limit burst=20 nodelay;
```

## Troubleshooting

### Issue: 502 Bad Gateway

**Cause:** NPM can't reach JankBuild

**Solutions:**
1. Verify JankBuild is running:
   ```powershell
   curl http://localhost:3050
   docker ps  # or pm2 status
   ```

2. Check Forward IP in NPM:
   - Should be `192.168.0.108` or `host.docker.internal`
   - Port should be `3050`

3. Test from NPM container:
   ```powershell
   docker exec -it <npm-container> curl http://host.docker.internal:3050
   ```

4. Check Windows Firewall:
   ```powershell
   # Allow port 3050 (if needed)
   New-NetFirewallRule -DisplayName "JankBuild" -Direction Inbound -LocalPort 3050 -Protocol TCP -Action Allow
   ```

### Issue: SSL Certificate Failed

**Cause:** Let's Encrypt can't verify domain

**Solutions:**
1. Ensure port 80 and 443 are forwarded to your server (router/firewall)
2. Verify DNS points to correct public IP
3. Check NPM has internet access
4. Try HTTP-01 challenge instead of DNS-01

### Issue: Can't access from outside network

**Cause:** Port forwarding or firewall

**Solutions:**
1. Forward ports in router:
   - Port 80 → 192.168.0.108:80
   - Port 443 → 192.168.0.108:443

2. Check Windows Firewall allows NPM ports

3. Verify public IP matches DNS A record

### Issue: Slow performance

**Solutions:**
1. Enable caching (see Advanced Configuration)
2. Enable HTTP/2 in SSL tab
3. Increase JankBuild resources:
   ```yaml
   # docker-compose.yml
   deploy:
     resources:
       limits:
         memory: 2G
   ```

## Health Monitoring

### Check JankBuild Status
```powershell
# Docker
docker ps
docker logs jankbuild

# PM2
pm2 status
pm2 logs jankbuild

# Native Node.js
# Check process manager or Task Manager
```

### Check NPM Status
```powershell
# If NPM is in Docker
docker ps | findstr nginx

# Check NPM logs
docker logs nginx-proxy-manager
```

### Monitor Resources
```powershell
# Docker stats
docker stats jankbuild

# System resources
Get-Counter '\Process(node)\% Processor Time'
```

## Quick Commands Reference

```powershell
# Start JankBuild (Docker)
docker-compose up -d

# Stop JankBuild
docker-compose down

# Restart JankBuild
docker-compose restart

# View logs
docker-compose logs -f

# Test local access
curl http://localhost:3050

# Test public access
curl https://jankbuild.com

# Check NPM proxy hosts
# Open: http://192.168.0.108:81

# Rebuild after changes
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## Configuration Checklist

- [ ] JankBuild running on port 3050
- [ ] Can access `http://localhost:3050` locally
- [ ] NPM proxy host created for `jankbuild.com`
- [ ] Forward hostname: `192.168.0.108` or `host.docker.internal`
- [ ] Forward port: `3050`
- [ ] SSL certificate requested and active
- [ ] Can access `https://jankbuild.com` in browser
- [ ] SSL certificate shows valid (green padlock)
- [ ] HTTP automatically redirects to HTTPS
- [ ] EDHREC/MTGJson data imported (optional)
- [ ] Admin user created

## Support

- **Self-Hosting Guide**: `SELF_HOSTING.md`
- **Quick Start**: `QUICK_START.md`
- **Deployment Checklist**: `DEPLOYMENT_CHECKLIST.md`
- **GitHub Issues**: https://github.com/silvernova0/magic/issues

---

**Your Configuration Summary:**
- **Local URL**: `http://localhost:3050`
- **Public URL**: `https://jankbuild.com`
- **NPM Admin**: `http://192.168.0.108:81`
- **Server IP**: `192.168.0.108`
- **JankBuild Port**: `3050`
