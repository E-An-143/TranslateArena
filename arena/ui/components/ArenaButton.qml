import QtQuick
import QtQuick.Controls
Button {
    id: control
    property string kind: "soft"
    property string iconName: ""
    property int textSize: compact ? Theme.controlSize : Theme.bodySize
    property bool compact: false
    property color foreground: kind === "primary" ? "white" : kind === "danger" ? Theme.error : Theme.text
    implicitHeight: compact ? 36 : 44
    implicitWidth: contentItem.implicitWidth + (compact ? 20 : 28)
    leftPadding: compact ? 10 : 14; rightPadding: leftPadding
    opacity: enabled ? 1 : 0.4
    hoverEnabled: true
    font.family: Theme.font; font.weight: kind === "primary" ? Theme.emphasisWeight : Theme.bodyWeight; font.pixelSize: textSize
    topPadding: 0; bottomPadding: 0
    contentItem: Item {
        id: content
        readonly property real iconWidth: control.iconName !== "" ? 17 : 0
        readonly property real gap: control.iconName !== "" && control.text !== "" ? 7 : 0
        implicitWidth: (control.text !== "" ? Math.ceil(metrics.advanceWidth(control.text)) : 0) + iconWidth + gap
        implicitHeight: Math.max(control.text !== "" ? metrics.height : 0, iconWidth)
        FontMetrics { id: metrics; font: control.font }
        Item {
            id: group
            objectName: "buttonContentGroup"
            // The icon and visible text form one centered unit.
            anchors.centerIn: parent
            width: content.iconWidth + content.gap + (label.visible ? label.contentWidth : 0)
            height: Math.max(content.iconWidth, label.visible ? label.contentHeight : 0)
            Icon {
                id: glyph
                objectName: "buttonIcon"
                visible: control.iconName !== ""; name: control.iconName; color: control.foreground
                stroke: control.iconName === "regenerate" ? 1.45 : 1.7
                width: content.iconWidth; height: width
                anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter
            }
            CenteredCaption {
                id: label
                objectName: "buttonCaption"
                x: content.iconWidth + content.gap
                width: contentWidth; height: group.height
                text: {
                    // FontMetrics methods do not register their font as a binding dependency.
                    let measuredFont = metrics.font
                    return metrics.elidedText(control.text, Text.ElideRight, Math.max(0, content.width - content.iconWidth - content.gap))
                }
                elide: Text.ElideNone
                color: control.foreground; font: control.font
                visible: control.text !== ""
            }
        }
    }
    background: ButtonBackground {
        baseColor: control.kind === "primary" ? "#3478f6" : Theme.raised
        hoverColor: control.kind === "primary" ? "#4689ff" : Theme.hover
        pressedColor: control.kind === "primary" ? "#2460c9" : Theme.line
        baseVisible: control.kind !== "ghost"
        hovered: control.enabled && control.hovered
        pressed: control.enabled && control.down
    }
    Accessible.name: text
}
