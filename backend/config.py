"""
PackScan runtime settings (portable across machines).

Loads from (first found wins per key via pydantic-settings):
  1) packscan/.env
  2) packscan/backend/.env
  3) process environment variables
"""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent
ROOT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(
            str(ROOT_DIR / ".env"),
            str(BACKEND_DIR / ".env"),
        ),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # API bind
    packscan_api_host: str = "127.0.0.1"
    packscan_api_port: int = 8000

    # OCR: paddle | tesseract | auto
    packscan_ocr_engine: str = "paddle"

    # SQLite file name inside backend/
    packscan_db_name: str = "packscan_v2.db"

    # Comma-separated origins, or *
    packscan_cors_origins: str = "*"

    @property
    def db_path(self) -> Path:
        return BACKEND_DIR / self.packscan_db_name

    @property
    def upload_dir(self) -> Path:
        return BACKEND_DIR / "uploads"

    @property
    def report_dir(self) -> Path:
        return BACKEND_DIR / "reports"

    @property
    def cors_origin_list(self) -> list[str]:
        raw = (self.packscan_cors_origins or "*").strip()
        if raw == "*":
            return ["*"]
        return [o.strip() for o in raw.split(",") if o.strip()]


settings = Settings()
