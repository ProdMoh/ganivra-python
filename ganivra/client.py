"""Acknowledged REST client; independent of automatic instrumentation."""
from datetime import date, datetime
from decimal import Decimal
import json
from typing import Any, Callable, Mapping
from urllib.error import HTTPError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen
from uuid import UUID

from .economics import GanivraAPIError
from . import resources


def encode(value):
    if isinstance(value, (Decimal, UUID)):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    raise TypeError(f'Unsupported JSON value: {type(value).__name__}')


class APIError(GanivraAPIError):
    def __init__(self, message, *, status_code=None, body=None, headers=None):
        super().__init__(message)
        self.status_code = status_code
        self.body = body
        self.headers = dict(headers or {})
        self.retry_after = next((v for k, v in self.headers.items() if k.lower() == "retry-after"), None)


class Client:
    """Use api_key for ingestion OR access_token for authenticated product APIs.

    access_token may be a callable returning the current user token on each
    request. The caller owns login/refresh. Writes are never automatically retried.
    """
    def __init__(self, *, api_key: str | None = None,
                 access_token: str | Callable[[], str] | None = None,
                 endpoint: str = 'https://api.ganivra.com',
                 workspace_id: str | None = None, timeout_seconds: float = 10):
        if (api_key is None) == (access_token is None):
            raise ValueError('Supply exactly one of api_key or access_token')
        parsed = urlparse(endpoint)
        if parsed.scheme not in {'https', 'http'} or not parsed.netloc or parsed.query or parsed.fragment:
            raise ValueError('endpoint must be an HTTP(S) base URL without query or fragment')
        if timeout_seconds <= 0:
            raise ValueError('timeout_seconds must be positive')
        self.endpoint = endpoint.rstrip('/')
        self._credential = api_key if api_key is not None else access_token
        self.workspace_id = workspace_id
        self.timeout_seconds = timeout_seconds
        self.events = resources.Events(self)
        self.revenue = resources.Revenue(self)
        self.pricing_plans = resources.PricingPlans(self)
        self.customer_plans = resources.CustomerPlans(self)
        self.economics = resources.Economics(self)
        self.transactions = resources.Transactions(self)
        self.delivery_costs = resources.Delivery(self)
        self.reports = resources.Reports(self)
        self.bills = resources.Bills(self)
        self.budgets = resources.Budgets(self)
        self.workspaces = resources.Workspaces(self)
        self.audit = resources.Audit(self)
        self.account = resources.Account(self)
        self.executions = resources.Executions(self)
        self.value = resources.Value(self)
        self.margin_review = resources.MarginReview(self)
        self.spend_close = resources.SpendClose(self)

    def request(self, method: str, path: str, *, payload: Mapping[str, Any] | None = None,
                params: Mapping[str, Any] | None = None, raw: bool = False) -> Any:
        if not path.startswith('/v1/') or '?' in path or '#' in path:
            raise ValueError('Use a /v1/ API path and pass query fields through params')
        query = dict(params or {})
        if self.workspace_id is not None:
            query.setdefault('workspace_id', self.workspace_id)
        query = {k: (v.isoformat() if isinstance(v, (date, datetime)) else v)
                 for k, v in query.items() if v is not None}
        token = self._credential() if callable(self._credential) else self._credential
        if not token or not token.strip():
            raise ValueError('Credential must not be empty')
        url = self.endpoint + path + ('?' + urlencode(query, doseq=True) if query else '')
        body = None if payload is None else json.dumps(payload, default=encode, allow_nan=False).encode()
        request = Request(url, data=body, method=method, headers={
            'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json',
            'User-Agent': 'ganivra-python/0.6.1',
        })
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                data = response.read()
        except HTTPError as error:
            detail = error.read().decode('utf-8', errors='replace')
            raise APIError(f'Ganivra request rejected ({error.code})', status_code=error.code, body=detail, headers=error.headers) from error
        except Exception as error:
            raise APIError('Ganivra request could not be confirmed; check before retrying non-idempotent writes') from error
        if raw:
            return data
        if not data:
            return None
        try:
            return json.loads(data)
        except (ValueError, UnicodeDecodeError) as error:
            raise APIError('Ganivra returned an invalid JSON response') from error
