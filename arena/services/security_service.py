"""User-scoped Windows DPAPI. No insecure fallback persistence."""
import ctypes
import os
from ctypes import wintypes
from pathlib import Path

VALID_NAMES = ("A", "B", "C", "Judge")


class SecurityError(Exception):
    pass


class DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]


def _blob(data: bytes):
    buffer = ctypes.create_string_buffer(data, len(data))
    return DATA_BLOB(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte))), buffer


def _dpapi(data: bytes, protect: bool) -> bytes:
    if os.name != "nt":
        raise SecurityError("只有 Windows 可持久保存 Key；当前开发会话中的 Key 不会写入磁盘。")
    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p
    incoming, buffer = _blob(data)
    entropy, entropy_buffer = _blob(b"TranslateArena.credentials.v1")
    outgoing = DATA_BLOB()
    if protect:
        func = crypt32.CryptProtectData
        func.argtypes = [ctypes.POINTER(DATA_BLOB), wintypes.LPCWSTR, ctypes.POINTER(DATA_BLOB),
                         ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(DATA_BLOB)]
        description = "Translate Arena API Credential"
    else:
        func = crypt32.CryptUnprotectData
        func.argtypes = [ctypes.POINTER(DATA_BLOB), ctypes.c_void_p, ctypes.POINTER(DATA_BLOB),
                         ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(DATA_BLOB)]
        description = None
    func.restype = wintypes.BOOL
    # CRYPTPROTECT_UI_FORBIDDEN, and deliberately no LOCAL_MACHINE flag.
    if not func(ctypes.byref(incoming), description, ctypes.byref(entropy), None, None, 1, ctypes.byref(outgoing)):
        raise SecurityError("无法访问 Windows 加密凭据，请重新输入 Key。")
    try:
        return ctypes.string_at(outgoing.pbData, outgoing.cbData)
    finally:
        kernel32.LocalFree(outgoing.pbData)


class SecurityService:
    def __init__(self, directory: Path):
        self.directory = directory
        directory.mkdir(parents=True, exist_ok=True)
        self._session = {}

    def _path(self, name):
        if name not in VALID_NAMES:
            raise SecurityError("无效的凭据名称")
        return self.directory / (name + ".dpapi")

    def set(self, name: str, key: str):
        path = self._path(name)
        if name in self._session or path.exists():
            raise SecurityError("已保存的 API Key 不能直接替换，请先清空。")
        key = key.strip()
        if not key:
            raise SecurityError("请输入 API Key。")
        if any(c.isspace() for c in key) or len(key) > 512:
            raise SecurityError("API Key 格式无效，请检查是否粘贴了空格或其他内容。")
        if os.name == "nt":
            encrypted = _dpapi(key.encode("utf-8"), True)
            temporary = path.with_suffix(".tmp")
            temporary.write_bytes(encrypted)
            temporary.replace(path)
        self._session[name] = key

    def get(self, name: str) -> str:
        path = self._path(name)
        if name in self._session:
            return self._session[name]
        if os.name == "nt" and path.exists():
            key = _dpapi(path.read_bytes(), False).decode("utf-8")
            self._session[name] = key
            return key
        return ""

    def delete(self, name):
        path = self._path(name)
        path.unlink(missing_ok=True)
        self._session.pop(name, None)

    def masked(self, name):
        try:
            key = self.get(name)
            return "•" * len(key) if key else "未配置"
        except SecurityError:
            return "需要重新配置"

    def snapshot(self):
        result = {}
        for name in VALID_NAMES:
            mask = self.masked(name)
            result[name] = {"configured": mask not in ("未配置", "需要重新配置"), "mask": mask}
        return result

    @property
    def persistent(self):
        return os.name == "nt"
