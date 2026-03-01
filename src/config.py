"""Load config from YAML and env. Keeps paths relative to project root."""
import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _load_yaml(name: str) -> dict:
    path = PROJECT_ROOT / "config" / name
    if not path.exists():
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def get_sources() -> dict:
    return _load_yaml("sources.yaml")


def get_settings() -> dict:
    return _load_yaml("settings.yaml")


def get_data_dir() -> Path:
    raw = os.getenv("DATA_DIR", "")
    if raw:
        return Path(raw).expanduser().resolve()
    return PROJECT_ROOT / "data"
