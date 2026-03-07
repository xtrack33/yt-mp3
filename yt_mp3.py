#!/usr/bin/env python3
"""YT-MP3 — Mini serveur web pour télécharger des YouTube en MP3 via yt-dlp."""

import http.server
import json
import subprocess
import os
import sys
import re
import shutil
import argparse
import mimetypes
import urllib.parse

DEFAULT_PORT = 8899
DEFAULT_DIR = os.path.join(os.path.expanduser("~"), "Downloads")

# Auto-detect yt-dlp and ffmpeg paths
YTDLP = shutil.which("yt-dlp") or "/opt/homebrew/bin/yt-dlp"
FFMPEG = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"


HTML = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>YT-MP3</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: #0f0f0f;
    color: #e1e1e1;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
  }
  .container {
    background: #1a1a1a;
    border-radius: 16px;
    padding: 40px;
    width: 520px;
    max-width: 95vw;
    box-shadow: 0 8px 32px rgba(0,0,0,.4);
  }
  h1 {
    font-size: 24px;
    font-weight: 700;
    margin-bottom: 24px;
    text-align: center;
  }
  h1 span { color: #ff4444; }
  input {
    width: 100%;
    padding: 14px 16px;
    border: 2px solid #333;
    border-radius: 10px;
    background: #0f0f0f;
    color: #fff;
    font-size: 15px;
    outline: none;
    transition: border-color .2s;
  }
  input:focus { border-color: #ff4444; }
  input::placeholder { color: #666; }
  .btn-convert {
    width: 100%;
    margin-top: 16px;
    padding: 14px;
    border: none;
    border-radius: 10px;
    background: #ff4444;
    color: #fff;
    font-size: 16px;
    font-weight: 600;
    cursor: pointer;
    transition: background .2s, transform .1s;
  }
  .btn-convert:hover { background: #e03030; }
  .btn-convert:active { transform: scale(.98); }
  .btn-convert:disabled { background: #555; cursor: wait; }
  #status {
    margin-top: 20px;
    padding: 12px 16px;
    border-radius: 8px;
    font-size: 14px;
    display: none;
    text-align: center;
  }
  .loading { background: #1e293b; color: #93c5fd; }
  .success { background: #052e16; color: #86efac; }
  .error   { background: #350a0a; color: #fca5a5; }
  .spinner {
    display: inline-block;
    width: 14px; height: 14px;
    border: 2px solid #93c5fd;
    border-top-color: transparent;
    border-radius: 50%;
    animation: spin .6s linear infinite;
    vertical-align: middle;
    margin-right: 8px;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  .history { margin-top: 24px; }
  .history h3 { font-size: 13px; color: #666; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 1px; }
  .history-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    padding: 10px 14px;
    background: #0f0f0f;
    border-radius: 8px;
    font-size: 13px;
    margin-bottom: 6px;
    color: #ccc;
  }
  .history-item .name {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .btn-dl {
    flex-shrink: 0;
    padding: 6px 14px;
    border: none;
    border-radius: 6px;
    background: #22c55e;
    color: #fff;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    text-decoration: none;
    transition: background .2s;
  }
  .btn-dl:hover { background: #16a34a; }
</style>
</head>
<body>
<div class="container">
  <h1><span>YT</span>-MP3</h1>
  <input type="text" id="url" placeholder="Colle un lien YouTube ici..." autofocus>
  <button class="btn-convert" id="btn" onclick="convert()">Convertir en MP3</button>
  <div id="status"></div>
  <div class="history" id="historyBox" style="display:none">
    <h3>Fichiers</h3>
    <div id="historyList"></div>
  </div>
</div>
<script>
const status = document.getElementById('status');
const btn = document.getElementById('btn');
const urlInput = document.getElementById('url');
const historyBox = document.getElementById('historyBox');
const historyList = document.getElementById('historyList');

urlInput.addEventListener('keydown', e => { if (e.key === 'Enter') convert(); });

async function convert() {
  const url = urlInput.value.trim();
  if (!url) return;
  status.style.display = 'block';
  status.className = 'loading';
  status.innerHTML = '<span class="spinner"></span> Conversion en cours...';
  btn.disabled = true;
  try {
    const res = await fetch('/download', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({url})
    });
    const data = await res.json();
    if (data.ok) {
      status.className = 'success';
      status.textContent = data.file;
      addHistory(data.file);
      urlInput.value = '';
    } else {
      status.className = 'error';
      status.textContent = data.error;
    }
  } catch(e) {
    status.className = 'error';
    status.textContent = 'Erreur connexion serveur';
  }
  btn.disabled = false;
}

function addHistory(filename) {
  historyBox.style.display = 'block';
  const d = document.createElement('div');
  d.className = 'history-item';
  const name = document.createElement('span');
  name.className = 'name';
  name.title = filename;
  name.textContent = filename;
  const dl = document.createElement('a');
  dl.className = 'btn-dl';
  dl.href = '/files/' + encodeURIComponent(filename);
  dl.download = filename;
  dl.textContent = 'Telecharger';
  d.appendChild(name);
  d.appendChild(dl);
  historyList.prepend(d);
}
</script>
</body>
</html>"""


class YTHandler(http.server.BaseHTTPRequestHandler):

    download_dir = DEFAULT_DIR

    def do_GET(self):
        if self.path == "/" or self.path == "":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML.encode())
        elif self.path.startswith("/files/"):
            self.serve_file()
        else:
            self.send_error(404)

    def serve_file(self):
        filename = urllib.parse.unquote(self.path[7:])  # strip /files/
        # Sécurité : pas de path traversal
        filename = os.path.basename(filename)
        filepath = os.path.join(self.download_dir, filename)
        if not os.path.isfile(filepath):
            self.send_error(404, "Fichier non trouve")
            return
        self.send_response(200)
        mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(os.path.getsize(filepath)))
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.end_headers()
        with open(filepath, "rb") as f:
            while chunk := f.read(65536):
                self.wfile.write(chunk)

    def do_POST(self):
        if self.path != "/download":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))
        url = body.get("url", "")

        if not re.match(r"https?://(www\.)?(youtube\.com|youtu\.be|music\.youtube\.com)/", url):
            self.respond({"ok": False, "error": "Lien YouTube invalide"})
            return

        try:
            cmd = [YTDLP]
            if FFMPEG:
                cmd += ["--ffmpeg-location", FFMPEG]
            cmd += [
                "-x", "--audio-format", "mp3", "--audio-quality", "0",
                "-o", os.path.join(self.download_dir, "%(title)s.%(ext)s"),
                "--no-playlist",
                url,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)

            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    if "[ExtractAudio] Destination:" in line:
                        filename = os.path.basename(line.split("Destination: ", 1)[1])
                        self.respond({"ok": True, "file": filename})
                        return
                    if "[download] " in line and " has already been downloaded" in line:
                        filename = os.path.basename(
                            line.split("[download] ", 1)[1].split(" has already")[0]
                        )
                        self.respond({"ok": True, "file": filename})
                        return
                self.respond({"ok": True, "file": "MP3 converti"})
            else:
                err = result.stderr.strip().split("\n")[-1] if result.stderr else "Erreur yt-dlp"
                self.respond({"ok": False, "error": err[:200]})
        except subprocess.TimeoutExpired:
            self.respond({"ok": False, "error": "Timeout (>3min)"})
        except Exception as e:
            self.respond({"ok": False, "error": str(e)[:200]})

    def respond(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def log_message(self, fmt, *args):
        print(f"  {args[0]}")


def main():
    parser = argparse.ArgumentParser(description="YT-MP3 — YouTube to MP3 downloader")
    parser.add_argument("-p", "--port", type=int, default=int(os.environ.get("YTMP3_PORT", DEFAULT_PORT)))
    parser.add_argument("-d", "--dir", default=os.environ.get("YTMP3_DIR", DEFAULT_DIR))
    parser.add_argument("--host", default=os.environ.get("YTMP3_HOST", "127.0.0.1"))
    args = parser.parse_args()

    os.makedirs(args.dir, exist_ok=True)
    YTHandler.download_dir = os.path.abspath(args.dir)

    server = http.server.HTTPServer((args.host, args.port), YTHandler)
    print(f"\n  YT-MP3 ready on http://{args.host}:{args.port}")
    print(f"  Download dir: {YTHandler.download_dir}\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Bye!")


if __name__ == "__main__":
    main()
