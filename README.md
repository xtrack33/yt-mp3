# YT-MP3

Minimal self-hosted YouTube to MP3 converter. Paste a link, click, download.

Files are automatically deleted from the server after download.

## Quick start (local)

```bash
# macOS
brew install yt-dlp ffmpeg
git clone https://github.com/xtrack33/yt-mp3.git ~/yt-mp3
cd ~/yt-mp3
python3 yt_mp3.py
```

Open http://localhost:8899

## Install on a server (Debian/Ubuntu)

```bash
# Clone the repo
cd /opt
git clone https://github.com/xtrack33/yt-mp3.git
cd yt-mp3

# Run the install script
chmod +x install.sh
sudo ./install.sh
```

The install script will:
- Install `ffmpeg` and `yt-dlp`
- Create the download directory `/opt/yt-mp3/downloads`
- Install and start the `yt-mp3` systemd service
- The app runs on `http://127.0.0.1:8899`

### Reverse proxy (Apache)

```apache
ProxyPass /yt-mp3/ http://127.0.0.1:8899/
ProxyPassReverse /yt-mp3/ http://127.0.0.1:8899/
```

### Reverse proxy (Nginx)

```nginx
location /yt-mp3/ {
    proxy_pass http://127.0.0.1:8899/;
}
```

## Options

```
-p, --port    Port (default: 8899)
-d, --dir     Download directory (default: ~/Downloads)
--host        Bind address (default: 127.0.0.1)
```

Environment variables: `YTMP3_PORT`, `YTMP3_DIR`, `YTMP3_HOST`

## Update

```bash
cd /opt/yt-mp3
git pull
sudo systemctl restart yt-mp3
```

## License

MIT
