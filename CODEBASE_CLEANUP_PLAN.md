# Codebase Cleanup Plan

**Goal**: Organize 130 scripts into a clean, maintainable structure.

**Current State**: 98 Python + 27 TypeScript + 5 JavaScript files in flat `/scripts` directory

**Proposed Structure**:
```
scripts/
├── active/              # Currently used scripts (keep in main)
│   ├── pipeline/        # Model training & inference
│   ├── scrapers/        # Data collection
│   ├── database/        # DB import/export
│   └── testing/         # Active test scripts
├── archive/             # Deprecated but keep for reference
│   ├── v2-training/     # Old training pipeline
│   ├── old-tests/       # Deprecated test scripts
│   ├── experiments/     # One-off experiments
│   └── old-scrapers/    # Replaced scrapers
└── utils/               # Utilities (rarely changed)
    ├── monitoring/
    └── validation/
```

---

## Phase 1: Identify Active Scripts (DONE ✓)

### Critical - Current Pipeline (5 files)
**Keep in**: `scripts/active/pipeline/`
- ✅ `api-server.py` - FastAPI server for Gemma 3 4B model
- ✅ `execute-deck-structure.ts` - Database executor (just updated with validations)
- ✅ `import-mtgjson.ts` - Card database import
- ✅ `convert-to-v3-training.py` - Convert scraped decks to v3 structured format
- ✅ `train-v3-structured.py` - Current training script (Gemma 3 4B + LoRA)

### Active - Scrapers (5 files)
**Keep in**: `scripts/active/scrapers/`
- ✅ `scrape-edhrec-average-decks.py` - 2,557 commander decks
- ✅ `scrape-mtggoldfish-by-commander.py` - 12,314 decks (best source)
- ✅ `scrape-moxfield-themes.py` - 3,754 theme decks
- ✅ `scrape-archidekt-commanders.py` - 4,144 popular decks
- ✅ `scrape-mtggoldfish.py` - 466 archetype decks

### Active - Testing & Validation (3 files)
**Keep in**: `scripts/active/testing/`
- ✅ `validate_generated_deck.py` - Validates against database
- ✅ `test-site-quick.sh` - Fast integration test (~75s)
- ✅ `test-full-integration.sh` - Complete pipeline test

**Total Active**: 13 files to keep easily accessible

---

## Phase 2: Archive Deprecated (Estimate: 60-70 files)

### v2 Training Pipeline → `scripts/archive/v2-training/`
**Reason**: Replaced by v3 structured training (Gemma 3 4B)
- `train-commander-model-optimized.py` - v2 LoRA training (used Qwen 2.5 3B)
- `prepare-balanced-dataset.py` - 70/30 card/deck ratio (failed approach)
- `prepare-balanced-dataset-v2.py` - Variant
- `prepare-training-data.py` - Old format
- `analyze-token-lengths.py` - Token analysis for v2
- `convert-precons-to-training.py` - Precon conversion for v2
- `export-card-knowledge.py` - Card descriptions (not used in v3)

### Old Model Experiments → `scripts/archive/experiments/`
**Reason**: Abandoned due to VRAM/compatibility
- `test-openvino.py` - OpenVINO quantization attempt
- `download-openvino-model.py`
- `test-llama-model.py` - Llama 8B (17.5GB VRAM, too large)
- `download-llama-model.py`
- `test-gemma-model.py` - Old Gemma tests
- `test-merged-model.py` - Merge experiments

### Old Tests → `scripts/archive/old-tests/`
**Reason**: Tested v2 model or old formats
- `test-trained-model-validated.py` - Tests v2 with validation
- `test-trained-model.py` - Generic v2 test
- `test-model.py` - Very old test
- `test-v3-model.py` - Tests v3 but old format
- `test-with-reconstruction.py`
- `test-single-deck.py`
- `quick-test-gemma.py`
- All `test-*.py` files that are one-offs

### Deprecated Scrapers → `scripts/archive/old-scrapers/`
**Reason**: Sites changed, or replaced by better scrapers
- `scrape-edhrec-decks.py` - Replaced by scrape-edhrec-average-decks.py
- `scrape-edhrec-combos.py` - Broken (0 combos found)
- `scrape-tappedout-*.py` - TappedOut requires login now
- `scrape-mtggoldfish-advanced.py` - Replaced by simpler version
- `test-edhrec-scraper.ts` - Old test
- `test-tappedout-*.py` - Broken site
- Debug scripts: `debug-edhrec.py`, `debug-tappedout-*.py`

