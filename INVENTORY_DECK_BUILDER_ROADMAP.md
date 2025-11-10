# Inventory-Based Commander Deck Builder - Development Roadmap

**Goal**: Build a self-hosted AI-powered Commander deck builder that generates decks based on user's card inventory, budget constraints, and power level preferences.

**Hardware**: Intel Arc B50 16GB VRAM, i7-11700K, 128GB RAM (primary server)

---

## Phase 1: Base Model Training (Current)

### ✅ 1. Monitor Scraping Completion (~4-5 hours)
**Status**: IN PROGRESS

**Current Scrapers**:
- ✅ Archidekt: Theme + bracket filtering (57 themes × 5 brackets)
- ✅ Moxfield: Theme + bracket filtering (48 themes × 5 brackets)
- ✅ MTGGoldfish: Archetype-based metagame decks

**Commands**:
```bash
# Check progress
wc -l data/training/{archidekt,moxfield,mtggoldfish}_decks.jsonl

# Watch logs
tail -f archidekt_scraping.log
tail -f moxfield_scraping.log
tail -f mtggoldfish_scraping.log

# Check processes
ps aux | grep -E "(scrape-arch|scrape-mox|scrape-mtg)" | grep -v grep
```

**Expected Totals (Conservative)**:
- Archidekt: ~3,350 decks (57 themes × 5 brackets × 10-12 decks)
- Moxfield: ~8,961 decks (48 themes × 5 brackets × 37 decks avg)
- MTGGoldfish: ~3,000 decks (15 archetypes × 100 decks each)
- **Total**: ~15,311 decks

**Optional: Extended MTGGoldfish Scraping**
MTGGoldfish advanced search has 100k+ decks available (313+ pages):
```bash
# Scrape additional 50,000 decks (if needed for higher card-to-deck ratio)
python3 scripts/scrape-mtggoldfish-advanced.py --max-decks 50000

# Resume from specific page
python3 scripts/scrape-mtggoldfish-advanced.py --max-decks 50000 --start-page 100

# Scrape in smaller batches
python3 scripts/scrape-mtggoldfish-advanced.py --max-decks 10000 --max-pages 100
```

This would give total dataset: ~65,311 decks for more card diversity!

**Validation**:
- Sample decks from each source for quality
- Verify exactly 100 cards per deck
- Check proper formatting (Commander, categories, metadata)

---

### 2. Create Balanced Training Dataset v2
**Status**: NOT STARTED

**Script**: `scripts/prepare-balanced-dataset-v2.py`

**Ratio Options (Conservative ~15k decks)**:
- **Recommended**: 30/70 card/deck = 6,515 card + 15,311 decks = 21,826 total
- Alternative: 40/60 card/deck = 10,207 card + 15,311 decks = 25,518 total

**Ratio Options (Extended ~65k decks if using MTGGoldfish advanced)**:
- Conservative: 20/80 card/deck = 16,328 card + 65,311 decks = 81,639 total
- Balanced: 30/70 card/deck = 27,990 card + 65,311 decks = 93,301 total
- Higher card knowledge: 40/60 card/deck = 43,541 card + 65,311 decks = 108,852 total

**Input Files**:
- `data/training/card_knowledge.jsonl` (65,378 examples available)
- `data/training/archidekt_decks.jsonl`
- `data/training/moxfield_decks.jsonl`
- `data/training/mtggoldfish_decks.jsonl`
- `data/training/mtggoldfish_advanced_decks.jsonl` (optional, if extended scraping)

**Output**: `data/training/combined_training_balanced_v2.jsonl`

**Recommendation**: Start with conservative 15k dataset (30/70 ratio). If model still hallucinates, add extended MTGGoldfish data for more card knowledge diversity.

**Validation**:
- Check format consistency across all examples
- No duplicate decks
- Proper instruction/output structure
- Random sampling of card knowledge (not biased to certain types)

---

### 3. Train Model v2 on Intel Arc B50
**Status**: NOT STARTED

**Model**: Qwen 2.5 3B with LoRA fine-tuning

**Configuration**:
- LoRA rank: 16, alpha: 32, dropout: 0.05
- Batch size: 2, Gradient accumulation: 8
- Max sequence length: 675
- Learning rate: 2e-4 with linear warmup
- BF16 mixed precision + gradient checkpointing

**Command**:
```bash
BATCH_SIZE=2 GRADIENT_ACCUMULATION_STEPS=8 MAX_SEQ_LENGTH=675 \
  nohup python3 scripts/train-commander-model-optimized.py > training_v2.log 2>&1 &
```

**Duration**: ~12-16 hours on Intel Arc B50

**Monitoring**:
```bash
tail -f training_v2.log
watch -n 60 'nvidia-smi'  # Or equivalent for Arc GPU
```

**Output**: `models/commander-llama-lora/v2/`

---

### 4. Validate v2 Model Quality
**Status**: NOT STARTED

**Validation Tools**:
- `scripts/validate_generated_deck.py` - Validates against MTGJson database
- `scripts/test-model-with-validation.py` - Automated testing with validation

