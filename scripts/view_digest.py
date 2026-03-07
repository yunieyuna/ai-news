#!/usr/bin/env python3
"""Generate a standalone HTML digest viewer and open it in the browser.

Usage:
    python scripts/view_digest.py          # open latest digest
    python scripts/view_digest.py --all    # embed all digests (sidebar to switch)

Output: data/view.html  (also opens automatically in your default browser)
"""
from __future__ import annotations

import json
import re
import sys
import webbrowser
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DIGEST_DIR   = PROJECT_ROOT / "data" / "digests"
OUT_FILE     = PROJECT_ROOT / "data" / "view.html"


# ── helpers ──────────────────────────────────────────────────────────────────

def _parse_date(published: str | None) -> str | None:
    if not published:
        return None
    s = published.strip()
    try:
        if "T" in s:
            return datetime.fromisoformat(s.replace("Z", "+00:00")).strftime("%Y-%m-%d")
        return datetime.strptime(s[:25], "%a, %d %b %Y %H:%M:%S").strftime("%Y-%m-%d")
    except Exception:
        m = re.search(r"\d{4}-\d{2}-\d{2}", s)
        return m.group()[:10] if m else None


def load_digests() -> list[dict]:
    files = sorted(DIGEST_DIR.glob("digest_*.json"), reverse=True)
    if not files:
        print(f"[error] No digest JSON files in {DIGEST_DIR}", file=sys.stderr)
        sys.exit(1)

    digests = []
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            # enrich items with parsed date
            for item in data.get("items") or []:
                item.setdefault("published_date", _parse_date(item.get("published")))
            digests.append(data)
        except Exception as exc:
            print(f"[warn] skip {f.name}: {exc}", file=sys.stderr)
    return digests


# ── HTML template ─────────────────────────────────────────────────────────────

