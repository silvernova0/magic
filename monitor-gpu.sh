#!/bin/bash
# GPU Monitoring Script for Intel Arc B50 + Integrated Graphics

echo "GPU Monitoring Options:"
echo ""
echo "1. nvtop (interactive, shows both GPUs with VRAM usage)"
echo "2. intel_gpu_top (interactive Intel-specific monitor)"
echo "3. Python monitor script (system + GPU info)"
echo "4. Quick VRAM check"
echo ""
read -p "Choose option (1-4): " choice

case $choice in
    1)
        echo "Launching nvtop..."
        nvtop
        ;;
    2)
        echo "Launching intel_gpu_top..."
        sudo intel_gpu_top
        ;;
    3)
        echo "Launching Python monitor..."
        python3 scripts/monitor-combined.py
        ;;
    4)
        echo "Current GPU Memory Usage:"
        echo ""
        intel_gpu_top -J -s 100 | grep -A 5 memory | head -20
        ;;
    *)
        echo "Invalid option"
        exit 1
        ;;
esac
