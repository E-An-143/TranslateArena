"""SQLite with schema migration and explicit non-secret records."""
import json
import sqlite3
from contextlib import closing
from pathlib import Path
from uuid import uuid4

from arena.models import Settings, TranslationRecord


class Database:
    def __init__(self, path: Path):
        self.path = path.resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        try:
            self.connection.execute("PRAGMA journal_mode=WAL")
            self.connection.execute("PRAGMA busy_timeout=5000")
            self._migrate()
        except Exception:
            self.connection.close()
            raise

    def _migrate(self):
        version = self.connection.execute("PRAGMA user_version").fetchone()[0]
        if version > 6:
            raise RuntimeError("数据库来自更新版本，请更新应用。")
        if version < 1:
            with self.connection:
                self.connection.executescript("""
                    CREATE TABLE settings (id INTEGER PRIMARY KEY CHECK(id=1), data TEXT NOT NULL);
                    CREATE TABLE history (id TEXT PRIMARY KEY, created_at TEXT NOT NULL, title TEXT NOT NULL, data TEXT NOT NULL);
                    CREATE INDEX history_date ON history(created_at DESC);
                    PRAGMA user_version=6;
                """)
        elif version in (1, 2, 3, 4, 5):
            backups = self.path.parent / "backups"
            backups.mkdir(exist_ok=True)
            backup = backups / (f"schema-{version}-" + uuid4().hex + ".sqlite3")
            try:
                with closing(sqlite3.connect(backup)) as snapshot:
                    self.connection.backup(snapshot)
            except Exception:
                backup.unlink(missing_ok=True)
                raise
            # Preserve settings and discard history from the previous translation workflow.
            with self.connection:
                self.connection.execute("BEGIN IMMEDIATE")
                for row in self.connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
                    name = row[0]
                    if name not in ("settings", "history") and not name.startswith("sqlite_"):
                        quoted = name.replace('"', '""')
                        self.connection.execute(f'DROP TABLE "{quoted}"')
                row = self.connection.execute("SELECT data FROM settings WHERE id=1").fetchone()
                if row:
                    clean = Settings.from_dict(json.loads(row[0])).to_dict()
                    self.connection.execute("UPDATE settings SET data=? WHERE id=1", (json.dumps(clean, ensure_ascii=False),))
                self.connection.execute("DELETE FROM history")
                self.connection.execute("PRAGMA user_version=6")

    def settings(self):
        row = self.connection.execute("SELECT data FROM settings WHERE id=1").fetchone()
        return Settings.from_dict(json.loads(row[0])) if row else Settings()

    def save_settings(self, settings: Settings):
        with self.connection:
            self.connection.execute("INSERT INTO settings VALUES(1,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data",
                                    (json.dumps(settings.to_dict(), ensure_ascii=False),))

    def save_record(self, record: dict):
        # Construction from the whitelist model excludes any accidental credential fields.
        data = TranslationRecord.from_dict(record).to_dict()
        title = " ".join(data["source"].split())[:36] or "未命名翻译"
        with self.connection:
            self.connection.execute("INSERT INTO history VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET title=excluded.title,data=excluded.data",
                (data["id"], data["created_at"], title, json.dumps(data, ensure_ascii=False)))

    def history(self):
        return [dict(row) for row in self.connection.execute("SELECT id,title FROM history ORDER BY created_at DESC")]

    def record(self, record_id):
        row = self.connection.execute("SELECT data FROM history WHERE id=?", (record_id,)).fetchone()
        return TranslationRecord.from_dict(json.loads(row[0])).to_dict() if row else None

    def delete_records(self, record_ids):
        # One transaction prevents a failed batch from deleting only some records.
        with self.connection:
            return self.connection.executemany("DELETE FROM history WHERE id=?",
                                               ((record_id,) for record_id in record_ids)).rowcount

    def close(self):
        self.connection.close()
