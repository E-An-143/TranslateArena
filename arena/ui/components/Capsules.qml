import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
Rectangle {
    id: root
    property var options: []
    property string value: ""
    property bool equalWidth: true
    property int optionPadding: 11
    property font font: Qt.font({family: Theme.font, pixelSize: Theme.controlSize, weight: Theme.bodyWeight})
    signal chosen(string value)
    implicitHeight: 40
    implicitWidth: row.implicitWidth + 6
    color: Theme.background; radius: 10
    RowLayout {
        id: row
        anchors.fill: parent; anchors.margins: 3; spacing: 2
        Repeater {
            model: root.options
            Button {
                id: option
                required property var modelData
                Layout.fillWidth: root.equalWidth
                Layout.fillHeight: true
                implicitWidth: label.implicitWidth + root.optionPadding * 2
                hoverEnabled: true
                font.family: root.font.family; font.pixelSize: root.font.pixelSize
                font.weight: root.value === modelData.value ? Theme.emphasisWeight : Theme.bodyWeight
                leftPadding: root.optionPadding; rightPadding: leftPadding; topPadding: 0; bottomPadding: 0
                onClicked: root.chosen(modelData.value)
                contentItem: CenteredCaption { id: label; text: modelData.label; font: option.font; color: root.value === modelData.value ? Theme.text : Theme.secondary }
                background: ButtonBackground {
                    radius: 8
                    baseColor: Theme.card
                    baseVisible: root.value === option.modelData.value
                    hovered: option.enabled && option.hovered
                    pressed: option.enabled && option.down
                }
                Accessible.name: modelData.label
                Accessible.description: root.value === modelData.value ? "已选中" : "未选中"
            }
        }
    }
}
