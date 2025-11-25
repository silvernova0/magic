#!/bin/bash
# Install JankBuild services to run on boot

echo "Installing JankBuild systemd services..."

# Copy service files to systemd directory
sudo cp jankbuild-api.service /etc/systemd/system/
sudo cp jankbuild-web.service /etc/systemd/system/

# Reload systemd to recognize new services
sudo systemctl daemon-reload

# Enable services to start on boot
sudo systemctl enable jankbuild-api.service
sudo systemctl enable jankbuild-web.service

# Start services now
sudo systemctl start jankbuild-api.service
sudo systemctl start jankbuild-web.service

echo ""
echo "✅ Services installed and started!"
echo ""
echo "Useful commands:"
echo "  sudo systemctl status jankbuild-api    # Check API status"
echo "  sudo systemctl status jankbuild-web    # Check web status"
echo "  sudo systemctl restart jankbuild-api   # Restart API"
echo "  sudo systemctl restart jankbuild-web   # Restart web"
echo "  sudo systemctl stop jankbuild-api      # Stop API"
echo "  sudo systemctl stop jankbuild-web      # Stop web"
echo "  journalctl -u jankbuild-api -f         # View API logs"
echo "  journalctl -u jankbuild-web -f         # View web logs"
echo ""
echo "Services will now start automatically on boot!"
