# Windows RTX 5070 Ti Training - Complete Workflow

Complete end-to-end workflow for training a 7B Commander deck-building model on your Windows machine with RTX 5070 Ti.

## 📋 Overview

**Goal**: Train Mistral 7B or Llama 3.1 8B model on 75,000-100,000 Commander deck examples

**Hardware**:
- 💻 Windows 11 Pro machine with RTX 5070 Ti (16GB VRAM)
- 🐧 Linux data collection machine (current)
- 🔌 SMB share: `smb://192.168.0.151/aitrainingv4/`

**Timeline**:
- Data collection: 15-20 hours (Linux, can run overnight)
- Windows setup: 1-2 hours
- Training: 10-12 hours (Windows, automatic)
- **Total**: ~28-34 hours (mostly unattended)

---

## 🚀 Quick Start

### Step 1: Test SMB Connection (5 minutes)

```bash
cd /home/social/magicapp
bash scripts/test-smb-connection.sh
```

This verifies your Windows share is accessible and has write permissions.

### Step 2: Start Data Collection (15-20 hours, runs in background)

```bash
bash scripts/collect-training-data-windows.sh
```

This will:
- Scrape **25 decks per commander** from MTGGoldfish (~62,500 new examples)
- Optionally scrape Moxfield themes (~7,500 examples)
- Optionally scrape Archidekt popular commanders (~5,000 examples)
- All can run in parallel overnight

**Monitor progress**:
```bash
# Watch all scrapers at once
watch -n 60 'tail -3 mtggoldfish_commander.log moxfield_themes.log archidekt.log'

# Check how many examples collected
wc -l data/training/*.jsonl

# See current status
tail -f mtggoldfish_commander.log
```

### Step 3: Package and Transfer (30 minutes, after scraping completes)

```bash
bash scripts/package-training-data.sh
```

This will:
- Convert all scraped data to v3 training format
- Verify data quality and show statistics
- Create training package with all necessary files
- Mount SMB share
- Copy everything to your Windows machine
- Include training guide and quick start instructions

### Step 4: Windows Training (see `WINDOWS_RTX_TRAINING_GUIDE.md`)

On your Windows machine:
1. Copy package from network share to `C:\MTG_Training\`
2. Follow `WINDOWS_RTX_TRAINING_GUIDE.md` Phase 2 onwards
3. Install Python, CUDA, PyTorch
4. Run training script (~12 hours)
5. Test and package trained model

---

## 📊 Expected Dataset Size

**Current data** (already collected):
- EDHREC average decks: 2,557
- EDHTop16/TopDeck cEDH: 1,334
- v3 structured (existing): 23,405
- **Current total: ~27,296 examples**

**After MTGGoldfish scraping** (25 decks/commander):
- MTGGoldfish commander-specific: ~62,500
- **New total: ~89,796 examples**

**Optional additions**:
- Moxfield themes: +7,500
- Archidekt popular: +5,000
- **Maximum total: ~102,296 examples**

This is **excellent** for 7B model training!

---

## 🔧 Troubleshooting

### SMB Share Issues

**Can't connect to share:**
```bash
# Check if Windows machine is reachable
ping 192.168.0.151

# List available shares
smbclient -L //192.168.0.151

# Manual mount with credentials
sudo mount -t cifs //192.168.0.151/aitrainingv4 /mnt/test -o user=YOUR_USERNAME
```

**Permission denied:**
- On Windows: Right-click folder → Properties → Sharing
- Click "Advanced Sharing" → Check "Share this folder"
- Click "Permissions" → Add "Everyone" with Full Control
- Click "Security" tab → Edit → Add "Everyone"

### Scraping Issues

**Scraper stopped/crashed:**
```bash
# Check if process is still running
ps aux | grep scrape

# View last 50 lines of log
tail -50 mtggoldfish_commander.log

# Restart scraper (has deduplication, won't re-scrape)
nohup python3 scripts/scrape-mtggoldfish-by-commander.py \
  --decks-per-commander 25 \
  > mtggoldfish_commander.log 2>&1 &
```

**Out of disk space:**
```bash
# Check disk usage
df -h

# Each deck is ~3-5KB, so 100k decks = ~500MB max
# You need <1GB for all training data
```

### Windows Training Issues

See `WINDOWS_RTX_TRAINING_GUIDE.md` → Troubleshooting section

---

## 📁 File Structure

```
/home/social/magicapp/
├── scripts/
│   ├── collect-training-data-windows.sh      ← Start here (Step 2)
│   ├── package-training-data.sh              ← Run after scraping (Step 3)
│   ├── test-smb-connection.sh                ← Test connection first (Step 1)
│   ├── scrape-mtggoldfish-by-commander.py    ← Main scraper
│   ├── scrape-moxfield-themes.py             ← Optional
│   ├── scrape-archidekt-commanders.py        ← Optional
│   └── convert-to-v3-training.py             ← Auto-run by package script
│
├── data/training/
│   ├── v3_structured_training.jsonl          ← Final training data
│   ├── mtggoldfish_by_commander_decks.jsonl  ← New scraped data
│   ├── moxfield_theme_decks.jsonl            ← Optional
│   ├── archidekt_decks.jsonl                 ← Optional
│   ├── topdeck_decklists.json                ← cEDH tournaments
│   └── edhtop16_tournaments.json             ← Tournament metadata
│
├── WINDOWS_RTX_TRAINING_GUIDE.md             ← Complete Windows guide
└── WINDOWS_TRAINING_WORKFLOW.md              ← This file

