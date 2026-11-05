from __future__ import annotations

import json
import threading
from types import SimpleNamespace

import pytest

import ganivra
from ganivra.config import Config
from ganivra.context import trace
from ganivra.instrumentation import build_event, extract_usage, instrument_openai
from ganivra.mcp import build_mcp_event
from ganivra.sender import BackgroundSender


def test_initialization_validates_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    created: list[Config] = []

    class FakeSender:
        def __init__(self, config: Config) -> None:
            created.append(config)

        def shutdown(self, timeout: float) -> None:
            pass

        def flush(self, timeout: float) -> bool:
            return True

    monkeypatch.setattr(ganivra, "BackgroundSender", FakeSender)
    monkeypatch.setattr(ganivra, "instrument_openai", lambda *_: True)
    ganivra.init(api_key="test_key", endpoint="http://localhost:8000", environment="test")

    assert created[-1].events_url == "http://localhost:8000/v1/events"
    assert created[-1].environment == "test"
    with pytest.raises(ValueError):
        ganivra.init(api_key="", endpoint="http://localhost:8000")


def test_extracts_response_usage_including_cached_tokens() -> None:
    response = SimpleNamespace(
        usage=SimpleNamespace(
            input_tokens=120,
            output_tokens=30,
            total_tokens=150,
            input_tokens_details=SimpleNamespace(cached_tokens=80),
        )
    )
    assert extract_usage(response) == {
        "input_tokens": 120,
        "output_tokens": 30,
        "cached_tokens": 80,
        "total_tokens": 150,
    }


def test_trace_context_propagates_and_reuses_execution_id() -> None:
    with trace(
        metadata={
            "channel": "voice",
            "use_case": "sales_intelligence",
            "agent": {"name": "qualifier", "version": 3},
        },
        application="prodanalytics",
        workflow="support_answer",
        feature="chat",
        plan_key="growth",
        credits=25,
        customer_id="acme",
        prompt_id="support_answer",
        prompt_version="v17",
        revenue_usd=0.10,
    ) as ctx:
        first = build_event(
            response={"model": "gpt-5", "usage": {}},
            requested_model=None,
            latency_ms=1,
            environment="test",
        )
        second = build_event(
            response={"model": "gpt-5", "usage": {}},
            requested_model=None,
            latency_ms=1,
            environment="test",
        )

    assert first["execution_id"] == second["execution_id"] == ctx.execution_id
    assert first["attributes"] == {
        "channel": "voice",
        "use_case": "sales_intelligence",
        "agent": {"name": "qualifier", "version": 3},
        "application": "prodanalytics",
        "workflow": "support_answer",
        "feature": "chat",
        "plan_key": "growth",
        "credits": 25.0,
        "customer_id": "acme",
        "prompt_id": "support_answer",
        "prompt_version": "v17",
        "revenue_usd": 0.10,
    }
    assert first["step_id"] != second["step_id"]


def test_nested_trace_metadata_inherits_and_overrides_dimensions() -> None:
    with trace(metadata={"tenant": "acme", "channel": "voice"}):
        with trace(metadata={"channel": "chat", "campaign": "launch"}):
            event = build_event(
                response={"model": "gpt-5", "usage": {}},
                requested_model=None,
                latency_ms=1,
                environment="test",
            )

    assert event["attributes"] == {
        "tenant": "acme",
        "channel": "chat",
        "campaign": "launch",
    }


def test_call_without_trace_gets_an_execution_id() -> None:
    event = build_event(
        response={"model": "gpt-5", "usage": {}},
        requested_model=None,
        latency_ms=1,
        environment="test",
    )
    assert event["execution_id"].startswith("exec_")


def test_openai_instrumentation_observes_success_and_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[dict] = []

    class Responses:
        def create(self, **kwargs):
            if kwargs.get("model") == "broken":
                raise RuntimeError("provider failed")
            return SimpleNamespace(
                model=kwargs["model"],
                usage=SimpleNamespace(input_tokens=10, output_tokens=2, total_tokens=12),
            )

    monkeypatch.setattr("ganivra.instrumentation._responses_class", lambda: Responses)
    monkeypatch.setattr("ganivra.instrumentation._chat_completions_class", lambda: None)
    assert instrument_openai(lambda: "test", events.append)

    response = Responses().create(model="gpt-5", input="secret prompt")
    assert response.model == "gpt-5"
    assert events[0]["operation"] == "responses.create"
    assert events[0]["input_tokens"] == 10
    assert "secret prompt" not in json.dumps(events[0])

    with pytest.raises(RuntimeError, match="provider failed"):
        Responses().create(model="broken", input="also secret")
    assert events[1]["status"] == "error"
    assert events[1]["error_type"] == "RuntimeError"


