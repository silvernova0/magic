"""
Monitor system memory and GPU usage during training.

This script displays real-time memory usage to help identify if the system
is running out of RAM or GPU VRAM.

Usage:
    python scripts/monitor-memory.py
"""

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


def get_gpu_memory():
    """Get GPU memory usage if available."""
    if not GPU_AVAILABLE:
        return None
    
    try:
        # Get XPU memory info
        device_count = torch.xpu.device_count()
        gpu_info = []
        
        for i in range(device_count):
            device_name = torch.xpu.get_device_name(i)
            # Note: XPU doesn't have direct memory query like CUDA
            # We'll try to get basic info
            gpu_info.append({
                'id': i,
                'name': device_name,
                'memory_allocated': 'N/A',  # XPU doesn't expose this easily
                'memory_total': 'N/A'
            })
        
        return gpu_info
    except Exception as e:
        return None


def monitor_memory(interval=5):
    """Monitor system memory usage."""
    print("=" * 70)
    print("SYSTEM MEMORY & GPU MONITOR")
    print("=" * 70)
    print()
    
    if GPU_AVAILABLE:
        print("✓ Intel Arc GPU monitoring enabled")
    else:
        print("⚠ GPU monitoring unavailable (Intel XPU not detected)")
    
    print()
    print("Monitoring memory usage every {} seconds...".format(interval))
    print("Press Ctrl+C to stop")
    print()
    
    try:
        while True:
            # System memory
            mem = psutil.virtual_memory()
            
            # Find Python processes
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
            
            # Clear screen (Windows)
            os.system('cls' if os.name == 'nt' else 'clear')
            
            print("=" * 70)
            print(f"MEMORY & GPU MONITOR - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 70)
            print()
            
            # GPU memory stats (if available)
            gpu_info = get_gpu_memory()
            if gpu_info:
                print("🎮 GPU MEMORY:")
                for gpu in gpu_info:
                    print(f"   Device {gpu['id']}: {gpu['name']}")
                    if gpu['memory_allocated'] != 'N/A':
                        print(f"   Allocated: {gpu['memory_allocated']}")
                        print(f"   Total:     {gpu['memory_total']}")
                    else:
                        print(f"   Status:    Active (memory details not available via XPU)")
                print()
            
            # System memory stats
            print("📊 SYSTEM MEMORY:")
            print(f"   Total:     {format_bytes(mem.total)}")
            print(f"   Used:      {format_bytes(mem.used)} ({mem.percent}%)")
            print(f"   Available: {format_bytes(mem.available)}")
            
            # Memory bar
            bar_width = 50
            used_bars = int(bar_width * mem.percent / 100)
            free_bars = bar_width - used_bars
            
            if mem.percent < 70:
                color = "🟢"  # Green
            elif mem.percent < 85:
                color = "🟡"  # Yellow
            else:
                color = "🔴"  # Red
            
            print(f"   {color} [{'█' * used_bars}{'░' * free_bars}] {mem.percent}%")
            print()
            
            # Python processes
            if python_processes:
                print("🐍 PYTHON PROCESSES:")
                total_python_memory = 0
                for proc in sorted(python_processes, key=lambda x: x['memory'], reverse=True):
                    print(f"   PID {proc['pid']:6d}: {format_bytes(proc['memory']):>12s} - {proc['name']}")
                    total_python_memory += proc['memory']
                
                print(f"   {'─' * 66}")
                print(f"   Total:      {format_bytes(total_python_memory):>12s}")
                print()
            
            # Warnings
            if mem.percent > 90:
                print("⚠️  WARNING: System memory usage is very high!")
                print("   Training may crash due to out-of-memory error")
                print()
            elif mem.percent > 80:
                print("⚠️  CAUTION: System memory usage is high")
                print()
            
            print("Press Ctrl+C to stop monitoring...")
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print()
        print("Monitoring stopped")


if __name__ == "__main__":
    monitor_memory()
