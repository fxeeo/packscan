"""
Initialize SQLite schema + upload/report folders.

Usage (from backend/ with venv active):
  python scripts/init_db.py
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from config import settings
from database import Base, REPORT_DIR, UPLOAD_DIR, engine
import models  # noqa: F401 — register ORM tables


def main() -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    print("PackScan database ready:")
    print(f"  DB      : {settings.db_path}")
    print(f"  Uploads : {UPLOAD_DIR}")
    print(f"  Reports : {REPORT_DIR}")
    print("No demo seed is inserted (real OCR / barcode flow only).")


if __name__ == "__main__":
    main()
