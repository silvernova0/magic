# JankBuild Quick Start Script for Windows
# Run this script to set up and start JankBuild on port 3050

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  JankBuild Self-Hosting Setup" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Check prerequisites
Write-Host "Checking prerequisites..." -ForegroundColor Yellow

# Check Node.js
$nodeVersion = node --version 2>$null
if ($nodeVersion) {
    Write-Host "✓ Node.js installed: $nodeVersion" -ForegroundColor Green
} else {
    Write-Host "✗ Node.js not found. Please install Node.js 22.x" -ForegroundColor Red
    exit 1
}

# Check npm
$npmVersion = npm --version 2>$null
if ($npmVersion) {
    Write-Host "✓ npm installed: $npmVersion" -ForegroundColor Green
} else {
    Write-Host "✗ npm not found" -ForegroundColor Red
    exit 1
}

# Check Docker (optional)
$dockerVersion = docker --version 2>$null
if ($dockerVersion) {
    Write-Host "✓ Docker installed: $dockerVersion" -ForegroundColor Green
    $hasDocker = $true
} else {
    Write-Host "! Docker not found (optional - will use Node.js directly)" -ForegroundColor Yellow
    $hasDocker = $false
}

Write-Host ""
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  Deployment Method Selection" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Docker (Recommended - containerized deployment)" -ForegroundColor White
Write-Host "2. Node.js (Direct deployment on Windows)" -ForegroundColor White
Write-Host "3. PM2 (Node.js with process manager)" -ForegroundColor White
Write-Host ""

$choice = Read-Host "Select deployment method (1-3)"

