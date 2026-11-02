# Security policy

## Reporting a vulnerability

Email **help@ganivra.com** with the subject "Security report". Please don't open
a public GitHub issue for security problems.

Include the SDK version, a description of the issue and steps to reproduce it.
We'll acknowledge your report and keep you updated while we fix it.

## Supported versions

Security fixes go into the latest release on PyPI. Upgrade with:

```bash
python -m pip install --upgrade ganivra
```

## What the SDK sends

The SDK sends usage metadata only: model, token counts, latency, status and the
attributes you attach to a trace. It never sends prompts, responses, tool
arguments, tool results or error messages. Keep your Ganivra API key in an
environment variable or secret manager, never in source code.
