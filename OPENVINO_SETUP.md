# OpenVINO Setup for Local AI (Intel Arc GPU)

## Overview
OpenVINO provides native Intel Arc GPU acceleration for LLM inference on Windows, offering better performance than LM Studio and actually using your GPU (unlike Ollama).

## Your Current Setup
- **OpenVINO Version**: 2025.3.0 (latest)
- **GPU**: Intel Arc B50 Pro Graphics (16GB VRAM) + Intel UHD Graphics 750
- **Status**: ✅ Detected by OpenVINO (`GPU.0` and `GPU.1`)
- **Location**: `C:\Users\fuckthisshit\openvino_env\`

## Advantages Over Current Solutions

### vs. LM Studio
- ✅ **Native Intel optimization** (not just OpenAI API wrapper)
- ✅ **Lower latency** (direct GPU access)
- ✅ **Better structured output** support
- ✅ **More control** over inference parameters

### vs. Ollama
- ✅ **Actually uses Intel Arc GPU** (Ollama Windows = CPU only)
- ✅ **Better performance** on Intel hardware
- ✅ **More model format options**

### vs. Gemini API
- ✅ **No 503 errors** (local inference)
- ✅ **No rate limits** (unlimited generations)
- ✅ **Privacy** (data stays local)
- ❌ **Quality trade-off** (smaller models than Gemini)

## Quick Start

### 1. Download a Model
```powershell
& "C:\Users\fuckthisshit\openvino_env\Scripts\python.exe" scripts\download-openvino-model.py
```

**Recommended**: Start with **Phi-3.5 Mini 3.8B** (Option 2)
- Size: 7.6GB
- Quality: Good for Commander deck building
- Speed: Fast on Intel Arc
- Fits in 16GB VRAM with room for other apps

**Alternative models**:
- TinyLlama 1.1B (2.2GB) - Fast testing, lower quality
- Llama 3.2 3B (6GB) - Good balance
- Qwen 2.5 7B (14GB) - Best quality, slower

### 2. Test the Model
```powershell
& "C:\Users\fuckthisshit\openvino_env\Scripts\python.exe" scripts\test-openvino.py
```

Expected output:
```
✓ Available OpenVINO devices: ['CPU', 'GPU.0', 'GPU.1']
✓ Intel Arc GPU detected!
✓ Model loaded in 12.34 seconds
✓ OpenVINO GPU inference working!
```

## Integration Options

### Option A: Python REST API (Recommended)
Create a Flask/FastAPI server that runs in the OpenVINO environment:

**Pros**:
- Clean separation of concerns
- Easy to test independently
- Can be reused by other projects
- Familiar REST API pattern

**Cons**:
- Extra server to manage
- Slight network overhead (localhost only)

### Option B: Child Process from Node.js
Call Python scripts directly from TypeScript:

**Pros**:
- No extra server needed
- Simpler deployment

**Cons**:
- Slower (process startup overhead)
- Harder to debug
- Environment management tricky

### Option C: Python + Node.js Bridge
Use libraries like `python-shell` or `zerorpc`:

**Pros**:
- Direct communication
- No HTTP overhead

**Cons**:
- Complex setup
- More dependencies
- Harder to maintain

## Recommended Architecture

```
┌─────────────────────────────────────────────┐
│  Next.js App (Port 3050)                    │
│  src/app/api/commander/build/route.ts       │
└─────────────────┬───────────────────────────┘
                  │
                  │ HTTP POST
                  │
    ┌─────────────┴──────────────────┐
    │                                 │
    │  Gemini (Primary)               │  OpenVINO Service (Fallback)
    │  - High quality                 │  - Port 5000
    │  - Retry logic (3x)             │  - Python Flask
    │  - 503 errors                   │  - Intel Arc GPU
    │                                 │  - No rate limits
    └─────────────────────────────────┘
```

**Strategy**:
1. Try Gemini first (best quality)
2. If 503 after retries → fallback to OpenVINO
3. OpenVINO guarantees response (local)

## Expected Performance

### Phi-3.5 Mini 3.8B on Intel Arc B50 Pro:
- **Load time**: 10-20 seconds (first call)
- **Generation speed**: 20-40 tokens/second
- **Full deck (2000 tokens)**: 50-100 seconds
- **Memory usage**: ~8GB VRAM

### Quality Comparison:
- **Gemini 2.5 Flash**: 9/10 (best Commander knowledge)
- **Phi-3.5 Mini**: 6/10 (decent, needs good prompts)
- **TinyLlama**: 3/10 (testing only)
- **LM Studio (GPT-OSS-20B)**: 2/10 (your recent bad experience)

## Implementation Steps

### Phase 1: Python Service (2-3 hours)
1. ✅ Download Phi-3.5 Mini model
2. Create `scripts/openvino-service.py` (Flask API)
3. Test Commander deck generation
4. Fine-tune prompts for quality
5. Add error handling

### Phase 2: Node.js Integration (1-2 hours)
1. Update `src/app/api/commander/build/route.ts`
2. Add OpenVINO fallback logic
3. Test end-to-end flow
4. Monitor VRAM usage

### Phase 3: Production Ready (1 hour)
1. Add service health checks
2. Implement proper error messages
3. Document deployment process
4. Create systemd/Windows service wrapper

## Model Storage

Models will be cached at:
```
C:\Users\fuckthisshit\.cache\openvino_models\
├── Phi-3.5-mini-instruct\       (7.6GB)
│   ├── config.json
│   ├── tokenizer.json
│   └── model weights...
└── [other models]
```

## Next Steps

1. **Download a model** (start with Phi-3.5 Mini):
   ```powershell
   & "C:\Users\fuckthisshit\openvino_env\Scripts\python.exe" scripts\download-openvino-model.py
   ```

2. **Test inference**:
   ```powershell
   & "C:\Users\fuckthisshit\openvino_env\Scripts\python.exe" scripts\test-openvino.py
   ```

3. **Evaluate quality**: Generate a test Commander deck and compare to Gemini output

4. **Decide on architecture**: Python REST API vs. child process

5. **Build integration**: Create Flask service and update TypeScript code

## Questions to Answer

Before full integration:

1. **Is quality acceptable?** 
   - Generate 2-3 test decks with Phi-3.5 Mini
   - Compare to Gemini output
   - Check color identity violations

2. **Is speed acceptable?**
   - 50-100 seconds for full deck
   - vs. Gemini: 10-30 seconds (when not 503)
   - Trade-off: slower but guaranteed

3. **How often do we fallback?**
   - If Gemini 503 is rare (retry works), OpenVINO may not be needed
   - If Gemini 503 is frequent, OpenVINO is valuable backup

## Resources

- **OpenVINO Docs**: https://docs.openvino.ai/
- **GenAI API**: https://github.com/openvinotoolkit/openvino.genai
- **Intel Arc Optimization**: https://www.intel.com/content/www/us/en/developer/topic-technology/edge-5g/open-potential.html
- **Model Hub**: https://huggingface.co/models?library=openvino

## Troubleshooting

### "Could not find a model in the directory"
- Model not downloaded yet
- Run: `python scripts/download-openvino-model.py`

### "GPU not detected"
- Check drivers: `Get-WmiObject Win32_VideoController`
- Update Intel Graphics drivers
- Try CPU device: `device="CPU"` (slower)

### Out of memory errors
- Try smaller model (TinyLlama 1.1B)
- Close LM Studio (frees 10GB VRAM)
- Reduce `max_new_tokens` in generation config

### Slow generation
- First call is slow (model loading)
- Keep service running between requests
- Consider model caching strategies
