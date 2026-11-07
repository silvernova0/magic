"""
Enhanced memory and GPU monitor with Intel Arc support.

Monitors both system RAM and Intel Arc GPU usage in real-time.
"""

import subprocess
import psutil
import time
import os
import sys
from datetime import datetime

# Try to import Intel GPU monitoring
try:
    import intel_extension_for_pytorch as ipex
    import torch
    GPU_AVAILABLE = torch.xpu.is_available() if hasattr(torch, 'xpu') else False
except ImportError:
    GPU_AVAILABLE = False


def format_bytes(bytes_value):
    """Format bytes to human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} PB"


def check_xpu_smi():
    """Check if xpu-smi is available."""
    try:
        result = subprocess.run(['xpu-smi', 'discovery'], 
                              capture_output=True, text=True, timeout=2)
        return result.returncode == 0
    except:
        return False


def get_gpu_info_xpu_smi():
    """Get GPU info using xpu-smi if available."""
    try:
        # Get device info
        result = subprocess.run(['xpu-smi', 'dump', '-d', '0', '-m', '0,1,5'], 
                              capture_output=True, text=True, timeout=2)
        if result.returncode == 0:
            return result.stdout
        return None
    except:
        return None


def get_gpu_info_torch():
    """Get GPU info using PyTorch XPU."""
    if not GPU_AVAILABLE:
        return None
    
    try:
        info = []
        device_count = torch.xpu.device_count()
        for i in range(device_count):
            device_name = torch.xpu.get_device_name(i)
            info.append(f"Device {i}: {device_name}")
        return "\n".join(info) if info else None
    except:
        return None


def monitor_combined(interval=5):
    """Monitor both system memory and GPU."""
    has_xpu_smi = check_xpu_smi()
    
    print("=" * 70)
    print("COMBINED SYSTEM & GPU MONITOR")
    print("=" * 70)
    print()
    
    if has_xpu_smi:
        print("✓ Intel xpu-smi detected - detailed GPU monitoring enabled")
    elif GPU_AVAILABLE:
        print("✓ Intel XPU detected via PyTorch - basic GPU monitoring")
    else:
        print("⚠ GPU monitoring unavailable")
    
    print()
    print(f"Monitoring every {interval} seconds...")
    print("Press Ctrl+C to stop")
    print()
    
    try:
        while True:
            # Clear screen
            os.system('cls' if os.name == 'nt' else 'clear')
            
            print("=" * 70)
            print(f"SYSTEM & GPU MONITOR - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 70)
            print()
            
            # GPU Information
            print("🎮 GPU STATUS:")
            if has_xpu_smi:
                gpu_info = get_gpu_info_xpu_smi()
                if gpu_info:
                    print(gpu_info)
                else:
                    print("   Unable to get xpu-smi data")
            elif GPU_AVAILABLE:
                gpu_info = get_gpu_info_torch()
                if gpu_info:
                    print(f"   {gpu_info}")
                    print("   Note: Detailed memory usage not available via XPU API")
                else:
                    print("   GPU detected but unable to query info")
            else:
                print("   No GPU detected")
            
            print()
            
            # System Memory
            mem = psutil.virtual_memory()
            print("💾 SYSTEM MEMORY:")
            print(f"   Total:     {format_bytes(mem.total)}")
            print(f"   Used:      {format_bytes(mem.used)} ({mem.percent}%)")
            print(f"   Available: {format_bytes(mem.available)}")
            
            # Memory bar
            bar_width = 50
            used_bars = int(bar_width * mem.percent / 100)
            free_bars = bar_width - used_bars
            
            if mem.percent < 70:
                color = "🟢"
            elif mem.percent < 85:
                color = "🟡"
            else:
                color = "🔴"
            
            print(f"   {color} [{'█' * used_bars}{'░' * free_bars}] {mem.percent}%")
            print()
            
            # Python processes
            python_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
                try:
                    if 'python' in proc.info['name'].lower():
                        python_processes.append({
                            'pid': proc.info['pid'],
                            'name': proc.info['name'],
                            'memory': proc.info['memory_info'].rss
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            if python_processes:
                print("🐍 PYTHON PROCESSES:")
                total_python_memory = 0
                for proc in sorted(python_processes, key=lambda x: x['memory'], reverse=True):
                    print(f"   PID {proc['pid']:6d}: {format_bytes(proc['memory']):>12s}")
                    total_python_memory += proc['memory']
                
                print(f"   {'─' * 66}")
                print(f"   Total:      {format_bytes(total_python_memory):>12s}")
                print()
            
            # Warnings
            if mem.percent > 90:
                print("⚠️  WARNING: System memory >90% - training may crash!")
                print()
            elif mem.percent > 80:
                print("⚠️  CAUTION: System memory >80% - monitor closely")
                print()
            
            print("Press Ctrl+C to stop monitoring...")
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print()
        print("Monitoring stopped")


if __name__ == "__main__":
    monitor_combined()
