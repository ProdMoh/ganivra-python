from __future__ import annotations

import atexit
from contextlib import contextmanager
from decimal import Decimal
import threading
from typing import Any, Iterator, Mapping

from .client import Client, APIError
from .config import Config
from .context import trace
from .delivery import DeliveryCosts
from .economics import GanivraAPIError, Transactions
from .instrumentation import instrument_openai
from .anthropic_instrumentation import instrument_anthropic
from .mcp import MCPCallContext, observe_mcp_call
from .sender import BackgroundSender

__all__ = ["Client", "APIError", "init", "trace", "mcp_call", "flush", "transactions", "delivery_costs", "GanivraAPIError", "MCPCallContext"]
__version__ = "0.6.2"

_lock = threading.Lock()
_config: Config | None = None
_sender: BackgroundSender | None = None


def _get_config() -> Config | None:
    return _config


transactions = Transactions(_get_config)
delivery_costs = DeliveryCosts(_get_config)


def init(
    *,
    api_key: str,
    endpoint: str = "https://api.ganivra.com",
    environment: str = "production",
    queue_size: int = 1_000,
    batch_size: int = 20,
    timeout_seconds: float = 2.0,
    max_retries: int = 2,
) -> None:
    """Initialize best-effort telemetry and instrument installed supported providers once per process."""

    global _config, _sender
    config = Config(
        api_key=api_key,
        endpoint=endpoint,
        environment=environment,
        queue_size=queue_size,
        batch_size=batch_size,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
    )
    with _lock:
        previous = _sender
        _config = config
        _sender = BackgroundSender(config)
        instrument_openai(_get_environment, _enqueue)
        instrument_anthropic(_get_environment, _enqueue)
    if previous is not None:
        previous.shutdown(timeout=0.2)


def _get_environment() -> str:
    return _config.environment if _config else "production"


def _enqueue(event: dict[str, Any]) -> None:
    sender = _sender
    if sender is not None:
        sender.enqueue(event)


@contextmanager
def mcp_call(
    *,
    server: str,
    tool: str,
    transport: str | None = None,
    auth_type: str | None = None,
    metadata: Mapping[str, Any] | None = None,
    provider_reported_cost_usd: Decimal | float | int | None = None,
    execution_id: str | None = None,
    parent_step_id: str | None = None,
) -> Iterator[MCPCallContext]:
    """Observe one MCP tool invocation using the existing telemetry queue."""

    with observe_mcp_call(
        server=server,
        tool=tool,
        enqueue=_enqueue,
        environment=_get_environment(),
        transport=transport,
        auth_type=auth_type,
        metadata=metadata,
        provider_reported_cost_usd=provider_reported_cost_usd,
        execution_id=execution_id,
        parent_step_id=parent_step_id,
    ) as context:
        yield context


def flush(timeout: float = 2.0) -> bool:
    """Best-effort wait for queued telemetry, primarily useful in short scripts."""

    sender = _sender
    return True if sender is None else sender.flush(timeout)


def _shutdown() -> None:
    sender = _sender
    if sender is not None:
        sender.shutdown(timeout=0.5)


def _state_for_testing() -> tuple[Config | None, BackgroundSender | None]:
    return _config, _sender


atexit.register(_shutdown)
