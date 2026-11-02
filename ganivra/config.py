from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True, slots=True)
class Config:
    api_key: str
    endpoint: str = "https://api.ganivra.com"
    environment: str = "production"
    queue_size: int = 1_000
    batch_size: int = 20
    timeout_seconds: float = 2.0
    max_retries: int = 2

    def __post_init__(self) -> None:
        if not self.api_key.strip():
            raise ValueError("api_key must not be empty")
        parsed = urlparse(self.endpoint)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("endpoint must be an http(s) URL")
        if not self.environment.strip():
            raise ValueError("environment must not be empty")
        if self.queue_size < 1 or self.batch_size < 1:
            raise ValueError("queue_size and batch_size must be positive")
        if self.timeout_seconds <= 0 or self.max_retries < 0:
            raise ValueError("invalid timeout or retry configuration")

    @property
    def events_url(self) -> str:
        endpoint = self.endpoint.rstrip("/")
        if endpoint.endswith("/v1/events"):
            return endpoint
        return f"{endpoint}/v1/events"

    @property
    def transactions_url(self) -> str:
        endpoint = self.endpoint.rstrip("/")
        if endpoint.endswith("/v1/events"):
            endpoint = endpoint[: -len("/v1/events")]
        return f"{endpoint}/v1/economics/transactions"