_CSS = """
:root {
  --bg:#0f0f12; --surface:#18181c; --surface2:#1f1f24; --border:#2a2a30;
  --text:#e4e4e7; --muted:#71717a; --accent:#6366f1; --accent-h:#818cf8;
  --accent-dim:rgba(99,102,241,.15); --r:10px; --r-sm:6px;
  --c-must:#ef4444; --c-must-bg:rgba(239,68,68,.12);
  --c-news:#3b82f6; --c-news-bg:rgba(59,130,246,.12);
  --c-tools:#10b981; --c-tools-bg:rgba(16,185,129,.12);
  --c-research:#8b5cf6; --c-research-bg:rgba(139,92,246,.12);
  --c-skills:#f59e0b; --c-skills-bg:rgba(245,158,11,.12);
  --c-other:#71717a;  --c-other-bg:rgba(113,113,122,.12);
}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui,-apple-system,sans-serif;background:var(--bg);
  color:var(--text);line-height:1.6;-webkit-font-smoothing:antialiased}
.app{display:grid;grid-template-columns:240px 1fr;
  grid-template-rows:52px 1fr;height:100vh;overflow:hidden}

/* header */
.hdr{grid-column:1/-1;display:flex;align-items:center;gap:.75rem;
  padding:0 1.25rem;background:var(--surface);border-bottom:1px solid var(--border)}
.logo{font-size:1rem;font-weight:700;letter-spacing:-.02em}
.logo span{color:var(--accent)}
.hdr-r{margin-left:auto;font-size:.8rem;color:var(--muted)}

/* sidebar */
.sidebar{background:var(--surface);border-right:1px solid var(--border);
  overflow-y:auto;padding:.75rem .5rem}
.sb-label{font-size:.6875rem;font-weight:600;text-transform:uppercase;
  letter-spacing:.08em;color:var(--muted);padding:0 .5rem;margin-bottom:.5rem;display:block}
.dig-list{list-style:none}
.dig-btn{display:block;width:100%;text-align:left;padding:.5rem .625rem;
  border:1px solid transparent;border-radius:var(--r-sm);
  background:transparent;color:var(--text);font-size:.875rem;
  font-family:inherit;cursor:pointer;margin-bottom:.2rem;transition:background .1s,border-color .1s}
.dig-btn:hover{background:var(--surface2);border-color:var(--border)}
.dig-btn.active{background:var(--accent-dim);border-color:var(--accent);color:var(--accent-h)}
.dig-btn .d-date{font-weight:600;display:block}
.dig-btn .d-time{font-size:.75rem;color:var(--muted);display:block}

/* main */
.main{overflow-y:auto}
.inner{padding:1.125rem 1.375rem 2.5rem;max-width:820px}

/* digest header */
.dh{background:var(--surface);border:1px solid var(--border);
  border-radius:var(--r);padding:1rem 1.25rem;margin-bottom:.875rem}
.dh h1{font-size:1.125rem;font-weight:700;letter-spacing:-.02em;margin-bottom:.25rem}
.dh-meta{display:flex;flex-wrap:wrap;gap:.5rem 1rem;font-size:.8125rem;
  color:var(--muted);align-items:center}
.dh-meta .cnt{color:var(--accent);font-weight:500}
.dh-sum{font-size:.875rem;color:var(--muted);line-height:1.65;
  border-top:1px solid var(--border);padding-top:.625rem;margin-top:.625rem}

/* filters */
.filters{display:flex;flex-wrap:wrap;gap:.4rem;align-items:center;margin-bottom:.75rem}
.filters input,.filters select{padding:.35rem .65rem;border:1px solid var(--border);
  border-radius:var(--r-sm);background:var(--surface);color:var(--text);
  font-size:.8125rem;font-family:inherit}
.filters input[type=text]{flex:1;min-width:150px}
.filters input:focus,.filters select:focus{outline:none;border-color:var(--accent)}
.f-count{font-size:.8125rem;color:var(--muted);margin-left:auto}

/* article cards */
.art-list{display:flex;flex-direction:column;gap:.5rem}
.card{background:var(--surface);border:1px solid var(--border);
  border-radius:var(--r);padding:.875rem 1.125rem;transition:border-color .1s}
.card:hover{border-color:#3f3f46}
.card.must{border-left:3px solid var(--c-must)}
.card-top{display:flex;align-items:flex-start;gap:.75rem}
.card-title{flex:1;font-size:.9375rem;font-weight:600;line-height:1.4}
.card-title a{color:var(--text);text-decoration:none}
.card-title a:hover{color:var(--accent-h)}
.read-btn{flex-shrink:0;font-size:.75rem;color:var(--accent);font-weight:500;
  text-decoration:none;border:1px solid var(--border);border-radius:var(--r-sm);
  padding:.225rem .55rem;white-space:nowrap}
.read-btn:hover{border-color:var(--accent);background:var(--accent-dim)}
.card-snip{font-size:.8125rem;color:var(--muted);margin-top:.35rem;line-height:1.55}
.card-meta{display:flex;flex-wrap:wrap;align-items:center;gap:.3rem;margin-top:.4rem}
.badge{display:inline-block;padding:.12rem .45rem;border-radius:999px;
  font-size:.6875rem;font-weight:600;text-transform:uppercase;letter-spacing:.04em}
.b-src  {background:var(--accent-dim); color:var(--accent-h)}
.b-must {background:var(--c-must-bg); color:var(--c-must)}
.b-news {background:var(--c-news-bg); color:var(--c-news)}
.b-tools{background:var(--c-tools-bg);color:var(--c-tools)}
.b-res  {background:var(--c-research-bg);color:var(--c-research)}
.b-sk   {background:var(--c-skills-bg);color:var(--c-skills)}
.b-oth  {background:var(--c-other-bg); color:var(--c-other)}
.b-date {font-size:.75rem;color:var(--muted);font-weight:400;letter-spacing:0}

/* state */
.state{text-align:center;padding:3rem 1rem;color:var(--muted);font-size:.9375rem}
.empty-hint{font-size:.8125rem;color:var(--muted);margin-top:.25rem}

/* summary section */
.sum-section{background:var(--surface);border:1px solid var(--border);
  border-radius:var(--r);padding:1rem 1.25rem;margin-bottom:.875rem}
.sum-label{font-size:.6875rem;font-weight:600;text-transform:uppercase;
  letter-spacing:.08em;color:var(--muted);margin-bottom:.5rem}
.sum-body{font-size:1rem;line-height:1.75}
.sum-body h1{font-size:1.25rem;color:var(--text);margin:0 0 .75rem;font-weight:700}
.sum-body h2{font-size:1.125rem;color:var(--text);margin:1rem 0 .4rem;font-weight:700}
.sum-body h3{font-size:1rem;color:var(--text);margin:.75rem 0 .3rem;font-weight:600}
.sum-body h4{font-size:1rem;color:var(--accent-h);margin:.75rem 0 .25rem;font-weight:600}
.sum-body ul{padding-left:1.4rem}
.sum-body li{margin-bottom:.4rem}
.sum-body p{margin-bottom:.5rem}
.sum-body strong{color:var(--text);font-weight:600}
.sum-body em{color:var(--accent-h);font-style:italic}
.sum-body a{color:var(--accent-h);text-decoration:none;border-bottom:1px solid rgba(129,140,248,.35)}
.sum-body a:hover{border-bottom-color:var(--accent-h)}

@media(max-width:640px){
  .app{grid-template-columns:1fr;grid-template-rows:52px 140px 1fr;height:auto}
  .sidebar{border-right:none;border-bottom:1px solid var(--border);max-height:140px}
  .main{overflow-y:visible}.inner{padding:.875rem .875rem 2rem}
}
"""

