"""Optional first-party Claude Messages instrumentation; never captures content."""
import functools
import importlib
import time
from datetime import datetime, timezone
from .context import current_trace, new_id
from .instrumentation import _value, detect_platform


def usage_fields(usage):
    """Read only billing quantities. Stream updates are cumulative, not additive."""
    result = {}
    for key in ('input_tokens', 'output_tokens', 'cache_read_input_tokens', 'cache_creation_input_tokens'):
        value = _value(usage, key)
        if value is not None:
            result[key] = int(value)
    cache = _value(usage, 'cache_creation')
    for ttl in ('5m', '1h'):
        value = _value(cache, f'ephemeral_{ttl}_input_tokens')
        if value is not None:
            result[f'cache_creation_{ttl}_input_tokens'] = int(value)
    tools = _value(usage, 'server_tool_use')
    for key in ('web_search_requests', 'web_fetch_requests'):
        value = _value(tools, key)
        if value is not None:
            result[key] = int(value)
    if _value(usage, 'service_tier') == 'priority':
        result['priority_tier'] = 1
    if _value(usage, 'service_tier') == 'batch':
        result['batch'] = 1
    if _value(usage, 'inference_geo') == 'us':
        result['inference_geo_us'] = 1
    return result


class Observation:
    def __init__(self, model, environment, enqueue, platform=None):
        self.platform = platform
        self.trace = current_trace()
        self.model = model or 'unknown'
        self.environment = environment
        self.enqueue = enqueue
        self.started = time.perf_counter()
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.usage = {}
        self.done = False
        self.final_usage = False

    def message(self, message):
        try:
            self.model = _value(message, 'model') or self.model
            self.usage.update(usage_fields(_value(message, 'usage')))
        except Exception:
            pass

    def chunk(self, chunk):
        try:
            kind = _value(chunk, 'type')
            if kind == 'message_start':
                self.message(_value(chunk, 'message'))
            elif kind == 'message_delta':
                usage = usage_fields(_value(chunk, 'usage'))
                self.usage.update(usage)
                self.final_usage = self.final_usage or 'output_tokens' in usage
            elif kind == 'message_stop':
                self.finish(complete=self.final_usage)
        except Exception:
            pass

    def finish(self, error=None, *, complete=False):
        if self.done:
            return
        self.done = True
        try:
            u = self.usage
            known = complete and 'input_tokens' in u and 'output_tokens' in u
            details = {k: v for k, v in u.items() if k not in ('input_tokens', 'output_tokens', 'cache_read_input_tokens')}
            if not known:
                details['usage_incomplete'] = 1
            writes = (u.get('cache_creation_5m_input_tokens', 0) + u.get('cache_creation_1h_input_tokens', 0)) or u.get('cache_creation_input_tokens', 0)
            trace = self.trace
            event = {
                'event_id': new_id('evt'), 'execution_id': trace.execution_id if trace else new_id('exec'),
                'step_id': new_id('step'), 'timestamp': self.timestamp,
                'provider': 'anthropic', 'model': self.model, 'operation': 'messages.create',
                'input_tokens': u.get('input_tokens', 0), 'output_tokens': u.get('output_tokens', 0),
                'cached_tokens': u.get('cache_read_input_tokens', 0),
                'total_tokens': u.get('input_tokens', 0) + u.get('output_tokens', 0) + u.get('cache_read_input_tokens', 0) + writes,
                'usage_details': details, 'environment': self.environment,
                'latency_ms': round((time.perf_counter() - self.started) * 1000, 3),
                'status': 'error' if error else 'success', 'error_type': error,
                'attributes': trace.attributes() if trace else {},
            }
            if trace and trace.parent_step_id:
                event['parent_step_id'] = trace.parent_step_id
            if self.platform:
                event['platform'] = self.platform
            self.enqueue(event)
        except Exception:
            pass


