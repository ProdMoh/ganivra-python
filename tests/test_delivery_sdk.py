import json
from decimal import Decimal
from datetime import datetime, timezone
from ganivra.delivery import DeliveryCosts
from ganivra.config import Config
from ganivra.economics import GanivraAPIError
import pytest


def test_cost_request_preserves_decimal_and_identity(monkeypatch):
    calls=[]
    class Response:
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def read(self): return b'{"accepted":1,"duplicates":0}'
    def send(request,timeout):
        calls.append(request)
        return Response()
    monkeypatch.setattr('ganivra.delivery.urlopen',send)
    costs=DeliveryCosts(lambda:Config(api_key='test',endpoint='https://example.com/v1/events'))
    args=dict(event_id='provider-call',timestamp=datetime(2026,10,2,tzinfo=timezone.utc),provider='voice',category='telephony',source_reference='call',cost_usd=Decimal('0.01234567'))
    assert costs.create(**args)['accepted']==1
    costs.create(**args)
    assert calls[0].full_url=='https://example.com/v1/delivery-costs/events'
    assert calls[0].data==calls[1].data
    assert json.loads(calls[0].data)['events'][0]['cost_usd']=='0.01234567'


def test_cost_errors_are_not_silently_dropped(monkeypatch):
    with pytest.raises(GanivraAPIError):
        DeliveryCosts(lambda:None).create_batch([])
    def fail(*args,**kwargs): raise TimeoutError('timeout')
    monkeypatch.setattr('ganivra.delivery.urlopen',fail)
    with pytest.raises(GanivraAPIError,match='Retry the identical payload'):
        DeliveryCosts(lambda:Config(api_key='test')).create_batch([])
