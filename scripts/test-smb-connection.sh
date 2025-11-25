#!/bin/bash
#
# Test SMB share connectivity
# Usage: bash scripts/test-smb-connection.sh
#

SMB_SHARE="//192.168.0.151/aitrainingv4"
MOUNT_POINT="/mnt/aitraining_test"

echo "🔌 Testing SMB Share Connection"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Target: $SMB_SHARE"
echo ""

# Check if cifs-utils is installed
if ! command -v mount.cifs &> /dev/null; then
    echo "❌ cifs-utils not installed"
    echo ""
    echo "Install with:"
    echo "   sudo apt-get update"
    echo "   sudo apt-get install cifs-utils"
    echo ""
    exit 1
fi

echo "✅ cifs-utils installed"
echo ""

# Check network connectivity
echo "🌐 Testing network connectivity..."
if ping -c 1 -W 2 192.168.0.151 &> /dev/null; then
    echo "✅ Host 192.168.0.151 is reachable"
else
    echo "❌ Host 192.168.0.151 is not reachable"
    echo ""
    echo "Troubleshooting:"
    echo "   - Check if Windows machine is on"
    echo "   - Verify IP address: 192.168.0.151"
    echo "   - Check firewall settings on Windows"
    echo "   - Ensure SMB sharing is enabled"
    exit 1
fi

echo ""

# Create temporary mount point
sudo mkdir -p "$MOUNT_POINT"

# Try to mount
echo "🔧 Attempting to mount SMB share..."
echo "   (You may be prompted for credentials)"
echo ""

if sudo mount -t cifs "$SMB_SHARE" "$MOUNT_POINT" -o guest,uid=$UID,gid=$GID 2>/dev/null; then
    echo "✅ Mounted successfully (guest access)"
    
    # List contents
    echo ""
    echo "📁 Share contents:"
    ls -la "$MOUNT_POINT/" | head -10
    
    # Test write access
    echo ""
    echo "✍️  Testing write access..."
    TEST_FILE="$MOUNT_POINT/test_write_$(date +%s).txt"
    if echo "Test write from Linux" > "$TEST_FILE" 2>/dev/null; then
        echo "✅ Write access confirmed"
        rm "$TEST_FILE" 2>/dev/null
    else
        echo "⚠️  No write access (read-only or permissions issue)"
    fi
    
    # Unmount
    sudo umount "$MOUNT_POINT"
    echo ""
    echo "✅ Test complete - share is accessible!"
    
elif sudo mount -t cifs "$SMB_SHARE" "$MOUNT_POINT" -o user=$USER,uid=$UID,gid=$GID; then
    echo "✅ Mounted successfully (authenticated)"
    
    # List contents
    echo ""
    echo "📁 Share contents:"
    ls -la "$MOUNT_POINT/" | head -10
    
    # Test write access
    echo ""
    echo "✍️  Testing write access..."
    TEST_FILE="$MOUNT_POINT/test_write_$(date +%s).txt"
    if echo "Test write from Linux" > "$TEST_FILE" 2>/dev/null; then
        echo "✅ Write access confirmed"
        rm "$TEST_FILE" 2>/dev/null
    else
        echo "⚠️  No write access (read-only or permissions issue)"
    fi
    
    # Unmount
    sudo umount "$MOUNT_POINT"
    echo ""
    echo "✅ Test complete - share is accessible!"
    
else
    echo "❌ Failed to mount share"
    echo ""
    echo "Troubleshooting steps:"
    echo ""
    echo "1. Verify share path on Windows:"
    echo "   - Open File Explorer on Windows"
    echo "   - Right-click the folder → Properties → Sharing"
    echo "   - Note the share name (should be 'aitrainingv4')"
    echo ""
    echo "2. Check Windows sharing settings:"
    echo "   - Settings → Network & Internet → Advanced sharing settings"
    echo "   - Enable 'File and printer sharing'"
    echo "   - Enable 'Turn on network discovery'"
    echo ""
    echo "3. Windows Firewall:"
    echo "   - Allow 'File and Printer Sharing' through firewall"
    echo ""
    echo "4. Try manual mount with credentials:"
    echo "   sudo mount -t cifs $SMB_SHARE $MOUNT_POINT -o user=YOUR_USERNAME,uid=\$UID,gid=\$GID"
    echo ""
    echo "5. Alternative: Use smbclient to test:"
    echo "   smbclient -L //192.168.0.151"
    echo ""
fi

# Cleanup
sudo rmdir "$MOUNT_POINT" 2>/dev/null

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Next steps:"
echo "1. If test passed: Run bash scripts/collect-training-data-windows.sh"
echo "2. After scraping completes: Run bash scripts/package-training-data.sh"
echo ""
