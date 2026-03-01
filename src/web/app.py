"""Minimal web UI to list and view saved digests."""
from __future__ import annotations

import re
from pathlib import Path

import markdown
from flask import Flask, jsonify, send_from_directory

from src.config import PROJECT_ROOT, get_settings

app = Flask(__name__, static_folder="static", static_url_path="")


def _digest_dir() -> Path:
    settings = get_settings()
    output_dir = (settings.get("store") or {}).get("output_dir", "data/digests")
    return PROJECT_ROOT / output_dir


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


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
    """Return one digest as HTML. Stamp is filename part without digest_ and .md."""
    # Sanitize: only allow safe chars
    if not re.match(r"^[\d\-_]+$", stamp):
        return jsonify({"error": "invalid stamp"}), 400
    d = _digest_dir()
    path = d / f"digest_{stamp}.md"
    if not path.exists() or not path.is_file():
        return jsonify({"error": "not found"}), 404
    raw = path.read_text(encoding="utf-8")
    html = markdown.markdown(raw, extensions=["fenced_code", "nl2br"])
    return jsonify({"html": html, "stamp": stamp})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
