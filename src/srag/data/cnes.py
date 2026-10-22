"""CNES establishment names, bundled as a static CNES code → name table."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_CNES_PATH = Path(__file__).with_name("cnes_units.json")


@lru_cache(maxsize=1)
def _load_names() -> dict[str, str]:
    try:
        raw = json.loads(_CNES_PATH.read_text(encoding="utf-8"))
    except OSError, ValueError:
        return {}
    if not isinstance(raw, dict):
        return {}
    return {str(code): str(name) for code, name in raw.items()}


def unit_name(code: str) -> str:
    """Name of the establishment, or ``CNES <code>`` when the code is not in the table."""
    return _load_names().get(code.strip(), f"CNES {code.strip()}")
