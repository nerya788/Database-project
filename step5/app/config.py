"""Application configuration, loaded from environment variables / .env."""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class DBConfig:
    host: str = os.getenv("DB_HOST", "localhost")
    port: int = int(os.getenv("DB_PORT", "5432"))
    dbname: str = os.getenv("DB_NAME", "school_football_db")
    user: str = os.getenv("DB_USER", "postgres")
    password: str = os.getenv("DB_PASSWORD", "")

    @property
    def dsn(self) -> str:
        return (
            f"host={self.host} port={self.port} dbname={self.dbname} "
            f"user={self.user} password={self.password}"
        )


DB_CONFIG = DBConfig()

APP_NAME = "School Football & Fantasy League Manager"
APP_MIN_SIZE = (1200, 740)
DEFAULT_APPEARANCE = os.getenv("APP_THEME", "System")  # System | Light | Dark
DEFAULT_COLOR_THEME = "blue"
