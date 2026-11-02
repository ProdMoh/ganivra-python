from __future__ import annotations

import functools
import importlib
import time
from datetime import datetime, timezone
from typing import Any, Callable

from .context import current_trace, new_id


def _value(obj: Any, name: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


# Cloud clients bill differently from the provider's own API; tag their calls
# so Ganivra never prices them at first-party catalog rates.
_PLATFORM_MARKERS = (("Bedrock", "aws_bedrock"), ("Vertex", "google_vertex"), ("Foundry", "azure_foundry"), ("Azure", "azure_openai"))


def detect_platform(resource: Any) -> str | None:
    """Return the serving platform for a patched SDK resource, or None for first party."""
    name = type(getattr(resource, "_client", None)).__name__
    for marker, platform in _PLATFORM_MARKERS:
        if marker in name:
            return platform
    return None


# OpenAI-compatible APIs for open models, identified by the client's base URL so their
# calls are priced at that provider's rates. Other hosts keep the "openai" provider.
_PROVIDER_HOSTS = (("together.xyz", "together"), ("together.ai", "together"), ("fireworks.ai", "fireworks"),
                   ("deepinfra.com", "deepinfra"), ("baseten.co", "baseten"))


def detect_provider(resource: Any) -> str:
    """Return the Ganivra provider for a patched OpenAI SDK resource."""
    try:
        host = str(getattr(getattr(getattr(resource, "_client", None), "base_url", None), "host", "") or "").lower()
    except Exception:
        return "openai"
    for suffix, provider in _PROVIDER_HOSTS:
        if host == suffix or host.endswith("." + suffix):
            return provider
    return "openai"


# OpenAI reports the tier that actually served the call; standard tiers add nothing.
_SERVICE_TIER_FLAGS = {"flex": "flex", "priority": "priority_tier", "fast": "fast_mode",
                       "ultrafast": "ultrafast", "scale": "scale_tier"}


def service_tier_details(response: Any) -> dict[str, int]:
    flag = _SERVICE_TIER_FLAGS.get(str(_value(response, "service_tier") or "").lower())
    details = {flag: 1} if flag else {}
    # Cache writes are part of input_tokens and billed at their own rate.
    writes = _value(_value(_value(response, "usage"), "input_tokens_details"), "cache_write_tokens", 0)
    if writes:
        details["cache_write_tokens"] = int(writes)
    return details


def extract_usage(response: Any) -> dict[str, int]:
    usage = _value(response, "usage")
    # Responses API names, falling back to Chat Completions names.
    input_tokens = int(_value(usage, "input_tokens", None) or _value(usage, "prompt_tokens", 0) or 0)
    output_tokens = int(_value(usage, "output_tokens", None) or _value(usage, "completion_tokens", 0) or 0)
    details = _value(usage, "input_tokens_details") or _value(usage, "prompt_tokens_details")
    cached_tokens = int(_value(details, "cached_tokens", 0) or 0)
    total_tokens = int(
        _value(usage, "total_tokens", input_tokens + output_tokens)
        or input_tokens + output_tokens
    )
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cached_tokens": cached_tokens,
        "total_tokens": total_tokens,
    }


def build_event(
    *,
    response: Any,
    requested_model: str | None,
    latency_ms: float,
    environment: str,
    error: BaseException | None = None,
    platform: str | None = None,
    provider: str = "openai",
    operation: str = "responses.create",
    usage_details: dict[str, int] | None = None,
) -> dict[str, Any]:
    active_trace = current_trace()
    usage = extract_usage(response) if error is None else extract_usage(None)
    response_model = _value(response, "model")
    event = {
        "event_id": new_id("evt"),
        "execution_id": (
            active_trace.execution_id if active_trace else new_id("exec")
        ),
        "step_id": new_id("step"),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "provider": provider,
        "model": str(response_model or requested_model or "unknown"),
        "operation": operation,
        **usage,
        "latency_ms": round(max(latency_ms, 0), 3),
        "status": "error" if error else "success",
        "error_type": type(error).__name__ if error else None,
        "environment": environment,
        "attributes": active_trace.attributes() if active_trace else {},
    }
    if active_trace is not None and active_trace.parent_step_id is not None:
        event["parent_step_id"] = active_trace.parent_step_id
    details = {**(service_tier_details(response) if error is None else {}), **(usage_details or {})}
    if details:
        event["usage_details"] = details
    # Sent only when detected so first-party events keep the original contract.
    if platform:
        event["platform"] = platform
    return event


def _responses_class() -> type[Any] | None:
    for module_name in (
        "openai.resources.responses",
        "openai.resources.responses.responses",
    ):
        try:
            module = importlib.import_module(module_name)
            candidate = getattr(module, "Responses", None)
            if candidate is not None:
                return candidate
        except Exception:
            continue
    return None


