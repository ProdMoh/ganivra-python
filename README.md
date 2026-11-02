# Ganivra Python SDK

[![PyPI](https://img.shields.io/pypi/v/ganivra)](https://pypi.org/project/ganivra/)
[![Python](https://img.shields.io/pypi/pyversions/ganivra)](https://pypi.org/project/ganivra/)
[![CI](https://github.com/prodmoh/ganivra-python/actions/workflows/ci.yml/badge.svg)](https://github.com/prodmoh/ganivra-python/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](https://github.com/prodmoh/ganivra-python/blob/main/LICENSE)

Track what each customer's AI calls cost you. Add two lines to an existing
OpenAI or Claude app and Ganivra records every call's model and token usage,
prices it, and adds it up by customer, workflow and feature. See
[ganivra.com](https://ganivra.com) and the [integration guide](https://ganivra.com/integration).

Ganivra measures AI cost, revenue, profit, and margin without proxying model
traffic or storing prompt and response bodies. Version 0.6 supports automatic
OpenAI Responses and Claude Messages telemetry, explicit provider-independent
REST events, MCP tool calls, non-model delivery costs, pricing plans, customer
plan attribution, and confirmed purchase or subscription transactions.

## Version 0.6 capability status

| Capability | Status |
| --- | --- |
| OpenAI Responses | Automatic for synchronous, non-streaming calls |
| Claude Messages | Automatic for sync, async, and streaming calls with `ganivra[anthropic]` |
| OpenAI Chat Completions and open-model APIs | Automatic for synchronous calls, including streaming. A client pointed at Together AI, Fireworks, DeepInfra or Baseten is recorded under that provider and priced at its rates; other base URLs are recorded as `openai`. Streams need `stream_options={"include_usage": True}`; without it the call is recorded as unpriced |
| MCP tools | Instrument with `ganivra.mcp_call(...)` or submit through REST |
| Gemini and other providers | Submit complete usage through `ganivra.Client`; not automatically instrumented |
| Customer, workflow, feature, prompt, plan, and agent attribution | Supported through trace attributes and explicit events |
| Purchases, renewals, credit purchases, and refunds | Synchronous acknowledged transaction API |
| Telephony, speech, OCR, search, compute, and other delivery costs | Synchronous acknowledged delivery-cost API |

Automatic telemetry uses a bounded best-effort queue. Financial transactions,
delivery costs, and explicit REST writes require acknowledgement and surface
API errors to the caller.

## Install

```bash
python -m pip install ganivra
```

Ganivra requires Python 3.10 or newer. Auto-capture supports synchronous,
non-streaming OpenAI Responses and Claude Messages (sync, async and streaming).
Claude support requires SDK 0.6 and the optional Anthropic dependency.

## Initialize before creating the OpenAI client

```python
import ganivra
from openai import OpenAI

ganivra.init(api_key="gv_live_your_workspace_key")
client = OpenAI()

response = client.responses.create(
    model="gpt-6.1-sol",
    input="Explain our refund policy simply.",
)
```

Initialization automatically captures model, input/output/cached token counts,
latency, status, error type, and environment. Ganivra creates execution and step
IDs and exports the metadata on a bounded background queue.

## Add business context for unit economics

```python
def answer_for(account, credits_debited):
    with ganivra.trace(
        metadata={"channel": "voice"},
        application="support-platform",
        workflow="support_answer",
        feature="support_chatbot",
        customer_id=account.id,
        plan_key=account.plan_key,
        credits=credits_debited,
        prompt_id="support_answer",
        prompt_version="v1",
    ):
        return client.responses.create(
            model="gpt-6.1-sol",
            input="Explain our refund policy simply.",
        )
```

Trace metadata is optional. It enables customer, feature, workflow, prompt, and
margin reporting. Use the stable tenant or account identifier already present
in each authenticated request as `customer_id`; customers do not need to be
registered with Ganivra first. Configure customer pricing plans separately when
you want revenue derived automatically instead of sending `revenue_usd` per
execution. The `metadata` mapping accepts additional bounded JSON
dimensions and is inherited by nested traces. Use pseudonymous identifiers
where appropriate.

Pricing rates stay in Ganivra; never look up a rate or calculate revenue in the
instrumented request. Subscription and per-execution plans only need
`customer_id`. Token and hybrid plans use the token/execution telemetry captured
by the SDK. For a credit/unit plan, also pass the exact usage attribute
configured on the plan—`credits` above—with the units your application already
deducted. Send `plan_key` when customers can choose or change plans without a
manual Ganivra assignment. Ganivra combines the plan and credit usage with the
rate configured in your workspace.

Treat one billable customer action as one trace/execution. If one trace produces
multiple model calls, the inherited transaction-level credit value is repeated
on the resulting events and counted once. Start a separate trace for each
independently billed action.

Example: a customer pays $100 for 500 credits. Record the purchase through the
Transactions API as `credit_purchase` with `units_purchased=500`; a trace that
deducts 50 credits passes `credits=50` and earns $10 against the cost of its
model calls. Each subscription payment covers one month from its payment date
and is shared across the customer's actions in that period, and credits included with a subscription (`units_purchased` on the
`subscription_payment`) are used before pack credits. Do not pass a credit
`plan_key` for users who have not bought credits, such as guests.

## Track MCP tool calls through the same API

Use `ganivra.mcp_call(...)` to capture tool execution. It uses the same API key, background
queue, batching, retries, `/v1/events` endpoint, and active trace as automatic
model instrumentation. The helper measures latency and outcome around the tool
call but never receives or inspects its arguments or result.

```python
import ganivra

with ganivra.trace(
    application="customer-operations-platform",
    workflow="lead_qualification",
    feature="sales_agent",
    customer_id=account.id,
) as execution:
    with ganivra.mcp_call(
        server="crm-server",
        tool="search_accounts",
        transport="streamable_http",
        auth_type="oauth",
        metadata={
            "result_count": 3,
            "cache_hit": False,
            "region": "us-east",
        },
        provider_reported_cost_usd=0.002,
    ) as tool_call:
        result = mcp_client.call_tool("search_accounts", arguments)
```

The emitted MCP event shares `execution.execution_id` with model calls inside
the surrounding trace. On success it records `status="success"`; if the tool
raises, Ganivra records only the exception class as `error_type` and re-raises
the original exception unchanged.

### Link a model call caused by an MCP result

Shared `execution_id` is sufficient for execution-level cost attribution. When
you also need an explicit parent-child edge, use the yielded MCP `step_id` as
the next trace's `parent_step_id`:

```python
with ganivra.trace(
    execution_id=execution.execution_id,
    parent_step_id=tool_call.step_id,
):
    response = client.responses.create(
        model="gpt-6.1-sol",
        input=build_model_input(result),
    )
```

The OpenAI event remains a normal model event with no `event_type`; only the MCP
tool event sends `event_type="mcp"`.

### MCP helper parameters

| Parameter | Required | Guidance |
| --- | --- | --- |
| `server` | Yes | Stable logical MCP server name, such as `crm-server`; do not send a URL containing credentials |
| `tool` | Yes | Exact stable tool name advertised by the server |
| `transport` | No | Category such as `stdio`, `sse`, or `streamable_http` |
| `auth_type` | No | Coarse category such as `oauth`, `api_key`, or `none`; never send scopes or credentials |
| `metadata` | No | Bounded counts, categories, IDs, and booleans only |
| `provider_reported_cost_usd` | No | Exact known cost; send `0` only when the tool is known to be free |
| `execution_id` | No | Override when joining a trace created in another process or service |
| `parent_step_id` | No | Step that directly caused this MCP invocation |

Do not place tool arguments, tool results, prompts, responses, OAuth scopes,
workspace IDs, tokens, secrets, personal data, or request/response bodies in
`metadata`. Ganivra rejects these content-bearing fields at ingestion.

### MCP cost behavior

- If the MCP provider returns an exact cost, pass it through
  `provider_reported_cost_usd`.
- If a tool has a fixed contract rate, configure provider `mcp`, model
  `<server>/<tool>`, and a `request` component rate in Ganivra.
- Send `provider_reported_cost_usd=0` only for a confirmed free tool call.
- If no exact cost or rate exists, omit cost. Ganivra marks the step unpriced
  rather than silently treating unknown cost as zero.

### When not to use the Python helper

Use the REST event contract directly when MCP calls happen in Node.js, Java,
Go, another service, or existing middleware that already measures tool calls.
Do not duplicate the event from both the Python helper and REST integration;
if retries are possible, keep one stable `event_id` in the direct REST path.

## Record confirmed purchases (optional)

Event telemetry works on its own and provides AI cost plus plan-rated unit
economics. After your payment webhook is verified and your application has
updated the customer's credits or subscription, optionally send the confirmed
financial transaction so Ganivra can reconcile plan-rated revenue with payment
actuals.

```python
result = ganivra.transactions.create(
    external_id=payment_intent.id,  # stable provider ID; retries are idempotent
    customer_id=account.id,
    transaction_type="credit_purchase",
    amount=3999,
    currency="INR",
    amount_usd=47,
    units_purchased=1000,
    plan_key="growth",
    source="stripe",
)
```

Currency defaults to USD. For another currency, optionally send either
`amount_usd` or `exchange_rate_to_usd` to normalize (never both). Without either,
Ganivra retains the native amount and compares its raw number with USD costs;
contribution and margin display a currency-normalization warning. Use
`transaction_type="subscription_payment"` for renewals and
`transaction_type="refund"` for refunds. Include `execution_id` when a payment
belongs to a particular AI result. This call is synchronous and raises
`ganivra.GanivraAPIError` if Ganivra does not accept the transaction; only call
it after your own payment and entitlement updates succeed.

## Configuration

```python
ganivra.init(
    api_key="gv_live_your_workspace_key",
    endpoint="https://api.ganivra.com",
    environment="production",
    queue_size=1000,
    batch_size=20,
    timeout_seconds=2.0,
    max_retries=2,
)
```

For local Ganivra development, set `endpoint="http://127.0.0.1:8000"`.
Call `ganivra.flush()` in short-lived scripts when you want to wait briefly for
queued telemetry.

## Privacy and failure behavior

- OpenAI requests continue going directly from your application to OpenAI.
- Prompt and response bodies are never collected.
- OpenAI API keys are never collected.
- Telemetry failures never change the OpenAI result or exception your code sees.
- A full queue or unavailable Ganivra endpoint drops telemetry instead of
  blocking the application.

Prefer the language-independent REST API when automatic Python instrumentation
is not appropriate. The canonical API contract is documented at
`docs/API.md` in the Ganivra project.

## Integration fields that unlock value

Send a stable customer ID, application, feature and workflow with every execution.
For calculated revenue, send the configured `plan_key` or assign the customer to
an effective pricing plan. Credit/unit plans also need actual consumed units in
the configured attribute. Missing revenue appears as Unknown, not zero.

The [integration field guide](https://ganivra.com/integration#important-fields)
explains required fields, occurrence timestamps, execution/step identity, model
and MCP quantities, plan selection, and a one-execution verification checklist.
Preserve event IDs on delivery retries; actual additional calls need new IDs.
Business workflow names are open-ended; the top-level event_type is not.

### Additional delivery costs

Use `ganivra.delivery_costs.create(...)` or `create_batch([...])` to record explicit telephony, speech, OCR, search, compute and other non-model costs. Unlike best-effort model telemetry this call requires acknowledgement and raises `GanivraAPIError` on failure. Persist and retry identical event IDs/payloads in your application. See the [integration guide](https://ganivra.com/integration) for schemas and corrections. Do not report charges already present in model or MCP events.

## Explicit REST client and administration

`ganivra.Client` covers provider-independent events, revenue, pricing plans, assignments and historical dates, contract rates, reconciliation, reports, investigations, evidence, snapshots, audit logs, bills, allocations, budgets and workspace administration. Use `api_key` for ingestion or `access_token` for authorized management. See the [REST client guide](REST_CLIENT.md) for examples and methods. SDK 0.6 additionally supports automatic Claude Messages capture; Gemini remains explicit submission only.


### Explicit client quick start

```python
from ganivra import Client, APIError

usage = Client(api_key="your_workspace_key")
# event is a complete REST event with actual provider usage and stable IDs.
result = usage.events.create(payload=event)

admin = Client(access_token=current_user_access_token, workspace_id=workspace_id)
history = admin.events.history(event["event_id"])
assessments = admin.value.list(params={"limit": 25, "offset": 0})
```

The client supports complete REST payloads, including corrections, revenue
imports, pricing administration and evidence. Authentication and permissions
are identical to REST. Errors expose status, body and Retry-After; writes are
never automatically retried. Use `trace(agent_name="review_agent", ...)` for
first-class agent attribution in auto-captured calls. See REST_CLIENT.md for
coverage and the automatic-capture limitations.


## Automatic Claude capture (0.6)

```bash
pip install 'ganivra[anthropic]>=0.6,<0.7'
```

Install the optional Claude adapter with `pip install 'ganivra[anthropic]>=0.6,<0.7'`.
Version 0.6 is tested with official `anthropic==0.125.0`; the optional dependency
is constrained to `>=0.125,<0.126` for the managed-stream adapter. No paid
provider calls are required for the transport tests.

```python
import os
import ganivra
from anthropic import Anthropic

ganivra.init(api_key=os.environ['GANIVRA_API_KEY'])
client = Anthropic()  # Uses your ANTHROPIC_API_KEY; requests go directly to Claude.

with ganivra.trace(customer_id='tenant_42', plan_key='growth',
                   workflow='document_review', agent_name='review_agent'):
    with client.messages.stream(
        model='claude-sonnet-4-6', max_tokens=1024,
        messages=[{'role': 'user', 'content': 'Summarize the document.'}],
    ) as stream:
        for text in stream.text_stream:
            print(text, end='')

ganivra.flush()  # Best-effort queue drain; not proof of server acceptance.
```

Supported: `Anthropic.messages.create`, `AsyncAnthropic.messages.create`,
`stream=True`, and both clients' `messages.stream` context managers. Initialize
before constructing clients. Use `AsyncAnthropic` and `async with` / `async for`
for asynchronous streaming; attribution uses the context active at invocation.

One event is emitted per observed SDK operation, not per chunk. Usage updates
are cumulative. Capture includes input/output tokens, cache reads, 5-minute and
1-hour cache writes, and reported web search/fetch counts. Reasoning tokens are
already included in output tokens and are not added twice. No message, prompt,
response, tool content or error message is sent. Provider SDK internal retry
attempts are not separately visible; application-level calls generate new events.

Consume streams to completion or explicitly close them. Early closure, stream
errors and cancellation retain available usage with `usage_incomplete=1` and
error status. Ganivra leaves incomplete usage unpriced, including
after repricing, unless exact provider cost is supplied. Successful responses
without usage are also unpriced. Priority-tier usage is unpriced without exact
provider cost.

The default Messages API is covered; beta APIs, batch jobs, raw HTTP-response
helpers, Bedrock/Vertex clients, Gemini, and OpenAI async/streaming are outside
this adapter's supported scope. Do not also submit the same calls manually.
The background queue remains best-effort; process termination or queue exhaustion
can lose telemetry. This feature does not add durable delivery.