**Validation Checks**:
- ✅ Exactly 100 cards
- ✅ All cards exist in database (no hallucinations)
- ✅ All cards are Commander-legal
- ✅ Color identity matches commander
- ✅ No invalid duplicates (except Relentless Rats, etc.)
- ✅ Commander is legendary creature/planeswalker

**Command**:
```bash
# Automated testing with 5 test decks
python3 scripts/test-model-with-validation.py

# Manual validation of specific deck
python3 scripts/validate_generated_deck.py generated_decks/my_deck.txt
```

**Test Cases** (20 diverse decks):
- Tribal: Ur-Dragon (Dragons), Lathril (Elves), Krenko (Goblins)
- Combo: Kinnan, Thrasios+Tymna
- Reanimator: Muldrotha, Karador
- Tokens: Rhys, Chatterfang
- Voltron: Uril, Ardenn+Rograkh
- Control: Talrand, Baral
- Aristocrats: Teysa, Korvold
- Various brackets: 1 (casual), 3 (optimized), 5 (cEDH)

**Quality Checks**:
- ✅ Exactly 100 cards (no 26-95 card decks like v1)
- ✅ No hallucinated card names (all exist in MTGJson)
- ✅ No invalid duplicates (except legal ones like Rat Colony)
- ✅ Proper color identity enforcement (no red in W/U/B/G)
- ✅ Strategy coherence (tribal has tribal synergies, combo has combo pieces)

**Script**: `scripts/test-trained-model-validated.py`

**Documentation**: Create `TRAINING_V2_RESULTS.md` with quality metrics and example outputs

---

## Phase 2: Constraint-Focused Fine-Tuning

### 5. Scrape Budget-Constrained Decks
**Status**: NOT STARTED

**Source**: Moxfield with price filters

**Price Brackets**:
- Ultra-budget: `?price_max=25`
- Budget: `?price_max=50`
- Mid-budget: `?price_max=100`
- High-budget: `?price_max=200`

**Target**: 1,000-2,000 budget decks across themes and power levels

**Script**: Modify `scripts/scrape-moxfield-themes.py` to add `price_max` parameter

**Output**: `data/training/moxfield_budget_decks.jsonl`

**Format**:
```json
{
  "instruction": "Build a $50 Commander deck with Krenko, Mob Boss focused on Goblins tribal",
  "output": "Commander: Krenko, Mob Boss\nTotal Price: $47.23\n\nCreatures:\n1x Goblin Chieftain ($2.15)..."
}
```

**Validation**: Confirm deck total price matches constraint (±10%)

---

### 6. Generate Synthetic Card Pool Training Data
**Status**: NOT STARTED

**Method**: 
1. Take existing high-quality decks
2. Randomly subset 70-80% of cards as "available inventory"
3. Train model to build best possible deck from that subset

**Target**: 2,000-3,000 synthetic examples

**Script**: `scripts/generate-inventory-constrained-examples.py`

**Format**:
```json
{
  "instruction": "Build a Commander deck with Atraxa, Praetors' Voice using only these cards: [Proliferate cards, +1/+1 counter cards, available mana base]",
  "output": "Commander: Atraxa, Praetors' Voice\n\nCreatures:\n1x Deepglow Skate\n1x Fathom Mage..."
}
```

**Validation**: Generated deck uses ONLY cards from provided inventory (100% match rate)

---

### 7. Add Power-Level Explicit Training
**Status**: NOT STARTED

**Goal**: Make power levels explicit in ALL training instructions

**Bracket Mapping**:
- Bracket 1 → Power Level 3-4 (Casual)
- Bracket 2 → Power Level 5-6 (Focused)
- Bracket 3 → Power Level 7-8 (Optimized)
- Bracket 4 → Power Level 8-9 (High)
- Bracket 5 → Power Level 9-10 (cEDH)

**Script**: `scripts/add-power-levels-to-training.py`

**Input**: All deck examples from archidekt, moxfield, tappedout

**Output**: Modified JSONL with explicit power level in instruction

**Example**:
```
OLD: "Build a Commander deck with Atraxa focused on +1/+1 counters"
NEW: "Build a power level 7 Commander deck with Atraxa focused on +1/+1 counters"
```

**Validation**: Sample 100 decks, verify stated power level matches deck content

---

### 8. Train Phase 2 LoRA Fine-Tuning
**Status**: NOT STARTED

**Base Model**: Trained v2 model from Phase 1

**New Training Data**:
- Budget decks (~1,500 examples)
- Synthetic inventory examples (~2,500 examples)
- Power-level explicit examples (~13,311 updated examples)
- **Total**: ~5,000-8,000 constraint-focused examples

**LoRA Configuration**:
- Lower learning rate: 1e-4 (vs 2e-4 for base)
- Fewer epochs: 2-3 (vs 3-5 for base)
- Same rank/alpha: 16/32

**Duration**: ~2-4 hours on Arc B50

