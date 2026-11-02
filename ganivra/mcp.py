from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from decimal import Decimal
import time
from typing import Any

from .context import current_trace, new_id


@dataclass(frozen=True, slots=True)
class MCPCallContext:
    """Identifiers assigned to one observed MCP tool invocation."""

    execution_id: str
    step_id: str


def build_mcp_event(
    *,
    server: str,
    tool: str,
    execution_id: str,
    step_id: str,
    parent_step_id: str | None,
    transport: str | None,
    auth_type: str | None,
    latency_ms: float,
    environment: str,
    status: str,
    error: BaseException | None,
    metadata: Mapping[str, Any] | None,
    provider_reported_cost_usd: Decimal | float | int | None,
) -> dict[str, Any]:
    active_trace = current_trace()
    attributes = dict(metadata or {})
    if active_trace is not None:
        # Trace-level business attribution is authoritative when the same key
        # also appears in call-specific metadata.
        attributes.update(active_trace.attributes())
    event: dict[str, Any] = {
        "event_type": "mcp",
        "event_id": new_id("evt"),
        "execution_id": execution_id,
        "step_id": step_id,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "mcp_server": server,
        "mcp_tool": tool,
        "latency_ms": round(max(latency_ms, 0), 3),
        "status": status,
        "error_type": type(error).__name__ if error is not None else None,
        "environment": environment,
        "attributes": attributes,
    }
    if parent_step_id is not None:
        event["parent_step_id"] = parent_step_id
    if transport is not None:
        event["mcp_transport"] = transport
    if auth_type is not None:
        event["mcp_auth_type"] = auth_type
    if provider_reported_cost_usd is not None:
        event["provider_reported_cost_usd"] = float(provider_reported_cost_usd)
    return event


@contextmanager
def observe_mcp_call(
    *,
    server: str,
    tool: str,
    enqueue: Callable[[dict[str, Any]], None],
    environment: str,
    transport: str | None = None,
    auth_type: str | None = None,
    metadata: Mapping[str, Any] | None = None,
    provider_reported_cost_usd: Decimal | float | int | None = None,
    execution_id: str | None = None,
    parent_step_id: str | None = None,
) -> Iterator[MCPCallContext]:
    """Measure one MCP tool call without inspecting its arguments or result."""

    active_trace = current_trace()
    context = MCPCallContext(
        execution_id=execution_id
        or (active_trace.execution_id if active_trace is not None else new_id("exec")),
        step_id=new_id("step"),
    )
    started = time.perf_counter()
    try:
        yield context
    except BaseException as error:
        try:
            enqueue(
                build_mcp_event(
                    server=server,
                    tool=tool,
                    execution_id=context.execution_id,
                    step_id=context.step_id,
                    parent_step_id=parent_step_id or getattr(active_trace, "parent_step_id", None),
                    transport=transport,
                    auth_type=auth_type,
                    latency_ms=(time.perf_counter() - started) * 1_000,
                    environment=environment,
                    status="error",
                    error=error,
                    metadata=metadata,
                    provider_reported_cost_usd=provider_reported_cost_usd,
                )
            )
        except Exception:
            pass
        raise
    else:
        try:
            enqueue(
                build_mcp_event(
                    server=server,
                    tool=tool,
                    execution_id=context.execution_id,
                    step_id=context.step_id,
                    parent_step_id=parent_step_id or getattr(active_trace, "parent_step_id", None),
                    transport=transport,
                    auth_type=auth_type,
                    latency_ms=(time.perf_counter() - started) * 1_000,
                    environment=environment,
                    status="success",
                    error=None,
                    metadata=metadata,
                    provider_reported_cost_usd=provider_reported_cost_usd,
                )
            )
        except Exception:
            pass
