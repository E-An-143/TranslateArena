# Build on Windows for Windows. Linux is used only for packaging smoke verification.
import os
import sys
from importlib import metadata
from pathlib import Path

root = Path(SPECPATH)
portable = os.environ.get("ARENA_BUILD_LAYOUT") == "onedir"
is_windows = os.name == "nt"
dependency_licenses = []
for package in ("PySide6", "PySide6_Addons", "PySide6_Essentials", "shiboken6", "httpx", "httpcore", "anyio", "h11", "idna", "certifi", "typing_extensions"):
    dist = metadata.distribution(package)
    for file in dist.files or []:
        if file.name.lower().startswith(("license", "copying", "notice")):
            source = Path(dist.locate_file(file))
            if source.is_file():
                dependency_licenses.append((str(source), "licenses/" + package))
python_license = Path(sys.base_prefix) / "LICENSE.txt"
if python_license.exists():
    dependency_licenses.append((str(python_license), "licenses/Python"))

a = Analysis(
    [str(root / "main.py")],
    pathex=[str(root)],
    binaries=[],
    datas=[(str(root / "arena" / "ui"), "arena/ui"),
           (str(root / "arena" / "resources"), "arena/resources"),
           (str(root / "LICENSE"), "."),
           (str(root / "THIRD_PARTY_NOTICES.md"), ".")] + dependency_licenses,
    hiddenimports=["PySide6.QtNetwork", "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtQuickControls2"],
    hookspath=[str(root / "scripts" / "hooks")],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtWidgets",
              "PySide6.QtCharts", "PySide6.QtDataVisualization", "tkinter"],
    noarchive=False,
)
pyz = PYZ(a.pure)
common = dict(name="TranslateArena", debug=False, bootloader_ignore_signals=False,
              strip=False, upx=False, console=not is_windows,
              icon=str(root / "arena" / "resources" / "icon.ico") if is_windows else None)
if portable:
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, **common)
    coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="TranslateArena")
else:
    exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], **common)
