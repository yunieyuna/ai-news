#!/usr/bin/env bash
# Start the web UI (from project root)
cd "$(dirname "$0")/.."
python -m src.web.app
