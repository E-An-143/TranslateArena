"""Parallel translations, independent retries and one multi-dimensional review."""
import asyncio
import logging
import time
from typing import Callable

from arena.agents.judge_agent import JudgeAgent
from arena.agents.translator_agent import TranslatorAgent
from arena.models import TranslationRecord
from arena.providers.base_provider import ProviderError


class TranslationOrchestrator:
    def __init__(self, provider, emit: Callable[[dict], None]):
        self.provider = provider
        self.emit = emit
        self._started = 0.0
        self._previous_elapsed = 0.0
        self._tracking = hasattr(provider, "on_request")
        self._keys = {}
        self._retry_keys = {}
        self._accept_retries = True
        self._candidate_tasks = {}
        self._judge_task = None
        self._pending_retries = set()
        self._retry_event = asyncio.Event()

    def request_retry(self, agent_id, *, key=None):
        """Called on the network loop; a click replaces only this agent's task."""
        if not self._accept_retries or agent_id not in ("A", "B", "C"):
            return False
        if key is not None:
            self._retry_keys[agent_id] = key
        self._pending_retries.add(agent_id)
        self._retry_event.set()
        return True

    @staticmethod
    def _clear_judgement(record):
        record.error, record.judge, record.final = "", {}, ""
        record.judge_reasoning, record.judge_preview, record.judge_attempt = "", "", 0
        record.judge_usage, record.judge_latency = {}, 0

    async def _apply_retries(self, record):
        requested = self._pending_retries
        self._pending_retries = set()
        self._retry_event.clear()
        self._clear_judgement(record)
        record.stage = "translating"
        previous = [self._candidate_tasks.pop(agent_id) for agent_id in requested
                    if agent_id in self._candidate_tasks]
        for task in previous:
            task.cancel()
        if previous:
            # Close old streams before a replacement can publish into the same candidate.
            await asyncio.gather(*previous, return_exceptions=True)
        for config in record.agents:
            if config.id in requested:
                self._keys[config.id] = self._retry_keys.pop(config.id, self._keys.get(config.id, ""))
                self._candidate_tasks[config.id] = asyncio.create_task(
                    self._translate(record, config, self._keys.get(config.id, "")))
        self.publish(record)

    async def _wait_candidates(self, record):
        while True:
            if self._pending_retries:
                await self._apply_retries(record)
            completed = [agent_id for agent_id, task in self._candidate_tasks.items() if task.done()]
            if completed:
                await asyncio.gather(*(self._candidate_tasks.pop(agent_id) for agent_id in completed),
                                     return_exceptions=True)
            if not self._candidate_tasks:
                if self._pending_retries:
                    continue
                return
            wake = asyncio.create_task(self._retry_event.wait())
            try:
                await asyncio.wait([*self._candidate_tasks.values(), wake], return_when=asyncio.FIRST_COMPLETED)
            finally:
                wake.cancel()
                await asyncio.gather(wake, return_exceptions=True)

    async def _judge_current_candidates(self, record, judge_key):
        while True:
            if self._pending_retries:
                await self._wait_candidates(record)
            self._judge_task = asyncio.create_task(self._judge(record, judge_key))
            wake = asyncio.create_task(self._retry_event.wait())
            try:
                await asyncio.wait([self._judge_task, wake], return_when=asyncio.FIRST_COMPLETED)
            finally:
                wake.cancel()
                await asyncio.gather(wake, return_exceptions=True)
            if self._pending_retries:
                self._judge_task.cancel()
                await asyncio.gather(self._judge_task, return_exceptions=True)
                self._judge_task = None
                self._clear_judgement(record)
                continue
            await self._judge_task
            self._judge_task = None
            return

    async def _cancel_tasks(self):
        tasks = [*self._candidate_tasks.values()]
        if self._judge_task is not None:
            tasks.append(self._judge_task)
        for task in tasks:
            task.cancel()
        if tasks:
            cleanup = asyncio.gather(*tasks, return_exceptions=True)
            while not cleanup.done():
                try:
                    await asyncio.shield(cleanup)
                except asyncio.CancelledError:
                    pass  # Repeated Cancel clicks must not interrupt stream cleanup.
        self._candidate_tasks.clear()
        self._judge_task = None

    def publish(self, record):
        record.elapsed = self._previous_elapsed + time.monotonic() - self._started
        self.emit(record.to_dict())

    def count_request(self, record):
        record.call_count += 1
        self.publish(record)

    def _stream_updates(self, record, candidate):
        last_publish = 0.0

        def update(delta):
            nonlocal last_publish
            candidate.reasoning += delta.reasoning
            candidate.preview += delta.text
            now = time.monotonic()
            if now - last_publish >= 0.08:
                self.publish(record)
                last_publish = now
        return update

    async def _translate(self, record, config, key):
        candidate = record.candidates[config.id]
        candidate.status, candidate.error = "running", ""
        candidate.text, candidate.reasoning, candidate.preview = "", "", ""
        candidate.usage = {}
        self.publish(record)
        try:
            response = await TranslatorAgent(self.provider, config, key).translate(
                record, self._stream_updates(record, candidate))
            candidate.text, candidate.usage = response.text, response.usage
            candidate.preview, candidate.reasoning = response.text, response.reasoning
            candidate.status = "success"
            if not self._tracking:
                record.call_count += response.requests
        except asyncio.CancelledError:
            candidate.status = "cancelled"
            raise
        except ProviderError as exc:
            candidate.status, candidate.error = "error", str(exc)
            if not self._tracking:
                record.call_count += exc.requests
        except Exception:
            candidate.status, candidate.error = "error", "此路翻译遇到问题，可单独重试。"
            if not self._tracking:
                record.call_count += 1
        finally:
            self.publish(record)

    async def _judge(self, record, judge_key):
        candidates = {k: c.text for k, c in record.candidates.items() if c.text.strip()}
        if not candidates:
            record.stage, record.error = "error", "暂时没有可用译文。请检查 API 设置后重试。"
            return
        record.stage = "judging"
        self.publish(record)
        last_publish = 0.0

        def start_attempt(attempt):
            nonlocal last_publish
            record.judge_attempt = attempt
            record.judge_reasoning, record.judge_preview = "", ""
            last_publish = 0.0
            self.publish(record)

        def update(delta):
            nonlocal last_publish
            record.judge_reasoning += delta.reasoning
            record.judge_preview += delta.text
            now = time.monotonic()
            if now - last_publish >= 0.08:
                self.publish(record)
                last_publish = now

        try:
            verdict, response = await JudgeAgent(self.provider, judge_key).judge(
                record, candidates, on_delta=update, on_attempt=start_attempt)
            if not self._tracking:
                record.call_count += response.requests
            if self._pending_retries:
                return  # A new candidate was requested; this verdict is already obsolete.
            record.judge, record.final = verdict, verdict["final_translation"]
            record.judge_reasoning, record.judge_preview = response.reasoning, response.text
            record.judge_usage, record.judge_latency = response.usage, response.latency
            record.stage = "completed"
        except ProviderError as exc:
            record.stage, record.error = "judge_error", str(exc)
            record.judge_usage, record.judge_latency = exc.usage, exc.latency
            if not self._tracking:
                record.call_count += exc.requests
        except Exception:
            record.stage, record.error = "judge_error", "裁决暂时失败，所有译文已保留，可重新生成译文后评审。"

    async def run(self, record: TranslationRecord, keys: dict, judge_key: str,
                  selected_ids=None):
        self._started = time.monotonic()
        self._previous_elapsed = record.elapsed
        self._keys = dict(keys)
        self._accept_retries = True
        if self._tracking:
            self.provider.on_request = lambda: self.count_request(record)
        self._clear_judgement(record)
        self.publish(record)
        try:
            record.stage = "translating"
            self.publish(record)
            configs = [c for c in record.agents if selected_ids is None or c.id in selected_ids]
            self._candidate_tasks = {c.id: asyncio.create_task(self._translate(record, c, keys.get(c.id, "")))
                                     for c in configs}
            await self._wait_candidates(record)
            await self._judge_current_candidates(record, judge_key)
        except asyncio.CancelledError:
            self._accept_retries = False
            record.stage, record.error = "cancelled", "任务已取消，已完成的译文已保留。"
            await self._cancel_tasks()
            for candidate in record.candidates.values():
                if candidate.status in ("queued", "running"):
                    candidate.status = "cancelled"
        finally:
            self._accept_retries = False
            self._pending_retries.clear()
            self._retry_keys.clear()
            if self._tracking:
                self.provider.on_request = None
            self.publish(record)
            logging.getLogger("arena").info("Task finished stage=%s calls=%s elapsed=%.2fs", record.stage, record.call_count, record.elapsed)
        return record
