"""
Download and convert a model to OpenVINO format
"""
import sys
import os

try:
    from huggingface_hub import snapshot_download
    from pathlib import Path
    print("✓ HuggingFace Hub available")
except ImportError:
    print("✗ Installing huggingface-hub...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "huggingface-hub"])
    from huggingface_hub import snapshot_download

# Model options for Commander deck building
# Listed by size (smallest to largest)
MODELS = {
    "1": {
        "name": "TinyLlama 1.1B",
        "repo": "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
        "size": "2.2GB",
        "speed": "Very Fast",
        "quality": "Low (good for testing)"
    },
    "2": {
        "name": "Phi-3.5 Mini 3.8B",
        "repo": "microsoft/Phi-3.5-mini-instruct",
        "size": "7.6GB",
        "speed": "Fast",
        "quality": "Good (recommended for Intel Arc)"
    },
    "3": {
        "name": "Llama 3.2 3B",
        "repo": "meta-llama/Llama-3.2-3B-Instruct",
        "size": "6GB",
        "speed": "Fast",
        "quality": "Good"
    },
    "4": {
        "name": "Qwen 2.5 7B",
        "repo": "Qwen/Qwen2.5-7B-Instruct",
        "size": "14GB",
        "speed": "Medium",
        "quality": "Very Good"
    }
}

print("\n" + "="*60)
print("OPENVINO MODEL DOWNLOAD")
print("="*60)
print("\nAvailable models for Commander deck building:\n")

for key, model in MODELS.items():
    print(f"{key}. {model['name']}")
    print(f"   Size: {model['size']}")
    print(f"   Speed: {model['speed']}")
    print(f"   Quality: {model['quality']}")
    print()

print("Recommendation: Start with option 2 (Phi-3.5 Mini)")
print("- Optimized for Intel hardware")
print("- Good balance of speed and quality")
print("- 7.6GB fits in your 16GB VRAM")

choice = input("\nSelect model (1-4) or 'q' to quit: ").strip()

if choice.lower() == 'q':
    print("Cancelled.")
    sys.exit(0)

if choice not in MODELS:
    print(f"Invalid choice: {choice}")
    sys.exit(1)

model_info = MODELS[choice]
print(f"\n✓ Selected: {model_info['name']}")
print(f"Downloading from HuggingFace: {model_info['repo']}")
print(f"Size: {model_info['size']}")

# Create cache directory
cache_dir = Path.home() / ".cache" / "openvino_models"
cache_dir.mkdir(parents=True, exist_ok=True)

model_dir = cache_dir / model_info['repo'].split('/')[-1]

print(f"\nCache directory: {model_dir}")

if model_dir.exists() and any(model_dir.iterdir()):
    print("⚠ Model already exists in cache!")
    overwrite = input("Re-download? (y/n): ").strip().lower()
    if overwrite != 'y':
        print(f"✓ Using existing model at {model_dir}")
        print("\nTo use this model in your code:")
        print(f'  pipe = ov_genai.LLMPipeline("{model_dir}", device="GPU")')
        sys.exit(0)

try:
    print("\nDownloading... (this may take 5-15 minutes)")
    print("Progress:")
    
    downloaded_path = snapshot_download(
        repo_id=model_info['repo'],
        cache_dir=str(cache_dir),
        local_dir=str(model_dir),
        local_dir_use_symlinks=False
    )
    
    print(f"\n✓ Model downloaded successfully!")
    print(f"Location: {downloaded_path}")
    print(f"\n{'='*60}")
    print("NEXT STEPS:")
    print("="*60)
    print("\n1. Test the model:")
    print(f'   python scripts/test-openvino.py')
    print("\n2. Use in your code:")
    print(f'   pipe = ov_genai.LLMPipeline("{model_dir}", device="GPU")')
    print("\n3. For Commander deck building, you'll need to:")
    print("   - Create a new function in src/lib/openvino.ts (TypeScript wrapper)")
    print("   - Call Python via child_process or create a REST API")
    print("   - Handle structured output parsing")
    
except Exception as e:
    print(f"\n✗ Download failed: {e}")
    print("\nPossible solutions:")
    print("1. Check internet connection")
    print("2. Try a smaller model (option 1)")
    print("3. Check HuggingFace Hub status")
    sys.exit(1)
