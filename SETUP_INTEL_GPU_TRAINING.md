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

---

# Ubuntu 22.04+ Setup (Intel Arc B50 Pro)

The Windows instructions above remain valid, but you now run the stack on Ubuntu. Follow these steps to prepare the Arc GPU and Python environment before launching training.

## 1. Install Intel GPU Drivers & Level Zero

> Requires sudo privileges.

```bash
sudo apt update
sudo apt install -y gpg-agent software-properties-common
wget -qO- https://repositories.intel.com/graphics/intel-graphics.key | \
  sudo gpg --dearmor -o /usr/share/keyrings/intel-graphics.gpg
echo 'deb [arch=amd64 signed-by=/usr/share/keyrings/intel-graphics.gpg] https://repositories.intel.com/graphics/ubuntu jammy main' | \
  sudo tee /etc/apt/sources.list.d/intel.gpu.jammy.list
sudo apt update
sudo apt install -y \
  intel-opencl-icd intel-level-zero-gpu level-zero \
  intel-media-va-driver-non-free clinfo
```

Reboot after the packages finish installing:

```bash
sudo reboot
```

## 2. Install the Intel oneAPI Base Toolkit

Intel publishes an APT repo for Linux installers:

```bash
wget https://registrationcenter-download.intel.com/akdlm/irc_nas/18706/l_BaseKit_p_2024.2.0.596_offline.sh
sudo bash l_BaseKit_p_2024.2.0.596_offline.sh -a --silent --eula accept
```

> Prefer the latest installer from Intel’s download center if the version above changes. Minimal components needed: *Base Kit* → DPC++/C++, oneMKL, oneTBB.

oneAPI installs to `/opt/intel/oneapi`. Add the environment hook to your shell:

```bash
echo 'source /opt/intel/oneapi/setvars.sh' >> ~/.bashrc
source ~/.bashrc
```

To avoid polluting login shells, you can instead export `ONEAPI_ROOT=/opt/intel/oneapi` and source `setvars.sh` only when you train.

## 3. Create a Python Environment with PyTorch + IPEX (XPU)

```bash
cd /home/social/dev/myapp
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip wheel setuptools

# Install the Intel-provided PyTorch wheels for Arc GPUs (note the +xpu tag)
pip install --no-cache-dir \
  torch==2.8.0+xpu torchaudio==2.8.0+xpu \
  --index-url https://pytorch-extension.intel.com/release-whl/stable/xpu/us/

pip install --no-cache-dir \
  torchvision==0.23.0+xpu \
  --index-url https://pytorch-extension.intel.com/release-whl/stable/xpu/us/

# Install Intel Extension for PyTorch (IPEX) matching the Torch version
pip install --no-cache-dir intel-extension-for-pytorch==2.8.10+xpu \
  --index-url https://pytorch-extension.intel.com/release-whl/stable/xpu/us/

# (Optional) Clear pip cache first if you previously downloaded CUDA builds
# pip cache purge

# Install repo dependencies
pip install -r requirements.txt
```

If Intel releases newer matched versions (e.g., 2.4, 2.5), install the matching `torch` and `intel-extension-for-pytorch` builds from the same feed.

## 4. Validate GPU Visibility

```bash
source /opt/intel/oneapi/setvars.sh
source .venv/bin/activate
python -c "import torch, intel_extension_for_pytorch as ipex; \
print('Torch:', torch.__version__); \
print('IPEX:', ipex.__version__); \
print('XPU available:', torch.xpu.is_available()); \
print('Device:', torch.xpu.get_device_name(0) if torch.xpu.is_available() else 'N/A')"
```

You should see `XPU available: True` and the Arc B50 device string. If not, revisit the driver/oneAPI install.

You can also run the repo’s check:

```bash
python scripts/test-gpu.py
```

## 5. Launch Training (Manual Loop)

The new Linux helper mirrors the Windows batch file:

```bash
chmod +x train-model-manual.sh   # once
./train-model-manual.sh
```

Environment toggles such as `USE_IPEX`, `GRADIENT_CHECKPOINTING`, `RUN_PREP`, and `HF_DATASETS_CACHE` can be exported before the command or set inline:

```bash
USE_IPEX=1 GRADIENT_CHECKPOINTING=1 ./train-model-manual.sh
```

The script sources oneAPI, sets up caches, optionally re-generates training data, and invokes `scripts/train-commander-model-manual.py`.

## 6. Monitoring & Resume

- Training logs live in `models/commander-llama-lora/training_manual_*.log`
- Progress JSON: `models/commander-llama-lora/training_progress.json`
- Resume by re-running `./train-model-manual.sh`; the Python script loads the most recent checkpoint automatically.

## 7. Troubleshooting

- If `torch.xpu.is_available()` is `False`, check `dmesg | grep i915` for driver errors and confirm you sourced `setvars.sh`.
- For out-of-memory errors, drop `BATCH_SIZE=1` and raise `GRADIENT_ACCUMULATION_STEPS=16` in `scripts/train-commander-model-manual.py`.
- Test Level Zero devices: `python scripts/check-level-zero.py`

Once training completes, follow the existing sections in this guide to export to OpenVINO and integrate with the app.
