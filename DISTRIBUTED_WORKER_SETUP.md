# Distributed Worker Node Setup

## Hardware Specs
- CPU: i5-12400 (6 cores, 12 threads)
- RAM: 32GB
- Storage: 512GB SSD
- GPU: Intel iGPU (no discrete GPU)
- Current: No OS installed

## Best Use Cases for This Node

### ✅ RECOMMENDED: Web Scraping Worker
**Perfect fit** - CPU-bound, no GPU needed, runs 24/7

**What it does**:
- Scrapes MTGGoldfish, Moxfield, Archidekt, EDHREC
- Collects deck data in parallel with main node
- Stores results to shared SMB location
- Can run multiple scrapers simultaneously

**Advantages**:
- Frees up your main node for development
- 6 cores can run 3-6 scrapers in parallel
- 32GB RAM plenty for web scraping
- SSD good for temporary storage
- No GPU needed

### ✅ GOOD: Data Processing Worker
**Good fit** - CPU-intensive tasks

**What it does**:
- Convert scraped decks to v3 training format
- Deduplicate datasets
- Validate card data
- Generate statistics and reports

### ❌ NOT RECOMMENDED: AI Training
**Poor fit** - needs GPU for efficient training

- iGPU won't accelerate PyTorch training
- Would take 100+ hours to train 7B model on CPU
- Your RTX 5070 Ti is 50-100x faster

---

## Setup Option 1: Ubuntu Server (Headless) - RECOMMENDED

**Best for**: 24/7 scraping/processing node

### Installation Steps

1. **Download Ubuntu Server 24.04 LTS**
   - https://ubuntu.com/download/server
   - Burn to USB with Rufus (Windows) or dd (Linux)

2. **Install Ubuntu Server**
   - Boot from USB
   - Choose "Ubuntu Server (minimized)"
   - Configure:
     - Hostname: `scraper-node-01`
     - Username: `worker`
     - Enable OpenSSH server
     - No extra packages needed

3. **Network Setup**
   - Static IP recommended: `192.168.0.152`
   - Same subnet as main node (192.168.0.108)
   - Gateway: Your router IP

4. **Install Required Software**
   ```bash
   # Update system
   sudo apt update && sudo apt upgrade -y
   
   # Install Python 3.11
   sudo apt install -y python3.11 python3.11-venv python3-pip
   
   # Install git
   sudo apt install -y git
   
   # Install SMB client (to access shared storage)
   sudo apt install -y cifs-utils
   
   # Install monitoring tools
   sudo apt install -y htop tmux
   ```

5. **Mount SMB Share**
   ```bash
   # Create mount point
   sudo mkdir -p /mnt/aitraining
   
   # Add to /etc/fstab for auto-mount
   echo "//192.168.0.151/aitrainingv4 /mnt/aitraining cifs username=YOUR_USER,password=YOUR_PASS,uid=1000,gid=1000 0 0" | sudo tee -a /etc/fstab
   
   # Mount
   sudo mount -a
   ```

6. **Clone Project**
   ```bash
   cd ~
   git clone https://github.com/silvernova0/magic.git
   cd magic
   
   # Create virtualenv
   python3.11 -m venv venv
   source venv/bin/activate
   
   # Install dependencies
   pip install -r requirements.txt
   ```

7. **Start Scrapers**
   ```bash
   # Run multiple scrapers in tmux sessions
   tmux new -s scraper1 -d 'cd ~/magic && source venv/bin/activate && python3 scripts/scrape-archidekt-commanders.py'
   tmux new -s scraper2 -d 'cd ~/magic && source venv/bin/activate && python3 scripts/scrape-edhrec-average-decks.py'
   
   # Monitor
   tmux ls
   tmux attach -t scraper1
   ```

---

## Setup Option 2: Docker Container Host

**Best for**: Isolated, reproducible environments

### Installation

1. **Install Ubuntu Server** (same as Option 1, steps 1-3)

2. **Install Docker**
   ```bash
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh
   sudo usermod -aG docker $USER
   ```

3. **Create Dockerfile for Scraper**
   ```dockerfile
   FROM python:3.11-slim
   
   WORKDIR /app
   
   RUN apt-get update && apt-get install -y git cifs-utils
   
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   
   COPY scripts/ ./scripts/
   COPY data/ ./data/
   
   CMD ["python3", "scripts/scrape-mtggoldfish-by-commander.py"]
   ```

4. **Run Multiple Containers**
   ```bash
   # Build image
   docker build -t mtg-scraper .
   
   # Run different scrapers
   docker run -d --name scraper-mtggoldfish -v /mnt/aitraining:/data mtg-scraper python3 scripts/scrape-mtggoldfish-by-commander.py
   docker run -d --name scraper-moxfield -v /mnt/aitraining:/data mtg-scraper python3 scripts/scrape-moxfield-themes.py
   
   # Monitor
   docker ps
   docker logs -f scraper-mtggoldfish
   ```

---

## Setup Option 3: Proxmox VE (Advanced)

**Best for**: Running multiple VMs/containers, home lab setup

- Allows running multiple isolated workers
- Can allocate resources dynamically
- Overkill for just scraping, but very flexible

