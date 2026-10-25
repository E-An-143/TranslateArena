# Third-party components

The application code is MIT licensed. Dependencies retain their own licenses:

| Component | License / reference |
| --- | --- |
| Python | Python Software Foundation License · https://docs.python.org/3/license.html |
| PySide6 / Shiboken6 / Qt | LGPLv3 / GPLv3 / commercial options · https://doc.qt.io/qtforpython-6/licenses.html |
| httpx / httpcore / anyio / h11 / idna | BSD / MIT licenses, see each package's installed license |
| certifi | MPL-2.0 |
| PyInstaller bootloader | GPL-2.0 with bootloader distribution exception · https://pyinstaller.org/en/stable/license.html |
| MiSans Regular / Medium | MiSans Font Intellectual Property License Agreement · https://hyperos.mi.com/font/en/download/ |
| Noto Sans KR / Thai / Myanmar / Lao | SIL Open Font License 1.1 · https://github.com/google/fonts |

The build specification collects the installed package license files into `licenses/` where available. This project's QtQml hook limits QML imports to QtQml, QtQuick, Layouts, Templates and the Basic Controls style; unused Charts, DataVisualization and WebEngine bindings are excluded. Release maintainers should retain bundled license files and confirm the license obligations of the exact distribution they release. The directory build (`build.bat -Portable`) keeps Qt libraries separate and replaceable.

Qt's LGPLv3 and accompanying GPLv3 texts are included under `arena/resources/licenses/`, copied unchanged from the official Qt 6.8.3 source repository: https://github.com/qt/qtbase/tree/v6.8.3/LICENSES . They are also included in the frozen resources. Windows builds collect the installed Python runtime's `LICENSE.txt` when present.

This application uses MiSans fonts. Copyright © 2020–2025 Beijing Xiaomi Mobile Software Co., Ltd. All Rights Reserved. The original, unmodified Regular and Medium font files are bundled solely as application resources under `arena/resources/fonts/`, together with the official `MiSans-LICENSE.pdf`. The build specification includes that complete resource directory. The fonts retain their own license and are not covered by this project's MIT license. Obtain standalone fonts from https://hyperos.mi.com/font/en/download/ .

Unmodified Noto Sans KR, Thai, Myanmar and Lao font files from the official `google/fonts` repository are bundled for script fallback when MiSans lacks a character. Each font's full copyright notice and SIL OFL 1.1 license are included beside it as `NotoSans*-OFL.txt`; `Noto-font-sources.json` records the source URLs, source blob identities and checksums. These fonts are application resources, retain their original family names, and are not covered by the application code's MIT license. MiSans remains the primary UI font.

The product icon and QML vector icons are drawn in this project, with no third-party icon package.
