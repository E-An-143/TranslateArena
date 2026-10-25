"""Collect only QML modules this app uses; avoid bundling unrelated Qt products."""
from pathlib import PurePath
from PyInstaller.utils.hooks.qt import add_qt6_dependencies, pyside6_library_info

hiddenimports, binaries, datas = add_qt6_dependencies(__file__)
qml_binaries, qml_datas = pyside6_library_info.collect_qtqml_files()
qml_root = PurePath(pyside6_library_info.qt_rel_dir) / "qml"
allowed = {
    "QtQml", "QtQml/Models", "QtQml/WorkerScript",
    "QtQuick", "QtQuick/Window", "QtQuick/Layouts", "QtQuick/Templates",
    "QtQuick/Controls", "QtQuick/Controls/impl", "QtQuick/Controls/Basic", "QtQuick/Controls/Basic/impl",
    "QtQuick/Dialogs", "QtQuick/Dialogs/quickimpl", "Qt/labs/folderlistmodel",
}


def needed(entry):
    relative = PurePath(entry[1]).relative_to(qml_root).as_posix()
    return relative in allowed or relative.startswith(("QtQuick/Controls/Basic/", "QtQuick/Dialogs/"))


binaries += [entry for entry in qml_binaries if needed(entry)]
datas += [entry for entry in qml_datas if needed(entry)]
