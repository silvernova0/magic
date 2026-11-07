# Setup Intel Arc GPU for PyTorch Training

## Prerequisites
You already have:
- ✅ Intel Arc B50 Pro GPU
- ✅ Intel Graphics Driver installed

## Step 1: Install Intel oneAPI Base Toolkit

Download and install from:
https://www.intel.com/content/www/us/en/developer/tools/oneapi/base-toolkit-download.html

**Recommended**: Install only these components (to save space):
- Intel oneAPI DPC++/C++ Compiler
- Intel oneAPI Math Kernel Library (oneMKL)
- Intel oneAPI Threading Building Blocks (oneTBB)

**Installation Path**: Default is `C:\Program Files (x86)\Intel\oneAPI`

## Step 2: Set Environment Variables

After installation, run these commands in PowerShell (or add to your profile):

```powershell
# Set oneAPI environment variables
$env:ONEAPI_ROOT = "C:\Program Files (x86)\Intel\oneAPI"
call "$env:ONEAPI_ROOT\setvars.bat"
```

Or create a batch file `setup_oneapi.bat`:
```batch
@echo off
call "C:\Program Files (x86)\Intel\oneAPI\setvars.bat"
```

## Step 3: Verify Installation

After installing oneAPI, run:
```bash
C:\Users\fuckthisshit\openvino_env\Scripts\python -c "import torch; import intel_extension_for_pytorch as ipex; print('XPU available:', torch.xpu.is_available()); print('XPU device:', torch.xpu.get_device_name(0) if torch.xpu.is_available() else 'Not detected')"
```

## Step 4: Test GPU Training

Create a simple test:
```python
import torch
import intel_extension_for_pytorch as ipex

# Check XPU
print(f"XPU available: {torch.xpu.is_available()}")
print(f"XPU device count: {torch.xpu.device_count()}")

if torch.xpu.is_available():
    print(f"XPU device: {torch.xpu.get_device_name(0)}")
    
    # Simple tensor operation
    x = torch.randn(1000, 1000).to("xpu")
    y = torch.randn(1000, 1000).to("xpu")
    z = torch.mm(x, y)
    print("✅ GPU tensor operations working!")
```

## Alternative: CPU Training (Simpler)

If oneAPI installation is complex or fails:
- Train on CPU (24-36 hours instead of 12-18)
- Still export to OpenVINO for fast GPU inference
- CPU training is reliable and requires no additional setup

To proceed with CPU training right now:
```bash
C:\Users\fuckthisshit\openvino_env\Scripts\python scripts/train-commander-model.py
```

The script is already configured to work on CPU.

## Recommendation

**Option A (GPU Training - Faster but Complex)**:
1. Download oneAPI Base Toolkit (~3GB)
2. Install (15-30 minutes)
3. Set environment variables
4. Test GPU detection
5. Run training (12-18 hours)

**Option B (CPU Training - Simple)**:
1. Run training script now
2. Wait 24-36 hours
3. Export to OpenVINO for fast inference

Both options produce the same final model. The difference is only training time.