**Command**:
```bash
BATCH_SIZE=2 GRADIENT_ACCUMULATION_STEPS=8 \
  nohup python3 scripts/train-commander-model-phase2.py > training_phase2.log 2>&1 &
```

**Output**: `models/commander-llama-lora/phase2/`

---

## Phase 3: Production Infrastructure

### 9. Setup PostgreSQL Database for Inventory
**Status**: NOT STARTED

**Installation**:
```bash
sudo apt install postgresql-15 postgresql-15-pgvector
```

**Schema**:
```sql
CREATE TABLE users (
  id SERIAL PRIMARY KEY,
  username VARCHAR(50) UNIQUE NOT NULL,
  email VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  role VARCHAR(20) DEFAULT 'USER'
);

CREATE TABLE cards (
  id SERIAL PRIMARY KEY,
  name VARCHAR(255) UNIQUE NOT NULL,
  types TEXT[],
  cmc INTEGER,
  colors TEXT[],
  color_identity TEXT[],
  keywords TEXT[],
  oracle_text TEXT,
  edhrec_rank INTEGER,
  price_usd DECIMAL(10,2),
  saltiness DECIMAL(5,2)
);

CREATE TABLE user_inventory (
  id SERIAL PRIMARY KEY,
  user_id INTEGER REFERENCES users(id),
  card_id INTEGER REFERENCES cards(id),
  quantity INTEGER DEFAULT 1,
  foil BOOLEAN DEFAULT false,
  condition VARCHAR(20),
  UNIQUE(user_id, card_id, foil, condition)
);

CREATE INDEX idx_cards_name ON cards(name);
CREATE INDEX idx_cards_colors ON cards USING GIN(colors);
CREATE INDEX idx_cards_types ON cards USING GIN(types);
CREATE INDEX idx_inventory_user ON user_inventory(user_id);
```

**Data Import**:
```bash
npm run import:mtgjson:full  # Import ~31,000 Commander-legal cards
```

**Backup Strategy**:
```bash
# Add to crontab
0 2 * * * pg_dump magicapp > /backup/magicapp_$(date +\%Y\%m\%d).sql
```

---

### 10. Setup Vector Database for Semantic Search
**Status**: NOT STARTED

**Option A: ChromaDB** (standalone):
```bash
pip install chromadb sentence-transformers
```

**Option B: pgvector** (PostgreSQL extension - recommended):
```sql
CREATE EXTENSION vector;

ALTER TABLE cards ADD COLUMN embedding vector(384);

CREATE INDEX ON cards USING ivfflat (embedding vector_cosine_ops);
```

**Embedding Generation**:
```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L6-v2')  # 384 dimensions

# Generate embeddings for all cards
for card in cards:
    text = f"{card.name} {card.oracle_text} {' '.join(card.types)}"
    embedding = model.encode(text)
    # Store in database
```

**API Endpoint**: `/api/cards/semantic-search`

**Use Cases**:
- "Find ramp in my Green cards"
- "Show removal spells I own in Orzhov"
- "Card draw effects under 3 CMC"

**Integration**: Connect to user inventory for filtering owned cards

---

### 11. Build FastAPI Backend for Multi-Step Generation
**Status**: NOT STARTED

**Installation**:
```bash
pip install fastapi uvicorn sqlalchemy psycopg2-binary redis
```

**Key Endpoints**:

**POST /api/generate-deck**:
```json
{
  "commander": "Atraxa, Praetors' Voice",
  "strategy": "Superfriends",
  "power_level": 7,
  "budget": 200,
  "use_inventory_only": true,
  "user_id": 123
}
```

**Multi-Step Flow**:
1. AI generates ideal deck strategy (commanders, win conditions, ratios)
2. Match cards from user inventory using semantic + exact search
3. Calculate inventory match % (e.g., 65% owned)
4. AI suggests replacements for missing cards from owned alternatives
5. Return deck with sections: "Using from inventory", "Recommended purchases"

**Model Serving**: Ollama or vLLM with Phase 2 model

**Optimization**:
- 4-bit quantization for 20-30+ concurrent users
- Response caching with Redis (popular commanders/themes)
- Queue system for fair request scheduling

**Other Endpoints**:
- `GET /api/cards/search` - Filter cards by types, colors, CMC, keywords
- `POST /api/inventory/add` - Add cards to user inventory
- `GET /api/inventory/{user_id}` - Get user's collection
- `POST /api/decks/save` - Save generated deck to user account

---

### 12. Implement Inventory Management Frontend
**Status**: NOT STARTED

**Pages**:
- `/inventory` - Add/remove cards with quantities
- `/collection` - View entire collection with filters
- `/import` - Bulk import from CSV, MTGO, Arena formats

**Components** (using existing Shadcn/UI):
- `CardSearch` - Autocomplete card name input
- `InventoryTable` - Display collection with sorting/filtering
- `BulkImportDialog` - CSV file upload and parsing
- `CardQuantitySelector` - Adjust quantities, foil, condition

