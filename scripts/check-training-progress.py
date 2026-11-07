"""
Check Commander model training progress.

This script reads the progress file created by the training script
and displays current training status, even if you're disconnected from
the training session.

Usage:
    python scripts/check-training-progress.py
"""

import json
import os
from datetime import datetime
from pathlib import Path


def format_time_diff(iso_time):
    """Format time difference from now."""
    last_update = datetime.fromisoformat(iso_time)
    diff = datetime.now() - last_update
    
    total_seconds = int(diff.total_seconds())
    if total_seconds < 60:
        return f"{total_seconds} seconds ago"
    elif total_seconds < 3600:
        return f"{total_seconds // 60} minutes ago"
    else:
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        return f"{hours}h {minutes}m ago"


def check_progress():
    """Check training progress."""
    progress_file = "models/commander-llama-lora/training_progress.json"
    
    print("=" * 70)
    print("COMMANDER MODEL TRAINING - PROGRESS CHECK")
    print("=" * 70)
    print()
    
    # Check if progress file exists
    if not os.path.exists(progress_file):
        print("❌ No training progress file found")
        print(f"   Expected: {progress_file}")
        print()
        print("Possible reasons:")
        print("  • Training hasn't started yet")
        print("  • Training failed before first progress update")
        print("  • Progress file was deleted")
        print()
        
        # Check for checkpoints
        checkpoint_dir = "models/commander-llama-lora/checkpoints"
        if os.path.exists(checkpoint_dir):
            checkpoints = [d for d in os.listdir(checkpoint_dir) 
                          if d.startswith("checkpoint-")]
            if checkpoints:
                checkpoints.sort(key=lambda x: int(x.split("-")[1]))
                print(f"✓ Found {len(checkpoints)} checkpoint(s):")
                for cp in checkpoints[-5:]:  # Show last 5
                    print(f"  • {cp}")
                print()
                print("Training may have completed or is using old checkpoints.")
            else:
                print("No checkpoints found either.")
        
        return
    
    # Read progress
    try:
        with open(progress_file, 'r') as f:
            progress = json.load(f)
    except Exception as e:
        print(f"❌ Error reading progress file: {e}")
        return
    
    # Display status
    print("✓ TRAINING IS ACTIVE")
    print()
    
    # Progress
    step = progress.get('global_step', 0)
    max_steps = progress.get('max_steps', 0)
    percent = progress.get('progress_percent', 0)
    
    print(f"📊 Progress:     {step:,} / {max_steps:,} steps ({percent}%)")
    
    # Progress bar
    bar_width = 50
    filled = int(bar_width * percent / 100)
    bar = "█" * filled + "░" * (bar_width - filled)
    print(f"               [{bar}]")
    print()
    
    # Current metrics
    epoch = progress.get('epoch', 0)
    loss = progress.get('loss', 'N/A')
    lr = progress.get('learning_rate', 'N/A')
    
    print(f"📈 Current Epoch: {epoch:.2f}" if isinstance(epoch, float) else f"📈 Current Epoch: {epoch}")
    
    if isinstance(loss, (int, float)):
        print(f"📉 Training Loss: {loss:.4f}")
    else:
        print(f"📉 Training Loss: {loss}")
    
    if isinstance(lr, (int, float)):
        print(f"🎯 Learning Rate: {lr:.2e}")
    else:
        print(f"🎯 Learning Rate: {lr}")
    
    print()
    
    # Last update
    last_update = progress.get('last_update', 'Unknown')
    if last_update != 'Unknown':
        time_ago = format_time_diff(last_update)
        print(f"⏱️  Last Update:   {time_ago}")
        print(f"               {last_update}")
    
    print()
    
    # Estimate time remaining
    if max_steps > 0 and step > 0:
        steps_remaining = max_steps - step
        # Rough estimate: ~0.5 seconds per step on Arc B50 Pro
        seconds_remaining = steps_remaining * 0.5
        hours = int(seconds_remaining // 3600)
        minutes = int((seconds_remaining % 3600) // 60)
        print(f"⏳ Est. Time Left: ~{hours}h {minutes}m")
        print(f"               ({steps_remaining:,} steps remaining)")
    
    print()
    
    # Check for checkpoints
    checkpoint_dir = "models/commander-llama-lora/checkpoints"
    if os.path.exists(checkpoint_dir):
        checkpoints = [d for d in os.listdir(checkpoint_dir) 
                      if d.startswith("checkpoint-")]
        if checkpoints:
            checkpoints.sort(key=lambda x: int(x.split("-")[1]))
            latest = checkpoints[-1]
            print(f"💾 Latest Checkpoint: {latest}")
            print(f"                   Total: {len(checkpoints)} checkpoints saved")
    
    print()
    print("=" * 70)
    
    # Check if training seems stuck
    if last_update != 'Unknown':
        last_time = datetime.fromisoformat(last_update)
        diff_seconds = (datetime.now() - last_time).total_seconds()
        
        if diff_seconds > 600:  # 10 minutes
            print()
            print("⚠️  WARNING: No progress update in 10+ minutes")
            print("   Training may have crashed or stalled")
            print("   Check the training log file or restart training")


if __name__ == "__main__":
    check_progress()
