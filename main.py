"""Desktop entry point, also used by packaged Windows releases."""
import argparse
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

# ZIP updates may preserve QML timestamps, which can make Qt reuse older UI code.
# Set this before importing Qt so python/pythonw and frozen launches load the source.
os.environ["QML_DISABLE_DISK_CACHE"] = "1"
os.environ.pop("QML_FORCE_DISK_CACHE", None)

# Explicit imports make the required Qt modules discoverable to PyInstaller.
from PySide6 import QtNetwork, QtQml, QtQuick, QtQuickControls2
from PySide6.QtCore import QStandardPaths, Qt, QTimer, QUrl
from PySide6.QtGui import QFont, QFontDatabase, QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterType

from arena.bridge import Bridge
from arena.storage.data_directory import DataDirectoryError, resolve_data_directory
from arena.ui_text import LanguageCaption, TextLineSpacing

qmlRegisterType(LanguageCaption, "TranslateArena.Ui", 1, 0, "LanguageCaption")
qmlRegisterType(TextLineSpacing, "TranslateArena.Ui", 1, 0, "TextLineSpacing")


def resource_root():
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) / "arena"


def install_ui_fonts(app, root):
    """Use MiSans with bundled script fallbacks on every platform."""
    for name in ("MiSans-Regular.ttf", "MiSans-Medium.ttf", "NotoSansKR.ttf", "NotoSansThai.ttf",
                 "NotoSansMyanmar.ttf", "NotoSansLao.ttf"):
        font_id = QFontDatabase.addApplicationFont(str(root / "resources" / "fonts" / name))
        if font_id < 0:
            raise RuntimeError(f"Unable to load bundled UI font: {name}")
    font = QFont("MiSans", 12)
    font.setWeight(QFont.Weight(330))
    app.setFont(font)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, help="Isolated local data directory, for development/testing")
    parser.add_argument("--smoke-test", action="store_true", help="Load the full QML window, then exit")
    parser.add_argument("--screenshot", type=Path)
    parser.add_argument("--preview", choices=("empty", "results", "dark", "review", "settings"))
    parser.add_argument("--width", type=int, default=1440)
    parser.add_argument("--height", type=int, default=980)
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--qa-font", type=Path, help="Optional font for screenshots on Linux")
    parser.add_argument("--scroll-end", action="store_true", help="QA: screenshot candidate and final areas")
    parser.add_argument("--dialog", choices=("analysis","reader","directory"),default="")
    args = parser.parse_args()
    # Software rendering is a supported fallback for older drivers and headless QA.
    if args.smoke_test or args.screenshot:
        os.environ.setdefault("QSG_RHI_BACKEND", "software")
        os.environ.setdefault("QT_QUICK_BACKEND", "software")
    QtQuickControls2.QQuickStyle.setStyle("Basic")
    app = QGuiApplication(sys.argv)
    app.setOrganizationName("TranslateArena")
    app.setApplicationName("TranslateArena")
    app.setApplicationDisplayName("翻译竞技场 · Translate Arena")
    app.setApplicationVersion("1.0.0")
    root = resource_root()
    install_ui_fonts(app, root)
    if args.qa_font:
        QFontDatabase.addApplicationFont(str(args.qa_font))
    app.setWindowIcon(QIcon(str(root / "resources" / "icon.svg")))
    default_data_dir = args.data_dir or Path(QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation))
    location_file = default_data_dir.resolve() / "data-location.json"
    try:
        data_dir = resolve_data_directory(default_data_dir, location_file)
        data_dir.mkdir(parents=True, exist_ok=True)
    except (DataDirectoryError, OSError):
        if os.name == "nt":
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, "无法打开保存的数据目录，请检查文件夹是否存在以及访问权限", "Translate Arena", 0x10)
        return 1
    log_dir = data_dir / "logs"
    log_dir.mkdir(exist_ok=True)
    handler = RotatingFileHandler(log_dir / "app.log", maxBytes=500000, backupCount=2, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logging.getLogger("arena").addHandler(handler)
    logging.getLogger("arena").setLevel(logging.DEBUG if args.debug else logging.INFO)
    # Do not enable httpx/httpcore debug logs or log request bodies/headers.
    logging.getLogger("arena").info("Application started version=1.0.0 ui_root=%s qml_disk_cache=disabled", root / "ui")
    try:
        bridge = Bridge(data_dir, root / "resources", location_file=location_file)
    except Exception:
        logging.getLogger("arena").error("Unable to open application data")
        # For a packaged, windowed binary provide a native error even before QML loads.
        if os.name == "nt":
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, "无法打开应用数据。请检查数据目录权限或升级应用。", "Translate Arena", 0x10)
        return 1
    if args.preview in ("results", "dark", "review"):
        from scripts.preview_data import install_preview
        install_preview(bridge)
    if args.preview == "dark":
        bridge.settings.appearance = "dark"
        bridge._refresh()
    def relocate_log(directory):
        nonlocal handler
        logger = logging.getLogger("arena")
        logger.removeHandler(handler)
        handler.close()
        destination = Path(directory) / "logs"
        destination.mkdir(exist_ok=True)
        handler = RotatingFileHandler(destination / "app.log", maxBytes=500000, backupCount=2, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)
    bridge.dataDirectoryChanged.connect(relocate_log)
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("backend", bridge)
    engine.rootContext().setContextProperty("initialWidth", args.width)
    engine.rootContext().setContextProperty("initialHeight", args.height)
    engine.rootContext().setContextProperty("initialPage", "settings" if args.preview == "settings" or args.dialog == "directory" else "arena")
    engine.rootContext().setContextProperty("initialDialog", args.dialog)
    warnings = []
    engine.warnings.connect(lambda values: warnings.extend(str(w) for w in values))
    engine.load(QUrl.fromLocalFile(str(root / "ui" / "Main.qml")))
    if not engine.rootObjects():
        bridge.close()
        return 2
    window = engine.rootObjects()[0]
    if args.dialog == "directory":
        from PySide6.QtCore import QObject, QMetaObject
        QTimer.singleShot(150, lambda: QMetaObject.invokeMethod(window.findChild(QObject, "dataDirectoryPicker"), "open"))
    if args.scroll_end:
        from PySide6.QtCore import QObject
        def scroll_to_end():
            scroll = window.findChild(QObject,"workScroll")
            flickable = scroll.property("contentItem")
            flickable.setProperty("contentY",max(0,flickable.property("contentHeight")-flickable.property("height")))
        QTimer.singleShot(350,scroll_to_end)

    def finish_qa():
        if args.screenshot:
            args.screenshot.parent.mkdir(parents=True, exist_ok=True)
            image = window.grabWindow()
            if image.isNull() or not image.save(str(args.screenshot)):
                print("SCREENSHOT_FAILED", file=sys.stderr)
                app.exit(3)
                return
        if warnings:
            for warning in warnings:
                print(warning, file=sys.stderr)
            app.exit(4)
        else:
            print("QML_SMOKE_OK", flush=True)
            app.exit(0)
    if args.smoke_test or args.screenshot:
        QTimer.singleShot(1300, finish_qa)
    code = app.exec()
    # Tear down QML while the context facade is still alive, preventing stale bindings.
    import shiboken6
    shiboken6.delete(engine)
    bridge.close()
    return code


if __name__ == "__main__":
    raise SystemExit(main())
