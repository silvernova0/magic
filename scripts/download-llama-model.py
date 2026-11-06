"""
Download Llama 3.1 8B Instruct model from HuggingFace
"""
import os
from huggingface_hub import snapshot_download

# Set HuggingFace token
HF_TOKEN = "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"
os.environ['HF_TOKEN'] = HF_TOKEN

# Model details
MODEL_ID = "meta-llama/Meta-Llama-3.1-8B-Instruct"
LOCAL_DIR = "models/llama-3.1-8b"

print("="*60)
print("LLAMA 3.1 8B MODEL DOWNLOAD")
print("="*60)
print(f"\nModel: {MODEL_ID}")
print(f"Destination: {LOCAL_DIR}")
print(f"Estimated size: ~16 GB")
print(f"Estimated time: 20-30 minutes\n")
print("Starting download...\n")

try:
    # Create directory
    os.makedirs(LOCAL_DIR, exist_ok=True)
    
    # Download model
    snapshot_download(
        repo_id=MODEL_ID,
        local_dir=LOCAL_DIR,
        token=HF_TOKEN,
        resume_download=True,  # Resume if interrupted
        local_dir_use_symlinks=False  # Copy files instead of symlinks
    )
    
    print("\n" + "="*60)
    print("DOWNLOAD COMPLETE")
    print("="*60)
    print(f"Model saved to: {LOCAL_DIR}")
    print("✓ Ready for fine-tuning!")
    
except Exception as e:
    print(f"\n❌ Error downloading model: {str(e)}")
    print("\nTroubleshooting:")
    print("1. Check internet connection")
    print("2. Verify HuggingFace token is valid")
    print("3. Ensure you have access to Llama models (accept license on HF)")
    print("4. Check disk space (need ~16GB free)")