### One-Time Utilities → `scripts/archive/utilities/`
**Reason**: Ran once, keep for reference
- `analyze-deck-sources.py` - Analysis script
- `find-commander-cards.py` - One-time discovery
- `discover-archidekt-tags.py` - Tag discovery
- `check-*.py` - Various one-time checks
- `color-identity-checker.py` - Standalone checker

---

## Phase 3: Keep as Utils (10-15 files)

### Monitoring → `scripts/utils/monitoring/`
- `monitor-combined.py` - GPU + training monitoring
- `monitor-memory.py` - Memory tracking
- `monitor-scrapers.py` - Scraper status

### Validation → `scripts/utils/validation/`
- `card_validator.py` - Card validation library (used by others)
- `build_deck_from_structure.py` - Alternative deck builder (Python)

### Database → `scripts/utils/database/`
- Any DB utilities we want to keep separate

---

## Phase 4: Root-Level Cleanup

### Markdown Files (Keep)
- `README.md` - Main docs
- `QUICK_START.md` - Setup guide
- `.github/copilot-instructions.md` - AI context (CRITICAL)
- `docs/*.md` - All documentation

### Deprecated MD Files → Move to `docs/archive/`
- `TRAINING_GUIDE.md` - Outdated (v2 focused)
- `TRAINING_PROGRESS.md` - Historical
- `LLAMA_8B_SETUP.md` - Abandoned
- `OPENVINO_SETUP.md` - Abandoned
- `GPU_CRASH_TROUBLESHOOTING.md` - Mostly resolved
- `SETUP_INTEL_GPU_TRAINING.md` - Incorporated into main docs
- `MEMORY_MANAGEMENT.md` - Mostly resolved

### Shell/Batch Scripts
**Keep**:
- `train-model-optimized.sh` - Current training launcher (?)
- Package.json scripts (npm run commands)

**Archive**:
- `train-model-llama8b.sh` - Llama 8B (abandoned)
- `*.bat` files - Windows-specific (not used on Linux server)

---

## Implementation Steps

### Option A: Safe Archive (Recommended)
1. Create `scripts/archive/` directory structure
2. **Move** (not delete) deprecated files to archive
3. Update any import paths in active scripts
4. Test that pipeline still works
5. Add `scripts/archive/.gitignore` to mark as low-priority
6. Update README with new structure

### Option B: Git Branch Archive
1. Create branch `archive/deprecated-scripts`
2. Commit current state to archive branch
3. Delete deprecated files from main
4. Keep archive branch for reference
5. Cleaner main branch, full history preserved

### Option C: Aggressive Cleanup
1. Delete deprecated files entirely
2. Git history preserves them if needed
3. Cleanest approach but harder to reference

---

## Recommended: Option A with Metadata

Create `scripts/archive/ARCHIVE_INDEX.md`:
```markdown
# Archived Scripts Index

## Why These Were Archived
- **v2 Training**: Replaced by v3 structured training (Gemma 3 4B)
- **Llama 8B**: Too large for Arc B50 16GB VRAM
- **OpenVINO**: Compatibility issues with Intel XPU
- **Old Scrapers**: Sites changed or better alternatives exist

## If You Need These
All files preserved in git history. To restore:
```bash
git checkout HEAD -- scripts/archive/[filename]
```

## Last Updated: Nov 14, 2025
```

---

## Files to Update After Cleanup

1. **package.json** - Update script paths
2. **README.md** - Document new structure
3. **.github/copilot-instructions.md** - Update file paths
4. **Import statements** - Check for broken imports

---

## Quick Stats

**Before Cleanup**: 130 scripts in flat structure
**After Cleanup**:
- `scripts/active/`: ~13 files (frequently used)
- `scripts/utils/`: ~10-15 files (occasionally used)
- `scripts/archive/`: ~60-70 files (reference only)
- Better organized, easier to navigate
- Faster to find what you need

---

## Next Steps

1. Review this plan
2. Choose Option A, B, or C
3. Run cleanup script (I can generate)
4. Test pipeline still works
5. Update documentation