**Features**:
- Real-time card name validation against MTGJson
- Quantity tracking (support playsets, 29x Rat Colony, etc.)
- Foil/condition tracking (NM, LP, MP, HP)
- Price tracking (integrate with Scryfall/TCGPlayer APIs)
- Statistics (total cards, total value, colors distribution)

**Bulk Import Formats**:
```csv
# CSV format
Card Name,Quantity,Foil,Condition
"Sol Ring",3,false,NM
"Rhystic Study",1,true,LP

# MTGO format
1 Sol Ring
1 Rhystic Study

# Arena format
1 Sol Ring (C21) 234
```

**Export**: Support CSV export of entire collection

---

### 13. Build Inventory-Constrained Deck Builder UI
**Status**: NOT STARTED

**Page**: `/build-from-inventory`

**Input Form**:
```typescript
interface DeckBuildRequest {
  commander: string;           // Autocomplete from database
  strategy?: string;           // Optional (Tribal, Combo, Control, etc.)
  power_level: number;         // 1-10 slider
  budget?: number;             // Max total deck price
  use_inventory_only: boolean; // Toggle for strict inventory mode
}
```

**Generation Flow**:

**Step 1: Ideal Strategy** (AI-generated)
```
Commander: Atraxa, Praetors' Voice
Strategy: Superfriends with +1/+1 counters
Win Conditions: Ultimate planeswalkers, combat with proliferate
Card Ratios: 15 planeswalkers, 10 ramp, 8 removal, 10 draw, 38 lands
```

**Step 2: Inventory Match**
```
✅ Found in inventory: 65/99 cards (66%)
❌ Missing: 34 cards ($127.45 total)

Categories:
- Planeswalkers: 8/15 owned (need 7 more)
- Ramp: 10/10 owned ✅
- Removal: 6/8 owned (need 2 more)
- Card Draw: 7/10 owned (need 3 more)
- Lands: 34/38 owned (need 4 more)
```

**Step 3: AI Replacements**
```
Missing: Teferi, Hero of Dominaria ($25)
Owned Alternative: Teferi, Temporal Archmage ($8)
Reason: Similar card advantage and control elements

Missing: Tropical Island ($450)
Owned Alternative: Breeding Pool ($15)
Reason: Dual land with same color identity, enters tapped
```

**Step 4: Final Decklist**
- Real-time validation (100 cards, color identity, legality)
- Sections: "From Inventory" (green highlight), "Recommended Purchases" (yellow)
- Total cost calculation for missing cards
- Save to user account with metadata

**Features**:
- Preview cards on hover (image + oracle text)
- Swap suggestions (click to try different alternatives)
- Export to MTGO, Arena, Moxfield formats
- Share deck via public URL

---

### 14. Setup Model Serving with Ollama on Arc B50
**Status**: NOT STARTED

**Option A: Ollama** (recommended for simplicity):
```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Convert LoRA to GGUF format with 4-bit quantization
python scripts/convert-lora-to-gguf.py \
  --base models/Qwen2.5-3B-Instruct \
  --lora models/commander-llama-lora/phase2 \
  --output models/commander-deck-builder-q4.gguf \
  --quantization q4_k_m

# Create Modelfile
cat > Modelfile <<EOF
FROM ./models/commander-deck-builder-q4.gguf
PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER stop "<|endoftext|>"
EOF

# Import model
ollama create commander-deck-builder -f Modelfile

# Serve (with Intel GPU support)
XPU_DEVICE=0 ollama serve
```

**Option B: vLLM** (for higher performance):
```bash
pip install vllm intel-extension-for-pytorch

python -m vllm.entrypoints.openai.api_server \
  --model models/commander-llama-lora/phase2 \
  --device xpu \
  --dtype bfloat16 \
  --max-model-len 675 \
  --gpu-memory-utilization 0.8
```

**Performance Targets**:
- 4-bit quantization: ~4GB VRAM usage
- Generation time: 2-3 seconds per deck
- Concurrency: 20-30 simultaneous users
- Queue depth monitoring

**Monitoring**:
```bash
# GPU usage
watch -n 5 'intel_gpu_top'

# Response times
curl http://localhost:11434/api/generate \
  -d '{"model":"commander-deck-builder","prompt":"Build a deck with Atraxa"}' \
  | jq '.eval_duration'
```

**Fallback Strategy**: If local model overloaded (queue >10), use Gemini API

---

### 15. Implement Multi-User Authentication and Roles
**Status**: NOT STARTED

**Extend Existing**: NextAuth.js setup in `src/lib/auth.ts`

**Roles**:
- **USER**: Own inventory management + deck building
- **ADMIN**: All features + user management + system monitoring

**Permissions**:
```typescript
// User can only access own data
if (session.user.id !== requestedUserId && session.user.role !== 'ADMIN') {
  return res.status(403).json({ error: 'Unauthorized' });
}
```

**Public Features** (no login required):
- View shared decks via public URL
- Search Commander-legal cards
- Browse example decks

**User Features** (login required):
- Manage personal inventory
- Generate decks from inventory
- Save/edit/delete own decks
- Export decklists

