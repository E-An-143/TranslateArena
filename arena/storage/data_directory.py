"""Consistent data relocation with no overwrites and an atomic startup pointer."""
import json
import os
import shutil
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path

from arena.storage.database import Database


class DataDirectoryError(Exception):
    pass


def resolve_data_directory(default: Path, location_file: Path) -> Path:
    if not location_file.exists():
        return default.resolve()
    try:
        value = json.loads(location_file.read_text(encoding="utf-8"))["data_dir"]
        path = Path(value).expanduser()
        if not path.is_absolute() or not path.is_dir():
            raise ValueError("Unavailable directory")
        return path.resolve()
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise DataDirectoryError("无法访问已保存的数据目录，请检查该文件夹是否存在。") from exc


def _write_location(location_file: Path, target: Path):
    location_file.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=".arena-location-", dir=location_file.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump({"data_dir": str(target)}, stream, ensure_ascii=False)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(location_file)
    finally:
        temporary.unlink(missing_ok=True)


def relocate_data_directory(database: Database, current: Path, target: Path, location_file: Path) -> Database:
    current, target = current.resolve(), target.resolve()
    if target == current or target.is_relative_to(current):
        raise DataDirectoryError("请选择当前数据目录以外的文件夹。")
    target.mkdir(parents=True, exist_ok=True)
    managed_names = ("arena.sqlite3", "arena.sqlite3-wal", "arena.sqlite3-shm", "credentials", "logs", "backups")
    if any((target / name).exists() or (target / name).is_symlink() for name in managed_names):
        raise DataDirectoryError("该文件夹已有应用数据，请选择其他文件夹，避免覆盖。")
    created = []
    replacement = None
    try:
        with tempfile.TemporaryDirectory(prefix=".arena-copy-", dir=target) as temporary:
            staging = Path(temporary)
            # SQLite backup includes committed changes still present in the WAL.
            with closing(sqlite3.connect(staging / "arena.sqlite3")) as snapshot:
                database.connection.backup(snapshot)
            for name in ("credentials", "logs", "backups"):
                source = current / name
                if source.is_dir():
                    shutil.copytree(source, staging / name, symlinks=True, ignore=shutil.ignore_patterns("*.tmp"))
            for source in sorted(staging.iterdir()):
                destination = target / source.name
                if source.is_dir():
                    destination.mkdir()  # Fail if someone created it during staging.
                    created.append(destination)
                    shutil.copytree(source, destination, dirs_exist_ok=True, symlinks=True)
                else:
                    with destination.open("xb") as output:
                        created.append(destination)
                        with source.open("rb") as incoming:
                            shutil.copyfileobj(incoming, output)
            replacement = Database(target / "arena.sqlite3")
            replacement.settings()
        _write_location(location_file, target)
        return replacement
    except Exception:
        if replacement is not None:
            replacement.close()
        for path in reversed(created):
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink(missing_ok=True)
        if target / "arena.sqlite3" in created:
            for suffix in ("-wal", "-shm"):
                (target / ("arena.sqlite3" + suffix)).unlink(missing_ok=True)
        raise