_JS = """
const $ = id => document.getElementById(id);
let cur = null;  // current digest data

function esc(s) {
  const d = document.createElement('div');
  d.textContent = s ?? '';
  return d.innerHTML;
}

function fmtDate(d) {
  if (!d) return '';
  try {
    const [y,m,day] = d.split('-');
    const mo=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    return mo[+m-1]+' '+(+day)+', '+y;
  } catch { return d; }
}

function inlineMd(s) {
  s = s.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
  s = s.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  s = s.replace(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/g, '<em>$1</em>');
  return s;
}

function renderMd(md) {
  const lines = md.split('\\n');
  let out = '';
  let inUl = false;
  lines.forEach(line => {
    const h4 = line.match(/^####\\s+(.+)/);
    const h3 = !h4 && line.match(/^###\\s+(.+)/);
    const h2 = !h4 && !h3 && line.match(/^##\\s+(.+)/);
    const h1 = !h4 && !h3 && !h2 && line.match(/^#\\s+(.+)/);
    const li = line.match(/^[*-]\\s+(.+)/);
    if (h4 || h3 || h2 || h1) {
      if (inUl) { out += '</ul>'; inUl = false; }
      const tag = h4 ? 'h4' : h3 ? 'h3' : h2 ? 'h2' : 'h1';
      const txt = (h4||h3||h2||h1)[1];
      out += '<' + tag + '>' + inlineMd(esc(txt)) + '</' + tag + '>';
    } else if (li) {
      if (!inUl) { out += '<ul>'; inUl = true; }
      out += '<li>' + inlineMd(esc(li[1])) + '</li>';
    } else {
      if (inUl) { out += '</ul>'; inUl = false; }
      if (line.trim()) out += '<p>' + inlineMd(esc(line)) + '</p>';
    }
  });
  if (inUl) out += '</ul>';
  return out;
}

function catCls(c) {
  if (!c) return null;
  const l = c.toLowerCase();
  if (l.includes('must'))                          return {cls:'b-must',lbl:'🔥 Must Read'};
  if (l.includes('news'))                          return {cls:'b-news',lbl:'News'};
  if (l.includes('tool'))                          return {cls:'b-tools',lbl:'Tools'};
  if (l.includes('research'))                      return {cls:'b-res',lbl:'Research'};
  if (l.includes('skill')||l.includes('learn'))    return {cls:'b-sk',lbl:'📚 Skills'};
  return {cls:'b-oth', lbl:c};
}

function renderArticles(items) {
  const list = $('art-list');
  const msg  = $('state-msg');
  list.innerHTML = '';
  if (!items.length) {
    msg.style.display = '';
    msg.innerHTML = 'No articles match your filters.';
    list.style.display = 'none';
    return;
  }
  msg.style.display = 'none';
  list.style.display = '';
  $('f-count').textContent = items.length + ' article' + (items.length!==1?'s':'');

  items.forEach(it => {
    const isMust = (it.category||'').toLowerCase().includes('must');
    const cat    = catCls(it.category);
    const date   = fmtDate(it.published_date) || it.published || '';

    const card = document.createElement('div');
    card.className = 'card' + (isMust?' must':'');
    const snip = (it.summary||'').replace(/<[^>]+>/g,'').trim().slice(0,200);
    card.innerHTML =
      '<div class="card-top">' +
        '<div class="card-title"><a href="'+esc(it.link)+'" target="_blank" rel="noopener">'+esc(it.title||'Untitled')+'</a></div>' +
        '<a class="read-btn" href="'+esc(it.link)+'" target="_blank" rel="noopener">Read →</a>' +
      '</div>' +
      (snip?'<div class="card-snip">'+esc(snip)+(it.summary.length>200?'…':'')+'</div>':'')+
      '<div class="card-meta">' +
        (it.source_name?'<span class="badge b-src">'+esc(it.source_name)+'</span>':'')+
        (cat?'<span class="badge '+cat.cls+'">'+esc(cat.lbl)+'</span>':'')+
        (date?'<span class="b-date">'+esc(date)+'</span>':'')+
      '</div>';
    list.appendChild(card);
  });
}

function applyFilters() {
  if (!cur) return;
  const q    = $('s-word').value.trim().toLowerCase();
  const src  = $('s-src').value;
  const from = $('s-from').value;
  const to   = $('s-to').value;

  const out = (cur.items||[]).filter(it => {
    if (q   && !(it.title||'').toLowerCase().includes(q)) return false;
    if (src && it.source_name !== src) return false;
    const d = it.published_date;
    if (from && d && d < from) return false;
    if (to   && d && d > to)   return false;
    return true;
  });
  renderArticles(out);
}

function populateSources(items) {
  const srcs = [...new Set(items.map(i=>i.source_name).filter(Boolean))].sort();
  const cur  = $('s-src').value;
  $('s-src').innerHTML = '<option value="">All sources</option>' +
    srcs.map(s=>'<option value="'+esc(s)+'"'+(s===cur?' selected':'')+'>'+esc(s)+'</option>').join('');
}

function showDigest(data) {
  cur = data;
  const parts = (data.stamp||'').split('_');
  $('dh-title').textContent = 'Digest · ' + (parts[0]||data.stamp);
  $('dh-stamp').textContent = parts[0] + (parts[1]?' at '+parts[1].replace('-',':'):'');
  $('dh-cnt').textContent   = (data.item_count||(data.items||[]).length) + ' articles';

  // summary / LLM output
  const sumEl = $('sum-section');
  const sumMd = (data.summary||'').replace(/<think>[\s\S]*?<\/think>/g,'').trim();
  if (sumMd && !sumMd.startsWith('[Summarization error')) {
    sumEl.style.display = '';
    sumEl.innerHTML = '<div class="sum-label">AI Summary</div><div class="sum-body">' + renderMd(sumMd) + '</div>';
  } else {
    sumEl.style.display = 'none';
  }

  populateSources(data.items||[]);

  // reset filters
  ['s-word','s-from','s-to'].forEach(id=>$(id).value='');
  $('s-src').selectedIndex=0;

  renderArticles(data.items||[]);
}

// Build sidebar
function init() {
  if (!DIGESTS.length) {
    $('dig-list').innerHTML = '<li style="padding:.5rem .5rem;font-size:.8125rem;color:var(--muted)">No digests found.</li>';
    return;
  }

  $('dig-list').innerHTML = DIGESTS.map((d,i) => {
    const parts = (d.stamp||'').split('_');
    const date  = parts[0]||d.stamp;
    const time  = (parts[1]||'').replace('-',':');
    return '<li><button class="dig-btn'+(i===0?' active':'')+'" data-idx="'+i+'">' +
      '<span class="d-date">'+esc(date)+'</span>' +
      (time?'<span class="d-time">'+esc(time)+'</span>':'')+
      '</button></li>';
  }).join('');

  document.querySelectorAll('.dig-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.dig-btn').forEach(b=>b.classList.remove('active'));
      btn.classList.add('active');
      showDigest(DIGESTS[+btn.dataset.idx]);
    });
  });

  // auto-load first
  showDigest(DIGESTS[0]);
}

// filter wiring
let debT;
$('s-word').addEventListener('input', ()=>{ clearTimeout(debT); debT=setTimeout(applyFilters,220); });
['s-src','s-from','s-to'].forEach(id=>$(id).addEventListener('change',applyFilters));

init();
"""


