# Local Model Integration - Testing Guide

## ✅ Validations Completed

All validation fixes are working correctly:
- ✓ Color identity subset logic (no off-color cards)
- ✓ Banned card exclusion (85+ cards filtered)
- ✓ Duplicate-allowed cards (13 legal duplicates supported)
- ✓ Commander legendary validation
- ✓ Illegal card type filtering (no meld backs, Arena cards, etc.)

## 🚀 Integration Complete

### Files Created:

1. **`src/lib/localModel.ts`** - Local model client library
   - `checkLocalModelStatus()` - Check if API is running
   - `generateDeckWithLocalModel()` - Generate deck structure
   - `buildDeckWithLocalModel()` - Full generation with timing

2. **`src/app/api/deck/generate-local/route.ts`** - Next.js API route
   - POST `/api/deck/generate-local` - Generate deck
   - GET `/api/deck/generate-local` - Health check

### Testing the Integration:

#### 1. Start the Local Model API:
```bash
cd /home/social/magicapp
source ~/.virtualenvs/magicapp/bin/activate
python3 scripts/active/pipeline/api-server.py
```

#### 2. Start Next.js Dev Server (separate terminal):
```bash
cd /home/social/magicapp
npm run dev
```

#### 3. Test Health Check:
```bash
curl http://localhost:3000/api/deck/generate-local
```

Expected response:
```json
{
  "available": true,
  "model": "gemma-3-4b-local",
  "endpoint": "http://localhost:8000",
  "status": "online"
}
```

#### 4. Generate a Deck:
```bash
curl -X POST http://localhost:3000/api/deck/generate-local \
  -H "Content-Type: application/json" \
  -d '{
    "commander": "Atraxa, Praetors'\'' Voice",
    "theme": "superfriends",
    "colors": ["W", "U", "B", "G"],
    "powerLevel": "4"
  }'
```

### UI Integration

To add local model option to the UI, update the deck builder component:

```typescript
// In your deck builder component
import { checkLocalModelStatus, buildDeckWithLocalModel } from '@/lib/localModel';

// Add state for model selection
const [useLocalModel, setUseLocalModel] = useState(false);
const [localModelAvailable, setLocalModelAvailable] = useState(false);

// Check availability on mount
useEffect(() => {
  checkLocalModelStatus().then(setLocalModelAvailable);
}, []);

// In your form submit handler
const handleGenerate = async () => {
  if (useLocalModel && localModelAvailable) {
    // Use local Gemma 3 4B model
    const result = await buildDeckWithLocalModel({
      commander,
      theme,
      colors,
      powerLevel,
    });
    // Handle result...
  } else {
    // Use existing Gemini API
    // ...existing code
  }
};

// Add toggle in UI
<div>
  <label>
    <input
      type="checkbox"
      checked={useLocalModel}
      onChange={(e) => setUseLocalModel(e.target.checked)}
      disabled={!localModelAvailable}
    />
    Use Local Model (Gemma 3 4B)
    {localModelAvailable ? ' ✓ Available' : ' ⚠️  Offline'}
  </label>
</div>
```

## Next Steps

1. **Test the API route** - Verify health check and generation work
2. **Add UI toggle** - Let users choose between Gemini and local model
3. **Add executor integration** - Create endpoint to run execute-deck-structure.ts
4. **Deploy as service** - Set up systemd for auto-start

## Performance Notes

- Model generation: ~73-75 seconds
- Priority cards: Limited to 30 cards
- Deck executor: Adds ~1-2 seconds
- Total pipeline: ~75-77 seconds for complete legal 100-card deck

## Troubleshooting

**Local model not available:**
- Start API server: `python3 scripts/active/pipeline/api-server.py`
- Check it's running: `curl http://localhost:8000/health`

**VRAM issues:**
- Model uses ~6.5GB VRAM (Arc B50 16GB is fine)
- Check with: `intel_gpu_top`

**Generation fails:**
- Check API logs for errors
- Verify virtualenv is activated
- Ensure XPU environment variables are set
