# Python SDK REST coverage (0.6)

This document describes the REST client included in Ganivra 0.6. Install
`ganivra>=0.6,<0.7` to use `Client`; older releases do not provide the complete
surface documented here.

`ganivra.init()` automatically captures synchronous, non-streaming OpenAI
Responses. SDK 0.6 adds Claude Messages sync, async and streaming capture when
installed with the Anthropic extra. Gemini and other unsupported APIs require
explicit event submission. Do not report the same call twice. The REST client
is synchronous; use a worker/thread boundary in an async application.

## Ingestion without automatic instrumentation

```python
import os
from ganivra import Client

usage = Client(api_key=os.environ['GANIVRA_API_KEY'])
result = usage.events.create(payload={
    'event_id': 'evt_saved_action_step_1',
    'execution_id': 'exec_saved_action',
    'step_id': 'step_saved_1',
    'timestamp': '2026-10-04T10:00:00Z',
    'provider': 'anthropic',
    'model': 'your-actual-provider-model-id',
    'operation': 'messages.create',
    'input_tokens': 1000,
    'output_tokens': 200,
    'total_tokens': 1200,
    'latency_ms': 850,
    'status': 'success',
    'attributes': {
        'customer_id': 'tenant_42', 'workflow': 'document_review',
        'agent_name': 'review_agent', 'plan_key': 'growth',
    },
})
```

Use actual provider usage and occurrence time. All REST fields are accepted,
including `usage_details`, `provider_reported_cost_usd`, custom attributes and
parent IDs. Provider-reported cost means actual billed cost, not your estimate.
Backend validation and unknown-model pricing behavior remain unchanged.
`events.create_batch(payload={'events': events})` accepts up to 100 events.
Persist identical IDs and payloads for delivery retries. Actual additional model
attempts need distinct IDs. These explicit methods require acknowledgement;
they do not use the best-effort background queue or retry automatically.

Revenue: `usage.revenue.create(payload=entry)` and
`usage.revenue.import_entries(payload={'entries': entries})` (up to 1,000).
Transactions: `usage.economics.transaction(payload=transaction)` or the existing
`ganivra.transactions.create(...)` helper after initialization.
Delivery: `usage.delivery_costs.create_batch(payload={'events': costs})` (up to
500), including quantities, exact decimal rates, corrections and source
references. The existing `ganivra.delivery_costs` helpers remain supported.

## Authenticated management and reporting

```python
admin = Client(
    access_token=lambda: session_manager.current_access_token(),
    workspace_id='receiving-workspace-id',
)
plan = admin.pricing_plans.create(payload={
    'name': 'Growth', 'plan_key': 'growth',
    'pricing_model': 'per_execution', 'rate_config': {'rate': '2.00'},
    'effective_from': '2026-01-01T00:00:00Z',
})
assignment = admin.customer_plans.assign(payload={
    'customer_id': 'tenant_42', 'pricing_plan_id': plan['id'],
    'effective_from': '2026-01-01T00:00:00Z',
})
admin.pricing_plans.update_dates(plan['id'], payload={
    'effective_from': '2025-12-01T00:00:00Z',
})
admin.customer_plans.update_dates(assignment['id'], payload={
    'effective_from': '2025-12-01T00:00:00Z',
})  # The plan now covers the earlier assignment date.
report = admin.delivery_costs.investigate(params={
    'start': '2026-10-01', 'end': '2026-10-04',
})
```

Use a signed-in user access token, never a Supabase service-role secret. The
caller owns token acquisition and refresh; a callable is invoked per request.
Existing viewer/admin/owner checks apply. An ingestion key does not gain product
read or management permissions. Only the selected workspace is addressed;
`params={'workspace_id': ...}` explicitly overrides the client default.

Every named method uses REST-shaped `payload` for the JSON body and `params` for
query filters. Resource IDs are positional arguments. No SDK field subset hides
new backend fields; validation stays on the server. JSON responses are returned
unchanged. Pagination is explicit via the endpoint's `limit`/`offset` parameters.
Exports return bytes for CSV, ZIP, or JSON so they can be written without decoding.

