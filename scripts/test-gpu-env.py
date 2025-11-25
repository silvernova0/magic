import torch
import intel_extension_for_pytorch as ipex
import sys

print(f"Python: {sys.version}")
print(f"Torch: {torch.__version__}")
print(f"IPEX: {ipex.__version__}")
print(f"XPU Available: {torch.xpu.is_available()}")
if torch.xpu.is_available():
    print(f"XPU Device Name: {torch.xpu.get_device_name(0)}")
    print(f"XPU Device Count: {torch.xpu.device_count()}")
else:
    print("❌ XPU NOT DETECTED")
