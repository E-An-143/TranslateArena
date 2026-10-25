import QtQuick
import QtQuick.Controls
import TranslateArena.Ui 1.0

TextArea {
    id: control
    property real lineHeight: Theme.readingLineHeight
    textFormat: TextEdit.PlainText

    TextLineSpacing {
        document: control.textDocument
        lineHeight: control.lineHeight
    }
}
