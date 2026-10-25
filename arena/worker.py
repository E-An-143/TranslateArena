"""Qt signals cross the thread boundary; only the UI thread writes SQLite."""
import asyncio
import threading

from PySide6.QtCore import QObject, Signal


class AsyncWorker(QObject):
    recordUpdated = Signal(object)
    finished = Signal(object)
    connectionFinished = Signal(str, bool, str)
    retryDeferred = Signal(str, str)

    def __init__(self):
        super().__init__()
        self.loop = asyncio.new_event_loop()
        self._started = threading.Event()
        self.thread = threading.Thread(target=self._run_loop, daemon=True, name="ArenaNetwork")
        self.active = None
        self._retry_handler = None
        self._record_id = ""
        self._job_token = None
        self._active_job_token = None
        self._cancel_token = None
        self._connection_tasks = {}
        self.thread.start()
        self._started.wait(timeout=3)

    def _run_loop(self):
        asyncio.set_event_loop(self.loop)
        self._started.set()
        self.loop.run_forever()
        pending = asyncio.all_tasks(self.loop)
        for task in pending:
            task.cancel()
        if pending:
            self.loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        self.loop.close()

    def start(self, coroutine, *, retry_handler=None, record_id=""):
        # Register before scheduling so a click immediately after Start is accepted.
        job_token = self._job_token = object()
        self._retry_handler, self._record_id = retry_handler, record_id
        async def execute():
            self.active = asyncio.current_task()
            self._active_job_token = job_token
            if self._cancel_token is job_token:
                self._cancel_token = None
                self.active.cancel()
            try:
                record = await coroutine
                self.finished.emit(record.to_dict())
            finally:
                if self.active is asyncio.current_task():
                    self.active = None
                    self._active_job_token = None
                if self._job_token is job_token:
                    self._retry_handler = None
                    self._record_id = ""
                    self._job_token = None
        asyncio.run_coroutine_threadsafe(execute(), self.loop)

    def regenerate(self, agent_id, record_id, key=None):
        def request():
            if self._record_id == record_id and self._retry_handler is not None:
                if self._retry_handler(agent_id, key=key):
                    return
            # The job may have finished before Qt received its final signal.
            self.retryDeferred.emit(agent_id, record_id)
        self.loop.call_soon_threadsafe(request)

    def cancel(self):
        def cancel_task():
            if self.active and self._active_job_token is self._job_token:
                if not self.active.cancelling():
                    self.active.cancel()
            else:
                self._cancel_token = self._job_token
        self.loop.call_soon_threadsafe(cancel_task)

    def test(self, name, provider, key):
        async def execute():
            try:
                models = await provider.test_connection(key)
                self.connectionFinished.emit(name, True, "已连接 · " + ", ".join(models))
            except Exception as exc:
                from arena.providers.base_provider import ProviderError
                message = str(exc) if isinstance(exc, ProviderError) else "连接测试失败，请检查网络和 API 设置。"
                self.connectionFinished.emit(name, False, message)
            finally:
                self._connection_tasks.pop(name, None)
        if name not in self._connection_tasks:
            self._connection_tasks[name] = asyncio.run_coroutine_threadsafe(execute(), self.loop)

    def shutdown(self):
        if not self.loop.is_closed():
            self.loop.call_soon_threadsafe(self.loop.stop)
            self.thread.join(timeout=3)