def test_telemetry_failure_never_changes_openai_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = object()

    class Responses:
        def create(self, **kwargs):
            return expected

    def unavailable(_: dict) -> None:
        raise OSError("telemetry unavailable")

    monkeypatch.setattr("ganivra.instrumentation._responses_class", lambda: Responses)
    monkeypatch.setattr("ganivra.instrumentation._chat_completions_class", lambda: None)
    instrument_openai(lambda: "test", unavailable)
    assert Responses().create(model="gpt-5", input="hello") is expected


def test_mcp_call_uses_existing_queue_and_inherits_trace_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[dict] = []
    monkeypatch.setattr(ganivra, "_enqueue", events.append)
    monkeypatch.setattr(ganivra, "_get_environment", lambda: "test")

    with ganivra.trace(
        application="customer-operations-platform",
        workflow="lead_qualification",
        feature="sales_agent",
        customer_id="account_northstar",
    ) as trace_context:
        with ganivra.mcp_call(
            server="crm-server",
            tool="search_accounts",
            transport="streamable_http",
            auth_type="oauth",
            metadata={"result_count": 3, "cache_hit": False},
            provider_reported_cost_usd=0.002,
        ) as call_context:
            pass

    assert call_context.execution_id == trace_context.execution_id
    event = events[0]
    assert event["event_type"] == "mcp"
    assert event["mcp_server"] == "crm-server"
    assert event["mcp_tool"] == "search_accounts"
    assert event["mcp_transport"] == "streamable_http"
    assert event["mcp_auth_type"] == "oauth"
    assert event["status"] == "success"
    assert event["provider_reported_cost_usd"] == 0.002
    assert event["attributes"] == {
        "result_count": 3,
        "cache_hit": False,
        "application": "customer-operations-platform",
        "workflow": "lead_qualification",
        "feature": "sales_agent",
        "customer_id": "account_northstar",
    }


def test_mcp_call_records_error_and_preserves_original_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[dict] = []
    monkeypatch.setattr(ganivra, "_enqueue", events.append)

    with pytest.raises(RuntimeError, match="tool unavailable"):
        with ganivra.mcp_call(server="inventory", tool="lookup_sku"):
            raise RuntimeError("tool unavailable")

    assert events[0]["status"] == "error"
    assert events[0]["error_type"] == "RuntimeError"
    assert "tool unavailable" not in json.dumps(events[0])


def test_mcp_event_supports_explicit_execution_and_parent_step() -> None:
    event = build_mcp_event(
        server="knowledge",
        tool="search",
        execution_id="exec_shared",
        step_id="step_tool",
        parent_step_id="step_model",
        transport=None,
        auth_type=None,
        latency_ms=10,
        environment="test",
        status="success",
        error=None,
        metadata=None,
        provider_reported_cost_usd=0,
    )

    assert event["execution_id"] == "exec_shared"
    assert event["parent_step_id"] == "step_model"
    assert event["provider_reported_cost_usd"] == 0.0
    assert "mcp_transport" not in event


def test_model_event_can_link_to_an_mcp_parent_step() -> None:
    with trace(execution_id="exec_shared", parent_step_id="step_mcp"):
        event = build_event(
            response={"model": "gpt-5", "usage": {}},
            requested_model=None,
            latency_ms=1,
            environment="test",
        )

    assert event["execution_id"] == "exec_shared"
    assert event["parent_step_id"] == "step_mcp"


def test_background_sender_posts_batches(monkeypatch: pytest.MonkeyPatch) -> None:
    received: list[tuple[str | None, dict]] = []
    ready = threading.Event()

    class Response:
        status = 202

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

    def fake_urlopen(request, timeout):
        received.append(
            (request.get_header("Authorization"), json.loads(request.data.decode()))
        )
        ready.set()
        return Response()

    monkeypatch.setattr("ganivra.sender.urlopen", fake_urlopen)
    sender = BackgroundSender(
        Config(
            api_key="workspace_secret",
            endpoint="http://telemetry.test",
            max_retries=0,
        )
    )
    try:
        sender.enqueue({"event_id": "evt_1"})
        assert ready.wait(2)
        assert sender.flush(1)
        assert received == [
            ("Bearer workspace_secret", {"events": [{"event_id": "evt_1"}]})
        ]
    finally:
        sender.shutdown()


