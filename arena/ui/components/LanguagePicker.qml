import QtQuick
import QtQuick.Controls
import TranslateArena.Ui 1.0
Button {
    id: control
    property var languages: []
    property string value: "en"
    property bool compact: false
    signal chosen(string code)
    property string currentName: {
        for(let i=0;i<languages.length;i++) if(languages[i].code===value) return languages[i].native
        return value
    }
    readonly property real widestLanguageWidth: {
        let widest = 0
        for (let i = 0; i < languages.length; i++)
            widest = Math.max(widest, languageMetrics.advanceWidth(languages[i].native), languageMetrics.tightBoundingRect(languages[i].native).width)
        return widest
    }
    // Leave room for menu padding, the scrollbar, and a small gap around the longest name.
    implicitWidth: Math.ceil(widestLanguageWidth) + 42; implicitHeight: compact ? 32 : 44
    hoverEnabled: true
    topPadding: 0; bottomPadding: 0
    font.family: Theme.font; font.pixelSize: compact ? Theme.controlSize : Theme.bodySize; font.weight: Theme.bodyWeight
    FontMetrics { id: languageMetrics; font: control.font }
    contentItem: LanguageCaption {
        objectName: "targetLanguageCaption"
        text: control.currentName; color: Theme.text
        font: control.font
    }
    leftPadding: compact ? 8 : 13; rightPadding: leftPadding
    background: ButtonBackground {
        baseColor: Theme.card
        hovered: control.enabled && control.hovered
        pressed: control.enabled && control.down
    }
    onClicked: popup.open()
    Accessible.name: "目标语言：" + currentName
    Popup {
        id: popup
        objectName: "targetLanguageMenu"
        y: control.height + 6
        width: control.width; height: 340
        padding: 8; focus: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        background: Rectangle { color: Theme.card; radius: 14; border.color: Theme.line; border.width: 1 }
        contentItem: Item {
            ListView {
                id: list
                objectName: "targetLanguageList"
                anchors.fill: parent
                // Keep hover backgrounds out of the scrollbar's own column.
                anchors.rightMargin: languageScrollBar.width + 4
                clip: true; model: control.languages
                ScrollBar.vertical: ScrollBar {
                    id: languageScrollBar
                    objectName: "targetLanguageScrollBar"
                    parent: list.parent
                    anchors.top: list.top; anchors.bottom: list.bottom; anchors.right: parent.right
                    width: 6; padding: 0; z: 1
                    policy: ScrollBar.AlwaysOn
                    visible: size < 1
                }
                delegate: Button {
                    id: languageOption
                    required property var modelData
                    objectName: "targetLanguageOption" + modelData.code
                    width: list.width; height: 42
                    leftPadding: 4; rightPadding: 4; topPadding: 0; bottomPadding: 0
                    hoverEnabled: true
                    font.family: Theme.font; font.pixelSize: Theme.controlSize; font.weight: Theme.bodyWeight
                    contentItem: LanguageCaption { text: modelData.native; color: control.value === modelData.code ? Theme.accent : Theme.text; font: languageOption.font }
                    background: ButtonBackground {
                        radius: 8; baseVisible: false
                        hovered: languageOption.enabled && languageOption.hovered
                        pressed: languageOption.enabled && languageOption.down
                    }
                    onClicked: { control.chosen(modelData.code); popup.close() }
                }
            }
        }
        onOpened: list.positionViewAtBeginning()
    }
}
