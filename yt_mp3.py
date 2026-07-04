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
import threading
import uuid
import time

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
  .quality-row {
    display: none;
    gap: 6px;
    margin-top: 8px;
  }
  .quality-row.visible { display: flex; }
  .quality-btn {
    flex: 1;
    padding: 8px;
    border: 2px solid #333;
    border-radius: 6px;
    background: #0f0f0f;
    color: #888;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    text-align: center;
    transition: all .2s;
  }
  .quality-btn.active {
    border-color: #ff8800;
    color: #fff;
    background: #1e1e1e;
  }
  .quality-btn:hover { border-color: #555; }
  .quality-btn.active:hover { border-color: #ff8800; }
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
  <input type="text" id="url" placeholder="Paste a YouTube or TikTok link here..." autofocus>
  <div class="format-row">
    <div class="format-btn active" data-fmt="mp4" onclick="setFormat(this)">
      Video<span class="format-label">MP4</span>
    </div>
    <div class="format-btn" data-fmt="mp3" onclick="setFormat(this)">
      MP3<span class="format-label">Audio only</span>
    </div>
    <div class="format-btn" data-fmt="avi" onclick="setFormat(this)">
      AVI<span class="format-label">Fullscreen</span>
    </div>
    <div class="format-btn" data-fmt="avi169" onclick="setFormat(this)">
      AVI 16:9<span class="format-label">Letterbox</span>
    </div>
  </div>
  <div class="quality-row" id="qualityRow">
    <div class="quality-btn active" data-q="hq" onclick="setQuality(this)">
      HQ<span class="format-label">Best image</span>
    </div>
    <div class="quality-btn" data-q="light" onclick="setQuality(this)">
      Light<span class="format-label">Smaller</span>
    </div>
    <div class="quality-btn" data-q="aigo" id="aigoBtn" onclick="setQuality(this)">
      Aigo<span class="format-label">Player</span>
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
let currentFormat = 'mp4';
let currentQuality = 'hq';
const qualityRow = document.getElementById('qualityRow');

function setFormat(el) {
  document.querySelectorAll('.format-btn').forEach(b => b.classList.remove('active'));
  el.classList.add('active');
  currentFormat = el.dataset.fmt;
  const aigoBtn = document.getElementById('aigoBtn');
  if (currentFormat === 'avi' || currentFormat === 'avi169') {
    qualityRow.classList.add('visible');
    aigoBtn.style.display = currentFormat === 'avi169' ? '' : 'none';
    if (currentFormat !== 'avi169' && currentQuality === 'aigo') {
      setQuality(document.querySelector('[data-q="hq"]'));
    }
  } else {
    qualityRow.classList.remove('visible');
  }
}

function setQuality(el) {
  document.querySelectorAll('.quality-btn').forEach(b => b.classList.remove('active'));
  el.classList.add('active');
  currentQuality = el.dataset.q;
}

urlInput.addEventListener('keydown', e => { if (e.key === 'Enter') convert(); });

const PHASE_LABEL = {
  starting: 'Starting',
  download: 'Downloading',
  encode: 'Converting',
  remux: 'Packaging',
  finalize: 'Finalizing'
};

async function convert() {
  const url = urlInput.value.trim();
  if (!url) return;
  status.style.display = 'block';
  status.className = 'loading';
  status.innerHTML = '<span class="spinner"></span> Starting...';
  btn.disabled = true;
  try {
    const res = await fetch('download', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({url, format: currentFormat, quality: currentQuality})
    });
    const data = await res.json();
    if (!data.ok || !data.job_id) {
      status.className = 'error';
      status.textContent = data.error || 'Server error';
      btn.disabled = false;
      return;
    }
    await pollProgress(data.job_id);
  } catch(e) {
    status.className = 'error';
    status.textContent = 'Server connection error';
    btn.disabled = false;
  }
}

async function pollProgress(jobId) {
  let misses = 0;
  while (true) {
    await new Promise(r => setTimeout(r, 800));
    let data;
    try {
      const res = await fetch('progress/' + jobId);
      data = await res.json();
    } catch(e) {
      if (++misses > 15) {
        status.className = 'error';
        status.textContent = 'Lost connection to server';
        btn.disabled = false;
        return;
      }
      continue;
    }
    misses = 0;
    if (data.done) {
      if (data.ok) {
        status.className = 'success';
        status.textContent = data.file;
        addHistory(data.file);
        urlInput.value = '';
      } else {
        status.className = 'error';
        status.textContent = data.error || 'Conversion failed';
      }
      btn.disabled = false;
      return;
    }
    const label = PHASE_LABEL[data.phase] || 'Working';
    const pct = (typeof data.percent === 'number') ? Math.round(data.percent) : null;
    status.className = 'loading';
    status.innerHTML = '<span class="spinner"></span> ' + label +
      (pct !== null ? ' ' + pct + '%' : '...');
  }
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
    # Files scheduled for deferred deletion (avoids piling up timers per file)
    _delete_lock = threading.Lock()
    _scheduled_delete = set()
    # Conversion jobs: id -> progress state, polled by the client at /progress/<id>
    jobs = {}
    _jobs_lock = threading.Lock()

    @classmethod
    def schedule_delete(cls, filepath, delay=600):
        """Delete the file after `delay` seconds instead of right after the first
        request. Mobile browsers (iOS Safari) issue several requests per download
        (a Range probe, then the real transfer, sometimes in parallel); deleting
        on the first one makes every later request 404. A deferred sweep lets all
        of them succeed while still keeping the server disk clean."""
        with cls._delete_lock:
            if filepath in cls._scheduled_delete:
                return
            cls._scheduled_delete.add(filepath)

        def _rm():
            try:
                os.remove(filepath)
                print(f"  Deleted: {os.path.basename(filepath)}")
            except OSError:
                pass
            finally:
                with cls._delete_lock:
                    cls._scheduled_delete.discard(filepath)

        t = threading.Timer(delay, _rm)
        t.daemon = True
        t.start()

    def do_GET(self):
        if self.path == "/" or self.path == "":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML.encode())
        elif self.path.startswith("/files/"):
            self.serve_file()
        elif self.path.startswith("/progress/"):
            self.serve_progress()
        else:
            self.send_error(404)

    def serve_progress(self):
        job_id = self.path[len("/progress/"):]
        with YTHandler._jobs_lock:
            state = YTHandler.jobs.get(job_id)
            snapshot = dict(state) if state else None
            # Drop the job once the client has seen its final state.
            if state and state.get("done"):
                YTHandler.jobs.pop(job_id, None)
        if snapshot is None:
            self.respond({"done": True, "ok": False, "error": "Job expired"})
        else:
            snapshot.pop("_t", None)
            self.respond(snapshot)

    def serve_file(self):
        filename = urllib.parse.unquote(self.path[7:])  # strip /files/
        # Security: prevent path traversal
        filename = os.path.basename(filename)
        filepath = os.path.join(self.download_dir, filename)
        if not os.path.isfile(filepath):
            self.send_error(404, "File not found")
            return

        filesize = os.path.getsize(filepath)
        mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        # RFC 5987: ASCII fallback + UTF-8 encoded filename
        ascii_name = filename.encode("ascii", "replace").decode("ascii")
        utf8_name = urllib.parse.quote(filename)
        disposition = (f'attachment; filename="{ascii_name}"; '
                       f"filename*=UTF-8''{utf8_name}")

        # Honour HTTP Range requests: iOS Safari and media players send a Range
        # probe before the real download and open parallel range connections.
        # Without 206 support they misbehave or retry, which (with deletion)
        # broke mobile downloads entirely.
        start, end = 0, filesize - 1
        is_range = False
        range_header = self.headers.get("Range")
        if range_header:
            m = re.match(r"bytes=(\d*)-(\d*)\s*$", range_header.strip())
            if m:
                g1, g2 = m.group(1), m.group(2)
                if g1 == "" and g2 != "":            # suffix range: last N bytes
                    start = max(0, filesize - int(g2))
                    end = filesize - 1
                else:
                    start = int(g1) if g1 else 0
                    end = int(g2) if g2 else filesize - 1
                end = min(end, filesize - 1)
                if start > end or start >= filesize:  # unsatisfiable
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{filesize}")
                    self.end_headers()
                    return
                is_range = True

        length = end - start + 1
        if is_range:
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{end}/{filesize}")
        else:
            self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(length))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Disposition", disposition)
        self.end_headers()

        try:
            with open(filepath, "rb") as f:
                f.seek(start)
                remaining = length
                while remaining > 0:
                    chunk = f.read(min(65536, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
        except (BrokenPipeError, ConnectionResetError):
            # Client aborted (common on mobile) — keep the file, a retry will come.
            return

        # Defer deletion so every request in a mobile download sequence succeeds.
        self.schedule_delete(filepath)

    def do_POST(self):
        if self.path != "/download":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))
        url = body.get("url", "")
        fmt = body.get("format", "mp3")
        quality = body.get("quality", "hq")

        if not re.match(r"https?://(www\.|vm\.|vt\.)?(youtube\.com|youtu\.be|music\.youtube\.com|tiktok\.com)/", url):
            self.respond({"ok": False, "error": "Invalid YouTube or TikTok link"})
            return

        # Run the conversion in a background thread; the client polls
        # /progress/<id> so the UI can show real download/encode percentages
        # instead of a mute spinner.
        job_id = uuid.uuid4().hex
        with YTHandler._jobs_lock:
            cutoff = time.time() - 3600
            for jid in [j for j, s in YTHandler.jobs.items() if s.get("_t", 0) < cutoff]:
                YTHandler.jobs.pop(jid, None)
            YTHandler.jobs[job_id] = {"phase": "starting", "percent": 0,
                                      "done": False, "_t": time.time()}
        threading.Thread(target=self._run_job,
                         args=(job_id, url, fmt, quality), daemon=True).start()
        self.respond({"ok": True, "job_id": job_id})

    def _run_job(self, job_id, url, fmt, quality):
        def prog(**kw):
            with YTHandler._jobs_lock:
                j = YTHandler.jobs.get(job_id)
                if j is not None:
                    j.update(kw)
        try:
            if fmt in ("avi", "avi169"):
                res = self.convert_avi(url, letterbox=(fmt == "avi169"),
                                       quality=quality, progress=prog)
            elif fmt == "mp4":
                res = self.convert_mp4(url, progress=prog)
            else:
                res = self.convert_mp3(url, progress=prog)
        except Exception as e:
            res = {"ok": False, "error": str(e)[:200]}
        res["done"] = True
        res["_t"] = time.time()
        with YTHandler._jobs_lock:
            YTHandler.jobs[job_id] = res

    # --- subprocess helpers with live progress -----------------------------

    def _stream_process(self, cmd, timeout, line_cb=None):
        """Run cmd, invoking line_cb(line) for each stdout line as it arrives.
        A watchdog kills the process after `timeout` seconds. Returns
        (returncode, stdout, stderr); returncode is -9 on timeout."""
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             text=True, bufsize=1)
        done = threading.Event()
        timed_out = {"v": False}

        def _watchdog():
            if not done.wait(timeout):
                timed_out["v"] = True
                try:
                    p.kill()
                except Exception:
                    pass

        threading.Thread(target=_watchdog, daemon=True).start()
        out = []
        try:
            for line in p.stdout:
                out.append(line)
                if line_cb:
                    try:
                        line_cb(line)
                    except Exception:
                        pass
        finally:
            p.wait()
            done.set()
        stderr = p.stderr.read() if p.stderr else ""
        rc = -9 if timed_out["v"] else p.returncode
        return rc, "".join(out), stderr

    def _probe(self, path):
        """Return (duration_seconds, video_codec, audio_codec) via ffprobe."""
        ffprobe = "ffprobe"
        if FFMPEG:
            cand = os.path.join(os.path.dirname(FFMPEG), "ffprobe")
            if os.path.isfile(cand):
                ffprobe = cand
        try:
            r = subprocess.run(
                [ffprobe, "-v", "error", "-of", "json",
                 "-show_entries", "format=duration:stream=codec_type,codec_name",
                 path],
                capture_output=True, text=True, timeout=30)
            data = json.loads(r.stdout or "{}")
            dur = float(data.get("format", {}).get("duration", 0) or 0)
            vcodec = acodec = None
            for s in data.get("streams", []):
                if s.get("codec_type") == "video" and not vcodec:
                    vcodec = s.get("codec_name")
                elif s.get("codec_type") == "audio" and not acodec:
                    acodec = s.get("codec_name")
            return dur, vcodec, acodec
        except Exception:
            return 0.0, None, None

    def _ytdlp_cb(self, progress):
        """Line callback parsing yt-dlp download percentage (needs --newline)."""
        pct_re = re.compile(r"\[download\]\s+([\d.]+)%")

        def cb(line):
            m = pct_re.search(line)
            if m:
                progress(phase="download", percent=float(m.group(1)))
            elif any(t in line for t in ("[ExtractAudio]", "[Merger]",
                                         "[EmbedThumbnail]", "[ThumbnailsConvertor]",
                                         "[VideoConvertor]")):
                progress(phase="finalize", percent=100.0)
        return cb

    def _ffmpeg_cb(self, duration, progress, phase):
        """Line callback parsing ffmpeg -progress pipe:1 output (out_time=)."""
        def cb(line):
            line = line.strip()
            if line.startswith("out_time="):
                t = line[len("out_time="):]
                try:
                    h, m, s = t.split(":")
                    sec = int(h) * 3600 + int(m) * 60 + float(s)
                    if duration > 0:
                        progress(phase=phase,
                                 percent=min(99.0, sec / duration * 100.0))
                except Exception:
                    pass
            elif line == "progress=end":
                progress(phase=phase, percent=100.0)
        return cb

    def _download_tmp(self, url, fmt_selector, progress):
        """Download to a *_tmp file with yt-dlp; return (tmp_path, None) or
        (None, error_message)."""
        tmp_template = os.path.join(self.download_dir, "%(title)s_tmp.%(ext)s")
        cmd = [YTDLP, "--newline"]
        if FFMPEG:
            cmd += ["--ffmpeg-location", FFMPEG]
        cmd += ["-f", fmt_selector, "-S", "vcodec:h264",
                "-o", tmp_template, "--no-playlist", url]
        progress(phase="download", percent=0)
        rc, out, err = self._stream_process(cmd, 300, self._ytdlp_cb(progress))
        if rc != 0:
            if rc == -9:
                return None, "Timeout (>5min)"
            e = err.strip().split("\n")[-1] if err.strip() else "yt-dlp error"
            return None, e[:200]
        tmp_file = None
        # Split on "\n" only (see convert_mp3): titles may contain U+2028/U+2029.
        for line in out.split("\n"):
            if "[download] Destination:" in line:
                tmp_file = line.split("Destination: ", 1)[1].strip()
            elif "[download] " in line and " has already been downloaded" in line:
                tmp_file = line.split("[download] ", 1)[1].split(" has already")[0].strip()
            elif "[Merger] Merging formats into" in line:
                tmp_file = line.split("Merging formats into \"", 1)[1].rstrip('"').strip()
        if not tmp_file or not os.path.isfile(tmp_file):
            candidates = glob.glob(os.path.join(self.download_dir, "*_tmp.*"))
            if candidates:
                tmp_file = max(candidates, key=os.path.getmtime)
            else:
                return None, "Download failed"
        return tmp_file, None

    def convert_mp3(self, url, progress):
        try:
            cmd = [YTDLP, "--newline"]
            if FFMPEG:
                cmd += ["--ffmpeg-location", FFMPEG]
            cmd += [
                "-x", "--audio-format", "mp3", "--audio-quality", "0",
                "--embed-thumbnail",
                # TikTok lists bytevc1 (H.265) formats as "best" but they are
                # video-only despite claiming aac audio, which breaks audio
                # extraction. Prefer H.264 formats, which carry real audio.
                "-S", "vcodec:h264",
                "-o", os.path.join(self.download_dir, "%(title)s.%(ext)s"),
                "--no-playlist",
                url,
            ]
            progress(phase="download", percent=0)
            rc, out, err = self._stream_process(cmd, 300, self._ytdlp_cb(progress))
            if rc == 0:
                # Split on "\n" only, not str.splitlines(): some titles contain
                # U+2028/U+2029 (line/paragraph separators) which splitlines()
                # treats as line breaks, truncating the parsed filename.
                # ExtractAudio wins: "has already been downloaded" may refer to a
                # leftover video file of the same title, not the produced .mp3.
                extracted = already = None
                for line in out.split("\n"):
                    if "[ExtractAudio] Destination:" in line:
                        extracted = os.path.basename(line.split("Destination: ", 1)[1])
                    elif "[download] " in line and " has already been downloaded" in line:
                        already = os.path.basename(
                            line.split("[download] ", 1)[1].split(" has already")[0])
                if extracted:
                    return {"ok": True, "file": extracted}
                if already and already.lower().endswith(".mp3"):
                    return {"ok": True, "file": already}
                mp3s = glob.glob(os.path.join(self.download_dir, "*.mp3"))
                if mp3s:
                    return {"ok": True,
                            "file": os.path.basename(max(mp3s, key=os.path.getmtime))}
                return {"ok": True, "file": "MP3 converted"}
            if rc == -9:
                return {"ok": False, "error": "Timeout (>5min)"}
            e = err.strip().split("\n")[-1] if err.strip() else "yt-dlp error"
            return {"ok": False, "error": e[:200]}
        except Exception as e:
            return {"ok": False, "error": str(e)[:200]}

    def convert_mp4(self, url, progress):
        try:
            tmp_file, err = self._download_tmp(
                url, "bestvideo[height<=720]+bestaudio/best[height<=720]/best", progress)
            if not tmp_file:
                return {"ok": False, "error": err}

            base_name = os.path.basename(tmp_file).rsplit("_tmp.", 1)[0]
            mp4_file = os.path.join(self.download_dir, base_name + ".mp4")
            ffmpeg_bin = FFMPEG or "ffmpeg"
            dur, vcodec, acodec = self._probe(tmp_file)

            if vcodec == "h264" and acodec == "aac":
                # Source is already QuickTime/iOS-compatible (typical for TikTok
                # and many YouTube videos): just remux + faststart. Near-instant,
                # no CPU-heavy re-encode — this is what made MP4 feel "infinite".
                progress(phase="remux", percent=0)
                ff_cmd = [ffmpeg_bin, "-nostats", "-progress", "pipe:1", "-y",
                          "-i", tmp_file, "-c", "copy", "-movflags", "+faststart",
                          mp4_file]
                phase = "remux"
            else:
                # Needs a real transcode (VP9/AV1/HEVC source). veryfast keeps it
                # bearable on a single core.
                progress(phase="encode", percent=0)
                ff_cmd = [ffmpeg_bin, "-nostats", "-progress", "pipe:1", "-y",
                          "-i", tmp_file,
                          "-c:v", "libx264", "-profile:v", "high", "-level:v", "4.1",
                          "-preset", "veryfast", "-crf", "23",
                          "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2",
                          "-movflags", "+faststart", mp4_file]
                phase = "encode"

            rc, _, ferr = self._stream_process(
                ff_cmd, 600, self._ffmpeg_cb(dur, progress, phase))
            try:
                os.remove(tmp_file)
            except OSError:
                pass
            if rc == 0 and os.path.isfile(mp4_file):
                return {"ok": True, "file": os.path.basename(mp4_file)}
            if rc == -9:
                return {"ok": False, "error": "Timeout (>10min)"}
            e = ferr.strip().split("\n")[-1] if ferr.strip() else "ffmpeg error"
            return {"ok": False, "error": e[:200]}
        except Exception as e:
            return {"ok": False, "error": str(e)[:200]}

    def convert_avi(self, url, letterbox=False, quality="hq", progress=None):
        if progress is None:
            progress = lambda **k: None
        try:
            tmp_file, err = self._download_tmp(url, "best[height<=480]/best", progress)
            if not tmp_file:
                return {"ok": False, "error": err}

            base_name = os.path.basename(tmp_file).rsplit("_tmp.", 1)[0]
            avi_file = os.path.join(self.download_dir, base_name + ".avi")
            ffmpeg_bin = FFMPEG or "ffmpeg"
            dur, _, _ = self._probe(tmp_file)

            # Aigo player mode: AVI 16:9 letterbox + rotation + special stack
            is_aigo = letterbox and quality == "aigo"

            if is_aigo:
                vf = "scale=288:162,transpose=2,pad=240:288:(240-iw)/2:0:black,setsar=1:1"
                avi_cmd = [
                    ffmpeg_bin, "-y", "-i", tmp_file,
                    "-c:v", "libx264",
                    "-profile:v", "baseline", "-level:v", "4.1",
                    "-preset", "ultrafast", "-tune", "fastdecode",
                    "-x264-params",
                    "bframes=0:ref=1:annexb=1:no-deblock=1:no-psy=1:no-mbtree=1:"
                    "aq-mode=0:chroma-qp-offset=0:partitions=none:me=dia:subme=0:"
                    "trellis=0:weightp=0:colorprim=undef:transfer=undef:colormatrix=undef",
                    "-qp", "38", "-g", "1",
                    "-vtag", "H264",
                    "-vf", vf,
                    "-r", "20",
                    "-c:a", "pcm_s16le", "-ar", "16000", "-ac", "1",
                    avi_file,
                ]
            else:
                # Standard mobile-compatible encoding, no rotation
                if letterbox:
                    vf = "scale=1280:720,setsar=1:1"
                else:
                    vf = "scale=854:480,setsar=1:1"
                crf = {"hq": "20", "light": "26"}.get(quality, "20")
                avi_cmd = [
                    ffmpeg_bin, "-y", "-i", tmp_file,
                    "-c:v", "libx264", "-profile:v", "high", "-level:v", "4.1",
                    "-preset", "fast", "-crf", crf,
                    "-vf", vf,
                    "-r", "30",
                    "-c:a", "libmp3lame", "-b:a", "128k", "-ar", "44100", "-ac", "2",
                    avi_file,
                ]

            # Inject live progress reporting (writes to stdout / pipe:1).
            avi_cmd = avi_cmd[:1] + ["-nostats", "-progress", "pipe:1"] + avi_cmd[1:]
            progress(phase="encode", percent=0)
            rc, _, ferr = self._stream_process(
                avi_cmd, 600, self._ffmpeg_cb(dur, progress, "encode"))

            # Clean up temp file
            try:
                os.remove(tmp_file)
            except OSError:
                pass

            if rc == 0 and os.path.isfile(avi_file):
                if is_aigo:
                    patch_avi_sps(avi_file)
                return {"ok": True, "file": os.path.basename(avi_file)}
            if rc == -9:
                return {"ok": False, "error": "Timeout (>10min)"}
            e = ferr.strip().split("\n")[-1] if ferr.strip() else "ffmpeg error"
            return {"ok": False, "error": e[:200]}
        except Exception as e:
            return {"ok": False, "error": str(e)[:200]}

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

    # Threading server: mobile browsers open several parallel connections per
    # download (Range requests); a single-threaded server would serialise them.
    server = http.server.ThreadingHTTPServer((args.host, args.port), YTHandler)
    print(f"\n  YT-MP3 ready on http://{args.host}:{args.port}")
    print(f"  Download dir: {YTHandler.download_dir}\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Bye!")


if __name__ == "__main__":
    main()
