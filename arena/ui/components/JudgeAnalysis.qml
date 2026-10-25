import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
Popup {
    id: root
    objectName: "judgeAnalysisPopup"
    property var record: backend.state.record
    readonly property bool hasVerdict: Object.keys((record.judge || {}).scores || {}).length > 0
    width: Math.min(1020, parent.width-60); height: Math.min(760,parent.height-70)
    x: (parent.width-width)/2; y: (parent.height-height)/2
    padding: 26; modal: true; focus: true
    background: Rectangle { color: Theme.card; radius: 22 }
    Overlay.modal: Rectangle { color: Theme.overlay }
    contentItem: ColumnLayout {
        spacing: 20
        RowLayout {
            Text { objectName: "judgeAnalysisHeading"; text: "Judge 评审"; color: Theme.text; font.family: Theme.font; font.pixelSize: Theme.dialogTitleSize; font.weight: Theme.emphasisWeight }
            Item { Layout.fillWidth: true }
            ArenaButton { iconName: "close"; kind: "ghost"; onClicked: root.close(); Accessible.name: "关闭评审" }
        }
        PreviewPane {
            objectName: "judgeReaderReasoning"
            Layout.fillWidth: true; Layout.preferredHeight: Math.max(100, root.height * 0.28)
            heading: root.record.id ? "思考过程" : ""
            muted: true; textSize: Theme.controlSize
            text: root.record.judge_reasoning || ""
            streaming: root.record.stage === "judging"
        }
        Loader {
            Layout.fillWidth: true; Layout.fillHeight: true
            Layout.minimumHeight: root.hasVerdict ? implicitHeight : 0
            sourceComponent: root.hasVerdict ? results : liveOutput
        }
    }
    Component {
        id: liveOutput
        PreviewPane {
            objectName: "judgeReaderOutput"
            heading: root.record.id ? "评审输出" : ""
            textSize: Theme.readingSize
            text: root.record.judge_preview || ""
            streaming: root.record.stage === "judging"
        }
    }
    Component {
        id: results
        Rectangle {
            implicitHeight: resultLayout.implicitHeight + 20
            color: Theme.background; radius: 10
            ColumnLayout {
                id: resultLayout
                anchors.fill: parent; anchors.margins: 10; spacing: 8
                Text {
                    text: "评审结果"; color: Theme.secondary
                    font.family: Theme.font; font.pixelSize: Theme.bodySize; font.weight: Theme.emphasisWeight
                }
                JudgeReview {
                    objectName: "expandedJudgeReview"
                    Layout.fillWidth: true; Layout.fillHeight: true
                    Layout.minimumHeight: resultContentHeight
                    resultHorizontalMargin: 0
                    record: root.record
                }
            }
        }
    }
}
