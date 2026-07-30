# ============================================
#   P2Pshare.py  -  made by Mild_spook
# ============================================
# HOW TO USE:
# 1. put p2pshare.py inside the folder you want to share (the one with all ur files in it)
# 2. run it with:   python p2pshare.py
# 3. it'll try to open port 20027 on your router automatically (needs miniupnpc, see below)
# 4. anyone on the same wifi/network (or outside it if upnp worked) can go to
#    http://YOUR_IP:20027  in a browser to see and download the files
#    (find ur local ip with "ipconfig" on windows or "ifconfig"/"ip a" on mac/linux)
# 5. for the auto port opening to work you need miniupnpc installed:
#       pip install miniupnpc
#    if its not installed it just skips that part and prints a warning, u can still
#    port forward 20027 tcp manually on your router if u want outside ppl to see it
# 6. terminal will print every time someone connects and what file they grab
# 7. ctrl+c to stop sharing (closes the port too if upnp was used)

import os
import io
import html
import socket
import datetime
import urllib.parse
import http.server
import socketserver

PORT = 20027

folder = os.path.dirname(os.path.abspath(__file__))
THIS_FILE = os.path.basename(os.path.abspath(__file__))
os.chdir(folder)


# ------------------------------------------------------------------
# helpers
# ------------------------------------------------------------------

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

    names = [n for n in names if n != THIS_FILE]
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


# ------------------------------------------------------------------
# HTTP handler
# ------------------------------------------------------------------

class Handler(http.server.SimpleHTTPRequestHandler):

    def log_message(self, format, *args):
        # shut up default logging, we do our own below
        pass

    def do_GET(self):
        client_ip = self.client_address[0]
        path = urllib.parse.unquote(self.path)
        ts = datetime.datetime.now().strftime("%H:%M:%S")

        # dont let ppl download the script itself
        fname_check = path.lstrip("/").split("?")[0]
        if fname_check == THIS_FILE:
            print(f"[{ts}] {client_ip} tried to grab the script itself, blocked")
            self.send_error(404, "File not found")
            return

        if path == "/" or path.endswith("/"):
            print(f"[{ts}] {client_ip} is browsing {path}")
        else:
            fname = path.lstrip("/")
            print(f"[{ts}] {client_ip} is downloading -> {fname}")

        super().do_GET()

    def list_directory(self, path):
        rows_html, total_items, total_files = build_rows(path)
        if rows_html is None:
            self.send_error(404, "No permission to list directory")
            return None

        breadcrumbs_html = build_breadcrumbs(self.path)
        item_label = "item" if total_items == 1 else "items"
        file_label = "file" if total_files == 1 else "files"
        page_title = html.escape(os.path.basename(folder) or folder)

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
    <span>Sharing <code>{html.escape(folder)}</code></span>
    <span>Local network <code>{LOCAL_IP}:{PORT}</code></span>
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


# ------------------------------------------------------------------
# upnp + startup
# ------------------------------------------------------------------

upnp = None
try:
    import miniupnpc
    upnp = miniupnpc.UPnP()
    upnp.discoverdelay = 200
    upnp.discover()
    upnp.selectigd()
    upnp.addportmapping(PORT, "TCP", upnp.lanaddr, PORT, "p2pshare", "")
    upnp.addportmapping(PORT, "UDP", upnp.lanaddr, PORT, "p2pshare", "")
    print("[upnp] port", PORT, "opened, external ip:", upnp.externalipaddress())
except Exception as e:
    print("[upnp] couldnt open port automatically (pip install miniupnpc), continuing anyway:", e)

print("=====================================")
print(" P2Pshare - made by Mild_spook")
print("=====================================")
print("sharing folder:", folder)
print("local network link: http://" + LOCAL_IP + ":" + str(PORT))
print("ctrl+c to stop")
print()

try:
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        httpd.serve_forever()
except KeyboardInterrupt:
    print("stopping...")
finally:
    if upnp:
        try:
            upnp.deleteportmapping(PORT, "TCP")
            upnp.deleteportmapping(PORT, "UDP")
            print("[upnp] port closed")
        except Exception as e:
            print("[upnp] couldnt close port:", e)