**Admin Features**:
- User management panel at `/admin`
- View all users' inventories (read-only)
- System metrics (model usage, API calls, storage)
- Role assignments (promote users to admin)

**Security**:
- Bcrypt password hashing (already implemented)
- JWT session tokens with expiration
- CSRF protection on form submissions
- Rate limiting (10 deck generations/hour for free users)

**Admin Panel** (`/admin`):
```typescript
- Users table (username, email, role, created_at, last_login)
- System stats (total users, total decks generated, avg response time)
- Model metrics (requests/hour, queue depth, VRAM usage)
- Database size and backup status
```

---

### 16. Deploy Production Environment
**Status**: NOT STARTED

**Server**: i7-11700K, Intel Arc B50 16GB, 128GB RAM (Ubuntu 22.04 LTS)

**Services Architecture**:
```
┌─────────────────────────────────────────┐
│         Nginx Reverse Proxy             │
│      (SSL termination, caching)         │
└─────────────────┬───────────────────────┘
                  │
    ┌─────────────┼─────────────┐
    │             │             │
┌───▼────┐   ┌───▼────┐   ┌───▼────┐
│ Next.js│   │FastAPI │   │ Ollama │
│Frontend│   │Backend │   │ Model  │
│Port    │   │Port    │   │Port    │
│3000    │   │8000    │   │11434   │
└───┬────┘   └───┬────┘   └────────┘
    │            │
    └────┬───────┘
         │
    ┌────▼─────────────────┐
    │   PostgreSQL + Redis │
    │   Port 5432, 6379    │
    └──────────────────────┘
```

**Nginx Configuration**:
```nginx
server {
    listen 80;
    server_name magicapp.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name magicapp.yourdomain.com;
    
    ssl_certificate /etc/letsencrypt/live/magicapp.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/magicapp.yourdomain.com/privkey.pem;
    
    # Frontend (Next.js)
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
    
    # Backend API (FastAPI)
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

**SSL Certificate** (Let's Encrypt):
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d magicapp.yourdomain.com
```

**Systemd Services**:

`/etc/systemd/system/magicapp-frontend.service`:
```ini
[Unit]
Description=MagicApp Next.js Frontend
After=network.target

[Service]
Type=simple
User=social
WorkingDirectory=/home/social/magicapp
ExecStart=/usr/bin/npm run start
Restart=always

[Install]
WantedBy=multi-user.target
```

`/etc/systemd/system/magicapp-backend.service`:
```ini
[Unit]
Description=MagicApp FastAPI Backend
After=network.target postgresql.service

[Service]
Type=simple
User=social
WorkingDirectory=/home/social/magicapp
ExecStart=/usr/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

`/etc/systemd/system/ollama.service`:
```ini
[Unit]
Description=Ollama Model Server
After=network.target

[Service]
Type=simple
User=social
Environment="XPU_DEVICE=0"
ExecStart=/usr/local/bin/ollama serve
Restart=always

[Install]
WantedBy=multi-user.target
```

**Enable Services**:
```bash
sudo systemctl enable magicapp-frontend
sudo systemctl enable magicapp-backend
sudo systemctl enable ollama
sudo systemctl enable postgresql
sudo systemctl enable redis-server

sudo systemctl start magicapp-frontend
sudo systemctl start magicapp-backend
sudo systemctl start ollama
```

**Monitoring** (Grafana + Prometheus):
```bash
# Install monitoring stack
sudo apt install prometheus grafana
sudo systemctl enable prometheus grafana-server
sudo systemctl start prometheus grafana-server
```

**Dashboards**:
- System metrics (CPU, RAM, GPU, disk I/O)
- Application metrics (API response times, request counts)
- Model metrics (generations/hour, queue depth, VRAM usage)
- Database metrics (query times, connection pool)

**Automated Backups**:
```bash
# Add to /etc/cron.daily/backup-magicapp
#!/bin/bash
DATE=$(date +%Y%m%d)
BACKUP_DIR=/backup/magicapp

# Database backup
pg_dump magicapp | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# Model checkpoints backup (if changed)
rsync -az /home/social/magicapp/models/ $BACKUP_DIR/models/

# Keep only last 7 days
find $BACKUP_DIR -name "db_*.sql.gz" -mtime +7 -delete

