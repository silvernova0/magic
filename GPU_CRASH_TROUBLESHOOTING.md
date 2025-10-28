# Intel Arc GPU Training Crash - Troubleshooting

## Problem
Training crashed with: `RuntimeError: Native API failed. Native API returns: 20 (UR_RESULT_ERROR_DEVICE_LOST)`

This means the Intel Arc GPU driver crashed or the device became unresponsive after processing 10 batches (~35 minutes).

## Root Causes

### 1. Windows TDR (Timeout Detection and Recovery)
Windows kills GPU operations that run too long without responding. This is the most likely cause.

**Solution:**
1. Run `disable-tdr.bat` **as Administrator**
2. Restart your computer
3. Try training again

### 2. GPU Overheating
Arc B50 Pro may be thermal throttling under sustained ML workload.

**Check:**
- Use HWiNFO64 or GPU-Z to monitor temperatures
- Check if GPU fans are working
- Ensure good case airflow

**Target:** Keep GPU under 80°C

### 3. Driver Instability
Intel Arc drivers are still maturing for ML workloads.

**Update:**
1. Go to: https://www.intel.com/content/www/us/en/download/785597/intel-arc-iris-xe-graphics-windows.html
2. Download latest Intel Arc Graphics driver
3. Install and restart
4. Try training again

### 4. Memory Pressure
8B model + 2048 token sequences overwhelming 16GB VRAM.

**Already Applied:**
- ✅ Reduced `MAX_SEQ_LENGTH` from 2048 → 1024 tokens
- ✅ Added XPU synchronization after backward pass
- ✅ More aggressive garbage collection (every 10 steps)
- ✅ GPU cache clearing after checkpoints

## Optimization Changes Applied

### 1. Reduced Sequence Length
```python
MAX_SEQ_LENGTH = 1024  # Was 2048
```
- **Impact:** 50% less GPU memory per batch
- **Trade-off:** May truncate longer deck descriptions

### 2. XPU Synchronization
```python
if device == "xpu":
    torch.xpu.synchronize()
```
- **Impact:** Prevents driver from queuing too many operations
- **Trade-off:** Slightly slower (~5-10%) but more stable

### 3. Aggressive Memory Management
```python
# Every 10 steps (was 50)
gc.collect()
torch.xpu.empty_cache()
```
- **Impact:** Prevents memory fragmentation
- **Trade-off:** Minor performance overhead

## Next Steps

### Option 1: Fix TDR and Retry (RECOMMENDED)
1. Run `disable-tdr.bat` as Administrator
2. Restart computer
3. Run `train-model-manual.bat`
4. Training should complete without driver crashes

### Option 2: Use CPU Training (SLOWER)
If GPU continues to crash, fall back to CPU:

1. Edit `train-commander-model-manual.py`
2. Change line ~169:
```python
# Force CPU training
device = "cpu"
dtype = torch.float32
```
3. Expected time: 3-5 days instead of 12-18 hours

### Option 3: Cloud GPU Training
Use a cloud provider with proven ML GPU support:
- AWS EC2 P3 instances (NVIDIA V100)
- Google Cloud Platform (NVIDIA A100/T4)
- Lambda Labs (cheaper, NVIDIA RTX 4090)

## Expected Training Time After Fixes
- **With TDR disabled:** 12-18 hours (original estimate)
- **With reduced sequence length:** May be 10-15 hours
- **214 seconds/batch is VERY SLOW** - should be 20-60 seconds after stabilization

The first few batches are always slower as XPU initializes kernels. If it stays at 200+ seconds per batch, there may be a deeper driver/performance issue.

## Monitoring Commands

```powershell
# Check if training is running
Get-Process -Name python | Where-Object {$_.CPU -gt 100}

# Check latest log entries
Get-Content "models\commander-llama-lora\training_manual_20251024_183006.log" -Tail 20

# Check progress (after step 1)
.\check-progress.bat

# Monitor memory
.\monitor-memory.bat
```

## If All Else Fails

Consider using a more mature ML GPU:
- Intel Arc is still experimental for PyTorch
- NVIDIA GPUs have much better driver support for ML
- AMD ROCm is improving but still behind NVIDIA
- Apple Silicon (M-series) is solid but macOS-only

The Intel Arc B50 Pro is a great budget GPU for gaming/graphics, but ML workloads expose driver immaturity issues.
