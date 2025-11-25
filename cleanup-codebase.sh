#!/bin/bash
# Codebase Cleanup Script - Option A: Safe Archive
# Moves deprecated files to archive/ while preserving git history

set -e  # Exit on error

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  Codebase Cleanup - Safe Archive${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# Confirm before proceeding
echo -e "${YELLOW}This will reorganize 130+ scripts into:${NC}"
echo "  - scripts/active/      (13 currently used files)"
echo "  - scripts/utils/       (10-15 utility files)"
echo "  - scripts/archive/     (60-70 deprecated files)"
echo ""
echo -e "${YELLOW}Git history will be preserved. Files will be MOVED, not deleted.${NC}"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

# Create directory structure
echo -e "\n${GREEN}Creating directory structure...${NC}"
mkdir -p scripts/active/{pipeline,scrapers,testing}
mkdir -p scripts/utils/{monitoring,validation,database}
mkdir -p scripts/archive/{v2-training,experiments,old-tests,old-scrapers,utilities}

# Move active pipeline scripts
echo -e "\n${GREEN}Moving active pipeline scripts...${NC}"
git mv api-server.py scripts/active/pipeline/ 2>/dev/null || mv api-server.py scripts/active/pipeline/
git mv scripts/execute-deck-structure.ts scripts/active/pipeline/ 2>/dev/null || true
git mv scripts/import-mtgjson.ts scripts/active/database/ 2>/dev/null || mv scripts/import-mtgjson.ts scripts/active/database/
git mv scripts/convert-to-v3-training.py scripts/active/pipeline/ 2>/dev/null || true
git mv scripts/train-v3-structured.py scripts/active/pipeline/ 2>/dev/null || true

# Move active scrapers
echo -e "${GREEN}Moving active scrapers...${NC}"
for scraper in scrape-edhrec-average-decks.py scrape-mtggoldfish-by-commander.py scrape-moxfield-themes.py scrape-archidekt-commanders.py scrape-mtggoldfish.py; do
    [ -f "scripts/$scraper" ] && (git mv "scripts/$scraper" scripts/active/scrapers/ 2>/dev/null || true)
done

# Move active testing
echo -e "${GREEN}Moving active testing scripts...${NC}"
for test in validate_generated_deck.py test-site-quick.sh test-full-integration.sh; do
    [ -f "scripts/$test" ] && (git mv "scripts/$test" scripts/active/testing/ 2>/dev/null || true)
done

# Move v2 training to archive
echo -e "${GREEN}Archiving v2 training pipeline...${NC}"
for v2script in train-commander-model-optimized.py prepare-balanced-dataset.py prepare-balanced-dataset-v2.py prepare-training-data.py analyze-token-lengths.py convert-precons-to-training.py export-card-knowledge.py; do
    [ -f "scripts/$v2script" ] && (git mv "scripts/$v2script" scripts/archive/v2-training/ 2>/dev/null || true)
done

# Move experiments to archive
echo -e "${GREEN}Archiving old experiments...${NC}"
for exp in test-openvino.py download-openvino-model.py test-llama-model.py download-llama-model.py test-gemma-model.py test-merged-model.py; do
    [ -f "scripts/$exp" ] && (git mv "scripts/$exp" scripts/archive/experiments/ 2>/dev/null || true)
done

# Move old tests to archive
echo -e "${GREEN}Archiving old test scripts...${NC}"
for oldtest in test-trained-model-validated.py test-trained-model.py test-model.py test-v3-model.py test-with-reconstruction.py test-single-deck.py quick-test-gemma.py; do
    [ -f "scripts/$oldtest" ] && (git mv "scripts/$oldtest" scripts/archive/old-tests/ 2>/dev/null || true)
done

# Move deprecated scrapers to archive
echo -e "${GREEN}Archiving old scrapers...${NC}"
for oldscraper in scrape-edhrec-decks.py scrape-edhrec-combos.py scrape-mtggoldfish-advanced.py; do
    [ -f "scripts/$oldscraper" ] && (git mv "scripts/$oldscraper" scripts/archive/old-scrapers/ 2>/dev/null || true)
done
# Archive all tappedout scrapers (site is broken)
for tappedout in scripts/scrape-tappedout*.py scripts/test-tappedout*.py scripts/debug-tappedout*.py; do
    [ -f "$tappedout" ] && (git mv "$tappedout" scripts/archive/old-scrapers/ 2>/dev/null || true)
done

# Move utilities to archive
echo -e "${GREEN}Archiving one-time utilities...${NC}"
for util in analyze-deck-sources.py find-commander-cards.py discover-archidekt-tags.py color-identity-checker.py; do
    [ -f "scripts/$util" ] && (git mv "scripts/$util" scripts/archive/utilities/ 2>/dev/null || true)
done
for check in scripts/check-*.py scripts/debug-*.py; do
    [ -f "$check" ] && (git mv "$check" scripts/archive/utilities/ 2>/dev/null || true)
done

# Move monitoring to utils
echo -e "${GREEN}Moving monitoring utilities...${NC}"
for mon in monitor-combined.py monitor-memory.py monitor-scrapers.py; do
    [ -f "scripts/$mon" ] && (git mv "scripts/$mon" scripts/utils/monitoring/ 2>/dev/null || true)
done

# Move validation utils
echo -e "${GREEN}Moving validation utilities...${NC}"
for val in card_validator.py build_deck_from_structure.py; do
    [ -f "scripts/$val" ] && (git mv "scripts/$val" scripts/utils/validation/ 2>/dev/null || true)
done

# Archive remaining test-* files that weren't explicitly categorized
echo -e "${GREEN}Archiving remaining test files...${NC}"
for remaining_test in scripts/test-*.{py,ts,js}; do
    if [ -f "$remaining_test" ]; then
        basename=$(basename "$remaining_test")
        # Check if not already moved
        if [ ! -f "scripts/active/testing/$basename" ] && [ ! -f "scripts/archive/old-tests/$basename" ]; then
            git mv "$remaining_test" scripts/archive/old-tests/ 2>/dev/null || true
        fi
    fi
done

# Create archive index
echo -e "\n${GREEN}Creating archive index...${NC}"
cat > scripts/archive/README.md << 'ARCHIVE_EOF'
# Archived Scripts

**These scripts are deprecated but preserved for reference.**

## Why Archived

### v2 Training (`v2-training/`)
- **Replaced by**: v3 structured training (Gemma 3 4B)
- **Issue**: Mixed card descriptions + decks, model couldn't learn both
- **Result**: Hallucinated cards, wrong counts

### Experiments (`experiments/`)
- **Llama 8B**: Too large for Arc B50 16GB VRAM (needs ~17.5GB)
- **OpenVINO**: Compatibility issues with Intel XPU
- **Old Gemma tests**: Superseded by current Gemma 3 4B pipeline

### Old Tests (`old-tests/`)
- Tested v2 model or deprecated formats
- Kept for reference on testing approaches

### Old Scrapers (`old-scrapers/`)
- TappedOut: Site requires login, blocks scraping
- EDHREC combos: HTML structure changed, returns 0 results
- Replaced by better alternatives

### Utilities (`utilities/`)
- One-time analysis scripts
- Check/debug scripts for specific issues

## Restoring Files

If you need an archived file:

```bash
# Copy from archive
cp scripts/archive/[category]/[filename] scripts/

# Or restore from git history
git log --all --full-history -- scripts/[filename]
git checkout [commit-hash] -- scripts/[filename]
```

## Last Archived
November 14, 2025
ARCHIVE_EOF

# Create main scripts README
echo -e "${GREEN}Creating scripts/README.md...${NC}"
cat > scripts/README.md << 'SCRIPTS_EOF'
# Scripts Directory

Organized structure for maintainability.

## Active Scripts

### `active/pipeline/`
Currently used model training and inference:
- `api-server.py` - FastAPI server for Gemma 3 4B model
- `execute-deck-structure.ts` - Database executor with validations
- `convert-to-v3-training.py` - Convert scraped decks to v3 format
- `train-v3-structured.py` - Current training (Gemma 3 4B + LoRA)

### `active/scrapers/`
Data collection (23,405 training examples):
- `scrape-edhrec-average-decks.py` - 2,557 commander decks
- `scrape-mtggoldfish-by-commander.py` - 12,314 decks (best source)
- `scrape-moxfield-themes.py` - 3,754 theme decks
- `scrape-archidekt-commanders.py` - 4,144 popular decks
- `scrape-mtggoldfish.py` - 466 archetype decks

### `active/testing/`
Validation and integration tests:
- `validate_generated_deck.py` - Validates against database
- `test-site-quick.sh` - Fast integration test (~75s)
- `test-full-integration.sh` - Complete pipeline test

### `active/database/`
Database operations:
- `import-mtgjson.ts` - Import 31k+ MTG cards

## Utilities

### `utils/monitoring/`
System monitoring tools

### `utils/validation/`
Validation libraries and utilities

### `utils/database/`
Database utilities

## Archive

See `archive/README.md` for deprecated scripts (preserved for reference).

## Running Scripts

```bash
# Training
source ~/.virtualenvs/magicapp/bin/activate
export ACCELERATE_USE_XPU=1 USE_XPU=1
python3 scripts/active/pipeline/train-v3-structured.py

# Scraping
python3 scripts/active/scrapers/scrape-mtggoldfish-by-commander.py

# API Server
python3 scripts/active/pipeline/api-server.py

# Testing
./scripts/active/testing/test-site-quick.sh
```
SCRIPTS_EOF

# Summary
echo -e "\n${CYAN}========================================${NC}"
echo -e "${GREEN}✓ Cleanup Complete!${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""
echo "New Structure:"
echo "  scripts/active/         - Currently used scripts"
echo "  scripts/utils/          - Utility scripts"
echo "  scripts/archive/        - Deprecated (reference only)"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "  1. Review moved files: git status"
echo "  2. Update any hardcoded paths in code"
echo "  3. Test pipeline: ./scripts/active/testing/test-site-quick.sh"
echo "  4. Commit changes: git commit -m 'Reorganize scripts directory'"
echo ""
echo -e "${GREEN}Files preserved in git history. Nothing deleted.${NC}"
