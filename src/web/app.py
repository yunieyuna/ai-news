"""Minimal web UI to list and view saved digests."""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

import markdown
from flask import Flask, jsonify, request, send_from_directory

from src.config import PROJECT_ROOT, get_settings, get_sources

app = Flask(__name__, static_folder="static", static_url_path="")


def _digest_dir() -> Path:
    settings = get_settings()
    output_dir = (settings.get("store") or {}).get("output_dir", "data/digests")
    return PROJECT_ROOT / output_dir


def _labels_path() -> Path:
    return PROJECT_ROOT / "data" / "labels.json"


def _load_labels() -> dict:
    p = _labels_path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_labels(data: dict) -> None:
    p = _labels_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _parse_date(published: str | None) -> str | None:
    """Return YYYY-MM-DD from published string, or None."""
    if not published:
        return None
    published = published.strip()
    try:
        if "T" in published:
            return datetime.fromisoformat(published.replace("Z", "+00:00")).strftime("%Y-%m-%d")
        dt = datetime.strptime(published[:25], "%a, %d %b %Y %H:%M:%S")
        return dt.strftime("%Y-%m-%d")
    except Exception:
        for part in published.split():
            if re.match(r"\d{4}-\d{2}-\d{2}", part):
                return part[:10]
        return None


def _parse_categories(html: str) -> list[dict]:
    """Split HTML by <h2> and return list of {title, content}."""
    # Match <h2>...</h2> and capture title; content is between this h2 and the next
    pattern = re.compile(r"<h2[^>]*>(.*?)</h2>", re.DOTALL | re.IGNORECASE)
    parts = pattern.split(html)
    # parts[0] = before first h2, parts[1]=title1, parts[2]=content1, parts[3]=title2, ...
    strip_tag = re.compile(r"<[^>]+>")
    categories = []
    i = 1
    while i + 1 < len(parts):
        title = strip_tag.sub("", parts[i]).strip()
        content = parts[i + 1].strip()
        if title or content:
            categories.append({"title": title or "Summary", "content": content})
        i += 2
    if not categories and parts[0].strip():
        categories.append({"title": "Summary", "content": parts[0].strip()})
    return categories


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/sources")
def list_sources():
    """Return configured RSS feeds (data sources)."""
    sources = get_sources()
    feeds = sources.get("rss_feeds") or []
    return jsonify([{"name": f.get("name", ""), "url": f.get("url", "")} for f in feeds])


@app.route("/api/digests")
def list_digests():
    """Return list of digest stamps (newest first)."""
    d = _digest_dir()
    if not d.exists():
        return jsonify([])
    out = []
    for f in d.glob("digest_*.md"):
        m = re.match(r"digest_(.+)\.md", f.name)
        if m:
            out.append({"id": m.group(1), "stamp": m.group(1)})
    out.sort(key=lambda x: x["stamp"], reverse=True)
    return jsonify(out)


@app.route("/api/digests/<stamp>")
def get_digest(stamp):
    """Return one digest: categories (parsed by ##), raw HTML, summary, and item count."""
    if not re.match(r"^[\d\-_]+$", stamp):
        return jsonify({"error": "invalid stamp"}), 400
    d = _digest_dir()
    path_md = d / f"digest_{stamp}.md"
    path_json = d / f"digest_{stamp}.json"
    if not path_md.exists() or not path_md.is_file():
        return jsonify({"error": "not found"}), 404
    raw = path_md.read_text(encoding="utf-8")
    html = markdown.markdown(raw, extensions=["fenced_code", "nl2br"])
    categories = _parse_categories(html)
    summary = ""
    item_count = 0
    if path_json.exists():
        try:
            data = json.loads(path_json.read_text(encoding="utf-8"))
            summary = data.get("summary", "")
            item_count = data.get("item_count", 0)
        except Exception:
            pass
    return jsonify({
        "stamp": stamp,
        "categories": categories,
        "html": html,
        "summary": summary,
        "item_count": item_count,
    })


@app.route("/api/digests/<stamp>/items")
def get_digest_items(stamp):
    """Return items for a digest with optional search: q (word), from, to (YYYY-MM-DD), source."""
    if not re.match(r"^[\d\-_]+$", stamp):
        return jsonify({"error": "invalid stamp"}), 400
    d = _digest_dir()
    path_json = d / f"digest_{stamp}.json"
    if not path_json.exists():
        return jsonify({"items": [], "summary": "", "item_count": 0})
    try:
        data = json.loads(path_json.read_text(encoding="utf-8"))
    except Exception:
        return jsonify({"items": [], "summary": "", "item_count": 0})
    items = data.get("items") or []
    labels_all = _load_labels().get(stamp, {})
    q = (request.args.get("q") or "").strip().lower()
    from_date = (request.args.get("from") or "").strip() or None
    to_date = (request.args.get("to") or "").strip() or None
    source = (request.args.get("source") or "").strip() or None
    category = (request.args.get("category") or "").strip() or None
    out = []
    for it in items:
        if q and q not in (it.get("title") or "").lower():
            continue
        pub = it.get("published")
        date_str = _parse_date(pub)
        if from_date and date_str and date_str < from_date:
            continue
        if to_date and date_str and date_str > to_date:
            continue
        if source and (it.get("source_name") or "") != source:
            continue
        if category and it.get("category") and (it.get("category") or "").lower() != category.lower():
            continue
        out.append({
            **it,
            "digest_stamp": stamp,
            "published_date": date_str,
            "labels": labels_all.get(it.get("link", ""), []),
        })
    return jsonify({
        "items": out,
        "summary": data.get("summary", ""),
        "item_count": len(out),
        "sources": sorted({it.get("source_name") for it in items if it.get("source_name")}),
    })


@app.route("/api/digests/<stamp>/labels", methods=["GET"])
def get_digest_labels(stamp):
    """Return labels for all items in a digest."""
    if not re.match(r"^[\d\-_]+$", stamp):
        return jsonify({"error": "invalid stamp"}), 400
    labels = _load_labels().get(stamp, {})
    return jsonify(labels)


@app.route("/api/digests/<stamp>/labels", methods=["POST"])
def set_digest_labels(stamp):
    """Set labels for one item. Body: { \"link\": \"...\", \"labels\": [\"a\", \"b\"] }."""
    if not re.match(r"^[\d\-_]+$", stamp):
        return jsonify({"error": "invalid stamp"}), 400
    data = _load_labels()
    if stamp not in data:
        data[stamp] = {}
    body = request.get_json() or {}
    link = (body.get("link") or "").strip()
    labels = list(body.get("labels") or [])
    if not link:
        return jsonify({"error": "link required"}), 400
    labels = [str(l).strip() for l in labels if str(l).strip()]
    data[stamp][link] = labels
    _save_labels(data)
    return jsonify({"ok": True, "labels": labels})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
