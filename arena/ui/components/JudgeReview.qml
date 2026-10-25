import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ScrollView {
    id: root
    property var record: ({})
    property int resultHorizontalMargin: 12
    readonly property var verdict: record.judge || ({})
    readonly property bool hasVerdict: Object.keys(verdict.scores || {}).length > 0
    readonly property bool hasContent: hasVerdict || !!((record.judge_reasoning || "").trim() || (record.judge_preview || "").trim())
    readonly property string lastResultId: ["C", "B", "A"].find(agentId => (verdict.scores || {})[agentId] !== undefined) || ""
    readonly property real resultContentHeight: hasVerdict ? reviewContents.implicitHeight : 0
    clip: true; contentWidth: availableWidth
    rightPadding: ScrollBar.vertical.width + 6
    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
    background: Item {}

    readonly property int livePaneCount: (!hasVerdict && !!record.judge_reasoning ? 1 : 0) + (!hasVerdict && !!record.judge_preview ? 1 : 0)
    readonly property real livePaneHeight: Math.max(140, (availableHeight - (statusLabel.visible ? statusLabel.implicitHeight + 12 : 0) - Math.max(0, livePaneCount - 1) * 12) / Math.max(1, livePaneCount))

    ColumnLayout {
        id: reviewContents
        width: root.availableWidth
        height: root.hasVerdict ? Math.max(implicitHeight, root.availableHeight) : implicitHeight
        spacing: root.hasVerdict ? 0 : 12
        Text {
            id: statusLabel
            objectName: root.objectName + "Placeholder"
            visible: !root.hasVerdict && !!text
            text: root.record.stage === "judging" ? "正在评审" : root.record.stage === "judge_error" ? "评审失败" : ""
            color: Theme.tertiary; font.family: Theme.font; font.weight: Theme.bodyWeight; font.pixelSize: Theme.bodySize
            Layout.fillWidth: true; wrapMode: Text.WordWrap
        }
        PreviewPane {
            objectName: root.objectName + "Reasoning"
            visible: !root.hasVerdict && !!root.record.judge_reasoning
            Layout.fillWidth: true; Layout.preferredHeight: root.livePaneHeight
            contentMargin: 0; muted: true; textSize: Theme.previewSize
            color: "transparent"
            text: root.record.judge_reasoning || ""
            streaming: root.record.stage === "judging"
        }
        PreviewPane {
            objectName: root.objectName + "Output"
            visible: !root.hasVerdict && !!root.record.judge_preview
            Layout.fillWidth: true; Layout.preferredHeight: root.livePaneHeight
            heading: "评审输出"; textSize: Theme.judgeSize
            color: "transparent"
            text: root.record.judge_preview || ""
            streaming: root.record.stage === "judging"
        }
        Repeater {
            model: ["A", "B", "C"]
            Rectangle {
                id: review
                required property string modelData
                readonly property var score: (root.verdict.scores || {})[modelData]
                readonly property var card: (root.verdict.candidates || {})[modelData] || ({})
                objectName: root.objectName + "Candidate" + modelData
                visible: score !== undefined
                Layout.fillWidth: true; Layout.fillHeight: modelData !== root.lastResultId
                Layout.minimumHeight: implicitHeight
                implicitHeight: details.implicitHeight + (modelData !== root.lastResultId ? 12 : 0)
                color: "transparent"
                ColumnLayout {
                    id: details
                    anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                    anchors.leftMargin: root.resultHorizontalMargin; anchors.rightMargin: root.resultHorizontalMargin
                    spacing: 4
                    RowLayout {
                        Layout.fillWidth: true; spacing: 6
                        Text { text: "Agent " + review.modelData; color: Theme.text; font.family: Theme.font; font.weight: Theme.emphasisWeight; font.pixelSize: Theme.judgeSize }
                        Icon {
                            objectName: root.objectName + "Winner" + review.modelData
                            visible: root.hasVerdict && root.verdict.winner === review.modelData
                            name: "trophy"; color: Theme.accent
                            implicitWidth: 18; implicitHeight: 18
                            Accessible.name: "胜出译文"
                        }
                        Item { Layout.fillWidth: true }
                    }
                    GridLayout {
                        visible: review.card.fidelity !== undefined
                        Layout.fillWidth: true; columns: width < 360 ? 1 : 2; columnSpacing: 12; rowSpacing: 2
                        Repeater {
                            model: [{key:"fidelity",name:"忠实性"},{key:"fluency",name:"语言表达"},{key:"terminology",name:"术语一致性"},{key:"style",name:"文体适配"}]
                            RowLayout {
                                required property var modelData
                                Layout.fillWidth: true; spacing: 8
                                Text { objectName: root.objectName + "DimensionLabel" + review.modelData + modelData.key; text: modelData.name; color: Theme.secondary; font.family: Theme.font; font.weight: Theme.bodyWeight; font.pixelSize: Theme.judgeSize; Layout.fillWidth: true }
                                Text { objectName: root.objectName + "DimensionScore" + review.modelData + modelData.key; text: modelData.key === "terminology" && review.card[modelData.key] == null ? "不适用" : review.card[modelData.key] !== undefined ? Number(review.card[modelData.key]).toFixed(1) : ""; color: Theme.text; font.family: Theme.font; font.weight: Theme.emphasisWeight; font.pixelSize: Theme.judgeSize }
                            }
                        }
                    }
                }
            }
        }
    }
}
