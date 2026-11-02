"""Explicit, acknowledged delivery-cost recording (not best-effort telemetry)."""
import json
from datetime import datetime
from decimal import Decimal
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from .economics import GanivraAPIError


def _encode(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f'Unsupported value: {type(value).__name__}')


class DeliveryCosts:
    def __init__(self, config_getter):
        self._config_getter = config_getter

    def create(self, *, event_id, timestamp, provider, category, source_reference, **fields):
        """Record a cost or signed correction. Retry with the identical event ID and payload."""
        return self.create_batch([dict(event_id=event_id, timestamp=timestamp, provider=provider,
                                       category=category, source_reference=source_reference, **fields)])

    def create_batch(self, events):
        config = self._config_getter()
        if config is None:
            raise GanivraAPIError('call ganivra.init() before recording delivery costs')
        endpoint = config.endpoint.rstrip('/')
        if endpoint.endswith('/v1/events'):
            endpoint = endpoint[:-len('/v1/events')]
        request = Request(endpoint + '/v1/delivery-costs/events',
                          data=json.dumps({'events': events}, default=_encode).encode(), method='POST',
                          headers={'Authorization': f'Bearer {config.api_key}', 'Content-Type': 'application/json'})
        try:
            with urlopen(request, timeout=config.timeout_seconds) as response:
                return json.loads(response.read())
        except HTTPError as error:
            raise GanivraAPIError(f'Delivery costs rejected ({error.code}): {error.read().decode(errors="replace")}') from error
        except Exception as error:
            raise GanivraAPIError(f'Delivery costs could not be confirmed: {error}. Retry the identical payload.') from error
