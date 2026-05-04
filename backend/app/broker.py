from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class BrokerConfig:
    redis_url: str

    def validate(self) -> None:
        parsed = urlparse(self.redis_url)
        if parsed.scheme != "redis":
            raise ValueError("REDIS_URL must use the redis:// scheme")
        if not parsed.hostname:
            raise ValueError("REDIS_URL must include a host")


def create_redis_connection(redis_url: str):
    """Create a Redis connection when runtime dependencies are installed."""
    BrokerConfig(redis_url).validate()
    try:
        from redis import Redis
    except ImportError as exc:
        raise RuntimeError("redis package is required to create a broker connection") from exc
    return Redis.from_url(redis_url)

