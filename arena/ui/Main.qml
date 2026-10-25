import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "components"

ApplicationWindow {
    id: window
    objectName: "arenaWindow"
    width: initialWidth; height: initialHeight
    minimumWidth: 860; minimumHeight: 640
    visible: true
    title: "翻译竞技场 · Translate Arena"
    color: Theme.background
    property var s: backend.state
    property string page: initialPage
    property bool narrow: width < 1180
    property bool compactLayout: height < 900
    readonly property real resultCardHeight: Math.max(compactLayout ? 268 : 348, judgeReview.resultContentHeight + (compactLayout ? 24 : 40))
    property string candidateTab: "A"
    property var currentRecord: s.record || ({})
    function languageName(code) { for(let i=0;i<s.languages.length;i++) if(s.languages[i].code===code) return s.languages[i].native; return code }
    Component.onCompleted: {
        if(initialDialog==="analysis") analysis.open()
        else if(initialDialog==="reader") reader.open()
    }
    Binding { target: Theme; property: "dark"; value: s.settings.appearance === "dark" }
    Shortcut { sequence: "Ctrl+N"; onActivated: { historyList.endSelection(); backend.newTranslation() } }
    Shortcut { sequence: "Escape"; onActivated: if(s.busy) backend.cancel() }
    Connections {
        target: backend
        function onNavigate(value) { window.page=value; if(value==="arena") workScroll.contentItem.contentY=0 }
        function onToast(message) { toastText.text=message; toastBanner.visible=true; toastTimer.restart() }
    }
    RowLayout {
        anchors.fill: parent; spacing: 0
        Rectangle {
            Layout.preferredWidth: window.width < 1000 ? 180 : 220
            Layout.fillHeight: true; color: Theme.sidebar
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 16; spacing: 20
                ArenaButton { id: newTranslationButton; objectName: "newButton"; Layout.fillWidth: true; text: "新建翻译"; kind: "soft"; onClicked: { historyList.endSelection(); backend.newTranslation() } enabled: !s.busy }
                HistoryList {
                    id: historyList
                    Layout.fillWidth: true; Layout.fillHeight: true
                    history: s.history; currentRecordId: currentRecord.id || ""
                    arenaPage: window.page === "arena"; busy: s.busy
                    headingFont: newTranslationButton.font
                    onRestoreRequested: recordId => backend.restoreHistory(recordId)
                    onBulkDeleteRequested: recordIds => { confirmPopup.recordIds=recordIds; confirmPopup.open() }
                }
                ColumnLayout {
                    spacing: 6; Layout.fillWidth: true
                    ArenaButton {
                        objectName: "selectHistoryButton"
                        Layout.fillWidth: true; text: historyList.selectionMode ? "退出多选模式" : "选择翻译记录"; kind: "soft"
                        enabled: !s.busy && s.history.length > 0
                        onClicked: historyList.toggleSelectionMode()
                        Accessible.description: historyList.selectionMode ? "退出记录多选" : "进入记录多选"
                    }
                    ArenaButton { objectName: "homeButton"; Layout.fillWidth: true; text: "主页"; kind: "soft"; onClicked: { window.page="arena"; workScroll.contentItem.contentY=0 } }
                    ArenaButton { objectName: "settingsButton"; Layout.fillWidth: true; text: "设置"; kind: "soft"; onClicked: window.page="settings" }
                }
            }
        }
        Item {
            objectName: "translationArea"
            Layout.fillWidth: true; Layout.fillHeight: true
            MouseArea {
                objectName: "historyDismissHandler"
                anchors.fill: parent; z: 100
                enabled: historyList.selectionMode && window.page === "arena"
                acceptedButtons: Qt.LeftButton
                // Observe the press, then pass that same event to the underlying control.
                onPressed: mouse => {
                    mouse.accepted = false
                    historyList.endSelection()
                }
                onWheel: wheel => wheel.accepted = false
            }
            ScrollView {
                id: workScroll
                objectName: "workScroll"
                anchors.fill: parent; anchors.margins: window.width < 1180 ? 24 : 38
                anchors.topMargin: 16 + (newTranslationButton.height - sourceToolbar.implicitHeight) / 2
                anchors.leftMargin: Math.max(window.width < 1180 ? 24 : 38,(parent.width-1540)/2)
                anchors.rightMargin: anchors.leftMargin
                visible: window.page === "arena"
                clip: true; contentWidth: availableWidth
                rightPadding: ScrollBar.vertical.width + 8
                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                ColumnLayout {
                    id: workspace
                    width: workScroll.availableWidth; spacing: window.compactLayout ? 10 : 18
                    ColumnLayout {
                        objectName: "sourceSection"
                        Layout.fillWidth: true; spacing: window.compactLayout ? 8 : 12
                        RowLayout {
                            id: sourceToolbar
                            objectName: "sourceToolbar"
                            Layout.fillWidth: true; spacing: 10
                            CenteredCaption { objectName: "sourceHeading"; text: "原文"; font.family: Theme.font; font.pixelSize: Theme.sectionTitleSize; font.weight: Theme.emphasisWeight; color: Theme.text; Layout.preferredHeight: 32; Layout.rightMargin: 6 }
                            Item { Layout.fillWidth: true }
                            RowLayout {
                                objectName: "targetLanguageControls"
                                spacing: 6
                                CenteredCaption { objectName: "targetLanguageLabel"; text: "目标语言"; color: Theme.secondary; font: languagePicker.font; Layout.preferredHeight: languagePicker.height }
                                LanguagePicker { id: languagePicker; objectName: "targetLanguagePicker"; compact: true; languages: s.languages; value: s.targetLanguage; enabled: !s.busy; onChosen: code => backend.setTargetLanguage(code) }
                            }
                            ArenaButton { objectName: "translateButton"; text: s.busy ? "取消" : "开始翻译"; kind: s.busy ? "soft" : "primary"; compact: true; implicitWidth: 122; implicitHeight: 32; enabled: s.busy || sourceEditor.text.trim() !== ""; onClicked: backend.translate() }
                        }
                        Rectangle {
                            objectName: "sourceInputCard"
                            Layout.fillWidth: true; implicitHeight: window.compactLayout ? Math.max(68, Math.min(112, window.height - 572)) : 116; color: Theme.card; radius: 16
                            border.color: sourceEditor.activeFocus ? (Theme.dark ? "#4a5d7a" : "#baccf0") : "transparent"; border.width: 1
                            ScrollView {
                                anchors.fill: parent; anchors.margins: window.compactLayout ? 12 : 20; contentWidth: availableWidth; clip: true
                                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                                ReadingTextArea {
                                    id: sourceEditor
                                    objectName: "sourceEditor"
                                    text: s.source; readOnly: s.busy
                                    color: Theme.text; font.family: Theme.font; font.weight: Theme.bodyWeight; font.pixelSize: Theme.sourceSize
                                    placeholderText: "请输入"; placeholderTextColor: Theme.tertiary
                                    selectByMouse: true; wrapMode: TextEdit.Wrap; selectionColor: Theme.accent; selectedTextColor: "white"
                                    leftPadding: 0; rightPadding: 5; topPadding: 0; bottomPadding: 0
                                    background: Item {}
                                    onTextChanged: if (text !== s.source) backend.setSource(text)
                                    Accessible.name: "翻译原文编辑器"
                                }
                            }
                        }
                    }
                    ColumnLayout {
                        objectName: "translatorsSection"
                        Layout.fillWidth: true; spacing: window.compactLayout ? 8 : 12
                        Text { objectName: "translatorsHeading"; text: "翻译者"; color: Theme.text; font.family: Theme.font; font.pixelSize: Theme.sectionTitleSize; font.weight: Theme.emphasisWeight; Layout.fillWidth: true }
                        RowLayout {
                            Layout.fillWidth: true; spacing: 12
                            Repeater {
                                model: 3
                                AgentCard {
                                    required property int index
                                    Layout.fillWidth: true; Layout.preferredWidth: 1
                                    config: s.agents[index]; agentIndex: index; ready: s.credentials[config.id].configured
                                    compact: window.compactLayout
                                    enabled: !s.busy
                                }
                            }
                        }
                    }
                    ColumnLayout {
                        objectName: "translationPreviewSection"
                        Layout.fillWidth: true; spacing: window.compactLayout ? 8 : 12
                        RowLayout {
                            objectName: "previewControls"
                            visible: window.narrow
                            Layout.fillWidth: true
                            Item { Layout.fillWidth: true }
                            Capsules { objectName: "previewAgentPicker"; visible: window.narrow; Layout.preferredWidth: 244; implicitHeight: 32; value: window.candidateTab; options: [{label:"Agent A",value:"A"},{label:"Agent B",value:"B"},{label:"Agent C",value:"C"}]; onChosen: value => window.candidateTab=value }
                        }
                        RowLayout {
                            Layout.fillWidth: true; spacing: 12
                            Repeater {
                                model: 3
                                CandidateCard {
                                    required property int index
                                    agentId: ["A","B","C"][index]; agentIndex: index
                                    hasRecord: !!currentRecord.id
                                    compact: window.compactLayout
                                    compactHeight: Math.max(188, Math.min(254, window.height - 526))
                                    visible: !window.narrow || window.candidateTab === agentId
                                    Layout.fillWidth: true; Layout.preferredWidth: 1
                                    candidate: (currentRecord.candidates || {})[agentId] || ({status:"queued",text:"",error:""})
                                    onExpand: id => { reader.agentId=id; reader.open() }
                                }
                            }
                        }
                    }
                    RowLayout {
                        objectName: "finalResultSection"
                        Layout.fillWidth: true; spacing: 12
                        ColumnLayout {
                            objectName: "judgeReviewSection"
                            Layout.fillWidth: true; Layout.preferredWidth: (workScroll.availableWidth - 12) / 2
                            spacing: window.compactLayout ? 8 : 12
                            RowLayout {
                                Layout.fillWidth: true; spacing: 12
                                Text { objectName: "judgeReviewHeading"; text: "评审"; color: Theme.text; font.family: Theme.font; font.pixelSize: Theme.sectionTitleSize; font.weight: Theme.emphasisWeight }
                                Item { Layout.fillWidth: true }
                                ArenaButton { objectName: "expandJudgeButton"; iconName: "expand"; enabled: judgeReview.hasContent; kind: "soft"; compact: true; implicitWidth: 32; implicitHeight: 32; onClicked: analysis.open(); Accessible.name: "展开评审" }
                            }
                            Rectangle {
                                objectName: "judgeReviewCard"
                                Layout.fillWidth: true; Layout.preferredHeight: window.resultCardHeight
                                radius: 16; color: Theme.card
                                JudgeReview { id: judgeReview; objectName: "inlineJudgeReview"; anchors.fill: parent; anchors.margins: window.compactLayout ? 12 : 20; record: currentRecord }
                            }
                        }
                        ColumnLayout {
                            objectName: "finalTranslationSection"
                            Layout.fillWidth: true; Layout.preferredWidth: (workScroll.availableWidth - 12) / 2
                            spacing: window.compactLayout ? 8 : 12
                            RowLayout {
                                Layout.fillWidth: true; spacing: 12
                                Text { objectName: "finalHeading"; text: "最终译文"; color: Theme.text; font.family: Theme.font; font.pixelSize: Theme.sectionTitleSize; font.weight: Theme.emphasisWeight }
                                Item { Layout.fillWidth: true }
                                ArenaButton { objectName: "expandFinalButton"; iconName: "expand"; enabled: !!(currentRecord.final || "").trim(); kind: "soft"; compact: true; implicitWidth: 32; implicitHeight: 32; onClicked: finalReader.open(); Accessible.name: "展开最终译文" }
                                ArenaButton { objectName: "copyFinalButton"; text: "复制"; enabled: !!currentRecord.final; iconName: "copy"; kind: "soft"; compact: true; implicitHeight: 32; onClicked: backend.copyText(currentRecord.final) }
                            }
                            Rectangle {
                                objectName: "finalResultCard"
                                Layout.fillWidth: true; Layout.preferredHeight: window.resultCardHeight
                                radius: 16; color: Theme.card
                                ScrollView {
                                    anchors.fill: parent; anchors.margins: window.compactLayout ? 12 : 20
                                    contentWidth: availableWidth; clip: true
                                    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                                    ReadingTextArea {
                                        id: finalText; objectName: "finalText"
                                        placeholderText: s.busy ? currentRecord.stage === "judging" ? "正在评审" : "翻译中" : ""; placeholderTextColor: Theme.tertiary
                                        text: currentRecord.final || ""; textFormat: TextEdit.PlainText; readOnly: true; selectByMouse: true; wrapMode: TextEdit.Wrap
                                        font.family: Theme.font; font.weight: Theme.bodyWeight; font.pixelSize: Theme.translationSize; color: Theme.text; selectionColor: Theme.accent; selectedTextColor: "white"; padding: 0
                                        background: Item {} Accessible.name: "最终翻译结果"
                                    }
                                }
                            }
                        }
                    }
                    Rectangle {
                        visible: !!currentRecord.error
                        Layout.fillWidth: true; implicitHeight: errorRow.implicitHeight+32; radius: 12; color: Theme.card
                        RowLayout {
                            id: errorRow
                            anchors.fill: parent; anchors.margins: 16; spacing: 12
                            Icon { name: "info"; color: Theme.error }
                            Text { text: currentRecord.error || ""; color: Theme.error; font.family: Theme.font; font.weight: Theme.bodyWeight; font.pixelSize: Theme.controlSize; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                        }
                    }
                }
            }
            Loader {
                anchors.fill: parent; anchors.margins: window.width < 1180 ? 24 : 38
                anchors.leftMargin: Math.max(window.width < 1180 ? 24 : 38,(parent.width-1100)/2)
                anchors.rightMargin: anchors.leftMargin
                active: window.page === "settings"; visible: active
                sourceComponent: SettingsPage {}
            }
        }
    }
    JudgeAnalysis { id: analysis; parent: Overlay.overlay }
    Popup {
        id: finalReader
        objectName: "finalTranslationReader"
        parent: Overlay.overlay
        width: Math.min(940, window.width - 60)
        height: Math.min(760, window.height - 70)
        x: (parent.width - width) / 2; y: (parent.height - height) / 2
        padding: 26; modal: true; focus: true
        onOpened: finalReaderScroll.contentItem.contentY = 0
        background: Rectangle { color: Theme.card; radius: 22 }
        Overlay.modal: Rectangle { color: Theme.overlay }
        contentItem: ColumnLayout {
            spacing: 20
            RowLayout {
                Layout.fillWidth: true
                Text { text: "最终译文"; color: Theme.text; font.family: Theme.font; font.pixelSize: Theme.dialogTitleSize; font.weight: Theme.emphasisWeight; Layout.fillWidth: true }
                ArenaButton { objectName: "copyExpandedFinalButton"; text: "复制"; iconName: "copy"; kind: "ghost"; onClicked: backend.copyText(window.currentRecord.final) }
                ArenaButton { objectName: "closeFinalReaderButton"; iconName: "close"; kind: "ghost"; onClicked: finalReader.close(); Accessible.name: "关闭最终译文阅读" }
            }
            ScrollView {
                id: finalReaderScroll
                objectName: "expandedFinalScroll"
                Layout.fillWidth: true; Layout.fillHeight: true
                contentWidth: availableWidth; clip: true
                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                ReadingTextArea {
                    objectName: "expandedFinalText"
                    text: window.currentRecord.final || ""
                    textFormat: TextEdit.PlainText; readOnly: true; selectByMouse: true; wrapMode: TextEdit.Wrap
                    font.family: Theme.font; font.weight: Theme.bodyWeight; font.pixelSize: Theme.finalReadingSize
                    color: Theme.text; selectionColor: Theme.accent; selectedTextColor: "white"
                    padding: 0; rightPadding: 4; background: Item {}
                    Accessible.name: "最终翻译结果全文"
                }
            }
        }
    }
    Popup {
        id: reader
        objectName: "agentPreviewReader"
        parent: Overlay.overlay
        property string agentId: "A"
        property var candidate: (window.currentRecord.candidates || {})[agentId] || ({})
        property string reasoningText: candidate.reasoning || ""
        property string resultText: candidate.text || candidate.preview || ""
        property string committedText: candidate.text || ""
        width: Math.min(940,window.width-100)
        height: window.height-100
        x: (parent.width-width)/2; y: (parent.height-height)/2
        padding: 28; modal: true; focus: true
        background: Rectangle { color: Theme.card; radius: 22 }
        Overlay.modal: Rectangle { color: Theme.overlay }
        contentItem: ColumnLayout {
            spacing: 20
            RowLayout {
                Text { text: "Agent " + reader.agentId; color: Theme.text; font.family: Theme.font; font.pixelSize: Theme.dialogTitleSize; font.weight: Theme.emphasisWeight; Layout.fillWidth: true }
                ArenaButton { text: "复制"; iconName: "copy"; kind: "ghost"; enabled: !!reader.committedText; onClicked: backend.copyText(reader.committedText) }
                ArenaButton { iconName: "close"; kind: "ghost"; onClicked: reader.close(); Accessible.name: "关闭阅读" }
            }
            PreviewPane { objectName: "readerReasoning"; Layout.fillWidth: true; Layout.preferredHeight: Math.max(100,reader.height*0.28); heading: window.currentRecord.id ? "思考过程" : ""; muted: true; textSize: Theme.controlSize; text: reader.reasoningText; streaming: reader.candidate.status === "running" }
            PreviewPane { objectName: "readerTranslation"; Layout.fillWidth: true; Layout.fillHeight: true; heading: window.currentRecord.id ? "译文结果" : ""; textSize: Theme.readingSize; text: reader.resultText; streaming: reader.candidate.status === "running" }
            Text { visible: !!reader.candidate.error; text: reader.candidate.error || ""; color: Theme.error; font.family: Theme.font; font.weight: Theme.bodyWeight; font.pixelSize: Theme.captionSize; wrapMode: Text.WordWrap; Layout.fillWidth: true }
        }
    }
    Popup {
        id: confirmPopup
        objectName: "deleteConfirmationPopup"
        property var recordIds: []
        parent: Overlay.overlay
        width: 320; height: 144; x: (parent.width-width)/2; y: (parent.height-height)/2
        modal: true; focus: true; padding: 18
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        background: Rectangle { color: Theme.card; radius: 16 }
        Overlay.modal: Rectangle { color: Theme.overlay }
        contentItem: Item {
            Column {
                objectName: "deleteConfirmationGroup"
                anchors.centerIn: parent
                width: parent.width; height: implicitHeight
                spacing: 24
                CenteredCaption {
                    objectName: "deleteConfirmationText"
                    width: parent.width; height: contentHeight
                    elide: Text.ElideNone
                    text: "确认删除选中的 " + confirmPopup.recordIds.length + " 条记录？"
                    color: Theme.text; font.family: Theme.font; font.pixelSize: Theme.bodySize; font.weight: Theme.emphasisWeight
                }
                RowLayout {
                    objectName: "deleteConfirmationButtons"
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: 8
                    ArenaButton { objectName: "cancelHistoryDeleteButton"; text: "取消"; compact: true; textSize: Theme.bodySize; kind: "ghost"; onClicked: confirmPopup.close() }
                    ArenaButton {
                        objectName: "confirmHistoryDeleteButton"
                        text: "确认"; compact: true; textSize: Theme.bodySize; kind: "danger"; enabled: !s.busy
                        onClicked: {
                            if (!backend.deleteHistoryBatch(confirmPopup.recordIds)) return
                            historyList.endSelection()
                            confirmPopup.close()
                        }
                    }
                }
            }
        }
    }
    Rectangle {
        id: toastBanner
        objectName: "notificationToast"
        anchors.bottom: parent.bottom; anchors.bottomMargin: 24; anchors.horizontalCenter: parent.horizontalCenter
        width: Math.min(toastText.implicitWidth+36,window.width-60); height: toastText.implicitHeight+24
        visible: false; color: Theme.text; radius: 12; z: 100
        Text { id: toastText; anchors.fill: parent; anchors.margins: 12; color: Theme.card; font.family: Theme.font; font.weight: Theme.bodyWeight; font.pixelSize: Theme.controlSize; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; wrapMode: Text.WordWrap }
    }
    Timer { id: toastTimer; interval: 2600; onTriggered: toastBanner.visible=false }
}
