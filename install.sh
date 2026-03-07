#!/bin/bash
set -e

echo "=== YT-MP3 Installer ==="

# Check root
if [ "$(id -u)" -ne 0 ]; then
    echo "Run as root: sudo ./install.sh"
    exit 1
fi

INSTALL_DIR="$(cd "$(dirname "$0")" && pwd)"
DL_DIR="$INSTALL_DIR/downloads"

echo "[1/4] Installing dependencies..."
apt-get update -qq
apt-get install -y -qq ffmpeg python3
pip3 install --break-system-packages yt-dlp 2>/dev/null || pip3 install yt-dlp
echo "  yt-dlp: $(which yt-dlp)"
echo "  ffmpeg: $(which ffmpeg)"

echo "[2/4] Creating download directory..."
mkdir -p "$DL_DIR"
chown www-data:www-data "$DL_DIR"

echo "[3/4] Installing systemd service..."
cat > /etc/systemd/system/yt-mp3.service << EOF
[Unit]
Description=YT-MP3 Web Downloader
After=network.target

[Service]
Type=simple
User=www-data
ExecStart=/usr/bin/python3 $INSTALL_DIR/yt_mp3.py --host 127.0.0.1 --port 8899 --dir $DL_DIR
Restart=on-failure
RestartSec=5
Environment=PATH=/usr/local/bin:/usr/bin:/bin

[Install]
WantedBy=multi-user.target
EOF

echo "[4/4] Starting service..."
systemctl daemon-reload
systemctl enable --now yt-mp3

echo ""
echo "=== Done ==="
echo "YT-MP3 running on http://127.0.0.1:8899"
echo "Downloads: $DL_DIR"
echo ""
echo "Configure your reverse proxy to forward /yt-mp3/ to http://127.0.0.1:8899/"