# Copy to secondary server (optional)
rsync -az $BACKUP_DIR/ secondary-server:/backup/magicapp/
```

**Secondary Server Usage** (Dual E5-2683 v4, 256GB RAM, no GPU):
- PostgreSQL replica for read queries
- Vector database (ChromaDB/pgvector)
- Analytics/reporting jobs
- Backup storage

---

## Phase 4: Testing & Optimization

### 17. Test End-to-End Inventory-Constrained Generation
**Status**: NOT STARTED

**Test Scenarios**:

**Test 1: Small Collection (500 cards)**
- Commander: Krenko, Mob Boss
- Strategy: Goblins tribal
- Power level: 6
- Expected: 60-70% inventory match, coherent Goblin synergies

**Test 2: Budget Constraint ($50)**
- Commander: Zada, Hedron Grinder
- Strategy: Spell-slinger
- Power level: 5
- Expected: Deck under $50, uses budget staples (Crimson Wisps, Expedite)

**Test 3: High Power (Level 7)**
- Commander: Atraxa, Praetors' Voice
- Strategy: Superfriends
- Power level: 7
- Expected: Efficient removal, good mana base, multiple win conditions

**Test 4: Partial Inventory (Mixed)**
- Commander: Muldrotha, the Gravetide
- Strategy: Reanimator
- Power level: 8
- Inventory: 30% expensive cards (Survival of the Fittest), 70% budget
- Expected: Smart replacements (Fauna Shaman for Survival if missing)

**Validation Criteria**:
- ✅ All generated decks use ONLY owned cards (strict mode)
- ✅ OR clearly show "Missing Cards" section (flexible mode)
- ✅ Replacement suggestions are appropriate (similar function, same colors)
- ✅ Total generation time <5 seconds (AI + inventory matching)
- ✅ Decks are coherent and synergistic (not random piles)
- ✅ Power level matches request (casual decks don't have cEDH staples)

**Performance Benchmarks**:
```
Step 1 (AI Strategy): ~1-2 seconds
Step 2 (Inventory Match): ~0.5 seconds (database query + vector search)
Step 3 (AI Replacements): ~1-2 seconds
Step 4 (Validation): ~0.5 seconds
Total: <5 seconds end-to-end
```

**User Testing**:
- Recruit 3-5 beta testers with varied collections
- Collect feedback on usability, accuracy, suggestion quality
- Iterate on prompts and matching algorithms

**Documentation**: Create `TESTING_RESULTS.md` with findings and metrics

---

### 18. Document Self-Hosting Guide
**Status**: NOT STARTED

**File**: `SELF_HOSTING_INVENTORY.md`

**Sections**:

**1. Hardware Requirements**
- Minimum: 8GB RAM, 4 CPU cores, 50GB storage, no GPU (uses Gemini API)
- Recommended: 16GB+ RAM, 8+ cores, 100GB storage, Intel Arc GPU
- Optimal: 128GB RAM, i7/Ryzen 7, 500GB NVMe, Intel Arc B50/A770

**2. Software Installation (Ubuntu/Debian)**
```bash
# System updates
sudo apt update && sudo apt upgrade -y

# Node.js 20
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# PostgreSQL 15 + pgvector
sudo apt install -y postgresql-15 postgresql-15-pgvector

# Python 3.11 + dependencies
sudo apt install -y python3.11 python3-pip
pip3 install torch sentence-transformers chromadb

# Ollama (optional, for local AI)
curl -fsSL https://ollama.com/install.sh | sh

# Nginx + Let's Encrypt
sudo apt install -y nginx certbot python3-certbot-nginx

# Redis (for caching)
sudo apt install -y redis-server
```

**3. Application Setup**
```bash
# Clone repository
git clone https://github.com/yourusername/magicapp.git
cd magicapp

# Install dependencies
npm install

# Setup database
createdb magicapp
npx prisma db push
npm run import:mtgjson:full

# Configure environment variables
cp .env.example .env.local
nano .env.local  # Fill in database URL, API keys, etc.

# Build frontend
npm run build

# Start services
sudo systemctl start postgresql redis-server
npm run start  # Frontend
```

**4. Model Setup**

**Option A: Local Model (recommended for privacy)**
```bash
# Download Phase 2 model
wget https://your-model-host.com/commander-deck-builder-q4.gguf
ollama create commander-deck-builder -f Modelfile
XPU_DEVICE=0 ollama serve  # Use GPU if available
```

**Option B: Gemini API (easier setup)**
```bash
# Get API key from https://aistudio.google.com/
echo "GEMINI_API_KEY=your-key-here" >> .env.local
# No local model needed
```

**5. Environment Variables**
```bash
# Database
DATABASE_URL="postgresql://user:password@localhost:5432/magicapp"

# Authentication
NEXTAUTH_SECRET="generate-with-openssl-rand-base64-32"
NEXTAUTH_URL="https://magicapp.yourdomain.com"

# AI Model (choose one)
OLLAMA_URL="http://localhost:11434"  # Local model
# OR
GEMINI_API_KEY="your-gemini-key"  # Gemini API

# Redis (optional, for caching)
REDIS_URL="redis://localhost:6379"

# Email (optional, for notifications)
SMTP_HOST="smtp.gmail.com"
SMTP_USER="your-email@gmail.com"
SMTP_PASS="your-app-password"
```

**6. SSL Certificate (Production)**
```bash
sudo certbot --nginx -d magicapp.yourdomain.com
sudo systemctl reload nginx
```

**7. Systemd Services Setup**
```bash
# Copy service files
sudo cp systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now magicapp-frontend
sudo systemctl enable --now magicapp-backend
```

**8. Backup Configuration**
```bash
# Database backup script
sudo cp scripts/backup-database.sh /etc/cron.daily/
sudo chmod +x /etc/cron.daily/backup-database.sh

