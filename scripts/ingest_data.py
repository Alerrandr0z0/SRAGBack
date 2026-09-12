"""Master data ingestion CLI for SRAG Mossoró (thin wrapper over srag.data.pipeline)."""

from __future__ import annotations

import sys
from pathlib import Path

# Path adjustment for local imports
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from srag.data.pipeline import run_ingest

if __name__ == "__main__":
    run_ingest()
