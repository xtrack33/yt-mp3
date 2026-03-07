# YT-MP3

Minimal self-hosted YouTube to MP3 converter. Paste a link, click, download.

## Requirements

- Python 3.8+
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- [ffmpeg](https://ffmpeg.org/)

## Quick start

```bash
# macOS
brew install yt-dlp ffmpeg
python3 yt_mp3.py

# Linux (Debian/Ubuntu)
sudo apt install ffmpeg
pip3 install yt-dlp
python3 yt_mp3.py
```

Open `http://localhost:8899`

## Options

```
-p, --port    Port (default: 8899)
-d, --dir     Download directory (default: ~/Downloads)
--host        Bind address (default: 127.0.0.1)
```

Environment variables: `YTMP3_PORT`, `YTMP3_DIR`, `YTMP3_HOST`

## Deploy with systemd

```bash
sudo cp yt-mp3.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now yt-mp3
```

## License

MIT
