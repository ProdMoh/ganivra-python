# Changelog

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
