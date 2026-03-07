#!/bin/bash
set -e

echo "=== YT-MP3 Uninstaller ==="

if [ "$(id -u)" -ne 0 ]; then
    echo "Run as root: sudo ./uninstall.sh"
    exit 1
fi

echo "[1/3] Stopping service..."
systemctl stop yt-mp3 2>/dev/null || true
systemctl disable yt-mp3 2>/dev/null || true
rm -f /etc/systemd/system/yt-mp3.service
systemctl daemon-reload
echo "  Service removed"

echo "[2/3] Removing Apache config..."
if [ -f /etc/apache2/conf-enabled/yt-mp3.conf ]; then
    a2disconf yt-mp3 2>/dev/null || true
    rm -f /etc/apache2/conf-available/yt-mp3.conf
    systemctl reload apache2 2>/dev/null || true
    echo "  Apache conf removed"
else
    echo "  No standalone Apache conf found (check your vhost manually)"
fi

echo "[3/3] Cleaning downloads..."
INSTALL_DIR="$(cd "$(dirname "$0")" && pwd)"
rm -rf "$INSTALL_DIR/downloads"
echo "  Downloads deleted"

echo ""
echo "=== Done ==="
echo "Service and downloads removed."
echo "The app files are still in $INSTALL_DIR — delete manually if needed:"
echo "  rm -rf $INSTALL_DIR"
