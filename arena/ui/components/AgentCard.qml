import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
Rectangle {
    id: root
    required property var config
    required property int agentIndex
    property bool ready: false
    property bool compact: false
    objectName: "agentCard" + config.id
    implicitHeight: compact ? 160 : 184
    color: Theme.card; radius: 16
    function setField(name, value) { backend.setAgent(config.id, name, JSON.stringify(value)) }
    ColumnLayout {
        anchors.fill: parent; anchors.margins: root.compact ? 12 : 16; spacing: root.compact ? 6 : 8
        RowLayout {
            spacing: 7
            Rectangle { width: 26; height: 26; radius: 8; color: Theme.background
                Text { anchors.centerIn: parent; text: root.config.id; font.family: Theme.font; font.pixelSize: Theme.bodySize; font.weight: Theme.emphasisWeight; color: Theme.identity(root.agentIndex) }
            }
            Text { text: "Agent " + root.config.id; color: Theme.text; font.family: Theme.font; font.pixelSize: Theme.cardTitleSize; font.weight: Theme.emphasisWeight; Layout.fillWidth: true; Layout.minimumWidth: 0; elide: Text.ElideRight }
            Text { objectName: "agentKeyStatus" + root.config.id; visible: !root.ready; text: "api未配置"; color: Theme.secondary; font.family: Theme.font; font.weight: Theme.bodyWeight; font.pixelSize: Theme.captionSize }
        }
        Capsules {
            objectName: "agentRouteOptions" + root.config.id
            Layout.fillWidth: true; implicitHeight: root.compact ? 30 : 34; value: root.config.route
            options: [{label:"偏直译",value:"literal"},{label:"偏意译",value:"free"}]
            onChosen: value => root.setField("route", value)
            Accessible.name: "Agent " + root.config.id + " 翻译路线"
        }
        Capsules {
            objectName: "agentCulturalDirectionOptions" + root.config.id
            Layout.fillWidth: true; implicitHeight: root.compact ? 30 : 34; value: root.config.cultural_direction
            options: [{label:"偏异化",value:"foreignizing"},{label:"偏归化",value:"domesticating"}]
            onChosen: value => root.setField("cultural_direction", value)
            Accessible.name: "Agent " + root.config.id + " 异化与归化"
        }
        RowLayout {
            Layout.fillWidth: true; spacing: 8
            CenteredCaption { objectName: "agentStyleLabel" + root.config.id; text: "翻译风格"; color: Theme.secondary; font: stylePicker.font; Layout.preferredHeight: stylePicker.height }
            OptionPicker {
                id: stylePicker
                objectName: "agentStyleOptions" + root.config.id
                Layout.fillWidth: true; Layout.minimumWidth: 84
                implicitHeight: root.compact ? 32 : 34
                value: root.config.style; options: backend.state.translationStyles
                onChosen: value => root.setField("style", value)
                Accessible.name: "Agent " + root.config.id + " 翻译风格"
            }
        }
    }
}
