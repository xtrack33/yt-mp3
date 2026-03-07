#!/usr/bin/env python3
"""YT-MP3 — Minimal web server to download YouTube videos as MP3 or AVI via yt-dlp."""

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
import glob

DEFAULT_PORT = 8899
DEFAULT_DIR = os.path.join(os.path.expanduser("~"), "Downloads")

# Auto-detect yt-dlp and ffmpeg paths
YTDLP = shutil.which("yt-dlp") or "/opt/homebrew/bin/yt-dlp"
FFMPEG = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"


HTML = """<!DOCTYPE html>
<html lang="en">
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
  .format-row {
    display: flex;
    gap: 8px;
    margin-top: 12px;
  }
  .format-btn {
    flex: 1;
    padding: 10px;
    border: 2px solid #333;
    border-radius: 8px;
    background: #0f0f0f;
    color: #888;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    text-align: center;
    transition: all .2s;
  }
  .format-btn.active {
    border-color: #ff4444;
    color: #fff;
    background: #1e1e1e;
  }
  .format-btn:hover { border-color: #555; }
  .format-btn.active:hover { border-color: #ff4444; }
  .format-label { font-size: 11px; color: #666; display: block; margin-top: 2px; font-weight: 400; }
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
  <input type="text" id="url" placeholder="Paste a YouTube link here..." autofocus>
  <div class="format-row">
    <div class="format-btn active" data-fmt="mp3" onclick="setFormat(this)">
      MP3<span class="format-label">Audio only</span>
    </div>
    <div class="format-btn" data-fmt="avi" onclick="setFormat(this)">
      AVI<span class="format-label">Video 240p</span>
    </div>
  </div>
  <button class="btn-convert" id="btn" onclick="convert()">Convert</button>
  <div id="status"></div>
  <div class="history" id="historyBox" style="display:none">
    <h3>Files</h3>
    <div id="historyList"></div>
  </div>
</div>
<script>
const status = document.getElementById('status');
const btn = document.getElementById('btn');
const urlInput = document.getElementById('url');
const historyBox = document.getElementById('historyBox');
const historyList = document.getElementById('historyList');
let currentFormat = 'mp3';

function setFormat(el) {
  document.querySelectorAll('.format-btn').forEach(b => b.classList.remove('active'));
  el.classList.add('active');
  currentFormat = el.dataset.fmt;
}

urlInput.addEventListener('keydown', e => { if (e.key === 'Enter') convert(); });

async function convert() {
  const url = urlInput.value.trim();
  if (!url) return;
  status.style.display = 'block';
  status.className = 'loading';
  status.innerHTML = '<span class="spinner"></span> Converting to ' + currentFormat.toUpperCase() + '...';
  btn.disabled = true;
  try {
    const res = await fetch('download', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({url, format: currentFormat})
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
    status.textContent = 'Server connection error';
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
  dl.href = 'files/' + encodeURIComponent(filename);
  dl.download = filename;
  dl.textContent = 'Download';
  d.appendChild(name);
  d.appendChild(dl);
  historyList.prepend(d);
}
</script>
</body>
</html>"""


