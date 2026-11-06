# Quick Start: Train Your Commander Model

## TL;DR
1. **Scrape 3000 decks from EDHREC** (~3-5 hours automated)
2. **Download Llama 3.1 8B** (~30 min, 16GB)
3. **Train model** (~12-18 hours on Intel Arc)
4. **Deploy** (~2-3 hours integration)

Total time: ~2-3 days mostly automated

---

## Step 1: Scrape EDHREC Decks (Start Now)

```powershell
# Navigate to project
cd C:\magicapp

# Run scraper (will take 3-5 hours)
& "C:\Users\fuckthisshit\openvino_env\Scripts\python.exe" scripts\scrape-edhrec-decks.py
```

**What it does**:
- Fetches top 3000 commanders from EDHREC
- Scrapes average decklist for each
- Saves to `data/training/edhrec_decks.jsonl`
- Rate limited (2-4 sec between requests)

**Expected output**:
```
[1/3000] Scraping Atraxa, Praetors' Voice...
  ✓ Found 98 cards
[2/3000] Scraping The Ur-Dragon...
  ✓ Found 100 cards
...
✓ Successfully scraped: 2847 decks
✗ Failed: 153 decks
📁 Saved to: data/training/edhrec_decks.jsonl
```

**Run this now** - it's automated and takes hours. Come back when done.

---

## Step 2: Validate Data Quality

```powershell
# Check what we got
& "C:\Users\fuckthisshit\openvino_env\Scripts\python.exe" scripts\validate-decks.py
```

