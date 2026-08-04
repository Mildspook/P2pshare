import os
import io
import sys
import math
import html
import json
import queue
import socket
import datetime
import threading
import subprocess
import urllib.parse
import http.server
import socketserver

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

SCRIPT_PATH = os.path.abspath(__file__)
SCRIPT_DIR = os.path.dirname(SCRIPT_PATH)
CONFIG_PATH = os.path.join(SCRIPT_DIR, "p2pshare_config.json")

DEFAULT_PORT = 20027

CREDITS_TEXT = (
    "P2Pshare\n\n"
    "Primary coder:  Mild_spook\n\n"
    "Credits:\n"
    "  - Totally Legit\n"
    "  - Helper\n"
)


def local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


LOCAL_IP = local_ip()


def is_port_free(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("", port))
            return True
        except OSError:
            return False


def find_available_port(start_port, max_tries=50):
    port = start_port
    for _ in range(max_tries):
        if is_port_free(port):
            return port
        port += 1
    return None


def human_size(num_bytes):
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


CATEGORY_EXTENSIONS = {
    "image": {"jpg", "jpeg", "png", "gif", "webp", "bmp", "svg", "ico", "tiff", "heic"},
    "video": {"mp4", "mkv", "mov", "avi", "webm", "flv", "wmv", "m4v"},
    "audio": {"mp3", "wav", "flac", "ogg", "m4a", "aac", "wma"},
    "document": {"pdf", "doc", "docx", "txt", "md", "rtf", "odt", "xls", "xlsx", "ppt", "pptx", "csv"},
    "archive": {"zip", "rar", "7z", "tar", "gz", "bz2", "xz", "iso"},
    "code": {"py", "js", "ts", "html", "css", "json", "xml", "c", "cpp", "h",
              "java", "go", "rs", "sh", "yml", "yaml", "sql", "php"},
}


def file_category(name, is_dir):
    if is_dir:
        return "folder"
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    for category, extensions in CATEGORY_EXTENSIONS.items():
        if ext in extensions:
            return category
    return "other"


ICON_PATHS = {
    "folder": '<path d="M3 6.5a1 1 0 0 1 1-1h4.4l1.6 2H20a1 1 0 0 1 1 1V18a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z"/>',
    "image": '<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="8.5" cy="9.5" r="1.5"/>'
             '<path d="M21 16l-5.2-5.2a1 1 0 0 0-1.4 0L4 21"/>',
    "video": '<rect x="2.5" y="5.5" width="13.5" height="13" rx="1.5"/><path d="M16 10.2l5-3v9.6l-5-3z"/>',
    "audio": '<path d="M9 17.5V5.5l10-2v12"/><circle cx="6.5" cy="17.5" r="2.5"/><circle cx="16.5" cy="15.5" r="2.5"/>',
    "document": '<path d="M6.5 2.5h7l4 4v14a1 1 0 0 1-1 1h-10a1 1 0 0 1-1-1v-17a1 1 0 0 1 1-1z"/>'
                '<path d="M13.5 2.5V7h4"/><path d="M8.5 12.5h7M8.5 15.8h7M8.5 19h4"/>',
    "archive": '<rect x="3" y="4.5" width="18" height="15" rx="1.5"/><path d="M3 9h18"/><path d="M10.2 13h3.6"/>',
    "code": '<path d="M8.5 8L3 12l5.5 4"/><path d="M15.5 8L21 12l-5.5 4"/><path d="M13.2 5l-2.4 14"/>',
    "other": '<path d="M6.5 2.5h7l4 4v14a1 1 0 0 1-1 1h-10a1 1 0 0 1-1-1v-17a1 1 0 0 1 1-1z"/><path d="M13.5 2.5V7h4"/>',
}


def render_icon(category):
    inner = ICON_PATHS.get(category, ICON_PATHS["other"])
    return (f'<svg class="icon icon-{category}" viewBox="0 0 24 24" fill="none" '
            f'stroke="currentColor" stroke-width="1.6" stroke-linecap="round" '
            f'stroke-linejoin="round" aria-hidden="true">{inner}</svg>')


DOWNLOAD_ICON = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
                 'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
                 '<path d="M12 4v11"/><path d="M7.5 11.5L12 16l4.5-4.5"/><path d="M5 19.5h14"/></svg>')

FOLDER_ARROW_ICON = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
                      'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
                      '<path d="M9 6l6 6-6 6"/></svg>')

FAVICON_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40">'
    '<rect width="40" height="40" rx="9" fill="#ffffff"/>'
    '<line x1="10" y1="28" x2="20" y2="10" stroke="#a83882" stroke-width="2.4"/>'
    '<line x1="20" y1="10" x2="30" y2="28" stroke="#a83882" stroke-width="2.4"/>'
    '<circle cx="10" cy="28" r="4.5" fill="#a83882"/>'
    '<circle cx="20" cy="10" r="4.5" fill="#131113"/>'
    '<circle cx="30" cy="28" r="4.5" fill="#a83882"/>'
    "</svg>"
)
FAVICON_DATA_URI = "data:image/svg+xml," + urllib.parse.quote(FAVICON_SVG)


