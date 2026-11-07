"""Test Intel Arc GPU detection with Intel Extension for PyTorch"""
import sys

print("Testing Intel Arc GPU detection...")
print("=" * 60)

try:
    import torch
    print(f"✓ PyTorch version: {torch.__version__}")
except Exception as e:
    print(f"✗ PyTorch import failed: {e}")
    sys.exit(1)

try:
    import intel_extension_for_pytorch as ipex
    print(f"✓ IPEX version: {ipex.__version__}")
except Exception as e:
    print(f"✗ IPEX import failed: {e}")
    print(f"  Error details: {e}")
    sys.exit(1)

try:
    xpu_available = torch.xpu.is_available()
    print(f"✓ XPU available: {xpu_available}")
    
    if xpu_available:
        device_count = torch.xpu.device_count()
        print(f"✓ XPU device count: {device_count}")
        
        if device_count > 0:
            device_name = torch.xpu.get_device_name(0)
            print(f"✓ XPU device name: {device_name}")
            
            # Test simple tensor operation
            print("\nTesting GPU tensor operations...")
            x = torch.randn(100, 100).to("xpu")
            y = torch.randn(100, 100).to("xpu")
            z = torch.mm(x, y)
            print("✓ GPU tensor operations working!")
            
            print("\n" + "=" * 60)
            print("SUCCESS! Intel Arc GPU is ready for training!")
            print("=" * 60)
    else:
        print("\n✗ XPU not available")
        print("  Make sure oneAPI environment is set:")
        print('  Run: setvars.bat from "C:\\Program Files (x86)\\Intel\\oneAPI"')
        sys.exit(1)
        
except Exception as e:
    print(f"\n✗ XPU test failed: {e}")
    print("  This may be a driver or oneAPI configuration issue")
    sys.exit(1)