def instrument_openai(
    get_environment: Callable[[], str],
    enqueue: Callable[[dict[str, Any]], None],
) -> bool:
    responses_class = _responses_class()
    if responses_class is None:
        return False

    original = getattr(responses_class, "create", None)
    if original is None:
        return False
    if getattr(original, "_ganivra_instrumented", False):
        return True

    @functools.wraps(original)
    def wrapped(self: Any, *args: Any, **kwargs: Any) -> Any:
        started = time.perf_counter()
        requested_model = kwargs.get("model")
        try:
            response = original(self, *args, **kwargs)
        except BaseException as error:
            try:
                enqueue(
                    build_event(
                        response=None,
                        requested_model=requested_model,
                        latency_ms=(time.perf_counter() - started) * 1_000,
                        environment=get_environment(),
                        error=error,
                        platform=detect_platform(self),
                        provider=detect_provider(self),
                    )
                )
            except Exception:
                pass
            raise

        try:
            enqueue(
                build_event(
                    response=response,
                    requested_model=requested_model,
                    latency_ms=(time.perf_counter() - started) * 1_000,
                    environment=get_environment(),
                    platform=detect_platform(self),
                    provider=detect_provider(self),
                )
            )
        except Exception:
            pass
        return response

    setattr(wrapped, "_ganivra_instrumented", True)
    setattr(wrapped, "_ganivra_original", original)
    setattr(responses_class, "create", wrapped)
    instrument_chat_completions(get_environment, enqueue)
    return True


def _chat_completions_class() -> type[Any] | None:
    for module_name in ("openai.resources.chat.completions", "openai.resources.chat.completions.completions"):
        try:
            candidate = getattr(importlib.import_module(module_name), "Completions", None)
            if candidate is not None:
                return candidate
        except Exception:
            continue
    return None


class _ChatStream:
    """Passes a streamed chat completion through unchanged and records it once it ends.

    Usage arrives only in the final chunk when the request sets
    stream_options={"include_usage": True}; without it the call is recorded as
    incomplete, so Ganivra shows it as unpriced instead of free.
    """

    def __init__(self, stream: Any, finish: Callable[[Any, BaseException | None], None]) -> None:
        self._stream, self._finish, self._last, self._done = stream, finish, None, False
        self._chunks = self._observe()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._stream, name)

    def __iter__(self) -> "_ChatStream":
        return self

    def __next__(self) -> Any:
        return next(self._chunks)

    def __enter__(self) -> "_ChatStream":
        return self

    def __exit__(self, *exc: Any) -> Any:
        self._end(exc[1])
        exit_ = getattr(self._stream, "__exit__", None)
        return exit_(*exc) if exit_ else None

    def close(self) -> None:
        self._end(None)
        close = getattr(self._stream, "close", None)
        if close:
            close()

    def _observe(self):
        try:
            for chunk in self._stream:
                if _value(chunk, "usage") is not None or self._last is None:
                    self._last = chunk
                yield chunk
        except BaseException as error:
            self._end(error)
            raise
        self._end(None)

    def _end(self, error: BaseException | None) -> None:
        if not self._done:
            self._done = True
            self._finish(self._last, error)


def instrument_chat_completions(
    get_environment: Callable[[], str],
    enqueue: Callable[[dict[str, Any]], None],
) -> bool:
    completions_class = _chat_completions_class()
    original = getattr(completions_class, "create", None) if completions_class else None
    if original is None:
        return False
    if getattr(original, "_ganivra_instrumented", False):
        return True

    @functools.wraps(original)
    def wrapped(self: Any, *args: Any, **kwargs: Any) -> Any:
        started = time.perf_counter()
        requested_model = kwargs.get("model")

        def record(response: Any, error: BaseException | None, usage_details: dict[str, int] | None = None) -> None:
            try:
                enqueue(build_event(
                    response=response, requested_model=requested_model,
                    latency_ms=(time.perf_counter() - started) * 1_000, environment=get_environment(),
                    error=error, platform=detect_platform(self), provider=detect_provider(self),
                    operation="chat.completions.create", usage_details=usage_details,
                ))
            except Exception:
                pass

        try:
            response = original(self, *args, **kwargs)
        except BaseException as error:
            record(None, error)
            raise
        if kwargs.get("stream"):
            def finish(last: Any, error: BaseException | None) -> None:
                complete = error is None and _value(last, "usage") is not None
                record(last if error is None else None, error, None if complete else {"usage_incomplete": 1})
            try:
                return _ChatStream(response, finish)
            except Exception:
                return response
        record(response, None)
        return response

    setattr(wrapped, "_ganivra_instrumented", True)
    setattr(wrapped, "_ganivra_original", original)
    setattr(completions_class, "create", wrapped)
    return True
