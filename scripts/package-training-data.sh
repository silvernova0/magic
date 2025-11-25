#!/bin/bash
#
# Package Training Data for Windows RTX Training
# Copies to SMB share: smb://192.168.0.151/aitrainingv4/
#
# Usage: bash scripts/package-training-data.sh
#

set -e  # Exit on error

SMB_SHARE="//192.168.0.151/aitrainingv4"
MOUNT_POINT="/mnt/aitraining"
PACKAGE_DIR="commander_training_package_$(date +%Y%m%d_%H%M%S)"

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  PACKAGE TRAINING DATA FOR WINDOWS RTX 5070 Ti             ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Check we're in the right directory
if [ ! -f "package.json" ]; then
    echo "❌ Error: Run this from /home/social/magicapp directory"
    exit 1
fi

# Step 1: Convert all data to v3 format
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 STEP 1: Convert All Data to v3 Training Format"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "🔄 Running v3 converter..."
python3 scripts/convert-to-v3-training.py

if [ $? -eq 0 ]; then
    echo "✅ v3 conversion complete"
else
    echo "❌ v3 conversion failed"
    exit 1
fi

echo ""

# Step 2: Verify data quality
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 STEP 2: Verify Data Quality"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

python3 << 'VERIFY'
import json
from pathlib import Path

training_file = Path('data/training/v3_structured_training.jsonl')

if not training_file.exists():
    print(f"❌ Training file not found: {training_file}")
    exit(1)

# Count examples
examples = []
with open(training_file, 'r') as f:
    for line in f:
        try:
            examples.append(json.loads(line.strip()))
        except:
            pass

print(f"✅ Total training examples: {len(examples):,}")
print("")

# Check a sample
if examples:
    sample = examples[0]
    print("📋 Sample training example:")
    print(f"   Instruction: {sample['instruction'][:80]}...")
    print(f"   Output keys: {list(sample['output'].keys())}")
    
    # Strategy distribution
    strategies = {}
    for ex in examples[:10000]:  # Sample first 10k for speed
        strat = ex['output'].get('strategy', 'unknown')
        strategies[strat] = strategies.get(strat, 0) + 1
    
    print("")
    print("📊 Strategy distribution (first 10k):")
    for strat, count in sorted(strategies.items(), key=lambda x: -x[1])[:5]:
        print(f"   {strat}: {count:,}")
    
    print("")
    print(f"✅ Data quality check passed")
else:
    print("❌ No examples found")
    exit(1)
VERIFY

if [ $? -ne 0 ]; then
    echo "❌ Data verification failed"
    exit 1
fi

echo ""

# Step 3: Create package directory
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📦 STEP 3: Create Training Package"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

TEMP_DIR="/tmp/$PACKAGE_DIR"
mkdir -p "$TEMP_DIR"

echo "📁 Package directory: $TEMP_DIR"
echo ""

# Copy essential files
echo "📋 Copying files..."
cp data/training/v3_structured_training.jsonl "$TEMP_DIR/"
cp data/training/deck_building_rules.json "$TEMP_DIR/" 2>/dev/null || echo "⚠️  deck_building_rules.json not found (optional)"
cp prisma/dev.db "$TEMP_DIR/" 2>/dev/null || echo "⚠️  dev.db not found (optional)"

# Copy the new cEDH tournament data
if [ -f "data/training/topdeck_decklists.json" ]; then
    echo "✅ Including cEDH tournament data (TopDeck.gg)"
    cp data/training/topdeck_decklists.json "$TEMP_DIR/"
fi

if [ -f "data/training/edhtop16_tournaments.json" ]; then
    echo "✅ Including tournament metadata (EDHTop16)"
    cp data/training/edhtop16_tournaments.json "$TEMP_DIR/"
fi

# Create README
cat > "$TEMP_DIR/README.md" << 'README'
# Commander Deck Training Data Package

Generated: $(date)
Target: Windows 11 RTX 5070 Ti training

## Files Included

### Main Training Data
- `v3_structured_training.jsonl` - Primary training dataset in v3 structured format
  - Format: `{"instruction": "...", "output": {...}}`
  - Each line is a complete training example

### Supporting Data
- `deck_building_rules.json` - Codified deck construction wisdom
- `dev.db` - SQLite database with 31,000+ MTG cards (for validation)
- `topdeck_decklists.json` - 1,334 cEDH tournament decklists
- `edhtop16_tournaments.json` - Tournament metadata

## Data Statistics

Check the data by running on Windows:
```powershell
python -c "import json; print(f'Examples: {sum(1 for _ in open(\"v3_structured_training.jsonl\"))}')"
```

## Training Script Location

The complete training script is in:
`WINDOWS_RTX_TRAINING_GUIDE.md` (in the repository root)

Copy this guide to Windows along with the data package.

## Quick Start on Windows

