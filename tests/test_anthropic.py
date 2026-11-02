import asyncio
import json
import httpx
import pytest
anthropic = pytest.importorskip('anthropic')
from ganivra import trace
from ganivra.anthropic_instrumentation import instrument_anthropic

MESSAGE = {'id':'msg_test','type':'message','role':'assistant','model':'claude-sonnet-4-6',
           'content':[{'type':'text','text':'private response'}], 'stop_reason':'end_turn','stop_sequence':None,
           'usage':{'input_tokens':100,'output_tokens':12,'cache_read_input_tokens':50,
                    'cache_creation_input_tokens':30,'cache_creation':{'ephemeral_5m_input_tokens':10,'ephemeral_1h_input_tokens':20},
                    'server_tool_use':{'web_search_requests':2,'web_fetch_requests':0}}}
ARGS={'model':'claude-sonnet-4-6','max_tokens':100,'messages':[{'role':'user','content':'private prompt'}]}


def sse(complete=True):
    start={**MESSAGE,'content':[], 'stop_reason':None,'usage':{**MESSAGE['usage'],'output_tokens':0}}
    events=[{'type':'message_start','message':start},
            {'type':'content_block_start','index':0,'content_block':{'type':'text','text':''}},
            {'type':'content_block_delta','index':0,'delta':{'type':'text_delta','text':'hello'}},
            {'type':'content_block_stop','index':0},
            {'type':'message_delta','delta':{'stop_reason':'end_turn','stop_sequence':None},'usage':{'output_tokens':12}}]
    if complete: events.append({'type':'message_stop'})
    return ''.join(f'event: {e["type"]}\ndata: {json.dumps(e)}\n\n' for e in events).encode()


@pytest.fixture
def captured(monkeypatch):
    from anthropic.resources.messages.messages import Messages, AsyncMessages
    for cls in (Messages,AsyncMessages):
        for name in ('create','stream'):
            method=getattr(cls,name)
            monkeypatch.setattr(cls,name,getattr(method,'_ganivra_original',method))
    events=[]
    assert instrument_anthropic(lambda:'test',events.append)
    assert instrument_anthropic(lambda:'test',events.append) # no duplicate wrapping
    return events


def response(request):
    if json.loads(request.content).get('stream'):
        return httpx.Response(200,headers={'content-type':'text/event-stream'},content=sse())
    return httpx.Response(200,json=MESSAGE)


def check(event):
    assert event['provider']=='anthropic'
    assert event['input_tokens']==100
    assert event['output_tokens']==12
    assert event['cached_tokens']==50
    assert event['total_tokens']==192
    assert event['usage_details']['cache_creation_1h_input_tokens']==20
    assert event['usage_details']['web_search_requests']==2
    assert event['status']=='success'
    assert 'usage_incomplete' not in event['usage_details']
    assert 'private' not in json.dumps(event)


def test_sync_create_context_and_native_result(captured):
    with anthropic.Anthropic(api_key='fake',http_client=httpx.Client(transport=httpx.MockTransport(response))) as client:
        with trace(customer_id='tenant',plan_key='growth',agent_name='reviewer') as context:
            message=client.messages.create(**ARGS)
        assert message.content[0].text=='private response'
    assert len(captured)==1
    check(captured[0])
    assert captured[0]['execution_id']==context.execution_id
    assert captured[0]['attributes']['plan_key']=='growth'
    assert captured[0]['attributes']['agent_name']=='reviewer'


@pytest.mark.parametrize('managed',[False,True])
def test_sync_stream_waits_for_completion(captured,managed):
    with anthropic.Anthropic(api_key='fake',http_client=httpx.Client(transport=httpx.MockTransport(response))) as client:
        with trace(customer_id='tenant'):
            stream=client.messages.stream(**ARGS) if managed else client.messages.create(**ARGS,stream=True)
        assert captured==[]
        with stream as active:
            if managed:
                assert ''.join(active.text_stream)=='hello'
                assert active.get_final_message().usage.output_tokens==12
            else: list(active)
    assert len(captured)==1
    check(captured[0])
    assert captured[0]['attributes']['customer_id']=='tenant'


