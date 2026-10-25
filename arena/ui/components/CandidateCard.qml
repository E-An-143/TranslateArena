import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
Rectangle {
    id: root
    required property string agentId
    required property int agentIndex
    required property var candidate
    property bool hasRecord: false
    property bool compact: false
    property real compactHeight: 188
    readonly property real cardHeight: compact ? Math.max(188, compactHeight) : 324
    property string reasoningText: candidate.reasoning || ""
    property string committedText: candidate.text || ""
    readonly property bool hasContent: !!(committedText.trim() || reasoningText.trim() || (candidate.preview || "").trim())
    readonly property bool showsResult: !!committedText && candidate.status !== "running"
    signal expand(string agentId)
    objectName: "agentPreview" + agentId
    implicitHeight: cardHeight
    Layout.minimumHeight: cardHeight
    Layout.preferredHeight: cardHeight
    Layout.maximumHeight: cardHeight
    Layout.fillHeight: false
    radius: 16; color: Theme.card
    ColumnLayout {
        anchors.fill: parent; anchors.margins: root.compact ? 12 : 14; spacing: root.compact ? 6 : 8
        RowLayout {
            objectName: "agentPreviewHeader" + root.agentId
            spacing: root.compact ? 6 : 8
            Rectangle { width: 7; height: 7; radius: 4; color: Theme.identity(root.agentIndex) }
            Text { text: "Agent " + root.agentId; color: Theme.text; font.family: Theme.font; font.pixelSize: Theme.cardTitleSize; font.weight: Theme.emphasisWeight; Layout.fillWidth: true }
            ArenaButton { objectName: "expandAgentButton" + root.agentId; iconName: "expand"; enabled: root.hasContent; kind: "ghost"; compact: true; implicitWidth: root.compact ? 24 : 28; implicitHeight: implicitWidth; onClicked: root.expand(root.agentId); Accessible.name: "展开 Agent " + root.agentId }
        }
        PreviewPane {
            objectName: "agentPreviewContent" + root.agentId
            Layout.fillWidth: true; Layout.fillHeight: true
            Layout.minimumHeight: 64
            compact: root.compact
            heading: root.hasRecord ? root.showsResult ? "译文结果" : "思考过程" : ""
            showsResult: root.showsResult
            muted: !root.showsResult
            textSize: Theme.previewSize
            text: root.showsResult ? root.committedText : root.reasoningText
            streaming: root.candidate.status === "running"
            errorText: root.candidate.error || ""
            errorObjectName: "agentPreviewError" + root.agentId
        }
        RowLayout {
            ArenaButton { text: "复制"; iconName: "copy"; kind: "ghost"; compact: true; implicitHeight: root.compact ? 28 : 32; enabled: !!root.committedText; onClicked: backend.copyText(root.committedText) }
            Item { Layout.fillWidth: true }
            ArenaButton { objectName: "regenerateButton" + root.agentId; text: root.candidate.status === "error" ? "重试" : "重新生成"; iconName: "regenerate"; kind: "ghost"; compact: true; implicitHeight: root.compact ? 28 : 32; enabled: root.hasRecord; onClicked: backend.regenerate(root.agentId) }
        }
    }
}
