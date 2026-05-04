from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse


POSTGRES_SCHEMES = {"postgresql", "postgresql+psycopg", "postgres"}


@dataclass(frozen=True)
class DatabaseConfig:
    url: str

    def validate(self) -> None:
        parsed = urlparse(self.url)
        if parsed.scheme not in POSTGRES_SCHEMES:
            raise ValueError("DATABASE_URL must use a PostgreSQL scheme")
        if not parsed.hostname:
            raise ValueError("DATABASE_URL must include a host")
        if not parsed.path or parsed.path == "/":
            raise ValueError("DATABASE_URL must include a database name")


def create_engine_from_url(database_url: str):
    """Create a SQLAlchemy engine when runtime dependencies are installed."""
    DatabaseConfig(database_url).validate()
    try:
        from sqlalchemy import create_engine
    except ImportError as exc:
        raise RuntimeError("SQLAlchemy is required to create a database engine") from exc
    return create_engine(database_url, pool_pre_ping=True)