---

## Recommended Configuration: Parallel Scraping

With 6 cores and 32GB RAM, you can run **4-6 scrapers simultaneously**:

### Scraper Distribution

**Main Node (192.168.0.108)** - Development + Testing:
- Dev server (Next.js)
- Database operations
- 1-2 scrapers for new strategies

**Worker Node (192.168.0.152)** - Production Scraping:
1. **MTGGoldfish Commander** (2 cores, 4GB RAM)
   - Target: 2,500 commanders
   - Output: 12,000-15,000 decks

2. **Archidekt Popular** (1 core, 4GB RAM)
   - Target: Top 1,000 commanders
   - Output: 5,000-8,000 decks

3. **EDHREC Average Decks** (1 core, 4GB RAM)
   - Target: All commanders with average decklists
   - Output: 2,000-3,000 decks

4. **Moxfield Themes** (1 core, 4GB RAM)
   - Target: All theme/bracket combinations
   - Output: 2,000-4,000 decks

5. **Data Validator** (1 core, 2GB RAM)
   - Validates scraped decks
   - Removes duplicates
   - Checks card counts

**Total**: 22,000-34,000 additional decks in parallel

---

## Network Setup Diagram

```
Router (192.168.0.1)
  │
  ├─ Main Node (192.168.0.108)
  │    - Ubuntu Desktop
  │    - Development
  │    - Database
  │    - Web server
  │
  ├─ Worker Node (192.168.0.152)
  │    - Ubuntu Server
  │    - Scraping only
  │    - Headless
  │
  └─ SMB Share (192.168.0.151)
       - aitrainingv4
       - Stores all scraped data
       - Accessible by both nodes
```

---

## Quick Start: 15-Minute Setup

```bash
# 1. Install Ubuntu Server 24.04 on spare PC (10 min)
# 2. Boot and configure network

# 3. SSH from main node
ssh worker@192.168.0.152

# 4. Quick setup script
sudo apt update && sudo apt install -y python3.11 python3.11-venv python3-pip git cifs-utils htop tmux

# 5. Clone and setup
cd ~
git clone https://github.com/silvernova0/magic.git
cd magic
python3.11 -m venv venv
source venv/bin/activate
pip install requests beautifulsoup4 prisma

# 6. Mount SMB share
sudo mkdir -p /mnt/aitraining
sudo mount -t cifs //192.168.0.151/aitrainingv4 /mnt/aitraining -o username=YOUR_USER,password=YOUR_PASS

# 7. Start scraper
nohup python3 scripts/scrape-archidekt-commanders.py > archidekt.log 2>&1 &
```

---

## Resource Allocation

| Task | Cores | RAM | Duration | Output |
|------|-------|-----|----------|--------|
| MTGGoldfish | 2 | 4GB | 8-12h | 15k decks |
| Archidekt | 1 | 4GB | 6-10h | 8k decks |
| EDHREC | 1 | 4GB | 4-8h | 3k decks |
| Moxfield | 1 | 4GB | 12-24h | 4k decks |
| Validator | 1 | 2GB | 1-2h | - |
| **Total** | **6** | **18GB** | **24h** | **30k decks** |

Remaining: 14GB RAM for OS overhead

---

## Monitoring & Management

### From Main Node

```bash
# SSH to worker
ssh worker@192.168.0.152

# Check running processes
htop

# Check scraper logs
tail -f ~/magic/archidekt.log

# Check disk usage
df -h

# Check network
ip a
```

### Tmux Sessions (Persistent)

```bash
# Create session
tmux new -s scraper1

# Detach: Ctrl+B, then D

# List sessions
tmux ls

# Reattach
tmux attach -t scraper1

# Kill session
tmux kill-session -t scraper1
```

---

## Cost-Benefit Analysis

### Time Savings
- **Current**: 1 node running 2 scrapers = 15-20 hours
- **With worker**: 2 nodes running 6 scrapers = 8-12 hours
- **Savings**: 40-50% faster data collection

### Data Volume
- **Current**: ~38,000 training examples
- **With worker**: ~60,000-70,000 training examples
- **Improvement**: 60-80% more data

### Development Impact
- **Current**: Main node busy scraping, can't dev
- **With worker**: Main node free for development
- **Benefit**: Parallel workflows

---

## Alternative: Rent Cloud Instance

If setup is too complex, consider:

**AWS EC2 t3.medium**:
- 2 vCPU, 4GB RAM
- $0.04/hour = $1/day
- Run scrapers for 24h = $1 total
- No hardware setup needed

**DigitalOcean Droplet**:
- 2 vCPU, 4GB RAM
- $24/month or $0.036/hour
- Better for long-term use

---

## Recommendation

**For your use case**: Install **Ubuntu Server 24.04** (Option 1)

**Why**:
- No GUI = more resources for scraping
- SSH access from main node
- Runs 24/7 reliably
- Easy to manage with tmux
- Perfect for i5-12400 + 32GB RAM

**Setup time**: 15-30 minutes
**Data collection boost**: 60-80% more decks
**Development freedom**: Main node freed up

Let me know if you want detailed step-by-step instructions for Ubuntu Server installation!