class Stream:
    def __init__(self, raw, observation):
        self.raw, self.observation = raw, observation
        self.iterator = iter(raw)
    def __getattr__(self, name): return getattr(self.raw, name)
    def __iter__(self): return self
    def __next__(self):
        try:
            item = next(self.iterator)
        except StopIteration:
            self.observation.finish('StreamIncomplete')
            raise
        except BaseException as error:
            self.observation.finish(type(error).__name__)
            raise
        self.observation.chunk(item)
        return item
    def close(self):
        try: return self.raw.close()
        finally: self.observation.finish('StreamClosed')
    def __enter__(self): return self
    def __exit__(self, *args): self.close()


class AsyncStream:
    def __init__(self, raw, observation):
        self.raw, self.observation = raw, observation
        self.iterator = raw.__aiter__()
    def __getattr__(self, name): return getattr(self.raw, name)
    def __aiter__(self): return self
    async def __anext__(self):
        try:
            item = await self.iterator.__anext__()
        except StopAsyncIteration:
            self.observation.finish('StreamIncomplete')
            raise
        except BaseException as error:
            self.observation.finish(type(error).__name__)
            raise
        self.observation.chunk(item)
        return item
    async def close(self):
        try: return await self.raw.close()
        finally: self.observation.finish('StreamClosed')
    async def __aenter__(self): return self
    async def __aexit__(self, *args): await self.close()


class Manager:
    def __init__(self, manager, observation):
        self.manager, self.observation = manager, observation
    def __enter__(self):
        try:
            stream = self.manager.__enter__()
        except BaseException as error:
            self.observation.finish(type(error).__name__)
            raise
        # Keep the native MessageStream: text_stream/get_final_message still work.
        try: stream._raw_stream = Stream(stream._raw_stream, self.observation)
        except Exception: pass
        return stream
    def __exit__(self, *args):
        try: return self.manager.__exit__(*args)
        finally: self.observation.finish('StreamClosed')


class AsyncManager:
    def __init__(self, manager, observation):
        self.manager, self.observation = manager, observation
    async def __aenter__(self):
        try:
            stream = await self.manager.__aenter__()
        except BaseException as error:
            self.observation.finish(type(error).__name__)
            raise
        try: stream._raw_stream = AsyncStream(stream._raw_stream, self.observation)
        except Exception: pass
        return stream
    async def __aexit__(self, *args):
        try: return await self.manager.__aexit__(*args)
        finally: self.observation.finish('StreamClosed')


def _patch(cls, name, async_call, environment, enqueue):
    original = getattr(cls, name, None)
    if original is None or getattr(original, '_ganivra_instrumented', False): return
    if async_call and name == 'create':
        @functools.wraps(original)
        async def wrapped(self, *args, **kwargs):
            observation = Observation(kwargs.get('model'), environment(), enqueue, detect_platform(self))
            try: result = await original(self, *args, **kwargs)
            except BaseException as error:
                observation.finish(type(error).__name__)
                raise
            if kwargs.get('stream'):
                return AsyncStream(result, observation)
            observation.message(result)
            observation.finish(complete=True)
            return result
    else:
        @functools.wraps(original)
        def wrapped(self, *args, **kwargs):
            observation = Observation(kwargs.get('model'), environment(), enqueue, detect_platform(self))
            try: result = original(self, *args, **kwargs)
            except BaseException as error:
                observation.finish(type(error).__name__)
                raise
            if name == 'stream':
                return (AsyncManager if async_call else Manager)(result, observation)
            if kwargs.get('stream'):
                return Stream(result, observation)
            observation.message(result)
            observation.finish(complete=True)
            return result
    wrapped._ganivra_instrumented = True
    wrapped._ganivra_original = original
    setattr(cls, name, wrapped)


def instrument_anthropic(environment, enqueue):
    try:
        module = importlib.import_module('anthropic.resources.messages.messages')
    except ImportError:
        return False
    for name, async_call in [('Messages', False), ('AsyncMessages', True)]:
        cls = getattr(module, name)
        for method in ('create', 'stream'):
            _patch(cls, method, async_call, environment, enqueue)
    return True