def _dist_point_to_segment(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(px - x1, py - y1)
    t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    cx, cy = x1 + t * dx, y1 + t * dy
    return math.hypot(px - cx, py - cy)


def _blend(fg, bg, alpha):
    return tuple(int(fg[i] * alpha + bg[i] * (1 - alpha)) for i in range(3))


def build_logo_image(size=40, bg=(255, 255, 255)):
\

    accent = (0xA8, 0x38, 0x82)
    ink = (0x13, 0x11, 0x13)
    soft = _blend(accent, bg, 0.3)

    scale = size / 40.0
    p1 = (10 * scale, 28 * scale)
    p2 = (20 * scale, 10 * scale)
    p3 = (30 * scale, 28 * scale)
    half_w = max(0.9, 1.0 * scale)
    node_r = 4 * scale

    rows = []
    for y in range(size):
        row = []
        for x in range(size):
            px, py = x + 0.5, y + 0.5
            col = bg
            if _dist_point_to_segment(px, py, *p1, *p2) <= half_w:
                col = accent
            if _dist_point_to_segment(px, py, *p2, *p3) <= half_w:
                col = accent
            if _dist_point_to_segment(px, py, *p1, *p3) <= half_w:
                col = soft
            if math.hypot(px - p1[0], py - p1[1]) <= node_r:
                col = accent
            if math.hypot(px - p2[0], py - p2[1]) <= node_r:
                col = ink
            if math.hypot(px - p3[0], py - p3[1]) <= node_r:
                col = accent
            row.append("#%02x%02x%02x" % col)
        rows.append("{" + " ".join(row) + "}")

    img = tk.PhotoImage(width=size, height=size)
    img.put(" ".join(rows))
    return img


def build_breadcrumbs(url_path):
    clean = url_path.split("?")[0]
    parts = [p for p in clean.split("/") if p]
    crumbs = ['<a href="/">Home</a>']
    acc = ""
    for i, part in enumerate(parts):
        acc += "/" + part
        label = html.escape(urllib.parse.unquote(part))
        if i == len(parts) - 1:
            crumbs.append(f'<span class="current">{label}</span>')
        else:
            crumbs.append(f'<a href="{acc}/">{label}</a>')
    sep = '<span class="crumb-sep">/</span>'
    return '<nav class="breadcrumbs" aria-label="Breadcrumb">' + sep.join(crumbs) + "</nav>"


def build_rows(path):
    try:
        names = os.listdir(path)
    except OSError:
        return None, 0, 0

    names = [n for n in names if os.path.join(path, n) != SCRIPT_PATH]
    entries = []
    for name in names:
        full = os.path.join(path, name)
        is_dir = os.path.isdir(full)
        try:
            size = 0 if is_dir else os.path.getsize(full)
            mtime = os.path.getmtime(full)
        except OSError:
            size, mtime = 0, 0
        entries.append({
            "name": name,
            "is_dir": is_dir,
            "size": size,
            "mtime": mtime,
            "category": file_category(name, is_dir),
        })
    entries.sort(key=lambda e: (not e["is_dir"], e["name"].lower()))

    rows_html = []
    for e in entries:
        safe_name = html.escape(e["name"], quote=True)
        link = urllib.parse.quote(e["name"]) + ("/" if e["is_dir"] else "")
        size_text = "—" if e["is_dir"] else human_size(e["size"])
        modified_text = (
            datetime.datetime.fromtimestamp(e["mtime"]).strftime("%b %d, %Y · %H:%M")
            if e["mtime"] else "—"
        )
        icon = render_icon(e["category"])
        is_dir_flag = "1" if e["is_dir"] else "0"
        if e["is_dir"]:
            action = f'<span class="row-hint" aria-hidden="true">{FOLDER_ARROW_ICON}</span>'
        else:
            action = f'<a class="dl-btn" href="{link}" download title="Download {safe_name}">{DOWNLOAD_ICON}</a>'
        suffix = "/" if e["is_dir"] else ""
        rows_html.append(
            '<tr class="file-row" '
            f'data-name="{safe_name}" data-category="{e["category"]}" '
            f'data-size="{e["size"]}" data-mtime="{int(e["mtime"])}" data-isdir="{is_dir_flag}">'
            f'<td class="cell-name"><a class="name-link" href="{link}">{icon}'
            f'<span class="name-text">{safe_name}{suffix}</span></a></td>'
            f'<td class="cell-size">{size_text}</td>'
            f'<td class="cell-modified">{modified_text}</td>'
            f'<td class="cell-action">{action}</td>'
            "</tr>"
        )
    total_files = sum(1 for e in entries if not e["is_dir"])
    return "".join(rows_html), len(entries), total_files


CSS_TEXT = """
:root {
  --bg: #ffffff;
  --ink: #131113;
  --ink-soft: #6f6a6f;
  --ink-faint: #a7a2a6;
  --accent: #a83882;
  --accent-dark: #7c2861;
  --accent-tint: #f8eef4;
  --line: #eae7e9;
  --radius-sm: 8px;
  --radius-md: 12px;
}
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body {
  background: var(--bg);
  color: var(--ink);
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  -webkit-font-smoothing: antialiased;
  line-height: 1.45;
}
::selection { background: var(--accent-tint); color: var(--accent-dark); }
*:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; border-radius: 4px; }

.page { max-width: 980px; margin: 0 auto; padding: 32px 24px 60px; }

.topbar {
  display: flex; align-items: center; flex-wrap: wrap; gap: 10px 20px;
  padding-bottom: 22px; border-bottom: 1px solid var(--line); margin-bottom: 24px;
}
.brand { display: flex; align-items: center; gap: 10px; }
.logo-mark { width: 30px; height: 30px; }
.logo-mark line { stroke: var(--accent); stroke-width: 2; stroke-linecap: round; }
.logo-mark .logo-line-soft { opacity: 0.3; }
.logo-mark .node-a { fill: var(--accent); }
.logo-mark .node-b { fill: var(--ink); }
.brand-name { font-family: 'Space Grotesk', 'Inter', sans-serif; font-weight: 700; font-size: 19px; letter-spacing: -0.01em; }

.breadcrumbs { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; font-size: 13.5px; color: var(--ink-soft); overflow-x: auto; }
.breadcrumbs a { color: var(--ink-soft); text-decoration: none; white-space: nowrap; }
.breadcrumbs a:hover { color: var(--accent); text-decoration: underline; }
.breadcrumbs .current { color: var(--ink); font-weight: 500; white-space: nowrap; }
.breadcrumbs .crumb-sep { color: var(--ink-faint); }

.toolbar { display: flex; align-items: center; flex-wrap: wrap; gap: 12px; margin-bottom: 8px; }
.search-wrap { position: relative; flex: 1 1 220px; min-width: 180px; }
.search-wrap .search-icon {
  position: absolute; left: 12px; top: 50%; transform: translateY(-50%);
  width: 16px; height: 16px; stroke: var(--ink-faint); fill: none; stroke-width: 1.8; pointer-events: none;
}
#searchInput {
  width: 100%; padding: 10px 12px 10px 36px; border: 1px solid var(--line); border-radius: var(--radius-sm);
  font: inherit; font-size: 14px; color: var(--ink); background: #fff;
  transition: border-color .15s ease, box-shadow .15s ease;
}
#searchInput:focus { border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-tint); }
#searchInput::placeholder { color: var(--ink-faint); }

.controls { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.select-wrap { position: relative; }
.select-wrap::after {
  content: ''; position: absolute; right: 11px; top: 50%; width: 7px; height: 7px;
  border-right: 1.6px solid var(--ink-soft); border-bottom: 1.6px solid var(--ink-soft);
  transform: translateY(-70%) rotate(45deg); pointer-events: none;
}
.select-wrap select {
  appearance: none; -webkit-appearance: none; font: inherit; font-size: 13.5px; color: var(--ink);
  background: #fff; border: 1px solid var(--line); border-radius: var(--radius-sm);
  padding: 9px 30px 9px 12px; cursor: pointer; transition: border-color .15s ease;
}
.select-wrap select:hover { border-color: var(--ink-faint); }
.select-wrap select:focus { border-color: var(--accent); }

.view-toggle { display: flex; border: 1px solid var(--line); border-radius: var(--radius-sm); overflow: hidden; }
.view-btn {
  display: flex; align-items: center; justify-content: center; width: 36px; height: 36px;
  background: #fff; border: none; color: var(--ink-soft); cursor: pointer;
  transition: background .15s ease, color .15s ease;
}
.view-btn + .view-btn { border-left: 1px solid var(--line); }
.view-btn svg { width: 16px; height: 16px; stroke: currentColor; fill: none; stroke-width: 1.8; }
.view-btn:hover { color: var(--accent); }
.view-btn.active { background: var(--accent-tint); color: var(--accent-dark); }

.item-count { font-size: 12.5px; color: var(--ink-faint); margin: 14px 2px 10px; }

.file-table { width: 100%; border-collapse: collapse; }
.file-table thead th {
  text-align: left; font-size: 11.5px; font-weight: 600; text-transform: uppercase; letter-spacing: .06em;
  color: var(--ink-faint); padding: 0 10px 8px; border-bottom: 1px solid var(--line);
}
.file-table thead th:nth-child(2), .file-table thead th:nth-child(3) { width: 130px; }
.file-table thead th:last-child { width: 44px; }

.file-row { border-bottom: 1px solid var(--line); transition: background .12s ease; }
.file-row:hover { background: var(--accent-tint); }
.file-row td { padding: 11px 10px; font-size: 14px; vertical-align: middle; }

.cell-name a.name-link { display: flex; align-items: center; gap: 11px; color: var(--ink); text-decoration: none; }
.cell-name a.name-link:hover .name-text { color: var(--accent-dark); text-decoration: underline; }
.icon { width: 19px; height: 19px; flex-shrink: 0; color: var(--ink-faint); }
.icon-folder { color: var(--accent); }
.name-text { word-break: break-word; }

.cell-size, .cell-modified { color: var(--ink-soft); font-family: 'JetBrains Mono', ui-monospace, monospace; font-size: 12.5px; white-space: nowrap; }

.cell-action { text-align: right; }
.dl-btn, .row-hint {
  display: inline-flex; width: 30px; height: 30px; align-items: center; justify-content: center;
  border-radius: 8px; color: var(--ink-faint); text-decoration: none; transition: background .15s ease, color .15s ease;
}
.dl-btn svg, .row-hint svg { width: 16px; height: 16px; }
.dl-btn:hover { background: #fff; color: var(--accent); }

.empty-state { display: none; flex-direction: column; align-items: center; text-align: center; gap: 6px; padding: 64px 20px; color: var(--ink-soft); }
.empty-state svg { width: 40px; height: 40px; stroke: var(--ink-faint); fill: none; stroke-width: 1.4; margin-bottom: 6px; }
.empty-title { font-weight: 600; color: var(--ink); margin: 0; }
.empty-sub { margin: 0; font-size: 13.5px; color: var(--ink-faint); }

.view-grid .file-table thead { display: none; }
.view-grid .file-table tbody { display: grid; grid-template-columns: repeat(auto-fill, minmax(136px, 1fr)); gap: 12px; }
.view-grid .file-row { display: flex; flex-direction: column; align-items: center; text-align: center; gap: 4px; border: 1px solid var(--line); border-radius: var(--radius-md); padding: 20px 10px 14px; }
.view-grid .file-row:hover { border-color: var(--accent); }
.view-grid .file-row td { padding: 0; border: none; }
.view-grid .cell-name { width: 100%; }
.view-grid .cell-name a.name-link { flex-direction: column; gap: 10px; }
.view-grid .icon { width: 32px; height: 32px; }
.view-grid .name-text { font-size: 13px; }
.view-grid .cell-size, .view-grid .cell-modified, .view-grid .cell-action { display: none; }

.footer { margin-top: 40px; padding-top: 18px; border-top: 1px solid var(--line); display: flex; flex-wrap: wrap; gap: 8px; font-size: 12.5px; color: var(--ink-faint); }
.footer code { font-family: 'JetBrains Mono', ui-monospace, monospace; background: var(--accent-tint); color: var(--accent-dark); padding: 2px 6px; border-radius: 4px; }
.footer-credit { margin-left: auto; }

@media (max-width: 640px) {
  .page { padding: 22px 16px 40px; }
  .file-table thead th:nth-child(3), .file-table td.cell-modified { display: none; }
  .footer-credit { margin-left: 0; }
}
@media (prefers-reduced-motion: reduce) { * { transition: none !important; } }
"""

JS_TEXT = """
(function () {
  var searchInput = document.getElementById('searchInput');
  var filterType = document.getElementById('filterType');
  var sortBy = document.getElementById('sortBy');
  var viewListBtn = document.getElementById('viewListBtn');
  var viewGridBtn = document.getElementById('viewGridBtn');
  var browserEl = document.querySelector('.browser');
  var tbody = document.getElementById('fileBody');
  var emptyState = document.getElementById('emptyState');
  var emptyTitle = emptyState.querySelector('.empty-title');
  var emptySub = emptyState.querySelector('.empty-sub');

  function applyFilters() {
    var q = searchInput.value.trim().toLowerCase();
    var type = filterType.value;
    var visible = 0;
    Array.prototype.forEach.call(tbody.children, function (row) {
      var name = (row.dataset.name || '').toLowerCase();
      var cat = row.dataset.category;
      var show = (!q || name.indexOf(q) !== -1) && (type === 'all' || cat === type);
      row.style.display = show ? '' : 'none';
      if (show) visible++;
    });
    if (tbody.children.length === 0) {
      emptyTitle.textContent = 'This folder is empty';
      emptySub.textContent = 'Nothing has been shared here yet.';
      emptyState.style.display = 'flex';
    } else if (visible === 0) {
      emptyTitle.textContent = 'No files match';
      emptySub.textContent = 'Try a different search or filter.';
      emptyState.style.display = 'flex';
    } else {
      emptyState.style.display = 'none';
    }
  }

  function applySort() {
    var mode = sortBy.value;
    var rows = Array.prototype.slice.call(tbody.children);
    rows.sort(function (a, b) {
      var aDir = a.dataset.isdir === '1';
      var bDir = b.dataset.isdir === '1';
      if (mode !== 'type' && aDir !== bDir) return aDir ? -1 : 1;
      switch (mode) {
        case 'name-desc': return b.dataset.name.localeCompare(a.dataset.name);
        case 'size-desc': return Number(b.dataset.size) - Number(a.dataset.size);
        case 'size-asc': return Number(a.dataset.size) - Number(b.dataset.size);
        case 'mtime-desc': return Number(b.dataset.mtime) - Number(a.dataset.mtime);
        case 'mtime-asc': return Number(a.dataset.mtime) - Number(b.dataset.mtime);
        case 'type': return a.dataset.category.localeCompare(b.dataset.category) || a.dataset.name.localeCompare(b.dataset.name);
        default: return a.dataset.name.localeCompare(b.dataset.name);
      }
    });
    rows.forEach(function (r) { tbody.appendChild(r); });
  }

  function setView(mode) {
    browserEl.classList.toggle('view-grid', mode === 'grid');
    browserEl.classList.toggle('view-list', mode !== 'grid');
    viewListBtn.classList.toggle('active', mode !== 'grid');
    viewGridBtn.classList.toggle('active', mode === 'grid');
    viewListBtn.setAttribute('aria-pressed', String(mode !== 'grid'));
    viewGridBtn.setAttribute('aria-pressed', String(mode === 'grid'));
    try { localStorage.setItem('p2pshare-view', mode); } catch (e) {}
  }

  searchInput.addEventListener('input', applyFilters);
  filterType.addEventListener('change', applyFilters);
  sortBy.addEventListener('change', applySort);
  viewListBtn.addEventListener('click', function () { setView('list'); });
  viewGridBtn.addEventListener('click', function () { setView('grid'); });

  var savedView = 'list';
  try { savedView = localStorage.getItem('p2pshare-view') || 'list'; } catch (e) {}
  setView(savedView);
  applyFilters();
  applySort();
})();
"""


SHARE_STATE = {
    "folder": None,
    "port": DEFAULT_PORT,
}


def make_handler_class(share_folder, log_func):
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=share_folder, **kwargs)

        def log_message(self, format, *args):
            pass

        def do_GET(self):
            client_ip = self.client_address[0]
            path = urllib.parse.unquote(self.path)
            ts = datetime.datetime.now().strftime("%H:%M:%S")

            requested_full = os.path.abspath(self.translate_path(self.path))
            if requested_full == SCRIPT_PATH:
                log_func(f"[{ts}] {client_ip} tried to grab the script itself, blocked")
                self.send_error(404, "File not found")
                return

            if path == "/" or path.endswith("/"):
                log_func(f"[{ts}] {client_ip} is browsing {path}")
            else:
                fname = path.lstrip("/")
                log_func(f"[{ts}] {client_ip} is downloading -> {fname}")

            super().do_GET()

        def list_directory(self, path):
            rows_html, total_items, total_files = build_rows(path)
            if rows_html is None:
                self.send_error(404, "No permission to list directory")
                return None

            breadcrumbs_html = build_breadcrumbs(self.path)
            item_label = "item" if total_items == 1 else "items"
            file_label = "file" if total_files == 1 else "files"
            page_title = html.escape(os.path.basename(share_folder) or share_folder)

            page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>P2Pshare · {page_title}</title>