**Creates**: `scripts/validate-decks.py` (I'll create this next if you want)

**Checks**:
- All cards exist in your database
- Color identity matches commander
- ~100 cards per deck
- No duplicates (except basics)

---

## Step 3: Prepare Training Data

```powershell
# Merge decks + card knowledge
node scripts\prepare-training-data.js
```

**Output**: `data/training/combined_training.jsonl`

**Format**:
```json
{
  "instruction": "Build a Commander deck with Meren of Clan Nel Toth. Theme: Graveyard recursion. Colors: B, G.",
  "output": "## Commander (1)\n1x Meren of Clan Nel Toth\n\n## Creatures (35)\n1x Sakura-Tribe Elder\n..."
}
```

---

## Step 4: Install Training Dependencies

```powershell
# In OpenVINO environment
& "C:\Users\fuckthisshit\openvino_env\Scripts\pip.exe" install transformers datasets peft accelerate torch bitsandbytes
```

**Size**: ~3GB additional packages

---

## Step 5: Download Base Model

```powershell
# Get HuggingFace token first
# https://huggingface.co/settings/tokens

# Set token
$env:HF_TOKEN="your_token_here"

# Download Llama 3.1 8B
& "C:\Users\fuckthisshit\openvino_env\Scripts\python.exe" scripts\download-llama-3.1.py
```

**Size**: 16GB download, ~20-30 minutes

**Alternative** (no auth required):
```powershell
# Use Mistral 7B instead
& "C:\Users\fuckthisshit\openvino_env\Scripts\python.exe" scripts\download-mistral-7b.py
```

---

## Step 6: Train Model

```powershell
# Start training (will run 12-18 hours)
& "C:\Users\fuckthisshit\openvino_env\Scripts\python.exe" scripts\train-commander-model.py
```

**What happens**:
```
Loading base model...
✓ Llama 3.1 8B loaded (7.8GB VRAM)

Applying LoRA...
✓ Trainable parameters: 1.2% (94M / 8B)

Loading training data...
✓ 68,379 examples loaded

Training epoch 1/3...
[====>                    ] 1500/68379 | Loss: 1.234 | ETA: 11:23:45
```

**Monitor**:
- Open Task Manager → Performance → GPU
- Should see ~12GB VRAM usage
- GPU utilization 90-100%

**Let it run overnight** ⏰

---

## Step 7: Test Quality

```powershell
# Generate 5 test decks
& "C:\Users\fuckthisshit\openvino_env\Scripts\python.exe" scripts\test-trained-model.py
```

**Compare**:
- Color identity correct?
- Cards make sense together?
- Better/worse than Gemini?

**Decision point**: If quality ≥85% of Gemini → proceed to deployment

---

## Step 8: Export to OpenVINO

```powershell
# Optimize for Intel Arc GPU
& "C:\Users\fuckthisshit\openvino_env\Scripts\python.exe" scripts\export-to-openvino.py
```

**Output**: `models/commander-openvino/`

**Benefit**: 2-3x faster inference on Intel Arc

---

## Step 9: Deploy Flask API

```powershell
# Start local API server
& "C:\Users\fuckthisshit\openvino_env\Scripts\python.exe" scripts\serve-commander-api.py
```

**Runs on**: http://localhost:5000

**API**:
```http
POST http://localhost:5000/v1/deck/generate
Content-Type: application/json

{
  "commander": "Meren of Clan Nel Toth",
  "theme": "Graveyard Recursion",
  "colors": ["B", "G"],
  "powerLevel": 7
}
```

---

## Step 10: Integrate with Next.js

Update `src/app/api/commander/build/route.ts`:

```typescript
// Try local model first, fallback to Gemini
try {
  const response = await fetch('http://localhost:5000/v1/deck/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(deckRequest)
  });
  
  if (response.ok) {
    const deck = await response.json();
    return NextResponse.json(deck);
  }
} catch (localError) {
  console.log('Local model unavailable, trying Gemini...');
}

// Gemini fallback (existing code)
```

---

## Timeline

### If starting now (evening):

**Tonight (30 min setup)**:
- ✅ Start EDHREC scraper (runs overnight)

**Tomorrow morning (1 hour)**:
- ✅ Validate scraped decks
- ✅ Prepare training data
- ✅ Download Llama 3.1 8B

**Tomorrow afternoon (30 min)**:
- ✅ Start training (runs overnight)

**Day 3 morning (2 hours)**:
- ✅ Test trained model
- ✅ Export to OpenVINO
- ✅ Deploy Flask API

**Day 3 afternoon (2 hours)**:
- ✅ Integrate with Next.js
- ✅ Test end-to-end

**Total**: 3 days, ~8 hours hands-on work

---

## What You'll Have

### Production Setup:
```
┌─────────────────────────────────────┐
│  Next.js (Port 3050)                │
│  User requests deck                 │
└────────────┬────────────────────────┘
             │
             ▼
   ┌─────────────────────┐
   │ Try Local First     │
   │ (Port 5000)         │
   │ - Fast (5-10s)      │
   │ - Free              │
   │ - No rate limits    │
   └─────────┬───────────┘
             │
             │ If fails/slow
             ▼
   ┌─────────────────────┐
   │ Fallback to Gemini  │
   │ - Slower (10-30s)   │
   │ - API costs         │
   │ - Better quality    │
   └─────────────────────┘
```

### Benefits:
- ⚡ **Fast**: 5-10 seconds per deck (vs. 10-30s Gemini)
- 💰 **Free**: No API costs after training
- 🔓 **Unlimited**: No rate limits
- 🔒 **Private**: Data stays local
- 📈 **Improving**: Re-train monthly with new data

---

## Troubleshooting

### EDHREC scraper fails
```powershell
# Check internet connection
Test-Connection edhrec.com

# Try with smaller sample
# Edit scripts/scrape-edhrec-decks.py line 194:
# decks = scraper.scrape_decks(num_decks=100)  # Instead of 3000
```

### Out of VRAM during training
```python
# Edit scripts/train-commander-model.py
# Reduce batch size:
per_device_train_batch_size=1  # Instead of 2
gradient_accumulation_steps=16  # Instead of 8
```

### Model quality poor
- Collect more decks (5000 instead of 3000)
- Train for more epochs (5 instead of 3)
- Use larger model (Qwen 2.5 14B)
- Add Archidekt data for diversity

---

## Ready to Start?

```powershell
# Start scraping now (3-5 hours automated)
cd C:\magicapp
& "C:\Users\fuckthisshit\openvino_env\Scripts\python.exe" scripts\scrape-edhrec-decks.py
```

While that runs, I can create the remaining scripts you'll need tomorrow:
1. `validate-decks.py` - Quality checks
2. `prepare-training-data.js` - Data merging
3. `download-llama-3.1.py` - Model download
4. `train-commander-model.py` - Training loop
5. `export-to-openvino.py` - Optimization
6. `serve-commander-api.py` - Flask API

Want me to create these now, or start scraping first and create them tomorrow?
