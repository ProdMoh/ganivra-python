# Changelog

## 0.6.3

### Added
- Clients pointed at Sarvam's OpenAI-compatible API (`https://api.sarvam.ai/v2`) are
  recorded under the `sarvam` provider and priced at Sarvam's rupee rates.
- `ganivra.init(self_hosted_hosts=[...])` names the hosts of your own model servers
  (vLLM, SGLang, TGI). Their calls are recorded as provider `self_hosted` and priced as a
  share of the GPU pools set up in Ganivra.
- `client.economics.gpu_pools()`, `create_gpu_pool()`, `end_gpu_pool()` and
  `delete_gpu_pool()`.
- `client.economics.gpu_tenants(params=...)`: customers renting dedicated GPU pools, with
  their GPU cost including idle hours, what they pay per GPU-hour and the margin.
  `create_gpu_pool()` accepts `customer_id` and `sell_hourly_rate_usd` for a pool rented
  to one customer.
- `client.economics.gpu_move_analysis(params=...)`: which features' API calls would cost
  less on an existing GPU pool or on GPUs you are considering.
- Self-hosted calls send the server's response id as `attributes.request_id`. Ganivra
  matches it to vLLM's own OpenTelemetry trace for the request and splits the GPU cost by
  the call's measured GPU time.

## 0.6.2

### Added
- Automatic capture of synchronous OpenAI Chat Completions, including streaming.
  Streams need `stream_options={"include_usage": True}`; without it the call is
  recorded as unpriced.
- Clients pointed at Together AI, Fireworks, DeepInfra or Baseten are recorded
  under that provider and priced at its rates.
- OpenAI calls record the service tier that served them (Flex, Priority, Fast
  mode, Ultrafast, Scale) and cache-write tokens, so they are priced correctly.
- OpenAI and Claude calls made through Amazon Bedrock, Google Vertex, Azure
  Foundry or Azure OpenAI clients are tagged with that platform, so they are not
  priced at the provider's own API rates.
- REST client helpers: `client.margin_review`, `client.spend_close`, emissions
  reports (`client.reports.emissions()`, `export_emissions()`,
  `recalculate_emissions()`), the account profile and
  `client.economics.create_model_policy()`.

### Changed
- Transactions default to `currency="USD"`.

### Project
- Source published on GitHub, with links from PyPI to the repository, issue
  tracker and changelog. Runnable examples in `examples/`.

## 0.6.1 and earlier

Released on PyPI before the source was public. See the
[release history](https://pypi.org/project/ganivra/#history). Version 0.6 added
automatic Claude Messages capture (`ganivra[anthropic]`) and event corrections
and history in the REST client.
