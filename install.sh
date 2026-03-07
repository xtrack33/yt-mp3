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

echo "[1/5] Installing dependencies..."
apt-get update -qq
apt-get install -y -qq ffmpeg python3
pip3 install --break-system-packages yt-dlp 2>/dev/null || pip3 install yt-dlp
echo "  yt-dlp: $(which yt-dlp)"
echo "  ffmpeg: $(which ffmpeg)"

echo "[2/5] Creating download directory..."
mkdir -p "$DL_DIR"
chown www-data:www-data "$DL_DIR"

echo "[3/5] Installing systemd service..."
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

echo "[4/5] Starting service..."
systemctl daemon-reload
systemctl enable --now yt-mp3

echo "[5/5] Configuring Apache reverse proxy..."
if command -v apache2 &>/dev/null; then
    a2enmod proxy proxy_http rewrite 2>/dev/null

    # Add /yt-mp3/ proxy to the default-ip vhost if it exists
    if [ -f /etc/apache2/sites-available/default-ip.conf ]; then
        if ! grep -q "yt-mp3" /etc/apache2/sites-available/default-ip.conf; then
            sed -i '/<\/VirtualHost>/i\
    ProxyPass /yt-mp3/ http://127.0.0.1:8899/\
    ProxyPassReverse /yt-mp3/ http://127.0.0.1:8899/' /etc/apache2/sites-available/default-ip.conf
        fi
    else
        # Create a standalone conf
        cat > /etc/apache2/conf-available/yt-mp3.conf << 'APCONF'
ProxyPass /yt-mp3/ http://127.0.0.1:8899/
ProxyPassReverse /yt-mp3/ http://127.0.0.1:8899/
<Location /yt-mp3/>
    Require all granted
</Location>
APCONF
        a2enconf yt-mp3
    fi

    apache2ctl configtest && systemctl reload apache2
    echo "  Apache: /yt-mp3/ -> localhost:8899"
elif command -v nginx &>/dev/null; then
    echo "  Nginx detected. Add this to your server block:"
    echo "    location /yt-mp3/ { proxy_pass http://127.0.0.1:8899/; }"
else
    echo "  No web server detected. Access directly on http://localhost:8899"
fi

echo ""
echo "=== Done ==="
echo "YT-MP3 running on http://<your-ip>/yt-mp3/"
echo "Downloads: $DL_DIR"
