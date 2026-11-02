from __future__ import annotations

import json
import queue
import threading
import time
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from typing import Any
from urllib.request import Request, urlopen

from .config import Config


def _user_agent() -> str:
    try:
        package_version = version("ganivra")
    except PackageNotFoundError:
        package_version = "development"
    return f"ganivra-python/{package_version}"


@dataclass(slots=True)
class SenderStats:
    queued: int = 0
    sent: int = 0
    dropped: int = 0
    failed_batches: int = 0


class BackgroundSender:
    """Bounded, best-effort delivery that never raises on the caller thread."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.queue: queue.Queue[dict[str, Any]] = queue.Queue(config.queue_size)
        self.stats = SenderStats()
        self._stop = threading.Event()
        self._thread = threading.Thread(
            target=self._run, name="ganivra-telemetry", daemon=True
        )
        self._thread.start()

    def enqueue(self, event: dict[str, Any]) -> None:
        try:
            self.queue.put_nowait(event)
            self.stats.queued += 1
        except Exception:
            self.stats.dropped += 1

    def flush(self, timeout: float = 2.0) -> bool:
        deadline = time.monotonic() + max(timeout, 0)
        while self.queue.unfinished_tasks and time.monotonic() < deadline:
            time.sleep(0.005)
        return self.queue.unfinished_tasks == 0

    def shutdown(self, timeout: float = 1.0) -> None:
        self._stop.set()
        self.flush(timeout)
        self._thread.join(timeout=max(timeout, 0))

    def _run(self) -> None:
        while not self._stop.is_set() or not self.queue.empty():
            try:
                first = self.queue.get(timeout=0.1)
            except queue.Empty:
                continue
            batch = [first]
            while len(batch) < self.config.batch_size:
                try:
                    batch.append(self.queue.get_nowait())
                except queue.Empty:
                    break

            delivered = False
            try:
                delivered = self._deliver(batch)
            except Exception:
                delivered = False
            finally:
                for _ in batch:
                    self.queue.task_done()

            if delivered:
                self.stats.sent += len(batch)
            else:
                self.stats.dropped += len(batch)
                self.stats.failed_batches += 1

    def _deliver(self, events: list[dict[str, Any]]) -> bool:
        payload = json.dumps({"events": events}, separators=(",", ":")).encode()
        request = Request(
            self.config.events_url,
            data=payload,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
                "User-Agent": _user_agent(),
            },
        )
        for attempt in range(self.config.max_retries + 1):
            try:
                with urlopen(request, timeout=self.config.timeout_seconds) as response:
                    if 200 <= response.status < 300:
                        return True
            except Exception:
                pass
            if attempt < self.config.max_retries:
                time.sleep(0.1 * (2**attempt))
        return False