```python
from pathlib import Path
from ganivra import APIError

try:
    data = admin.reports.export(params={
        'start': '2026-10-01', 'end': '2026-10-04', 'format': 'zip',
    })
    Path('cost-evidence.zip').write_bytes(data)
except APIError as error:
    print(error.status_code, error.body)  # Handle securely in your application.
```

Decimals are serialized as strings and dates as ISO values. Writes are never
retried automatically: a timeout can mean an accepted write whose response was
lost. Reuse stable IDs for idempotent operations; inspect state before repeating
plan creation, key rotation, and other non-idempotent operations.

## Method reference

| Resource | Methods |
| --- | --- |
| Events | `create()`, `create_batch()` |
| Revenue | `create()`, `import_entries()` |
| PricingPlans | `create()`, `update_dates()` |
| CustomerPlans | `assign()`, `update_dates()` |
| Economics | `get()`, `create_contract_rate()`, `reconcile()`, `reprice()`, `transaction()` |
| Delivery | `create_batch()`, `import_events()`, `report()`, `set_bill_policy()`, `create_snapshot()`, `get_snapshot()`, `investigate()`, `evidence()` |
| Reports | `costs()`, `export()`, `allocation_rules()`, `create_allocation_rule()`, `retire_allocation_rule()`, `reconcile()` |
| Bills | `list()`, `preview()`, `import_rows()`, `void()` |
| Budgets | `list()`, `create()`, `evaluate()`, `review()`, `set_owner()`, `archive()` |
| Workspaces | `list()`, `create()`, `get()`, `rename()`, `rotate_key()`, `access()`, `grant_access()`, `revoke_access()` |
| Audit | `list()`, `export()` |
| Account | `consumption()`, `bootstrap()`, `rotate_key()` |
| Executions | `list()`, `get()`, `dashboard()` |

`Client.request()` is available for any `/v1/` route without a named helper, with the same authorization requirements.

## Correct events and inspect history

With a user-session client, use `admin.events.correct(event_id, payload={
'request_id': '<stable UUID>', 'reason': 'Explain the correction', 'event': corrected_event})`.
Supply the complete event and explicit timestamp, preserving its event ID.
`admin.events.history(event_id, params={'limit': 50, 'offset': 0})` returns
corrections and pricing revisions. These methods require SDK 0.6 or newer.
Ingestion keys cannot perform corrections or read history. Conflicting ingestion
IDs now return 409; revenue imports are atomic. See [API integrity](https://ganivra.com/integration#python-rest-client).


## Parity and error handling

The named SDK resources cover every customer-facing Ganivra API route,
including value assessments (`client.value.list()` and
`client.value.import_assessment(payload=...)`), margin reviews and board
updates (`client.margin_review`), the monthly spend close
(`client.spend_close`), emissions reports (`client.reports.emissions()`), model
policies (`client.economics.create_model_policy(payload=...)`) and the account
profile. PDF and file exports return raw bytes. Routes used only by Ganivra's
own website forms are not included. A test checks each helper's actual method,
path and payload forwarding.

`client.transactions.create(payload=...)` is a discoverable alias for the
transaction endpoint. `client.delivery_costs.create(payload=cost)` wraps one
cost in the API batch envelope; `create_batch` accepts the REST batch payload.
All request-schema fields remain available through `payload` and all filters
through `params`, with backend validation unchanged.

`ganivra.trace(agent_name="review_agent", customer_id="tenant_42")` now accepts
agent attribution directly; nested traces inherit it unless overridden. Supply
the same execution ID explicitly when nesting scopes for a single action.

API conflicts (409), validation errors (422) and throttling (429) raise
`APIError` without automatic write retries. Inspect `status_code`, `body`,
`headers` and `retry_after` (the raw Retry-After value when provided). Choose
retry behavior for the specific operation; a retry delay is not permission to
repeat a non-idempotent write. Revenue imports preserve the backend's atomic
all-or-none behavior. Explicit `Client` submission does not monkey-patch provider
SDKs and does not require calling `ganivra.init()`.

This is REST capability parity, not automatic instrumentation parity. Automatic
capture in 0.6 covers Claude Messages sync, async and streaming; Gemini and
OpenAI async/streaming still require explicit completed-usage submission. Background auto-capture is still best-effort.