switch ($choice) {
    "1" {
        if (-not $hasDocker) {
            Write-Host "✗ Docker not installed. Please install Docker Desktop for Windows" -ForegroundColor Red
            Write-Host "Download: https://www.docker.com/products/docker-desktop/" -ForegroundColor Yellow
            exit 1
        }
        
        Write-Host ""
        Write-Host "=====================================" -ForegroundColor Cyan
        Write-Host "  Docker Deployment" -ForegroundColor Cyan
        Write-Host "=====================================" -ForegroundColor Cyan
        Write-Host ""
        
        # Check if .env exists
        if (-not (Test-Path ".env")) {
            Write-Host "⚠ .env file not found. Creating from template..." -ForegroundColor Yellow
            Copy-Item ".env.production.template" ".env"
            Write-Host "✓ Created .env file. Please edit it with your settings." -ForegroundColor Green
            Write-Host ""
            Write-Host "Press any key to open .env in notepad..."
            $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
            notepad .env
            Write-Host ""
            Write-Host "After editing .env, press any key to continue..."
            $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
        }
        
        Write-Host "Building Docker image..." -ForegroundColor Yellow
        docker-compose build
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ Docker image built successfully" -ForegroundColor Green
            
            Write-Host ""
            Write-Host "Starting container..." -ForegroundColor Yellow
            docker-compose up -d
            
            if ($LASTEXITCODE -eq 0) {
                Write-Host "✓ Container started successfully" -ForegroundColor Green
                Write-Host ""
                Write-Host "=====================================" -ForegroundColor Cyan
                Write-Host "  JankBuild is now running!" -ForegroundColor Green
                Write-Host "=====================================" -ForegroundColor Cyan
                Write-Host ""
                Write-Host "Local access: http://localhost:3050" -ForegroundColor White
                Write-Host "Configure Nginx Proxy Manager to forward jankbuild.com → 192.168.0.108:3050" -ForegroundColor Yellow
                Write-Host ""
                Write-Host "Useful commands:" -ForegroundColor Cyan
                Write-Host "  docker-compose logs -f        View logs" -ForegroundColor White
                Write-Host "  docker-compose restart        Restart container" -ForegroundColor White
                Write-Host "  docker-compose down           Stop container" -ForegroundColor White
            } else {
                Write-Host "✗ Failed to start container" -ForegroundColor Red
                Write-Host "Check logs: docker-compose logs" -ForegroundColor Yellow
            }
        } else {
            Write-Host "✗ Failed to build Docker image" -ForegroundColor Red
        }
    }
    
    "2" {
        Write-Host ""
        Write-Host "=====================================" -ForegroundColor Cyan
        Write-Host "  Node.js Deployment" -ForegroundColor Cyan
        Write-Host "=====================================" -ForegroundColor Cyan
        Write-Host ""
        
        # Install dependencies
        Write-Host "Installing dependencies..." -ForegroundColor Yellow
        npm ci
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ Dependencies installed" -ForegroundColor Green
            
            # Generate Prisma client
            Write-Host "Generating Prisma client..." -ForegroundColor Yellow
            npx prisma generate
            
            # Build application
            Write-Host "Building application..." -ForegroundColor Yellow
            npm run build
            
            if ($LASTEXITCODE -eq 0) {
                Write-Host "✓ Application built successfully" -ForegroundColor Green
                Write-Host ""
                Write-Host "=====================================" -ForegroundColor Cyan
                Write-Host "  Build Complete!" -ForegroundColor Green
                Write-Host "=====================================" -ForegroundColor Cyan
                Write-Host ""
                Write-Host "To start the application, run:" -ForegroundColor Yellow
                Write-Host "  npm run start" -ForegroundColor White
                Write-Host ""
                Write-Host "The application will run on: http://localhost:3050" -ForegroundColor White
                Write-Host ""
                Write-Host "To run in background, use Method 3 (PM2)" -ForegroundColor Yellow
            } else {
                Write-Host "✗ Build failed" -ForegroundColor Red
            }
        } else {
            Write-Host "✗ Failed to install dependencies" -ForegroundColor Red
        }
    }
    
    "3" {
        Write-Host ""
        Write-Host "=====================================" -ForegroundColor Cyan
        Write-Host "  PM2 Deployment" -ForegroundColor Cyan
        Write-Host "=====================================" -ForegroundColor Cyan
        Write-Host ""
        
        # Check if PM2 is installed
        $pm2Version = pm2 --version 2>$null
        if (-not $pm2Version) {
            Write-Host "Installing PM2..." -ForegroundColor Yellow
            npm install -g pm2
            npm install -g pm2-windows-startup
            
            Write-Host "Configuring PM2 startup..." -ForegroundColor Yellow
            pm2-startup install
        } else {
            Write-Host "✓ PM2 already installed: $pm2Version" -ForegroundColor Green
        }
        
        # Install dependencies
        Write-Host "Installing dependencies..." -ForegroundColor Yellow
        npm ci
        
        # Generate Prisma client
        Write-Host "Generating Prisma client..." -ForegroundColor Yellow
        npx prisma generate
        
        # Build application
        Write-Host "Building application..." -ForegroundColor Yellow
        npm run build
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ Application built successfully" -ForegroundColor Green
            
            # Start with PM2
            Write-Host "Starting with PM2..." -ForegroundColor Yellow
            pm2 start npm --name "jankbuild" -- run start
            pm2 save
            
            Write-Host ""
            Write-Host "=====================================" -ForegroundColor Cyan
            Write-Host "  JankBuild is now running!" -ForegroundColor Green
            Write-Host "=====================================" -ForegroundColor Cyan
            Write-Host ""
            Write-Host "Local access: http://localhost:3050" -ForegroundColor White
            Write-Host ""
            Write-Host "PM2 commands:" -ForegroundColor Cyan
            Write-Host "  pm2 status               View status" -ForegroundColor White
            Write-Host "  pm2 logs jankbuild       View logs" -ForegroundColor White
            Write-Host "  pm2 restart jankbuild    Restart app" -ForegroundColor White
            Write-Host "  pm2 stop jankbuild       Stop app" -ForegroundColor White
            Write-Host "  pm2 monit                Monitor resources" -ForegroundColor White
        } else {
            Write-Host "✗ Build failed" -ForegroundColor Red
        }
    }
    
    default {
        Write-Host "Invalid choice" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  Next Steps" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Configure Nginx Proxy Manager:" -ForegroundColor Yellow
Write-Host "   - Open NPM: http://192.168.0.108:81" -ForegroundColor White
Write-Host "   - Add Proxy Host: jankbuild.com → 192.168.0.108:3050" -ForegroundColor White
Write-Host "   - Enable SSL with Let's Encrypt" -ForegroundColor White
Write-Host ""
Write-Host "2. Import Card Database (optional):" -ForegroundColor Yellow
Write-Host "   - Download MTGJson files from https://mtgjson.com" -ForegroundColor White
Write-Host "   - Place in: C:\magicapp\data\mtgjson\" -ForegroundColor White
Write-Host "   - Run: npm run import:mtgjson:full" -ForegroundColor White
Write-Host ""
Write-Host "3. Create Admin User:" -ForegroundColor Yellow
Write-Host "   - Run: npm run create-admin" -ForegroundColor White
Write-Host ""
Write-Host "📖 See SELF_HOSTING.md for detailed documentation" -ForegroundColor Cyan
Write-Host ""
