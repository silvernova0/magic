#!/bin/bash

# Define the sudoers file path
SUDOERS_FILE="/etc/sudoers.d/jankbuild-web"

# Content to write
# Allows the 'social' user to run 'systemctl restart jankbuild-web' without a password
CONFIG_LINE="social ALL=(root) NOPASSWD: /usr/bin/systemctl restart jankbuild-web"

echo "Configuring passwordless restart for jankbuild-web..."

# Check if the file already exists
if [ -f "$SUDOERS_FILE" ]; then
    echo "Updating existing sudoers file: $SUDOERS_FILE"
else
    echo "Creating new sudoers file: $SUDOERS_FILE"
fi

# Write the configuration using sudo
echo "$CONFIG_LINE" | sudo tee "$SUDOERS_FILE" > /dev/null

# Set correct permissions (0440 is standard for sudoers files)
sudo chmod 0440 "$SUDOERS_FILE"

# Validate the sudoers file syntax
if sudo visudo -c -f "$SUDOERS_FILE"; then
    echo "✅ Configuration successful! You can now restart the server without a password."
    echo "Test it by running: sudo systemctl restart jankbuild-web"
else
    echo "❌ Configuration failed validation. Removing file to prevent issues."
    sudo rm "$SUDOERS_FILE"
    exit 1
fi