def test_transaction_helper_posts_confirmed_purchase(monkeypatch: pytest.MonkeyPatch) -> None:
    received: list[tuple[str, str | None, dict]] = []

    class Response:
        status = 201

        def read(self):
            return b'{"external_id":"stripe_pi_123","created":true,"amount_usd":47}'

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

    def fake_urlopen(request, timeout):
        received.append((request.full_url, request.get_header("Authorization"), json.loads(request.data.decode())))
        return Response()

    monkeypatch.setattr("ganivra.economics.urlopen", fake_urlopen)
    ganivra.init(api_key="workspace_secret", endpoint="http://ganivra.test", environment="test")
    result = ganivra.transactions.create(
        external_id="stripe_pi_123",
        customer_id="customer_123",
        transaction_type="credit_purchase",
        amount=3999,
        currency="inr",
        amount_usd=47,
        units_purchased=1000,
        plan_key="growth",
        source="stripe",
    )

    assert result["created"] is True
    assert received == [(
        "http://ganivra.test/v1/economics/transactions",
        "Bearer workspace_secret",
        {
            "external_id": "stripe_pi_123",
            "customer_id": "customer_123",
            "transaction_type": "credit_purchase",
            "amount": 3999,
            "currency": "INR",
            "amount_usd": 47,
            "plan_key": "growth",
            "units_purchased": 1000,
            "source": "stripe",
            "metadata": {},
        },
    )]


@pytest.mark.parametrize("currency, expected", [(None, "USD"), ("inr", "INR")])
def test_transaction_helper_currency_defaults_and_optional_fx(monkeypatch, currency, expected):
    captured = []
    class Response:
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def read(self): return b'{"created":true}'
    def send(request, timeout):
        captured.append(json.loads(request.data.decode()))
        return Response()
    monkeypatch.setattr("ganivra.economics.urlopen", send)
    ganivra.init(api_key="workspace_secret", endpoint="http://ganivra.test", environment="test")
    options = {} if currency is None else {"currency": currency}
    ganivra.transactions.create(external_id="native", customer_id="acme", amount=299, **options)
    assert captured[0]["currency"] == expected
    assert "amount_usd" not in captured[0] and "exchange_rate_to_usd" not in captured[0]


def test_openai_service_tier_and_platform_are_reported() -> None:
    from ganivra.instrumentation import detect_platform

    usage = SimpleNamespace(input_tokens=10, output_tokens=5, total_tokens=15, input_tokens_details=None)
    flex = build_event(response=SimpleNamespace(usage=usage, model="gpt-5", service_tier="flex"),
                       requested_model="gpt-5", latency_ms=1, environment="test")
    assert flex["usage_details"] == {"flex": 1} and "platform" not in flex
    priority = build_event(response=SimpleNamespace(usage=usage, model="gpt-5", service_tier="priority"),
                           requested_model="gpt-5", latency_ms=1, environment="test", platform="azure_openai")
    assert priority["usage_details"] == {"priority_tier": 1} and priority["platform"] == "azure_openai"
    standard = build_event(response=SimpleNamespace(usage=usage, model="gpt-5", service_tier="default"),
                           requested_model="gpt-5", latency_ms=1, environment="test")
    assert "usage_details" not in standard

    AzureOpenAI = type("AzureOpenAI", (), {})
    AnthropicBedrock = type("AnthropicBedrock", (), {})
    AnthropicVertex = type("AnthropicVertex", (), {})
    OpenAI = type("OpenAI", (), {})
    resource = lambda client: SimpleNamespace(_client=client())
    assert detect_platform(resource(AzureOpenAI)) == "azure_openai"
    assert detect_platform(resource(AnthropicBedrock)) == "aws_bedrock"
    assert detect_platform(resource(AnthropicVertex)) == "google_vertex"
    assert detect_platform(resource(OpenAI)) is None
    assert detect_platform(SimpleNamespace()) is None