# Model backup (after training)
rsync -az models/ /backup/models/
```

**9. Troubleshooting**

**GPU not detected**:
```bash
# Check Intel GPU
sudo apt install intel-gpu-tools
intel_gpu_top

# Verify Ollama sees GPU
ollama list
XPU_DEVICE=0 ollama run commander-deck-builder "test"
```

**Memory issues**:
```bash
# Increase swap
sudo fallocate -l 16G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

**Port conflicts**:
```bash
# Check what's using ports
sudo netstat -tulpn | grep -E ':(3000|8000|5432|6379|11434)'

# Change ports in systemd service files
sudo systemctl edit magicapp-frontend
```

**Database connection errors**:
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Reset password
sudo -u postgres psql
ALTER USER postgres PASSWORD 'newpassword';
```

**10. Update Procedures**

**Code updates**:
```bash
cd /home/social/magicapp
git pull
npm install  # If package.json changed
npm run build
sudo systemctl restart magicapp-frontend
```

**Model updates**:
```bash
# Download new model
wget https://your-host.com/commander-v3.gguf
ollama create commander-deck-builder:v3 -f Modelfile
# Test before switching
ollama run commander-deck-builder:v3 "Build Atraxa deck"
# Switch production
ollama rm commander-deck-builder:latest
ollama tag commander-deck-builder:v3 commander-deck-builder:latest
```

**Database migrations**:
```bash
npx prisma migrate deploy  # Apply pending migrations
npm run import:mtgjson:full  # Update card data
```

---

### 19. Optimize for Multi-User Public Access
**Status**: NOT STARTED

**Rate Limiting**:
```typescript
// middleware/rateLimit.ts
import rateLimit from 'express-rate-limit'

const deckGenerationLimiter = rateLimit({
  windowMs: 60 * 60 * 1000, // 1 hour
  max: 10, // 10 requests per hour for free users
  skipSuccessfulRequests: false,
  handler: (req, res) => {
    res.status(429).json({
      error: 'Rate limit exceeded',
      message: 'Free users can generate 10 decks per hour',
      reset: new Date(Date.now() + 60 * 60 * 1000)
    })
  }
})

// Premium users: 100 requests per hour
const premiumLimiter = rateLimit({
  windowMs: 60 * 60 * 1000,
  max: 100,
  skip: (req) => req.user?.role === 'PREMIUM'
})
```

**Response Caching** (Redis):
```typescript
// Cache popular commander/theme combinations
const cacheKey = `deck:${commander}:${strategy}:${power_level}`
const cached = await redis.get(cacheKey)

if (cached) {
  return JSON.parse(cached)  // Instant response
}

// Generate new deck
const deck = await generateDeck(...)

// Cache for 24 hours
await redis.setex(cacheKey, 86400, JSON.stringify(deck))
```

**Queue System**:
```typescript
// Fair scheduling for concurrent requests
import { Queue } from 'bull'

const deckQueue = new Queue('deck-generation', {
  redis: { host: 'localhost', port: 6379 }
})

// Add job to queue
const job = await deckQueue.add({
  commander, strategy, power_level, user_id
}, {
  priority: user.role === 'PREMIUM' ? 1 : 10,  // Premium first
  attempts: 3,
  backoff: { type: 'exponential', delay: 5000 }
})

// Worker processes jobs
deckQueue.process(5, async (job) => {  // 5 concurrent workers
  return await generateDeck(job.data)
})
```

**Metrics Tracking**:
```typescript
// Track usage patterns
interface Metrics {
  total_decks_generated: number;
  popular_commanders: Record<string, number>;
  avg_generation_time: number;
  success_rate: number;
  active_users_today: number;
}

// Log to database
await db.metrics.create({
  timestamp: new Date(),
  commander: request.commander,
  strategy: request.strategy,
  power_level: request.power_level,
  generation_time_ms: endTime - startTime,
  success: true,
  user_id: request.user_id
})
```

**Scaling Strategy**:

**Current Setup** (single server):
- Intel Arc B50: 20-30 concurrent users
- i7-11700K: Handles frontend + backend + database
- 128GB RAM: Plenty for model + PostgreSQL + Redis

**Future Scaling** (if needed):
- **Secondary Server** (E5-2683 v4, 256GB RAM): Move PostgreSQL + Redis
- **Load Balancer**: Nginx upstream for multiple backend instances
- **Read Replicas**: PostgreSQL streaming replication for read queries
- **CDN**: CloudFlare for static assets (card images, CSS, JS)

**Cost Estimation**:
```
Electricity:
- Intel Arc B50: ~150W under load
- i7-11700K: ~125W under load
- Total: ~275W × 24h × $0.12/kWh = $0.79/day
- Monthly: ~$24

Per 1000 deck generations:
- ~30 seconds GPU time × 150W = 1.25Wh
- Cost: ~$0.10-0.20

Bandwidth (with 100 users/day):
- 100 decks × 50KB JSON = 5MB/day
- 150MB/month (negligible)