def patch_avi_sps(filepath):
    """Patch H.264 SPS in AVI to remove VUI and strip SEI for portable player compatibility."""
    with open(filepath, "rb") as f:
        avi = bytearray(f.read())

    # Minimal SPS: baseline, level 4.1, no VUI (matches cheap player decoders)
    new_sps = bytes.fromhex("000000016742c029da0f0964")
    sps_prefix = bytes.fromhex("000000016742c029")

    pos = 0
    while True:
        idx = avi.find(sps_prefix, pos)
        if idx < 0:
            break
        j = idx + len(sps_prefix)
        while j < len(avi) - 3:
            if avi[j:j + 4] == b'\x00\x00\x00\x01' or avi[j:j + 3] == b'\x00\x00\x01':
                break
            j += 1
        old_len = j - idx
        diff = old_len - len(new_sps)
        if diff > 4:
            filler = b'\x00\x00\x00\x01\x0c' + b'\xff' * (diff - 5)
        elif diff > 0:
            filler = b'\xff' * diff
        else:
            filler = b''
        avi[idx:idx + old_len] = new_sps + filler
        pos = idx + old_len

    # Strip SEI NALs (replace with filler, same size)
    for sei_pat in [b'\x00\x00\x00\x01\x06', b'\x00\x00\x01\x06']:
        p = 0
        while True:
            idx = avi.find(sei_pat, p)
            if idx < 0:
                break
            j = idx + len(sei_pat)
            while j < len(avi) - 3:
                if avi[j:j + 4] == b'\x00\x00\x00\x01' or avi[j:j + 3] == b'\x00\x00\x01':
                    break
                j += 1
            filler = sei_pat[:-1] + b'\x0c' + b'\xff' * (j - idx - len(sei_pat))
            avi[idx:j] = filler
            p = idx + (j - idx)

    with open(filepath, "wb") as f:
        f.write(bytes(avi))


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
        # Security: prevent path traversal
        filename = os.path.basename(filename)
        filepath = os.path.join(self.download_dir, filename)
        if not os.path.isfile(filepath):
            self.send_error(404, "File not found")
            return
        self.send_response(200)
        mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        filesize = os.path.getsize(filepath)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(filesize))
        # RFC 5987: ASCII fallback + UTF-8 encoded filename
        ascii_name = filename.encode("ascii", "replace").decode("ascii")
        utf8_name = urllib.parse.quote(filename)
        self.send_header("Content-Disposition",
                         f'attachment; filename="{ascii_name}"; filename*=UTF-8\'\'{utf8_name}')
        self.end_headers()
        with open(filepath, "rb") as f:
            while chunk := f.read(65536):
                self.wfile.write(chunk)
        # Auto-delete after download
        try:
            os.remove(filepath)
            print(f"  Deleted: {filename}")
        except OSError:
            pass

    def do_POST(self):
        if self.path != "/download":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))
        url = body.get("url", "")
        fmt = body.get("format", "mp3")

        if not re.match(r"https?://(www\.)?(youtube\.com|youtu\.be|music\.youtube\.com)/", url):
            self.respond({"ok": False, "error": "Invalid YouTube link"})
            return

        if fmt == "avi":
            self.convert_avi(url)
        else:
            self.convert_mp3(url)

    def convert_mp3(self, url):
        try:
            cmd = [YTDLP]
            if FFMPEG:
                cmd += ["--ffmpeg-location", FFMPEG]
            cmd += [
                "-x", "--audio-format", "mp3", "--audio-quality", "0",
                "--embed-thumbnail",
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
                self.respond({"ok": True, "file": "MP3 converted"})
            else:
                err = result.stderr.strip().split("\n")[-1] if result.stderr else "yt-dlp error"
                self.respond({"ok": False, "error": err[:200]})
        except subprocess.TimeoutExpired:
            self.respond({"ok": False, "error": "Timeout (>3min)"})
        except Exception as e:
            self.respond({"ok": False, "error": str(e)[:200]})

    def convert_avi(self, url):
        try:
            # Step 1: download with yt-dlp (best quality, temp file)
            tmp_template = os.path.join(self.download_dir, "%(title)s_tmp.%(ext)s")
            cmd = [YTDLP]
            if FFMPEG:
                cmd += ["--ffmpeg-location", FFMPEG]
            cmd += [
                "-f", "best[height<=480]/best",
                "-o", tmp_template,
                "--no-playlist",
                url,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode != 0:
                err = result.stderr.strip().split("\n")[-1] if result.stderr else "yt-dlp error"
                self.respond({"ok": False, "error": err[:200]})
                return

            # Find the downloaded temp file
            tmp_file = None
            for line in result.stdout.splitlines():
                if "[download] Destination:" in line:
                    tmp_file = line.split("Destination: ", 1)[1].strip()
                elif "[download] " in line and " has already been downloaded" in line:
                    tmp_file = line.split("[download] ", 1)[1].split(" has already")[0].strip()
                elif "[Merger] Merging formats into" in line:
                    tmp_file = line.split("Merging formats into \"", 1)[1].rstrip('"').strip()
            if not tmp_file or not os.path.isfile(tmp_file):
                # Fallback: find most recent _tmp file
                candidates = glob.glob(os.path.join(self.download_dir, "*_tmp.*"))
                if candidates:
                    tmp_file = max(candidates, key=os.path.getmtime)
                else:
                    self.respond({"ok": False, "error": "Download failed"})
                    return

            # Step 2: convert to AVI with ffmpeg (ultra-simple H.264 for portable players)
            base_name = os.path.basename(tmp_file).rsplit("_tmp.", 1)[0]
            avi_file = os.path.join(self.download_dir, base_name + ".avi")

            ffmpeg_bin = FFMPEG or "ffmpeg"
            avi_cmd = [
                ffmpeg_bin, "-y", "-i", tmp_file,
                "-c:v", "libx264",
                "-profile:v", "baseline", "-level:v", "4.1",
                "-preset", "ultrafast", "-tune", "fastdecode",
                "-x264-params",
                "bframes=0:ref=1:annexb=1:no-deblock=1:no-psy=1:no-mbtree=1:"
                "aq-mode=0:chroma-qp-offset=0:partitions=none:me=dia:subme=0:"
                "trellis=0:weightp=0:colorprim=undef:transfer=undef:colormatrix=undef",
                "-qp", "28", "-g", "1",
                "-vtag", "H264",
                "-vf", "scale=240:288,setsar=1:1",
                "-r", "30",
                "-c:a", "pcm_s16le", "-ar", "16000", "-ac", "1",
                avi_file,
            ]
            conv = subprocess.run(avi_cmd, capture_output=True, text=True, timeout=600)

            # Clean up temp file
            try:
                os.remove(tmp_file)
            except OSError:
                pass

            if conv.returncode == 0 and os.path.isfile(avi_file):
                patch_avi_sps(avi_file)
                self.respond({"ok": True, "file": os.path.basename(avi_file)})
            else:
                err = conv.stderr.strip().split("\n")[-1] if conv.stderr else "ffmpeg error"
                self.respond({"ok": False, "error": err[:200]})

        except subprocess.TimeoutExpired:
            self.respond({"ok": False, "error": "Timeout (>10min)"})
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
    parser = argparse.ArgumentParser(description="YT-MP3 — YouTube to MP3/AVI downloader")
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