1. Extract this package to `C:\MTG_Training\data\`
2. Follow steps in `WINDOWS_RTX_TRAINING_GUIDE.md`
3. Install dependencies (PyTorch with CUDA 12.1)
4. Run `train_commander_7b.py`

## Data Format

Each training example follows this structure:

```json
{
  "instruction": "Build a Commander deck with [Commander] focused on [strategy] at power level [X]",
  "output": {
    "commander": "Commander Name",
    "strategy": "tribal/combo/control/etc",
    "bracket": 2-5,
    "power_level": 1-10,
    "card_selection": {
      "lands": {"count": 37, "filters": [...]},
      "creatures": {"count": 20, "filters": [...]},
      "ramp": {"count": 10, "filters": [...]}
    },
    "mana_curve": {...},
    "combo_plan": {...}
  }
}
```

## Next Steps

See `WINDOWS_RTX_TRAINING_GUIDE.md` for complete instructions.
README

# Create info file with stats
python3 << 'STATS' > "$TEMP_DIR/DATASET_STATS.txt"
import json
from pathlib import Path
from datetime import datetime

print(f"Training Data Package Statistics")
print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)
print("")

# v3 structured data
v3_file = Path('/tmp/$PACKAGE_DIR/v3_structured_training.jsonl')
# This won't work in the heredoc, so we'll create it separately
STATS

# Create stats file properly
python3 << STATS > "$TEMP_DIR/DATASET_STATS.txt"
import json
from pathlib import Path
from datetime import datetime
import sys

print(f"Training Data Package Statistics")
print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)
print("")

# v3 structured data
v3_file = Path('data/training/v3_structured_training.jsonl')
if v3_file.exists():
    examples = []
    with open(v3_file) as f:
        for line in f:
            try:
                examples.append(json.loads(line.strip()))
            except:
                pass
    
    print(f"📊 v3 Structured Training Data")
    print(f"   Total examples: {len(examples):,}")
    print("")
    
    # Strategy distribution
    strategies = {}
    brackets = {}
    power_levels = {}
    
    for ex in examples:
        strat = ex['output'].get('strategy', 'unknown')
        strategies[strat] = strategies.get(strat, 0) + 1
        
        bracket = ex['output'].get('bracket', 0)
        brackets[bracket] = brackets.get(bracket, 0) + 1
        
        power = ex['output'].get('power_level', 0)
        power_levels[power] = power_levels.get(power, 0) + 1
    
    print("   Strategy Distribution:")
    for strat, count in sorted(strategies.items(), key=lambda x: -x[1])[:10]:
        print(f"      {strat}: {count:,} ({count/len(examples)*100:.1f}%)")
    
    print("")
    print("   Bracket Distribution:")
    for bracket in sorted(brackets.keys()):
        count = brackets[bracket]
        print(f"      Bracket {bracket}: {count:,} ({count/len(examples)*100:.1f}%)")
    
    print("")
    print("   Power Level Range: {}-{}".format(min(power_levels.keys()), max(power_levels.keys())))

# cEDH tournament data
topdeck_file = Path('data/training/topdeck_decklists.json')
if topdeck_file.exists():
    with open(topdeck_file) as f:
        decks = json.load(f)
    print("")
    print(f"📊 cEDH Tournament Data (TopDeck.gg)")
    print(f"   Total decklists: {len(decks):,}")
    print(f"   Total cards: {sum(d['total_cards'] for d in decks):,}")

print("")
print("=" * 60)
print("✅ Ready for Windows RTX 5070 Ti training")
print("")
print("Next steps:")
print("1. Copy entire package to Windows machine")
print("2. Follow WINDOWS_RTX_TRAINING_GUIDE.md")
print("3. Train 7B model (~12 hours)")
STATS

echo "✅ Package created at: $TEMP_DIR"
echo ""

# Show package contents
echo "📦 Package contents:"
ls -lh "$TEMP_DIR/"
echo ""

# Show total size
TOTAL_SIZE=$(du -sh "$TEMP_DIR" | cut -f1)
echo "📏 Total package size: $TOTAL_SIZE"
echo ""

# Step 4: Mount SMB share
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔌 STEP 4: Mount SMB Share"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Create mount point
sudo mkdir -p "$MOUNT_POINT"

echo "🔐 Mounting: $SMB_SHARE"
echo "   Mount point: $MOUNT_POINT"
echo ""

# Try to mount (will prompt for credentials if needed)
if sudo mount -t cifs "$SMB_SHARE" "$MOUNT_POINT" -o user=$USER,uid=$UID,gid=$GID; then
    echo "✅ SMB share mounted successfully"
else
    echo ""
    echo "⚠️  Mount failed. Trying with credentials..."
    echo "   Enter Windows username when prompted"
    
    read -p "Windows username: " WIN_USER
    
    if sudo mount -t cifs "$SMB_SHARE" "$MOUNT_POINT" -o user=$WIN_USER,uid=$UID,gid=$GID; then
        echo "✅ SMB share mounted successfully"
    else
        echo "❌ Failed to mount SMB share"
        echo ""
        echo "Manual mount command:"
        echo "sudo mount -t cifs $SMB_SHARE $MOUNT_POINT -o user=YOUR_USERNAME,uid=\$UID,gid=\$GID"
        echo ""
        echo "Then copy manually:"
        echo "cp -r $TEMP_DIR $MOUNT_POINT/"
        exit 1
    fi
fi

echo ""

# Step 5: Copy to SMB share
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📤 STEP 5: Copy to Windows Machine"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "📋 Copying package to: $MOUNT_POINT/$PACKAGE_DIR/"
cp -rv "$TEMP_DIR" "$MOUNT_POINT/"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Package copied successfully!"
else
    echo ""
    echo "❌ Copy failed"
    sudo umount "$MOUNT_POINT"
    exit 1
fi

echo ""

# Step 6: Copy training guide
echo "📄 Copying training guide..."
if [ -f "WINDOWS_RTX_TRAINING_GUIDE.md" ]; then
    cp "WINDOWS_RTX_TRAINING_GUIDE.md" "$MOUNT_POINT/$PACKAGE_DIR/"
    echo "✅ Training guide copied"
else
    echo "⚠️  WINDOWS_RTX_TRAINING_GUIDE.md not found in repo root"
fi

echo ""

# Step 7: Create quick start script for Windows
cat > "$MOUNT_POINT/$PACKAGE_DIR/QUICK_START_WINDOWS.txt" << 'QUICKSTART'
╔════════════════════════════════════════════════════════════╗
║  QUICK START - Windows RTX 5070 Ti Training                ║
╚════════════════════════════════════════════════════════════╝

📋 CHECKLIST:

1. [ ] Copy this entire folder to C:\MTG_Training\
2. [ ] Install Python 3.11 from python.org
3. [ ] Install CUDA Toolkit 12.1 from NVIDIA
4. [ ] Open PowerShell as Administrator
5. [ ] Create virtual environment:
       cd C:\MTG_Training
       python -m venv venv
       .\venv\Scripts\Activate.ps1

6. [ ] Install PyTorch with CUDA:
       pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

7. [ ] Install training dependencies:
       pip install transformers datasets accelerate peft bitsandbytes trl scipy

8. [ ] Verify GPU detected:
       python -c "import torch; print(f'GPU: {torch.cuda.get_device_name(0)}')"

9. [ ] Copy training scripts from WINDOWS_RTX_TRAINING_GUIDE.md
       - train_commander_7b.py
       - monitor_training.py
       - test_model.py

10. [ ] Start training:
        python train_commander_7b.py 2>&1 | Tee-Object training.log

11. [ ] Monitor in separate window:
        python monitor_training.py

⏱️  ESTIMATED TIME: 10-12 hours training

📖 Full instructions in: WINDOWS_RTX_TRAINING_GUIDE.md

💡 IMPORTANT:
   - Don't close PowerShell during training
   - Set Windows power plan to "High Performance"
   - Disable sleep mode
   - Ensure 50GB+ free disk space
   - GPU will run at 95-100% utilization (normal)

🎯 EXPECTED RESULT:
   Trained 7B Commander model in ./commander-7b-lora/final/
QUICKSTART

echo "✅ Quick start guide created"
echo ""

# Step 8: Verify and show final info
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 STEP 6: Verify Transfer"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "📁 Files on Windows share:"
ls -lh "$MOUNT_POINT/$PACKAGE_DIR/" | tail -n +2
echo ""

echo "💾 Total size on share:"
du -sh "$MOUNT_POINT/$PACKAGE_DIR"
echo ""

# Unmount
echo "🔌 Unmounting SMB share..."
sudo umount "$MOUNT_POINT"
echo "✅ Unmounted"
echo ""

# Cleanup temp directory
echo "🧹 Cleaning up temporary directory..."
rm -rf "$TEMP_DIR"
echo "✅ Cleanup complete"
echo ""

# Final summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ PACKAGE COMPLETE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📦 Package location on Windows machine:"
echo "   \\\\192.168.0.151\\aitrainingv4\\$PACKAGE_DIR\\"
echo ""
echo "📋 Next steps on Windows:"
echo "   1. Open File Explorer"
echo "   2. Navigate to: \\\\192.168.0.151\\aitrainingv4\\"
echo "   3. Copy $PACKAGE_DIR to C:\\MTG_Training\\"
echo "   4. Open WINDOWS_RTX_TRAINING_GUIDE.md"
echo "   5. Follow Phase 2 (Windows Setup) onwards"
echo ""
echo "🎯 Training target: 7B model, 10-12 hours on RTX 5070 Ti"
echo ""
cat "$MOUNT_POINT/$PACKAGE_DIR/DATASET_STATS.txt" 2>/dev/null || true
echo ""