Total: ~$24/month for unlimited personal + public access
```

**Public Instance Features**:
- Free tier: 10 decks/hour, basic features
- Registered: 50 decks/hour, save decks, inventory management
- Premium ($5/month): 100 decks/hour, priority queue, export formats
- Domain: `magicapp.yourdomain.com`

---

### 20. Create Budget Deck Collection Analysis
**Status**: NOT STARTED

**Purpose**: Analyze budget deck patterns to improve AI suggestions for affordable alternatives

**Script**: `scripts/analyze-budget-decks.py`

**Analysis Metrics**:

**1. Price Distribution by Card Type**
```python
# Average prices for budget decks (under $50 total)
creatures_avg = budget_decks.filter(type='Creature').mean('price')
lands_avg = budget_decks.filter(type='Land').mean('price')
removal_avg = budget_decks.filter(keyword='Removal').mean('price')
```

**2. Budget Staples (Cards in >50% of budget decks)**
```
Ramp:
- Sol Ring: $1.50 (in 95% of decks)
- Arcane Signet: $0.50 (in 85%)
- Kodama's Reach: $0.25 (in 60%)
- Cultivate: $0.30 (in 55%)

Removal:
- Swords to Plowshares: $1.50 (White, 70%)
- Beast Within: $0.75 (Green, 65%)
- Chaos Warp: $0.50 (Red, 60%)
- Counterspell: $0.25 (Blue, 55%)

Card Draw:
- Rhystic Study: $25 (too expensive, skip)
- Harmonize: $0.35 (Green, 50%)
- Blue Sun's Zenith: $2.00 (Blue, 45%)
```

**3. Budget Alternatives to Expensive Cards**
```python
expensive_alternatives = {
    "Mana Crypt ($180)": "Sol Ring ($1.50)",
    "Gaea's Cradle ($800)": "Growing Rites of Itlimoc ($8)",
    "Tropical Island ($450)": "Breeding Pool ($15)",
    "Rhystic Study ($25)": "Mystic Remora ($5)",
    "Sylvan Library ($35)": "Elemental Bond ($0.50)",
    "Cyclonic Rift ($35)": "Devastation Tide ($0.50)",
}
```

**4. Budget Deck Templates by Strategy**
```json
{
  "Goblins Tribal (Krenko)": {
    "total_price": "$45",
    "commander": "Krenko, Mob Boss ($1)",
    "creatures": "$15 (20 cards, avg $0.75)",
    "removal": "$5 (5 cards, avg $1.00)",
    "ramp": "$8 (8 cards, avg $1.00)",
    "lands": "$10 (36 cards, mostly basics)",
    "draw": "$7 (5 cards, avg $1.40)"
  }
}
```

**5. Price Optimization Recommendations**
```
To build a $50 deck:
- Commander: $0.50 - $3 (avoid expensive legends)
- Lands: $10-15 (basics + tap lands, avoid shocks/fetches)
- Ramp: $5-8 (Sol Ring + signets + Cultivate effects)
- Removal: $5-8 (efficient but cheap: Path, Beast Within)
- Card Draw: $5-10 (avoid Rhystic Study, use Harmonize-style)
- Synergy pieces: $15-20 (the core strategy cards)
```

**Output Files**:
- `data/analysis/budget_staples.json` - Top budget cards by category
- `data/analysis/expensive_alternatives.json` - Replacement mapping
- `data/analysis/budget_templates.json` - Price breakdowns by strategy
- `BUDGET_DECK_BUILDING.md` - Human-readable guide

**Integration with AI**:
```python
# When user sets budget constraint
if deck_request.budget and deck_request.budget < 100:
    # Load budget alternatives
    alternatives = load_budget_alternatives()
    
    # Modify prompt
    prompt += f"\nUse budget alternatives: {alternatives}"
    prompt += f"\nTarget total price: ${deck_request.budget}"
    prompt += f"\nPrioritize cards under $2 each"
```

**Validation**:
- Generate 20 budget decks with AI
- Calculate actual prices via Scryfall API
- Verify 90%+ of decks are within ±10% of target price

---

## Summary

**Total Estimated Time**:
- Phase 1 (Base Model): ~3-5 days (mostly scraping + training time)
- Phase 2 (Constraint Fine-Tuning): ~1-2 weeks (data prep + training + testing)
- Phase 3 (Infrastructure): ~2-3 weeks (database + API + frontend + deployment)
- Phase 4 (Testing & Docs): ~1 week (comprehensive testing + documentation)

**Total**: ~6-8 weeks for complete inventory-based Commander deck builder

**Priority Order**:
1. ✅ Complete scraping (currently in progress)
2. Train v2 base model and validate quality
3. Test with Gemini API first (faster iteration)
4. Once satisfied, train Phase 2 for local deployment
5. Build inventory + generation infrastructure
6. Deploy and gather user feedback
7. Iterate on constraints and suggestions

**Next Immediate Action**: Monitor scraping completion, then prepare balanced v2 dataset
