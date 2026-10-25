"""The Qt-facing application facade. All persistent writes stay on the UI thread."""
from __future__ import annotations

import json
import os
import sqlite3
import time
from dataclasses import asdict
from pathlib import Path

from PySide6.QtCore import QObject, Property, Signal, Slot, QUrl
from PySide6.QtGui import QDesktopServices, QGuiApplication

from arena.config import DEFAULT_TARGET_LANGUAGE, REQUEST_TIMEOUT
from arena.models import AgentConfig, Settings, TranslationRecord
from arena.notifications import notification_text
from arena.providers.deepseek_provider import DeepSeekProvider
from arena.services.security_service import SecurityError, SecurityService
from arena.services.translation_orchestrator import TranslationOrchestrator
from arena.storage.database import Database
from arena.storage.data_directory import DataDirectoryError, relocate_data_directory
from arena.translation_styles import TRANSLATION_STYLES
from arena.worker import AsyncWorker


class Bridge(QObject):
    stateChanged = Signal()
    toast = Signal(str)
    navigate = Signal(str)
    dataDirectoryChanged = Signal(str)

    def __init__(self, data_dir: Path, resources: Path, *, provider_factory=None, location_file=None):
        super().__init__()
        self.data_dir = data_dir.resolve()
        self.location_file = location_file or self.data_dir / "data-location.json"
        self.db = Database(data_dir / "arena.sqlite3")
        self.security = SecurityService(data_dir / "credentials")
        self.worker = AsyncWorker()
        self.provider_factory = provider_factory or DeepSeekProvider
        self.worker.recordUpdated.connect(self._on_update)
        self.worker.finished.connect(self._on_finished)
        self.worker.connectionFinished.connect(self._on_connection)
        self.worker.retryDeferred.connect(self._on_retry_deferred)
        self.settings = self.db.settings()
        self.languages = json.loads((resources / "languages.json").read_text(encoding="utf-8"))
        self.draft_agents = [asdict(a) for a in self.settings.agents]
        self.target_language = DEFAULT_TARGET_LANGUAGE
        self.source = ""
        self.record = {}
        self.busy = False
        self.connections = {}
        self._last_saved_stage = None
        self._last_saved_at = 0.0
        self._closed = False
        self._deferred_retries = set()
        self._refresh()

    def _refresh(self):
        history = self.db.history()
        record = dict(self.record)
        if record:
            record["error"] = notification_text(record.get("error", ""))
            record["candidates"] = {
                key: {**item, "error": notification_text(item.get("error", ""))}
                for key, item in record.get("candidates", {}).items()
            }
        self._state = {
            "settings": self.settings.to_dict(), "agents": self.draft_agents,
            "translationStyles": [{"value": value, "label": label} for value, (label, _) in TRANSLATION_STYLES.items()],
            "languages": self.languages,
            "targetLanguage": self.target_language,
            "source": self.source, "record": record, "busy": self.busy,
            "history": history,
            "credentials": self.security.snapshot(), "connections": self.connections,
            "dataDir": str(self.data_dir), "dataDirUrl": QUrl.fromLocalFile(str(self.data_dir)).toString(),
            "connecting": any(item.get("status") == "running" for item in self.connections.values()),
        }
        self.stateChanged.emit()

    def _notify(self, message):
        self.toast.emit(notification_text(message))

    @Property("QVariantMap", notify=stateChanged)
    def state(self):
        return self._state

    @Slot(str)
    def setSource(self, value):
        if not self.busy:
            self.source = value
            # Keystrokes need not rebuild every history row or write SQLite.
            self._state["source"] = value
            if self.record and value != self.record.get("source"):
                self.record = {}
                self._refresh()

    @Slot(str)
    def setTargetLanguage(self, code):
        if self.busy or code not in {l["code"] for l in self.languages}:
            return
        self.target_language = code
        if self.record and code != self.record.get("target_language"):
            self.record = {}
        self._refresh()

    @Slot(str, str, str)
    def setAgent(self, agent_id, field, encoded):
        if self.busy:
            return
        try:
            for index, current in enumerate(self.draft_agents):
                if current["id"] == agent_id:
                    data = dict(current)
                    if field == "id" or field not in current:
                        return
                    data[field] = json.loads(encoded)
                    self.draft_agents[index] = asdict(AgentConfig.from_dict(data))
                    break
            # Defaults are updated explicitly from the current working configuration.
            self.settings.agents = [AgentConfig.from_dict(a) for a in self.draft_agents]
            self.db.save_settings(self.settings)
            self._refresh()
        except (ValueError, TypeError):
            self._notify("设置值无效。")

    @Slot(str, str)
    def setSetting(self, name, encoded):
        if name != "appearance":
            return
        try:
            data = self.settings.to_dict()
            data[name] = json.loads(encoded)
            self.settings = Settings.from_dict(data)
            self.db.save_settings(self.settings)
            self._refresh()
        except (ValueError, TypeError):
            self._notify("设置值无效。")

    @Slot(str, str)
    def saveKey(self, name, value):
        if self.busy:
            return
        try:
            self.security.set(name, value)
            self.connections.pop(name, None)
            self._refresh()
            self._notify("Key 已加密保存。" if self.security.persistent else "Key 仅保留在当前开发会话。")
        except SecurityError as exc:
            self._notify(str(exc))
        except OSError:
            self._notify("无法保存凭据，请检查输入与数据目录权限。")

    @Slot(str)
    def deleteKey(self, name):
        if not self.busy:
            try:
                self.security.delete(name)
                self.connections.pop(name, None)
                self._refresh()
                self._notify("凭据已删除。")
            except (SecurityError, OSError):
                self._notify("无法删除凭据。")

    @Slot(str)
    def testConnection(self, name):
        try:
            key = self.security.get(name)
            if not key:
                self._notify("请先输入并保存此 Key。")
                return
            if self.connections.get(name, {}).get("status") == "running":
                return
            self.connections[name] = {"status": "running", "message": "正在连接…"}
            self._refresh()
            self.worker.test(name, self.provider_factory(REQUEST_TIMEOUT), key)
        except SecurityError as exc:
            self._notify(str(exc))

    @Slot(str, bool, str)
    def _on_connection(self, name, ok, message):
        if self._closed:
            return
        self.connections[name] = {"status": "success" if ok else "error", "message": notification_text(message)}
        self._refresh()

    def _keys(self, names=("A", "B", "C", "Judge")):
        return {name: self.security.get(name) for name in names}

    def _launch(self, record, selected=None):
        if self.busy:
            return
        needed = selected or ("A", "B", "C")
        try:
            keys = self._keys(needed)
            judge_key = self.security.get("Judge")
        except SecurityError as exc:
            self._notify(str(exc))
            self.navigate.emit("settings")
            return
        if not any(keys[i] for i in needed):
            self._notify("请在设置中配置 DeepSeek API Key。")
            self.navigate.emit("settings")
            return
        if not judge_key:
            self._notify("请先配置 Judge 的独立 API Key。")
            self.navigate.emit("settings")
            return
        self.busy = True
        self._last_saved_stage = None
        provider = self.provider_factory(REQUEST_TIMEOUT)
        orchestrator = TranslationOrchestrator(provider, self.worker.recordUpdated.emit)
        self.record = record.to_dict()
        self._refresh()
        self.worker.start(orchestrator.run(record, keys, judge_key, selected_ids=selected),
                          retry_handler=orchestrator.request_retry, record_id=record.id)

    @Slot()
    def translate(self):
        if self.busy:
            self._deferred_retries.clear()
            self.worker.cancel()
            return
        if not self.source.strip():
            self._notify("先输入需要翻译的原文。")
            return
        if len(self.source) > 100000:
            self._notify("原文过长，请拆分为较短的段落")
            return
        record = TranslationRecord(self.source, self.target_language,
            [AgentConfig.from_dict(a) for a in self.draft_agents])
        self._launch(record)

    @Slot(str)
    def regenerate(self, agent_id):
        if not self.record or agent_id not in ("A", "B", "C"):
            return
        if self.busy:
            try:
                key = self.security.get(agent_id)
            except SecurityError as exc:
                self._notify(str(exc))
                return
            if not key:
                self._notify("请先配置 Agent " + agent_id + " 的 API Key")
                return
            self.worker.regenerate(agent_id, self.record["id"], key)
            return
        record = TranslationRecord.from_dict(self.record)
        index = ("A", "B", "C").index(agent_id)
        record.agents[index] = AgentConfig.from_dict(self.draft_agents[index])
        self._launch(record, [agent_id])

    @Slot(str, str)
    def _on_retry_deferred(self, agent_id, record_id):
        if self._closed or self.record.get("id") != record_id:
            return
        if self.busy:
            self._deferred_retries.add(agent_id)
        else:
            self.regenerate(agent_id)

    @Slot()
    def cancel(self):
        if self.busy:
            self._deferred_retries.clear()
            self.worker.cancel()

    @Slot(object)
    def _on_update(self, record):
        if self._closed:
            return
        self.record = record
        # Coalesce token updates while saving every stage/status boundary immediately.
        signature = (record.get("stage"), tuple((key, item.get("status"))
                     for key, item in record.get("candidates", {}).items()))
        now = time.monotonic()
        if signature != self._last_saved_stage or now - self._last_saved_at >= 0.5:
            self.db.save_record(record)
            self._last_saved_stage, self._last_saved_at = signature, now
        self._refresh()

    @Slot(object)
    def _on_finished(self, record):
        if self._closed:
            return
        self.record, self.busy = record, False
        self.db.save_record(record)
        self._refresh()
        deferred, self._deferred_retries = self._deferred_retries, set()
        if deferred and record["stage"] != "cancelled":
            next_record = TranslationRecord.from_dict(record)
            for index, config in enumerate(next_record.agents):
                if config.id in deferred:
                    next_record.agents[index] = AgentConfig.from_dict(self.draft_agents[index])
            self._launch(next_record, selected=list(deferred))

    @Slot()
    def newTranslation(self):
        if self.busy:
            self._notify("请先取消当前翻译。")
            return
        self.source, self.record = "", {}
        self.target_language = DEFAULT_TARGET_LANGUAGE
        self.draft_agents = [asdict(a) for a in self.settings.agents]
        self._refresh()
        self.navigate.emit("arena")

    @Slot(str)
    def restoreHistory(self, record_id):
        if self.busy:
            self._notify("请先取消当前翻译。")
            return
        value = self.db.record(record_id)
        if value:
            self.record = value
            self.source = value["source"]
            self.target_language = value["target_language"]
            self.draft_agents = value["agents"]
            if value["stage"] in ("translating", "judging", "ready"):
                self.record["stage"] = "interrupted"
                self.record["error"] = "上次任务中断，已恢复当时结果。可以重新翻译或单独重试。"
                for c in self.record["candidates"].values():
                    if c["status"] in ("running", "queued"):
                        c["status"] = "cancelled"
            self._refresh()
            self.navigate.emit("arena")

    @Slot("QVariantList", result=bool)
    def deleteHistoryBatch(self, record_ids):
        if self.busy:
            return False
        ids = list(dict.fromkeys(value for value in record_ids if isinstance(value, str) and value))
        if not ids:
            return False
        try:
            self.db.delete_records(ids)
        except (sqlite3.Error, OSError):
            self._notify("无法删除翻译记录，请稍后重试。")
            return False
        if self.record.get("id") in ids:
            self.record = {}
        self._refresh()
        return True

    @Slot(str)
    def copyText(self, value):
        QGuiApplication.clipboard().setText(value)
        self._notify("已复制。")

    @Slot()
    def openDataDirectory(self):
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.data_dir))):
            self._notify("无法打开文件夹，请检查该目录是否可访问。")

    @Slot(str)
    def setDataDirectory(self, value):
        if self.busy or any(item.get("status") == "running" for item in self.connections.values()):
            self._notify("请等待当前任务完成，再修改数据位置。")
            return
        value = value.strip()
        url = QUrl(value)
        target = Path(url.toLocalFile() if url.isLocalFile() else value).expanduser()
        if not value or not target.is_absolute():
            self._notify("请输入文件夹的完整路径。")
            return
        if target.resolve() == self.data_dir:
            return
        try:
            replacement = relocate_data_directory(self.db, self.data_dir, target, self.location_file)
        except DataDirectoryError as exc:
            self._notify(str(exc))
            return
        except (OSError, ValueError, sqlite3.Error):
            self._notify("无法修改数据位置，现有数据未改变。请检查文件夹权限。")
            return
        previous = self.db
        self.db, self.data_dir = replacement, target.resolve()
        self.security.directory = self.data_dir / "credentials"
        self.security.directory.mkdir(exist_ok=True)
        previous.close()
        self.dataDirectoryChanged.emit(str(self.data_dir))
        self._refresh()
        self._notify("数据位置已更新。")

    def close(self):
        if self._closed:
            return
        self._closed = True
        self.worker.shutdown()
        if self.busy and self.record:
            self.record["stage"] = "interrupted"
            self.db.save_record(self.record)
        self.db.close()
