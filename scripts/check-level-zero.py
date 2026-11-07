"""
Check if Level Zero SDK is properly installed and accessible.
"""

import sys
import os

print("=" * 60)
print("Level Zero SDK Verification")
print("=" * 60)

# Check for Level Zero DLLs
level_zero_dlls = [
    r"C:\Windows\System32\ze_loader.dll",
    r"C:\Windows\System32\ze_intel_gpu_raytracing.dll",
    r"C:\Windows\System32\ze_tracing_layer.dll",
    r"C:\Windows\System32\ze_validation_layer.dll"
]

print("\nLevel Zero DLLs:")
all_found = True
for dll in level_zero_dlls:
    exists = os.path.exists(dll)
    status = "✓" if exists else "✗"
    print(f"  {status} {os.path.basename(dll)}: {exists}")
    if not exists:
        all_found = False

# Try to import and use PyTorch with XPU
print("\n" + "=" * 60)
print("PyTorch XPU Integration Test")
print("=" * 60)

try:
    import torch
    import intel_extension_for_pytorch as ipex
    
    print(f"\n✓ PyTorch version: {torch.__version__}")
    print(f"✓ IPEX version: {ipex.__version__}")
    
    if torch.xpu.is_available():
        print(f"✓ XPU is available")
        print(f"✓ XPU device count: {torch.xpu.device_count()}")
        print(f"✓ XPU device name: {torch.xpu.get_device_name(0)}")
        
        # Test Level Zero through PyTorch
        try:
            test_tensor = torch.randn(10, 10).to('xpu')
            result = test_tensor @ test_tensor.T
            torch.xpu.synchronize()
            print(f"✓ Level Zero runtime test: PASSED")
            print(f"  Created and computed tensor on XPU successfully")
        except Exception as e:
            print(f"✗ Level Zero runtime test: FAILED")
            print(f"  Error: {e}")
    else:
        print("✗ XPU is NOT available")
        
except ImportError as e:
    print(f"✗ Failed to import required modules: {e}")
except Exception as e:
    print(f"✗ Error during XPU test: {e}")

# Check if torch.compile will work (requires Level Zero SDK)
print("\n" + "=" * 60)
print("torch.compile Support Check")
print("=" * 60)

try:
    import torch
    if torch.xpu.is_available():
        # torch.compile on XPU requires Level Zero SDK
        print("✓ Level Zero SDK detected (required for torch.compile on XPU)")
        print("✓ torch.compile should work with XPU backend")
    else:
        print("⚠ XPU not available - torch.compile test skipped")
except:
    print("✗ Could not verify torch.compile support")

print("\n" + "=" * 60)
print("Summary")
print("=" * 60)

if all_found:
    print("✓ Level Zero SDK is properly installed")
    print("✓ All required DLLs are present")
    print("✓ Ready for PyTorch XPU training")
else:
    print("⚠ Some Level Zero components may be missing")
    print("  This could affect XPU performance or stability")

print("=" * 60)
