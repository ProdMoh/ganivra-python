from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from typing import Any, Callable, Literal, Mapping
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from .config import Config

TransactionType = Literal[
    "purchase",
    "credit_purchase",
    "subscription_payment",
    "one_time_purchase",
    "refund",
]


class GanivraAPIError(RuntimeError):
    """Raised when Ganivra rejects or cannot record financial activity."""


def _json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"{type(value).__name__} is not JSON serializable")


class Transactions:
    def __init__(self, config_getter: Callable[[], Config | None]) -> None:
        self._config_getter = config_getter

    def create(
        self,
        *,
        external_id: str,
        customer_id: str,
        amount: Decimal | float | int,
        currency: str = "USD",
        transaction_type: TransactionType = "purchase",
        amount_usd: Decimal | float | int | None = None,
        exchange_rate_to_usd: Decimal | float | int | None = None,
        execution_id: str | None = None,
        plan_key: str | None = None,
        units_purchased: Decimal | float | int | None = None,
        source: str = "api",
        occurred_at: datetime | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Record a provider-confirmed purchase, renewal, or refund."""

        config = self._config_getter()
        if config is None:
            raise GanivraAPIError("call ganivra.init() before recording a transaction")
        payload = {
            key: value
            for key, value in {
                "external_id": external_id,
                "customer_id": customer_id,
                "transaction_type": transaction_type,
                "amount": amount,
                "currency": currency.upper(),
                "amount_usd": amount_usd,
                "exchange_rate_to_usd": exchange_rate_to_usd,
                "execution_id": execution_id,
                "plan_key": plan_key,
                "units_purchased": units_purchased,
                "source": source,
                "occurred_at": occurred_at,
                "metadata": dict(metadata or {}),
            }.items()
            if value is not None
        }
        body = json.dumps(payload, default=_json_value, separators=(",", ":")).encode()
        request = Request(
            config.transactions_url,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "ganivra-python",
            },
        )
        try:
            with urlopen(request, timeout=config.timeout_seconds) as response:
                response_body = response.read()
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise GanivraAPIError(f"Ganivra transaction failed with status {error.code}: {detail}") from error
        except Exception as error:
            raise GanivraAPIError(f"Ganivra transaction could not be recorded: {error}") from error
        try:
            return json.loads(response_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise GanivraAPIError("Ganivra returned an invalid transaction response") from error