def _html(digests: list[dict]) -> str:
    data_js = json.dumps(digests, ensure_ascii=False, separators=(",", ":"))
    count   = sum(len(d.get("items") or []) for d in digests)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AI News Digest — {len(digests)} digest(s)</title>
  <style>{_CSS}</style>
</head>
<body>
<div class="app">
  <header class="hdr">
    <div class="logo">AI News <span>Digest</span></div>
    <div class="hdr-r">{len(digests)} digest(s) · {count} total articles</div>
  </header>

  <aside class="sidebar">
    <span class="sb-label">Digests</span>
    <ul class="dig-list" id="dig-list"></ul>
  </aside>

  <main class="main">
    <div class="inner">

      <!-- Digest header -->
      <div class="dh">
        <h1 id="dh-title">—</h1>
        <div class="dh-meta">
          <span id="dh-stamp"></span>
          <span class="cnt" id="dh-cnt"></span>
        </div>
      </div>

      <!-- LLM summary (if available) -->
      <div class="sum-section" id="sum-section" style="display:none"></div>

      <!-- Filters -->
      <div class="filters">
        <input type="text"  id="s-word" placeholder="Search…" />
        <select id="s-src"><option value="">All sources</option></select>
        <input type="date"  id="s-from" title="From" />
        <input type="date"  id="s-to"   title="To" />
        <span class="f-count" id="f-count"></span>
      </div>

      <!-- Articles -->
      <div class="art-list" id="art-list"></div>
      <div class="state"    id="state-msg" style="display:none"></div>

    </div>
  </main>
</div>

<script>const DIGESTS={data_js};</script>
<script>{_JS}</script>
</body>
</html>"""


def main() -> None:
    if not DIGEST_DIR.exists():
        print(f"[error] Digest directory not found: {DIGEST_DIR}", file=sys.stderr)
        sys.exit(1)

    digests = load_digests()
    print(f"Loaded {len(digests)} digest(s)")

    html = _html(digests)

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(html, encoding="utf-8")
    print(f"Saved to: {OUT_FILE}")

    url = OUT_FILE.as_uri()
    webbrowser.open(url)
    print(f"Opened in browser: {url}")


if __name__ == "__main__":
    main()