<link rel="icon" type="image/svg+xml" href="{FAVICON_DATA_URI}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>{CSS_TEXT}</style>
</head>
<body>
<div class="page">
  <header class="topbar">
    <div class="brand">
      <svg class="logo-mark" viewBox="0 0 40 40" aria-hidden="true">
        <line x1="10" y1="28" x2="20" y2="10"></line>
        <line x1="20" y1="10" x2="30" y2="28"></line>
        <line x1="10" y1="28" x2="30" y2="28" class="logo-line-soft"></line>
        <circle cx="10" cy="28" r="4" class="node-a"></circle>
        <circle cx="20" cy="10" r="4" class="node-b"></circle>
        <circle cx="30" cy="28" r="4" class="node-a"></circle>
      </svg>
      <span class="brand-name">P2Pshare</span>
    </div>
    {breadcrumbs_html}
  </header>

  <main class="browser view-list">
    <div class="toolbar">
      <div class="search-wrap">
        <svg class="search-icon" viewBox="0 0 24 24" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5"></circle><line x1="15.5" y1="15.5" x2="21" y2="21"></line></svg>
        <input type="text" id="searchInput" placeholder="Filter files…" autocomplete="off">
      </div>
      <div class="controls">
        <div class="select-wrap">
          <select id="filterType" aria-label="Filter by type">
            <option value="all">All types</option>
            <option value="folder">Folders</option>
            <option value="image">Images</option>
            <option value="video">Video</option>
            <option value="audio">Audio</option>
            <option value="document">Documents</option>
            <option value="archive">Archives</option>
            <option value="code">Code</option>
            <option value="other">Other</option>
          </select>
        </div>
        <div class="select-wrap">
          <select id="sortBy" aria-label="Sort by">
            <option value="name-asc">Name (A–Z)</option>
            <option value="name-desc">Name (Z–A)</option>
            <option value="size-desc">Size (largest)</option>
            <option value="size-asc">Size (smallest)</option>
            <option value="mtime-desc">Modified (newest)</option>
            <option value="mtime-asc">Modified (oldest)</option>
            <option value="type">Type</option>
          </select>
        </div>
        <div class="view-toggle" role="group" aria-label="View">
          <button type="button" id="viewListBtn" class="view-btn active" aria-pressed="true" title="List view">
            <svg viewBox="0 0 24 24" aria-hidden="true"><line x1="4" y1="6" x2="20" y2="6"></line><line x1="4" y1="12" x2="20" y2="12"></line><line x1="4" y1="18" x2="20" y2="18"></line></svg>
          </button>
          <button type="button" id="viewGridBtn" class="view-btn" aria-pressed="false" title="Grid view">
            <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="4" y="4" width="7" height="7"></rect><rect x="13" y="4" width="7" height="7"></rect><rect x="4" y="13" width="7" height="7"></rect><rect x="13" y="13" width="7" height="7"></rect></svg>
          </button>
        </div>
      </div>
    </div>

    <div class="item-count">{total_items} {item_label} · {total_files} {file_label}</div>

    <table class="file-table">
      <thead>
        <tr><th>Name</th><th>Size</th><th>Modified</th><th></th></tr>
      </thead>
      <tbody id="fileBody">{rows_html}</tbody>
    </table>

    <div class="empty-state" id="emptyState">
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 7l2-3h5l2 3h7a1 1 0 0 1 1 1v11a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V8a1 1 0 0 1 1-1z"></path></svg>
      <p class="empty-title">This folder is empty</p>
      <p class="empty-sub">Nothing has been shared here yet.</p>
    </div>
  </main>

  <footer class="footer">
    <span>Sharing <code>{html.escape(share_folder)}</code></span>
    <span>Local network <code>{LOCAL_IP}:{SHARE_STATE['port']}</code></span>
    <span class="footer-credit">P2Pshare by Mild_spook</span>
  </footer>
