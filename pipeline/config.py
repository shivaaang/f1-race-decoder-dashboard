from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    db_dsn: str = os.getenv("F1_DB_DSN", "postgresql://f1app:f1app@localhost:5432/f1dw")
    fastf1_cache_dir: str = os.getenv(
        "FASTF1_CACHE_DIR", str((Path.cwd() / "fastf1_cache").resolve())
    )
    code_version: str = os.getenv("CODE_VERSION", "dev")


def get_settings() -> Settings:
    return Settings()
