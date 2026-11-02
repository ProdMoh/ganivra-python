from datetime import datetime, timezone
from decimal import Decimal
import inspect
import json
from urllib.error import HTTPError
from io import BytesIO

import pytest
from ganivra import Client, APIError
from ganivra import resources


class Response:
    def __init__(self, body=b'{"accepted":1}'):
        self.body = body
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self): return self.body


def test_event_fields_decimal_timestamp_and_workspace(monkeypatch):
    requests = []
    def send(request, **kwargs):
        requests.append(request)
        return Response()
    monkeypatch.setattr('ganivra.client.urlopen', send)
    c = Client(api_key='secret', workspace_id='workspace')
    payload = dict(event_id='stable', timestamp=datetime(2026, 10, 4, tzinfo=timezone.utc),
                   provider='anthropic', provider_reported_cost_usd=Decimal('0.12345678'),
                   usage_details={'cache_creation_5m_input_tokens': 10}, attributes={'agent_name':'review'})
    assert c.events.create(payload=payload)['accepted'] == 1
    assert json.loads(requests[0].data)['provider_reported_cost_usd'] == '0.12345678'
    assert json.loads(requests[0].data)['timestamp'] == '2026-10-04T00:00:00+00:00'
    assert requests[0].full_url.endswith('/v1/events?workspace_id=workspace')
    assert requests[0].get_header('Authorization') == 'Bearer secret'


def test_auth_refresh_scoping_and_export(monkeypatch):
    requests=[]
    tokens=iter(['first', 'refreshed'])
    def send(request, **kwargs):
        requests.append(request)
        return Response(b'csv,data')
    monkeypatch.setattr('ganivra.client.urlopen', send)
    c=Client(access_token=lambda: next(tokens), workspace_id='default')
    assert c.reports.export(params={'start':'2026-10-01','end':'2026-10-04','format':'csv','workspace_id':'other'}) == b'csv,data'
    c.audit.export()
    assert 'workspace_id=other' in requests[0].full_url
    assert requests[1].get_header('Authorization') == 'Bearer refreshed'


def test_http_error_is_inspectable_and_write_not_retried(monkeypatch):
    calls=[]
    def reject(request, **kwargs):
        calls.append(request)
        raise HTTPError(request.full_url,403,'Forbidden',{},BytesIO(b'{"detail":"owner required"}'))
    monkeypatch.setattr('ganivra.client.urlopen',reject)
    with pytest.raises(APIError) as caught:
        Client(api_key='ingestion').pricing_plans.create(payload={'name':'growth'})
    assert caught.value.status_code == 403
    assert 'owner required' in caught.value.body
    assert len(calls)==1


def test_path_encoding_and_credentials():
    for kwargs in ({}, {'api_key':'a','access_token':'b'}):
        with pytest.raises(ValueError): Client(**kwargs)
    c=Client(api_key='key')
    recorded=[]
    c.request=lambda *args, **kwargs: recorded.append((args,kwargs))
    c.customer_plans.update_dates('a/b',payload={'effective_from':'2026-01-01T00:00:00Z'})
    assert recorded[0][0][1].endswith('/a%2Fb/dates')


@pytest.mark.parametrize('status', [409, 422, 429])
def test_rest_failure_semantics_preserved(monkeypatch, status):
    calls=[]
    def reject(request, **kwargs):
        calls.append(request)
        raise HTTPError(request.full_url,status,'Rejected',{'Retry-After':'12'},BytesIO(b'{"detail":"reason"}'))
    monkeypatch.setattr('ganivra.client.urlopen',reject)
    with pytest.raises(APIError) as caught:
        Client(api_key='key').revenue.import_entries(payload={'entries':[]})
    assert caught.value.status_code == status
    assert caught.value.retry_after == '12'
    assert json.loads(caught.value.body) == {'detail':'reason'}
    assert len(calls)==1


def test_every_named_method_dispatches_its_documented_route():
    """Exercise real methods, not just their documentation labels."""
    client=Client(access_token='user-token')
    captured=[]
    client.request=lambda *args, **kwargs: captured.append((args,kwargs))
    for resource in vars(client).values():
        if not isinstance(resource, resources.Resource): continue
        for name, method in inspect.getmembers(resource, inspect.ismethod):
            doc=method.__doc__ or ''
            if not doc.startswith(('GET /','POST /')): continue
            verb,path=doc.split('. Pass')[0].split(' ',1)
            signature=inspect.signature(method)
            positional=[p for p in signature.parameters.values() if p.kind==p.POSITIONAL_OR_KEYWORD]
            args=['id_safe' for _ in positional]
            import re
            expected=re.sub(r'\{\w+\}', 'id_safe',path)
            kwargs={'params':{'workspace_id':'selected','start':'2026-10-01'}}
            if 'payload' in signature.parameters: kwargs['payload']={'custom_field':'retained'}
            method(*args,**kwargs)
            call,options=captured.pop()
            assert call==(verb,expected)
            assert options['params']==kwargs['params']
            if 'payload' in kwargs:
                expected_payload={'events':[kwargs['payload']]} if isinstance(resource,resources.Delivery) and name=='create' else kwargs['payload']
                assert options['payload']==expected_payload


def test_agent_context_is_first_class_and_inherited():
    from ganivra import trace
    with trace(customer_id='tenant',agent_name='reviewer') as root:
        with trace(execution_id=root.execution_id, workflow='review') as child:
            assert child.attributes()['agent_name']=='reviewer'
            assert child.attributes()['customer_id']=='tenant'
        with trace(execution_id=root.execution_id,agent_name='validator') as child:
            assert child.attributes()['agent_name']=='validator'