</div>
<script>{JS_TEXT}</script>
</body>
</html>
"""
            encoded = page.encode("utf-8", "surrogateescape")
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            return io.BytesIO(encoded)

    return Handler


class ThreadingHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True


class SingleHTTPServer(socketserver.TCPServer):
    allow_reuse_address = True


def ensure_miniupnpc(log_func):
    try:
        import miniupnpc
        return miniupnpc
    except ImportError:
        pass

    log_func("[upnp] miniupnpc not installed - installing it now, hang on...")
    try:
        proc = subprocess.Popen(
            [sys.executable, "-m", "pip", "install", "miniupnpc"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )
        for line in proc.stdout:
            log_func("[pip] " + line.rstrip())
        proc.wait()
        if proc.returncode != 0:
            log_func("[upnp] pip install failed, continuing without auto port-forwarding")
            return None
    except Exception as e:
        log_func(f"[upnp] couldn't run pip: {e}")
        return None

    try:
        import miniupnpc
        log_func("[upnp] miniupnpc installed successfully")
        return miniupnpc
    except ImportError:
        log_func("[upnp] install finished but miniupnpc still couldn't be imported")
        return None


def open_upnp_port(miniupnpc_mod, port, log_func):
    try:
        upnp = miniupnpc_mod.UPnP()
        upnp.discoverdelay = 200
        upnp.discover()
        upnp.selectigd()
        upnp.addportmapping(port, "TCP", upnp.lanaddr, port, "p2pshare", "")
        upnp.addportmapping(port, "UDP", upnp.lanaddr, port, "p2pshare", "")
        log_func(f"[upnp] port {port} opened, external ip: {upnp.externalipaddress()}")
        return upnp
    except Exception as e:
        log_func(f"[upnp] couldn't open port automatically, continuing on local network only: {e}")
        return None


def close_upnp_port(upnp, port, log_func):
    if not upnp:
        return
    try:
        upnp.deleteportmapping(port, "TCP")
        upnp.deleteportmapping(port, "UDP")
        log_func("[upnp] port closed")
    except Exception as e:
        log_func(f"[upnp] couldn't close port: {e}")


def load_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_config(data):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


class ControlPanel(tk.Tk):
    ACCENT = "#a83882"
    ACCENT_DARK = "#7c2861"
    ACCENT_TINT = "#f8eef4"
    BG = "#ffffff"
    PANEL = "#ffffff"
    LINE = "#eae7e9"
    INK = "#131113"
    INK_SOFT = "#6f6a6f"
    INK_FAINT = "#a7a2a6"
    WARN = "#b3261e"

    def __init__(self):
        super().__init__()
        self.title("P2Pshare - Control Panel")
        self.geometry("680x640")
        self.minsize(600, 520)
        self.configure(bg=self.BG)


        self.logo_img = build_logo_image(38, bg=(255, 255, 255))
        self.icon_img = build_logo_image(48, bg=(255, 255, 255))
        try:
            self.iconphoto(True, self.icon_img)
        except Exception:
            pass

        self.httpd = None
        self.server_thread = None
        self.upnp = None
        self.upnp_port = None
        self.running = False
        self.log_queue = queue.Queue()
        self.event_queue = queue.Queue()

        cfg = load_config()
        self.folder_var = tk.StringVar(value=cfg.get("folder", ""))
        self.port_var = tk.StringVar(value=str(cfg.get("port", DEFAULT_PORT)))
        self.upnp_var = tk.BooleanVar(value=cfg.get("upnp", True))
        self.threaded_var = tk.BooleanVar(value=cfg.get("threaded", True))
        self.link_var = tk.StringVar(value="not sharing yet")

        self._build_style()
        self._build_widgets()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(120, self._poll_queues)


    def _build_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("TFrame", background=self.BG)
        style.configure("Card.TFrame", background=self.PANEL)
        style.configure("TLabel", background=self.BG, foreground=self.INK, font=("Segoe UI", 10))
        style.configure("Card.TLabel", background=self.PANEL, foreground=self.INK, font=("Segoe UI", 10))
        style.configure("Title.TLabel", background=self.BG, foreground=self.INK,
                         font=("Segoe UI Semibold", 19))
        style.configure("Sub.TLabel", background=self.BG, foreground=self.INK_SOFT, font=("Segoe UI", 9))
        style.configure("CardSub.TLabel", background=self.PANEL, foreground=self.INK_SOFT, font=("Segoe UI", 9))
        style.configure("Heading.TLabel", background=self.PANEL, foreground=self.INK_FAINT,
                         font=("Segoe UI", 8, "bold"))
        style.configure("Status.TLabel", background=self.PANEL, foreground=self.INK_FAINT,
                         font=("Segoe UI Semibold", 11))
        style.configure("Link.TLabel", background=self.PANEL, foreground=self.INK_SOFT,
                         font=("Consolas", 10))

        style.configure("TCheckbutton", background=self.PANEL, foreground=self.INK, font=("Segoe UI", 9))
        style.map("TCheckbutton", background=[("active", self.PANEL)],
                  foreground=[("active", self.ACCENT_DARK)])

        style.configure("TEntry", fieldbackground="#ffffff", foreground=self.INK,
                         bordercolor=self.LINE, lightcolor=self.LINE, darkcolor=self.LINE,
                         insertcolor=self.INK, padding=7, relief="solid", borderwidth=1)
        style.map("TEntry", bordercolor=[("focus", self.ACCENT)])

        style.configure("Accent.TButton", font=("Segoe UI Semibold", 10), padding=(16, 9),
                         background=self.ACCENT, foreground="#ffffff", borderwidth=0, relief="flat")
        style.map("Accent.TButton",
                  background=[("disabled", "#e7c9dc"), ("active", self.ACCENT_DARK)],
                  foreground=[("disabled", "#ffffff")])

        style.configure("Secondary.TButton", font=("Segoe UI", 9), padding=(12, 7),
                         background="#ffffff", foreground=self.INK_SOFT,
                         bordercolor=self.LINE, borderwidth=1, relief="solid")
        style.map("Secondary.TButton",
                  foreground=[("active", self.ACCENT_DARK), ("disabled", self.INK_FAINT)],
                  bordercolor=[("active", self.ACCENT)])

        style.configure("TButton", font=("Segoe UI", 9), padding=6)
        style.configure("Vertical.TScrollbar", background=self.PANEL, troughcolor="#ffffff",
                         bordercolor=self.PANEL, arrowcolor=self.INK_FAINT)


    def _card(self, parent, **pack_opts):
        outer = tk.Frame(parent, bg=self.LINE)
        outer.pack(**pack_opts)
        inner = tk.Frame(outer, bg=self.PANEL)
        inner.pack(fill="both", expand=True, padx=1, pady=1)
        content = ttk.Frame(inner, style="Card.TFrame", padding=(16, 14))
        content.pack(fill="both", expand=True)
        return content

    def _build_widgets(self):
        header = tk.Frame(self, bg=self.BG)
        header.pack(fill="x", padx=20, pady=(20, 14))

        brand_row = tk.Frame(header, bg=self.BG)
        brand_row.pack(anchor="w")
        tk.Label(brand_row, image=self.logo_img, bg=self.BG).pack(side="left")
        text_col = tk.Frame(brand_row, bg=self.BG)
        text_col.pack(side="left", padx=(12, 0))
        ttk.Label(text_col, text="P2Pshare", style="Title.TLabel").pack(anchor="w")
        ttk.Label(text_col, text="host control panel  ·  by Mild_spook",
                  style="Sub.TLabel").pack(anchor="w")

        tk.Frame(self, bg=self.LINE, height=1).pack(fill="x", padx=20)

        body = tk.Frame(self, bg=self.BG)
        body.pack(fill="both", expand=True)


        folder_card = self._card(body, fill="x", padx=20, pady=(16, 0))
        ttk.Label(folder_card, text="FOLDER TO SHARE", style="Heading.TLabel").pack(anchor="w")
        row = ttk.Frame(folder_card, style="Card.TFrame")
        row.pack(fill="x", pady=(8, 0))
        self.folder_entry = ttk.Entry(row, textvariable=self.folder_var)
        self.folder_entry.pack(side="left", fill="x", expand=True, ipady=2)
        ttk.Button(row, text="Browse...", style="Secondary.TButton",
                   command=self._browse_folder).pack(side="left", padx=(8, 0))


        opts_card = self._card(body, fill="x", padx=20, pady=(12, 0))
        ttk.Label(opts_card, text="SETTINGS", style="Heading.TLabel").pack(anchor="w")

        port_row = ttk.Frame(opts_card, style="Card.TFrame")
        port_row.pack(fill="x", pady=(8, 0))
        ttk.Label(port_row, text="Port", style="Card.TLabel").pack(side="left")
        ttk.Entry(port_row, textvariable=self.port_var, width=8).pack(side="left", padx=(8, 0), ipady=2)

        ttk.Checkbutton(opts_card, text="Auto port-forward with UPnP (installs miniupnpc if needed)",
                         variable=self.upnp_var).pack(anchor="w", pady=(10, 0))
        ttk.Checkbutton(opts_card, text="Allow multiple simultaneous downloads",
                         variable=self.threaded_var).pack(anchor="w", pady=(4, 0))


        action_card = self._card(body, fill="x", padx=20, pady=(12, 0))
        btn_row = ttk.Frame(action_card, style="Card.TFrame")
        btn_row.pack(fill="x")
        self.start_btn = ttk.Button(btn_row, text="Start Sharing", style="Accent.TButton",
                                     command=self._on_start_clicked)
        self.start_btn.pack(side="left")
        self.stop_btn = ttk.Button(btn_row, text="Stop Sharing", style="Secondary.TButton",
                                    command=self._on_stop_clicked, state="disabled")
        self.stop_btn.pack(side="left", padx=(8, 0))
        ttk.Button(btn_row, text="Credits", style="Secondary.TButton",
                   command=self._show_credits).pack(side="right")

        self.status_label = ttk.Label(action_card, text="●  Stopped", style="Status.TLabel")
        self.status_label.pack(anchor="w", pady=(14, 0))

        link_row = ttk.Frame(action_card, style="Card.TFrame")
        link_row.pack(fill="x", pady=(8, 0))
        self.link_entry = ttk.Entry(link_row, textvariable=self.link_var, state="readonly")
        self.link_entry.pack(side="left", fill="x", expand=True, ipady=2)
        ttk.Button(link_row, text="Copy", style="Secondary.TButton",
                   command=self._copy_link).pack(side="left", padx=(8, 0))
        ttk.Button(link_row, text="Open", style="Secondary.TButton",
                   command=self._open_link).pack(side="left", padx=(8, 0))


        log_card = self._card(body, fill="both", expand=True, padx=20, pady=(12, 16))
        ttk.Label(log_card, text="ACTIVITY LOG", style="Heading.TLabel").pack(anchor="w")
        log_container = tk.Frame(log_card, bg="#ffffff", highlightbackground=self.LINE,
                                  highlightthickness=1)
        log_container.pack(fill="both", expand=True, pady=(8, 0))
        self.log_text = tk.Text(log_container, bg="#ffffff", fg=self.INK, insertbackground=self.INK,
                                 relief="flat", font=("Consolas", 9), wrap="word", state="disabled",
                                 padx=10, pady=8, borderwidth=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(log_container, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.log_text.tag_configure("brand", foreground=self.ACCENT, font=("Consolas", 9, "bold"))
        self.log_text.tag_configure("upnp", foreground=self.ACCENT_DARK)
        self.log_text.tag_configure("pip", foreground=self.INK_FAINT)
        self.log_text.tag_configure("warn", foreground=self.WARN)
        self.log_text.tag_configure("gui", foreground=self.INK_SOFT, font=("Consolas", 9, "italic"))


        tk.Frame(self, bg=self.LINE, height=1).pack(fill="x", padx=20)
        footer = ttk.Label(self, text="Primary coder: Mild_spook   ·   Credits: Totally Legit, Helper",
                            style="Sub.TLabel")
        footer.pack(anchor="w", padx=20, pady=(10, 16))


    def _log(self, msg):
        print(msg)
        self.log_queue.put(msg)

    def _append_log(self, msg):
        low = msg.lower()
        tag = None
        if low.startswith("====="):
            tag = "brand"
        elif low.startswith("[upnp]"):
            tag = "upnp"
        elif low.startswith("[pip]"):
            tag = "pip"
        elif low.startswith("[gui]"):
            tag = "gui"
        elif any(w in low for w in ("couldn't", "failed", "error")):
            tag = "warn"

        self.log_text.configure(state="normal")
        try:
            if tag:
                self.log_text.insert("end", msg + "\n", tag)
            else:
                self.log_text.insert("end", msg + "\n")
        finally:
            self.log_text.see("end")
            self.log_text.configure(state="disabled")

    def _poll_queues(self):
        try:
            try:
                while True:
                    msg = self.log_queue.get_nowait()
                    self._append_log(msg)
            except queue.Empty:
                pass

            try:
                while True:
                    event = self.event_queue.get_nowait()
                    self._handle_event(event)
            except queue.Empty:
                pass
        except Exception as e:
            print("[gui] poll error:", e)
        finally:
            self.after(120, self._poll_queues)

    def _handle_event(self, event):
        kind = event.get("type")
        if kind == "started":
            self.running = True
            self.status_label.configure(text=f"●  Sharing on port {event['port']}", foreground=self.ACCENT)
            self.link_var.set(f"http://{LOCAL_IP}:{event['port']}")
            self.start_btn.configure(state="disabled")
            self.stop_btn.configure(state="normal")
        elif kind == "stopped":
            self.running = False
            self.status_label.configure(text="●  Stopped", foreground=self.INK_FAINT)
            self.link_var.set("not sharing yet")
            self.start_btn.configure(state="normal")
            self.stop_btn.configure(state="disabled")
        elif kind == "error":
            self.start_btn.configure(state="normal")
            self.stop_btn.configure(state="disabled")
            messagebox.showerror("P2Pshare", event["msg"])


    def _browse_folder(self):
        chosen = filedialog.askdirectory(title="Choose folder to share",
                                          initialdir=self.folder_var.get() or os.path.expanduser("~"))
        if chosen:
            self.folder_var.set(chosen)

    def _copy_link(self):
        link = self.link_var.get()
        if link and link != "not sharing yet":
            self.clipboard_clear()
            self.clipboard_append(link)
            self._log(f"[gui] copied link to clipboard: {link}")

    def _open_link(self):
        link = self.link_var.get()
        if link and link != "not sharing yet":
            import webbrowser
            webbrowser.open(link)

    def _show_credits(self):
        messagebox.showinfo("Credits", CREDITS_TEXT)

    def _on_start_clicked(self):
        folder = self.folder_var.get().strip()
        if not folder:
            messagebox.showwarning("P2Pshare", "Pick a folder to share first.")
            return
        if not os.path.isdir(folder):
            messagebox.showwarning("P2Pshare", "That folder doesn't exist.")
            return
        try:
            port = int(self.port_var.get().strip())
            if not (1 <= port <= 65535):
                raise ValueError
        except ValueError:
            messagebox.showwarning("P2Pshare", "Port must be a number between 1 and 65535.")
            return

        use_upnp = self.upnp_var.get()
        use_threading = self.threaded_var.get()

        self.start_btn.configure(state="disabled")
        save_config({
            "folder": folder, "port": port,
            "upnp": use_upnp, "threaded": use_threading,
        })
        threading.Thread(target=self._start_worker, args=(folder, port, use_upnp, use_threading),
                          daemon=True).start()

    def _start_worker(self, folder, port, use_upnp, use_threading):
        actual_port = port
        if not is_port_free(actual_port):
            self._log(f"[server] port {actual_port} is busy, looking for a free one nearby...")
            found = find_available_port(actual_port + 1)
            if found is None:
                self.event_queue.put({"type": "error", "msg": "Couldn't find a free port to use."})
                return
            actual_port = found
            self._log(f"[server] using port {actual_port} instead")

        SHARE_STATE["folder"] = folder
        SHARE_STATE["port"] = actual_port

        handler_cls = make_handler_class(folder, self._log)
        server_cls = ThreadingHTTPServer if use_threading else SingleHTTPServer
        try:
            self.httpd = server_cls(("", actual_port), handler_cls)
        except OSError as e:
            self.event_queue.put({"type": "error", "msg": f"Couldn't start the server: {e}"})
            return

        self.server_thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.server_thread.start()

        self._log("=====================================")
        self._log(" P2Pshare - made by Mild_spook")
        self._log(" credits: Totally Legit, Helper")
        self._log("=====================================")
        self._log(f"sharing folder: {folder}")
        self._log(f"local network link: http://{LOCAL_IP}:{actual_port}")

        self.event_queue.put({"type": "started", "port": actual_port})

        if use_upnp:
            mod = ensure_miniupnpc(self._log)
            if mod:
                self.upnp = open_upnp_port(mod, actual_port, self._log)
                self.upnp_port = actual_port
            else:
                self._log("[upnp] skipping automatic port forwarding, sharing on local network only")

    def _on_stop_clicked(self):
        self.stop_btn.configure(state="disabled")
        threading.Thread(target=self._stop_worker, daemon=True).start()

    def _stop_worker(self):
        if self.httpd:
            try:
                self.httpd.shutdown()
                self.httpd.server_close()
            except Exception as e:
                self._log(f"[server] error while stopping: {e}")
            self.httpd = None
        if self.upnp:
            close_upnp_port(self.upnp, self.upnp_port, self._log)
            self.upnp = None
        self._log("[server] stopped sharing")
        self.event_queue.put({"type": "stopped"})

    def _on_close(self):
        if self.running:
            self._stop_worker()
        self.destroy()


def main():
    app = ControlPanel()
    app.mainloop()


if __name__ == "__main__":
    main()