On Windows (after transfer):
\\192.168.0.151\aitrainingv4\
└── commander_training_package_YYYYMMDD_HHMMSS\
    ├── v3_structured_training.jsonl
    ├── deck_building_rules.json
    ├── dev.db
    ├── topdeck_decklists.json
    ├── README.md
    ├── DATASET_STATS.txt
    ├── WINDOWS_RTX_TRAINING_GUIDE.md
    └── QUICK_START_WINDOWS.txt
```

---

## ⚡ Performance Expectations

### Linux Data Collection
- **MTGGoldfish**: ~2-3 decks/minute with rate limiting
- **62,500 decks**: ~15-20 hours total
- **Can run overnight**: Yes, uses `nohup` for background execution
- **Memory usage**: <500MB RAM
- **Disk usage**: ~300-500MB for all data

### Windows Training (RTX 5070 Ti)
- **VRAM usage**: 14-15 GB / 16 GB (90-95%)
- **GPU utilization**: 95-100%
- **Temperature**: 70-80°C (normal)
- **System RAM**: 16-32 GB used (depends on available)
- **Training speed**: ~6,000-7,000 examples/hour
- **Total time**: 10-12 hours for 3 epochs
- **Disk space needed**: 50GB (model + checkpoints)

---

## 🎯 Why This Approach?

**Why 7B instead of 3B?**
- 3B struggles to memorize 31k cards AND learn patterns
- 7B has capacity for both knowledge and reasoning
- RTX 5070 Ti can handle it comfortably

**Why separate machines?**
- Linux: Better for web scraping (requests, BeautifulSoup)
- Windows: Native CUDA support, gaming GPU optimized
- SMB transfer is fast and convenient

**Why 25 decks per commander?**
- More than 10: Good variation per commander
- Less than 50: Avoids duplicates and diminishing returns
- Sweet spot for dataset size vs collection time

**Why v3 format?**
- Structured JSON output (not text decks)
- Database handles actual cards (no hallucinations)
- Model learns strategy, not memorization

---

## 📈 Success Metrics

**After training, your model should:**
- ✅ Generate valid deck structures (100 cards, correct colors)
- ✅ Understand commander-specific strategies
- ✅ Respect power levels and brackets
- ✅ Handle partner commanders correctly
- ✅ Distinguish cEDH from casual
- ✅ Apply proper mana curves
- ✅ Select cards by strategy, not random

**How to validate:**
- Run `test_model.py` on Windows (included in guide)
- Compare output to known good decks
- Check if card_selection filters make sense
- Verify strategy matches commander

---

## 🔄 Workflow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ LINUX MACHINE (Data Collection)                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Test SMB connection                                     │
│     ↓                                                       │
│  2. Start scrapers (15-20 hours, background)               │
│     ├── MTGGoldfish: 62,500 decks                          │
│     ├── Moxfield: 7,500 decks (optional)                   │
│     └── Archidekt: 5,000 decks (optional)                  │
│     ↓                                                       │
│  3. Package training data                                   │
│     ├── Convert to v3 format                               │
│     ├── Verify quality                                      │
│     ├── Create package                                      │
│     └── Copy to SMB share                                   │
│                                                             │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ SMB Transfer
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ WINDOWS MACHINE (RTX 5070 Ti Training)                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  4. Setup environment (1-2 hours)                          │
│     ├── Install Python 3.11                                │
│     ├── Install CUDA 12.1                                  │
│     ├── Install PyTorch + dependencies                     │
│     └── Copy training scripts                              │
│     ↓                                                       │
│  5. Train model (10-12 hours, automatic)                   │
│     ├── Mistral 7B or Llama 3.1 8B                         │
│     ├── LoRA fine-tuning                                   │
│     ├── 75k-100k examples                                  │
│     └── 3 epochs                                            │
│     ↓                                                       │
│  6. Test and package                                        │
│     ├── Run test prompts                                   │
│     ├── Validate outputs                                    │
│     └── Package LoRA adapters                              │
│                                                             │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ Copy back or deploy
                         ↓
                    [Production Use]
```

---

## 📞 Support

**Scripts not working?**
1. Check script has execute permission: `chmod +x scripts/*.sh`
2. Ensure you're in `/home/social/magicapp` directory
3. Check logs in current directory (`.log` files)

**Need more commanders?**
- Edit scraper: `--max-commanders 5000` instead of 2500
- Will collect more but take longer

**Want fewer decks per commander?**
- Edit scraper: `--decks-per-commander 10` instead of 25
- Faster collection, less variety per commander

---

## 🎓 Next Steps After Training

1. **Integrate into your app**: Load LoRA adapter in inference code
2. **Compare models**: A/B test 7B vs existing 3B model
3. **Gather feedback**: Track which decks users like/modify
4. **Continuous improvement**: Re-train quarterly with new tournament data
5. **Expand dataset**: Add more commanders, update as new sets release

---

**Ready to start?**

```bash
cd /home/social/magicapp

# Test connection
bash scripts/test-smb-connection.sh

# Start data collection
bash scripts/collect-training-data-windows.sh

# After ~20 hours, package and transfer
bash scripts/package-training-data.sh
```

Then follow `WINDOWS_RTX_TRAINING_GUIDE.md` on your Windows machine!
