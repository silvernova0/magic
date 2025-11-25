# 🎯 QUICK START: Windows RTX 5070 Ti Training

**Goal**: Train a 7B Commander deck-building model on 75k-100k examples

**What you have**:
- ✅ Linux machine for data collection
- ✅ Windows 11 Pro + RTX 5070 Ti (16GB VRAM) for training
- ✅ SMB share: `smb://192.168.0.151/aitrainingv4/`
- ✅ Current dataset: 27,296 examples

**What you'll do**:
1. Scrape 62,500 more decks from MTGGoldfish (20 hours, background)
2. Transfer to Windows via SMB share
3. Train 7B model (12 hours, automatic)

---

## 📝 Three Simple Commands

```bash
# 1. Test connection (5 min)
bash scripts/test-smb-connection.sh

# 2. Collect data (15-20 hours, runs in background)
bash scripts/collect-training-data-windows.sh

# 3. Package & transfer (30 min, after step 2 completes)
bash scripts/package-training-data.sh
```

That's it for Linux! Then follow `WINDOWS_RTX_TRAINING_GUIDE.md` on Windows.

---

## 📖 Full Documentation

| File | Purpose |
|------|---------|
| `WINDOWS_TRAINING_WORKFLOW.md` | Complete overview and troubleshooting |
| `WINDOWS_RTX_TRAINING_GUIDE.md` | Detailed Windows training instructions |
| This file (`QUICK_START_RTX.md`) | Ultra-condensed quick reference |

---

## ⏰ Timeline

| Phase | Duration | What happens |
|-------|----------|--------------|
| Test SMB | 5 min | Verify Windows share accessible |
| Data collection | 15-20 hours | Background scraping (can run overnight) |
| Package/transfer | 30 min | Convert to v3, copy to Windows |
| **Linux total** | **~20 hours** | **Mostly unattended** |
| Windows setup | 1-2 hours | Install Python, CUDA, dependencies |
| Training | 10-12 hours | Automatic (don't close PowerShell) |
| Testing | 30 min | Validate model outputs |
| **Windows total** | **~13 hours** | **Mostly unattended** |
| **Grand total** | **~33 hours** | **~3 hours hands-on** |

---

## 💾 Data Sources

**What you already have** (27,296 examples):
- EDHREC average decks: 2,557
- EDHTop16/TopDeck cEDH: 1,334
- Existing v3 data: 23,405

**What you'll collect**:
- MTGGoldfish (25 decks × 2,500 commanders): 62,500
- **New total: ~89,796 examples** ← Perfect for 7B!

**Optional additions**:
- Moxfield themes: +7,500
- Archidekt popular: +5,000

---

## 🖥️ Windows Training Details

**Model options**:
- Mistral 7B Instruct v0.3 (recommended)
- Llama 3.1 8B Instruct (alternative)

**Training config**:
- Batch size: 2
- Gradient accumulation: 16 (effective batch: 32)
- Sequence length: 512 tokens
- LoRA rank: 32
- Epochs: 3
- VRAM usage: 14-15 GB / 16 GB

**What you'll need on Windows**:
- Python 3.11
- NVIDIA CUDA Toolkit 12.1
- 50GB free disk space
- Power plan: High Performance
- Sleep: Disabled during training

---

## ✅ Success Checklist

**Before you start**:
- [ ] Windows machine is on and accessible at 192.168.0.151
- [ ] SMB share `aitrainingv4` is configured
- [ ] Linux machine has internet connection
- [ ] You have time for 20+ hours of scraping

**Linux phase**:
- [ ] SMB connection test passed
- [ ] Data collection started
- [ ] Scrapers running in background (`ps aux | grep scrape`)
- [ ] Monitoring logs occasionally (`tail -f *.log`)
- [ ] Data packaged and transferred to Windows

**Windows phase**:
- [ ] Package copied from network share to `C:\MTG_Training\`
- [ ] Python 3.11 installed
- [ ] CUDA 12.1 installed
- [ ] PyTorch with CUDA installed
- [ ] Training dependencies installed
- [ ] GPU detected (`nvidia-smi` shows RTX 5070 Ti)
- [ ] Training script running
- [ ] Monitor script showing GPU usage
- [ ] Training completed successfully
- [ ] Model tested and generates valid outputs

---

## 🆘 Quick Troubleshooting

**SMB won't connect**:
```bash
ping 192.168.0.151  # Should respond
smbclient -L //192.168.0.151  # Should list shares
```
→ Check Windows firewall and sharing settings

**Scraper stopped**:
```bash
ps aux | grep scrape  # Check if still running
tail -50 mtggoldfish_commander.log  # Check for errors
```
→ Just restart it, has deduplication built-in

**Windows CUDA OOM**:
→ Edit `train_commander_7b.py`: `BATCH_SIZE = 1`

**Training loss not decreasing**:
→ Normal for first 100-200 steps, should drop after warmup

---

## 🎓 What You'll Learn

This process teaches you:
- ✅ Large-scale web scraping with deduplication
- ✅ Data pipeline: raw → structured → training format
- ✅ Distributed workflow (Linux scraping + Windows training)
- ✅ SMB/CIFS networking between Linux/Windows
- ✅ LoRA fine-tuning on consumer GPU
- ✅ CUDA optimization for limited VRAM
- ✅ Long-running background processes
- ✅ Model validation and testing

---

## 🎯 Expected Results

**After training, your model will**:
- Generate Commander deck structures (not full card lists)
- Understand strategy → card selection patterns
- Respect power levels and brackets
- Handle partner commanders
- Distinguish cEDH from casual
- Apply proper land ratios and mana curves
- **NOT hallucinate cards** (uses database for actual cards)

**Performance vs 3B model**:
- Better strategy coherence
- More nuanced power level understanding
- Stronger tournament meta awareness (from TopDeck data)
- Better combo detection

---

## 📞 Need Help?

1. Check the logs: `*.log` files in current directory
2. Read full docs: `WINDOWS_TRAINING_WORKFLOW.md`
3. Check GPU: `nvidia-smi` on Windows
4. Verify data: `wc -l data/training/*.jsonl`

---

**Ready? Start here**:

```bash
cd /home/social/magicapp
bash scripts/test-smb-connection.sh
```

Good luck! 🚀