def test_openai_cache_writes_and_fast_tiers_are_reported() -> None:
    usage = SimpleNamespace(input_tokens=1000, output_tokens=5, total_tokens=1005,
                            input_tokens_details=SimpleNamespace(cached_tokens=200, cache_write_tokens=300))
    event = build_event(response=SimpleNamespace(usage=usage, model="gpt-6.1-sol", service_tier="ultrafast"),
                        requested_model="gpt-6.1-sol", latency_ms=1, environment="test")
    assert event["usage_details"] == {"ultrafast": 1, "cache_write_tokens": 300}
    assert event["cached_tokens"] == 200
    fast = build_event(response=SimpleNamespace(usage=usage, model="gpt-6.1-sol", service_tier="fast"),
                       requested_model="gpt-6.1-sol", latency_ms=1, environment="test")
    assert fast["usage_details"]["fast_mode"] == 1


def test_open_model_providers_are_detected_from_the_base_url() -> None:
    from ganivra.instrumentation import detect_provider

    resource = lambda host: SimpleNamespace(_client=SimpleNamespace(base_url=SimpleNamespace(host=host)))
    assert detect_provider(resource("api.together.xyz")) == "together"
    assert detect_provider(resource("api.together.ai")) == "together"
    assert detect_provider(resource("api.fireworks.ai")) == "fireworks"
    assert detect_provider(resource("api.deepinfra.com")) == "deepinfra"
    assert detect_provider(resource("api.sarvam.ai")) == "sarvam"
    from ganivra.instrumentation import set_self_hosted_hosts
    set_self_hosted_hosts(["vllm.internal", "localhost"])
    try:
        assert detect_provider(resource("vllm.internal")) == "self_hosted"
        assert detect_provider(resource("gpu1.vllm.internal")) == "self_hosted"
        assert detect_provider(resource("localhost")) == "self_hosted"
        assert detect_provider(resource("api.together.xyz")) == "together"
    finally:
        set_self_hosted_hosts(())
    assert detect_provider(resource("inference.baseten.co")) == "baseten"
    assert detect_provider(resource("api.openai.com")) == "openai"
    assert detect_provider(resource("nottogether.ai")) == "openai"
    assert detect_provider(SimpleNamespace()) == "openai"


def test_chat_completions_are_recorded_with_the_detected_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    from ganivra.instrumentation import instrument_chat_completions

    events: list[dict] = []
    usage = SimpleNamespace(prompt_tokens=100, completion_tokens=20, total_tokens=120,
                            prompt_tokens_details=SimpleNamespace(cached_tokens=40))

    class Completions:
        _client = SimpleNamespace(base_url=SimpleNamespace(host="api.together.xyz"))

        def create(self, **kwargs):
            if kwargs.get("stream"):
                chunks = [SimpleNamespace(model=kwargs["model"], usage=None)]
                if kwargs.get("stream_options"):
                    chunks.append(SimpleNamespace(model=kwargs["model"], usage=usage))
                return iter(chunks)
            return SimpleNamespace(model=kwargs["model"], usage=usage)

    monkeypatch.setattr("ganivra.instrumentation._chat_completions_class", lambda: Completions)
    assert instrument_chat_completions(lambda: "test", events.append)

    Completions().create(model="openai/gpt-oss-120b", messages=[{"role": "user", "content": "secret"}])
    assert events[0]["provider"] == "together"
    assert events[0]["operation"] == "chat.completions.create"
    assert (events[0]["input_tokens"], events[0]["output_tokens"], events[0]["cached_tokens"]) == (100, 20, 40)
    assert "secret" not in json.dumps(events[0])

    assert len(list(Completions().create(model="m", stream=True, stream_options={"include_usage": True}))) == 2
    assert events[1]["input_tokens"] == 100 and "usage_details" not in events[1]

    # Without include_usage the stream has no token counts, so it is left unpriced rather than free.
    list(Completions().create(model="m", stream=True))
    assert events[2]["usage_details"] == {"usage_incomplete": 1}
    assert len(events) == 3


def test_self_hosted_calls_carry_the_response_id_to_match_the_servers_trace() -> None:
    response = SimpleNamespace(id="chatcmpl-0f3a", model="deepseek-ai/DeepSeek-V4.1-Flash",
                               usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5, total_tokens=15))
    event = build_event(response=response, requested_model=None, latency_ms=1, environment="test", provider="self_hosted",
                        operation="chat.completions.create")
    assert event["attributes"]["request_id"] == "chatcmpl-0f3a"
    api = build_event(response=response, requested_model=None, latency_ms=1, environment="test", provider="together",
                      operation="chat.completions.create")
    assert "request_id" not in api["attributes"]
