import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
ScrollView {
    id: page
    objectName: "settingsPage"
    readonly property int settingsTextSize: Theme.bodySize
    contentWidth: availableWidth
    clip: true
    rightPadding: ScrollBar.vertical.width + 8
    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
    FolderDialog {
        id: directoryPicker
        objectName: "dataDirectoryPicker"
        title: "选择数据文件夹"
        currentFolder: backend.state.dataDirUrl
        acceptLabel: "使用此文件夹"; rejectLabel: "取消"
        onAccepted: backend.setDataDirectory(selectedFolder.toString())
    }
    Popup {
        id: apiClearConfirmation
        objectName: "apiClearConfirmationPopup"
        property string providerName: ""
        parent: Overlay.overlay
        width: 320; height: 144
        x: (parent.width - width) / 2; y: (parent.height - height) / 2
        modal: true; focus: true; padding: 18
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        background: Rectangle { color: Theme.card; radius: 16 }
        Overlay.modal: Rectangle { color: Theme.overlay }
        contentItem: Item {
            Column {
                objectName: "apiClearConfirmationGroup"
                anchors.centerIn: parent
                width: parent.width; height: implicitHeight
                spacing: 24
                CenteredCaption {
                    objectName: "apiClearConfirmationText"
                    width: parent.width; height: contentHeight
                    elide: Text.ElideNone
                    text: "确认删除 " + (apiClearConfirmation.providerName === "Judge" ? "Judge" : "Translator " + apiClearConfirmation.providerName) + " 的 API？"
                    color: Theme.text; font.family: Theme.font; font.pixelSize: page.settingsTextSize; font.weight: Theme.emphasisWeight
                }
                RowLayout {
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: 8
                    ArenaButton { objectName: "cancelApiClearButton"; text: "取消"; compact: true; textSize: page.settingsTextSize; kind: "ghost"; onClicked: apiClearConfirmation.close() }
                    ArenaButton {
                        objectName: "confirmApiClearButton"
                        text: "确认"; compact: true; textSize: page.settingsTextSize; kind: "danger"
                        enabled: !backend.state.busy
                        onClicked: { backend.deleteKey(apiClearConfirmation.providerName); apiClearConfirmation.close() }
                    }
                }
            }
        }
        onClosed: providerName = ""
    }
    ColumnLayout {
        width: page.availableWidth; spacing: 20
        Rectangle {
            objectName: "appearanceCard"
            Layout.fillWidth: true; implicitHeight: 120; color: Theme.card; radius: 16
            ColumnLayout { anchors.fill: parent; anchors.margins: 20; spacing: 14
                Text { text: "外观"; color: Theme.text; font.family: Theme.font; font.pixelSize: page.settingsTextSize; font.weight: Theme.emphasisWeight }
                Capsules { objectName: "appearancePicker"; Layout.fillWidth: true; font.pixelSize: page.settingsTextSize; value: backend.state.settings.appearance; options: [{label:"浅色",value:"light"},{label:"深色",value:"dark"}]; onChosen: value => backend.setSetting("appearance",JSON.stringify(value)) }
            }
        }
        Repeater {
            model: ["A", "B", "C", "Judge"]
            Rectangle {
                id: providerCard
                required property string modelData
                objectName: "credentialCard" + modelData
                property var credential: backend.state.credentials[modelData]
                property bool keySaved: credential.configured || credential.mask === "需要重新配置"
                property var connection: backend.state.connections[modelData] || ({status:"",message:""})
                function saveCredential() {
                    if (keySaved || backend.state.busy || !keyField.text.trim()) return
                    backend.saveKey(modelData, keyField.text)
                    if (keySaved) keyField.text = ""
                }
                Layout.fillWidth: true; implicitHeight: connection.message ? 152 : 120
                radius: 16; color: Theme.card
                ColumnLayout { anchors.fill: parent; anchors.margins: 20; spacing: 10
                    RowLayout {
                        Icon { name: "key"; color: Theme.secondary; implicitWidth: 18; implicitHeight: 18 }
                        Text { objectName: "apiTitle" + providerCard.modelData; text: providerCard.modelData === "Judge" ? "Judge" : "Translator " + providerCard.modelData; color: Theme.text; font.family: Theme.font; font.pixelSize: page.settingsTextSize; font.weight: Theme.emphasisWeight; Layout.fillWidth: true }
                    }
                    RowLayout {
                        Layout.fillWidth: true; spacing: 8
                        ArenaField {
                            id: keyField
                            objectName: "keyField" + providerCard.modelData
                            Layout.fillWidth: true
                            font.pixelSize: page.settingsTextSize
                            font.letterSpacing: providerCard.credential.configured || keyField.text.length > 0 ? -7 : 0
                            echoMode: TextInput.Password
                            passwordCharacter: "•"
                            placeholderText: providerCard.keySaved ? providerCard.credential.mask : "输入 DeepSeek API Key"
                            placeholderTextColor: providerCard.keySaved ? Theme.text : Theme.tertiary
                            readOnly: providerCard.keySaved
                            enabled: !backend.state.busy && !providerCard.keySaved
                            maximumLength: 512; Accessible.name: providerCard.modelData + " API Key"
                            onAccepted: providerCard.saveCredential()
                        }
                        ArenaButton {
                            objectName: "saveApiButton" + providerCard.modelData
                            text: providerCard.keySaved ? "清空" : "保存"
                            textSize: page.settingsTextSize
                            Layout.minimumWidth: 60; Layout.preferredWidth: 60; Layout.maximumWidth: 60
                            enabled: !backend.state.busy && (providerCard.keySaved || keyField.text.trim().length > 0)
                            onClicked: {
                                if (providerCard.keySaved) {
                                    apiClearConfirmation.providerName = providerCard.modelData
                                    apiClearConfirmation.open()
                                } else providerCard.saveCredential()
                            }
                        }
                        ArenaButton { objectName: "testApiButton" + providerCard.modelData; text: providerCard.connection.status === "running" ? "连接中…" : "测试连接"; textSize: page.settingsTextSize; kind: "ghost"; enabled: !backend.state.busy && providerCard.credential.configured && providerCard.connection.status !== "running"; onClicked: backend.testConnection(providerCard.modelData) }
                    }
                    Text { visible: providerCard.connection.message !== ""; text: providerCard.connection.message; color: providerCard.connection.status === "error" ? Theme.error : providerCard.connection.status === "success" ? Theme.success : Theme.secondary; font.family: Theme.font; font.weight: Theme.bodyWeight; font.pixelSize: page.settingsTextSize; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                }
            }
        }
        Rectangle {
            objectName: "localDataCard"
            Layout.fillWidth: true; implicitHeight: localDataContent.implicitHeight + 24; radius: 16; color: Theme.card
            ColumnLayout { id: localDataContent; anchors.fill: parent; anchors.margins: 20; anchors.topMargin: 12; anchors.bottomMargin: 12; spacing: 10
                Text { text: "本地数据"; color: Theme.text; font.family: Theme.font; font.pixelSize: page.settingsTextSize; font.weight: Theme.emphasisWeight; Layout.fillWidth: true }
                ArenaField {
                    id: directoryField
                    objectName: "dataDirectoryField"
                    Layout.fillWidth: true; text: backend.state.dataDir
                    font.pixelSize: page.settingsTextSize
                    enabled: !backend.state.busy && !backend.state.connecting
                    selectByMouse: true; Accessible.name: "数据文件夹位置"
                    onAccepted: backend.setDataDirectory(text)
                }
                RowLayout {
                    Layout.fillWidth: true
                    Item { Layout.fillWidth: true }
                    ArenaButton { objectName: "selectDataDirectory"; text: "选择文件夹"; textSize: page.settingsTextSize; kind: "ghost"; compact: true; enabled: !backend.state.busy && !backend.state.connecting; onClicked: directoryPicker.open() }
                    ArenaButton { objectName: "openDataDirectory"; text: "打开文件夹"; textSize: page.settingsTextSize; compact: true; onClicked: backend.openDataDirectory() }
                }
            }
        }
    }
}
