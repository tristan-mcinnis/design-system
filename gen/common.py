"""Shared helpers for the token generators. Deterministic by construction:
no timestamps, no environment, only tokens.json bytes."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOKENS = ROOT / "tokens.json"


def load_tokens():
    return json.loads(TOKENS.read_text())


def tokens_sha():
    """Short sha256 of the exact bytes of tokens.json (the drift key)."""
    return hashlib.sha256(TOKENS.read_bytes()).hexdigest()[:12]


def header(comment):
    """Header line consumed by `make check` and the atlas DESIGN-DRIFT lint.
    Keep the format stable: `GENERATED from design-system/tokens.json <sha>`."""
    return f"{comment} GENERATED from design-system/tokens.json {tokens_sha()}; do not edit\n"


def rgba01(v):
    r, g, b, a = v
    return r / 255.0, g / 255.0, b / 255.0, float(a)


def fmt(x):
    """Stable float formatting (no trailing noise)."""
    s = f"{x:.4f}".rstrip("0").rstrip(".")
    return s if "." in s else s + ".0"
