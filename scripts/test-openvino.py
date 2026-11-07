"""
Test OpenVINO GenAI with Intel Arc GPU for Commander deck building
"""
import sys
import time

try:
    import openvino_genai as ov_genai
    print("✓ OpenVINO GenAI imported successfully")
except ImportError as e:
    print(f"✗ Failed to import OpenVINO GenAI: {e}")
    sys.exit(1)

# Check available devices
try:
    from openvino import Core
    core = Core()
    devices = core.available_devices
    print(f"\n✓ Available OpenVINO devices: {devices}")
    
    # Check for GPU
    gpu_available = any('GPU' in device for device in devices)
    if gpu_available:
        print("✓ Intel Arc GPU detected!")
    else:
        print("⚠ No GPU detected, will use CPU")
except Exception as e:
    print(f"✗ Error checking devices: {e}")

# Test prompt for Commander deck generation
test_prompt = """You are a Magic: The Gathering Commander deck builder.
Generate ONLY the commander name for a Red-Green aggro deck.
Output format: Just the card name, nothing else.
Example: "Xenagos, God of Revels"

Commander name:"""

print("\n" + "="*60)
print("TESTING OPENVINO MODEL LOADING")
print("="*60)
print("\nNote: First run will download the model (~4-8GB)")
print("Model: TinyLlama-1.1B-Chat (optimized for OpenVINO)")
print("\nStarting test...")

try:
    # Check for downloaded models
    from pathlib import Path
    cache_dir = Path.home() / ".cache" / "openvino_models"
    
    # Look for any downloaded models
    model_path = None
    if cache_dir.exists():
        models = [d for d in cache_dir.iterdir() if d.is_dir()]
        if models:
            model_path = str(models[0])
            print(f"\n✓ Found model: {models[0].name}")
    
    if not model_path:
        print("\n✗ No models found!")
        print("\nPlease run first:")
        print("  python scripts/download-openvino-model.py")
        sys.exit(1)
    
    print(f"\nLoading model from: {model_path}")
    print("This may take 30-60 seconds...")
    
    start_time = time.time()
    
    # Create LLM pipeline with GPU device
    pipe = ov_genai.LLMPipeline(
        model_path,
        device="GPU"  # Use Intel Arc GPU
    )
    
    load_time = time.time() - start_time
    print(f"✓ Model loaded in {load_time:.2f} seconds")
    
    # Generate response
    print("\nGenerating response...")
    gen_start = time.time()
    
    result = pipe.generate(
        test_prompt,
        max_new_tokens=50,
        do_sample=True,
        temperature=0.7
    )
    
    gen_time = time.time() - gen_start
    
    print("\n" + "="*60)
    print("RESULT:")
    print("="*60)
    print(result)
    print("="*60)
    print(f"\nGeneration time: {gen_time:.2f} seconds")
    print("\n✓ OpenVINO GPU inference working!")
    
except FileNotFoundError as e:
    print(f"\n✗ Model not found: {e}")
    print("\nTo download the model, run:")
    print("  pip install huggingface-hub")
    print("  python -c \"from huggingface_hub import snapshot_download; snapshot_download('TinyLlama/TinyLlama-1.1B-Chat-v1.0')\"")
except Exception as e:
    print(f"\n✗ Error during inference: {e}")
    print(f"\nError type: {type(e).__name__}")
    
    # Try CPU fallback
    print("\nTrying CPU fallback...")
    try:
        pipe_cpu = ov_genai.LLMPipeline(model_path, device="CPU")
        result_cpu = pipe_cpu.generate(test_prompt, max_new_tokens=50)
        print("\n✓ CPU inference successful (but slower than GPU)")
        print(f"Result: {result_cpu}")
    except Exception as cpu_error:
        print(f"✗ CPU fallback also failed: {cpu_error}")

print("\n" + "="*60)
print("Test complete!")
print("="*60)
