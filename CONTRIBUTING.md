# Contributing

Thanks for helping improve the Ganivra Python SDK. Bug reports, fixes and
documentation improvements are welcome.

## Development setup

Python 3.10 or newer is required.

```bash
git clone https://github.com/prodmoh/ganivra-python.git
cd ganivra-python
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[test]"
python -m pytest -q
```

The tests don't call OpenAI, Anthropic or the Ganivra API, so no keys are
needed.

## Pull requests

- Keep each pull request to one change, with a test that covers it.
- Never send prompt, response, tool or error-message content. The SDK records
  usage metadata only, and tests check this.
- Automatic capture must never break or slow the caller's AI request. Telemetry
  failures stay inside the SDK.
- Add a line to `CHANGELOG.md` under "Unreleased".

## Releases

Maintainers bump the version in `pyproject.toml` and `ganivra/__init__.py`,
then push a matching tag such as `v0.6.2`. The release workflow runs the tests
and publishes to PyPI.