@pytest.mark.parametrize('mode',['create','raw','managed'])
def test_async_create_and_streams(captured,mode):
    async def run():
        async with anthropic.AsyncAnthropic(api_key='fake',http_client=httpx.AsyncClient(transport=httpx.MockTransport(response))) as client:
            if mode=='create':
                assert (await client.messages.create(**ARGS)).content[0].text=='private response'
            else:
                stream=client.messages.stream(**ARGS) if mode=='managed' else await client.messages.create(**ARGS,stream=True)
                assert captured==[]
                async with stream as active:
                    if mode=='managed':
                        assert ''.join([part async for part in active.text_stream])=='hello'
                        assert (await active.get_final_message()).usage.output_tokens==12
                    else: [part async for part in active]
    asyncio.run(run())
    assert len(captured)==1
    check(captured[0])


def test_early_close_and_failure_are_not_free_successes(captured):
    with anthropic.Anthropic(api_key='fake',http_client=httpx.Client(transport=httpx.MockTransport(response))) as client:
        with client.messages.create(**ARGS,stream=True) as stream:
            next(stream)
    assert len(captured)==1
    assert captured[0]['status']=='error'
    assert captured[0]['usage_details']['usage_incomplete']==1
    assert captured[0]['input_tokens']==100


def test_api_error_preserved(captured):
    def rejected(request): return httpx.Response(401,json={'type':'error','error':{'type':'authentication_error','message':'private failure'}})
    with anthropic.Anthropic(api_key='fake',max_retries=0,http_client=httpx.Client(transport=httpx.MockTransport(rejected))) as client:
        with pytest.raises(anthropic.AuthenticationError): client.messages.create(**ARGS)
    assert len(captured)==1
    assert captured[0]['error_type']=='AuthenticationError'
    assert captured[0]['usage_details']['usage_incomplete']==1
    assert 'private failure' not in json.dumps(captured)


def test_telemetry_exception_does_not_change_result(captured, monkeypatch):
    from ganivra.anthropic_instrumentation import Observation
    original=Observation.__init__
    def initialize(self,*args,**kwargs):
        original(self,*args,**kwargs)
        self.enqueue=lambda event: (_ for _ in ()).throw(RuntimeError('telemetry unavailable'))
    monkeypatch.setattr(Observation,'__init__',initialize)
    with anthropic.Anthropic(api_key='fake',http_client=httpx.Client(transport=httpx.MockTransport(response))) as client:
        assert client.messages.create(**ARGS).usage.output_tokens==12


def test_truncated_stream_retains_partial_usage(captured):
    def truncated(request): return httpx.Response(200,headers={'content-type':'text/event-stream'},content=sse(False))
    with anthropic.Anthropic(api_key='fake',http_client=httpx.Client(transport=httpx.MockTransport(truncated))) as client:
        with client.messages.stream(**ARGS) as stream:
            list(stream)
    assert len(captured)==1
    assert captured[0]['error_type']=='StreamIncomplete'
    assert captured[0]['output_tokens']==12
    assert captured[0]['usage_details']['usage_incomplete']==1


def test_async_cancel_preserves_cancelled_error(captured):
    class CancelledBody(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield sse().split(b'event: content_block_start')[0]
            raise asyncio.CancelledError()
    async def run():
        transport=httpx.MockTransport(lambda request:httpx.Response(200,headers={'content-type':'text/event-stream'},stream=CancelledBody()))
        async with anthropic.AsyncAnthropic(api_key='fake',http_client=httpx.AsyncClient(transport=transport)) as client:
            with pytest.raises(asyncio.CancelledError):
                async with client.messages.stream(**ARGS) as stream:
                    async for _ in stream: pass
    asyncio.run(run())
    assert len(captured)==1
    assert captured[0]['error_type']=='CancelledError'
    assert captured[0]['input_tokens']==100


def test_async_requests_do_not_leak_customer_context(captured):
    async def run():
        async with anthropic.AsyncAnthropic(api_key='fake',http_client=httpx.AsyncClient(transport=httpx.MockTransport(response))) as client:
            async def request(customer):
                with trace(customer_id=customer):
                    await client.messages.create(**ARGS)
            await asyncio.gather(request('one'),request('two'))
    asyncio.run(run())
    assert {e['attributes']['customer_id'] for e in captured}=={'one','two'}
    assert len({e['execution_id'] for e in captured})==2
