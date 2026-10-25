import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: root
    objectName: "historySelectionPane"
    property var history: []
    property string currentRecordId: ""
    property bool arenaPage: true
    property bool busy: false
    property font headingFont: Qt.font({family: Theme.font, pixelSize: Theme.bodySize, weight: Theme.bodyWeight})
    property bool selectionMode: false
    property var selectedIds: []
    readonly property int selectedCount: selectedIds.length
    readonly property bool allSelected: history.length > 0 && selectedCount === history.length
    signal restoreRequested(string recordId)
    signal bulkDeleteRequested(var recordIds)
    spacing: 8

    function toggleSelectionMode() {
        if (busy || history.length === 0) return
        if (selectionMode) endSelection()
        else selectionMode = true
    }
    function endSelection() {
        selectionDrag.resetGesture()
        selectionMode = false
        selectedIds = []
    }
    function toggleRecord(recordId) {
        if (!selectionMode || busy) return
        let next = selectedIds.slice()
        let index = next.indexOf(recordId)
        if (index === -1) next.push(recordId)
        else next.splice(index, 1)
        selectedIds = next
    }
    onHistoryChanged: {
        selectionDrag.resetGesture()
        if (history.length === 0) { endSelection(); return }
        let existing = history.map(function(record) { return record.id })
        let remaining = selectedIds.filter(function(id) { return existing.indexOf(id) !== -1 })
        if (remaining.length !== selectedIds.length) selectedIds = remaining
    }
    onBusyChanged: if (busy) endSelection()

    CenteredCaption {
        objectName: "historyHeading"
        text: "翻译记录"
        font: root.headingFont; color: Theme.text
        Layout.fillWidth: true; Layout.minimumWidth: 0; Layout.preferredHeight: 28
    }
    Item {
        id: viewport
        Layout.fillWidth: true; Layout.fillHeight: true; Layout.minimumHeight: 0
        ListView {
            id: records
            objectName: "historyList"
            anchors.fill: parent
            clip: true; model: root.history; spacing: 5
            ScrollBar.vertical: ScrollBar { id: historyScrollBar; policy: ScrollBar.AsNeeded }
            delegate: Item {
                id: entry
                required property var modelData
                readonly property bool selected: root.selectedIds.indexOf(modelData.id) !== -1
                width: records.width; height: 42
                Rectangle {
                    objectName: "historySelectionBackground" + entry.modelData.id
                    anchors.fill: parent; radius: 10; color: Theme.accentSoft
                    visible: root.selectionMode && entry.selected
                }
                RowLayout {
                    anchors.fill: parent; spacing: 14
                    Button {
                        id: recordButton
                        objectName: "historyButton" + entry.modelData.id
                        Layout.fillWidth: true; Layout.fillHeight: true; Layout.minimumWidth: 0
                        hoverEnabled: true; enabled: !root.busy
                        onClicked: {
                            if (root.selectionMode) root.toggleRecord(entry.modelData.id)
                            else root.restoreRequested(entry.modelData.id)
                        }
                        background: ButtonBackground {
                            visible: !root.selectionMode
                            baseColor: Theme.card
                            baseVisible: !root.selectionMode && root.currentRecordId === entry.modelData.id && root.arenaPage
                            hovered: !root.selectionMode && recordButton.enabled && recordButton.hovered
                            pressed: !root.selectionMode && recordButton.enabled && recordButton.down
                        }
                        contentItem: CenteredCaption {
                            objectName: "historyTitle" + entry.modelData.id
                            text: entry.modelData.title; color: Theme.text
                            font.family: Theme.font; font.weight: Theme.bodyWeight; font.pixelSize: Theme.controlSize
                        }
                        leftPadding: 11; rightPadding: 11; topPadding: 0; bottomPadding: 0
                        Accessible.name: (root.selectionMode ? "选择翻译 " : "恢复翻译 ") + entry.modelData.title
                        Accessible.checkable: root.selectionMode
                        Accessible.checked: entry.selected
                    }
                    Button {
                        objectName: "historyCheck" + entry.modelData.id
                        visible: root.selectionMode; enabled: !root.busy
                        implicitWidth: 26; implicitHeight: 26
                        leftPadding: 4; rightPadding: 4; topPadding: 4; bottomPadding: 4
                        contentItem: Rectangle {
                            radius: width / 2
                            color: entry.selected ? Theme.accent : "transparent"
                            border.width: 1; border.color: entry.selected ? Theme.accent : Theme.tertiary
                            Icon { anchors.centerIn: parent; width: 14; height: 14; name: "check"; color: "white"; visible: entry.selected }
                        }
                        background: Item {}
                        onClicked: root.toggleRecord(entry.modelData.id)
                        Accessible.role: Accessible.CheckBox
                        Accessible.name: "选择翻译 " + entry.modelData.title
                        Accessible.checkable: true; Accessible.checked: entry.selected
                    }
                }
            }
        }
        MouseArea {
            id: selectionDrag
            objectName: "historySelectionGesture"
            anchors.fill: parent
            anchors.rightMargin: historyScrollBar.visible ? historyScrollBar.width : 0
            enabled: root.selectionMode && !root.busy
            acceptedButtons: Qt.LeftButton
            preventStealing: true
            pressAndHoldInterval: 350
            property int pressIndex: -1
            property real pressY: 0
            property real pointerY: 0
            property bool rangeActive: false
            property bool selecting: true
            property var originalIds: []
            property int lastIndex: -1

            function resetGesture() {
                pressIndex = -1
                rangeActive = false
                originalIds = []
                lastIndex = -1
            }
            function indexAtY(y, nearest) {
                let index = records.indexAt(4, records.contentY + y)
                if (index < 0 && nearest && root.history.length > 0)
                    index = Math.max(0, Math.min(root.history.length - 1, Math.floor((records.contentY + y) / (42 + records.spacing))))
                return index
            }
            function updateRange() {
                if (pressIndex < 0 || !rangeActive) return
                let end = indexAtY(Math.max(0, Math.min(height - 1, pointerY)), true)
                if (end < 0 || end === lastIndex) return
                lastIndex = end
                let first = Math.min(pressIndex, end), last = Math.max(pressIndex, end)
                let affected = root.history.slice(first, last + 1).map(function(record) { return record.id })
                let affectedIds = new Set(affected)
                let next = originalIds.filter(function(id) { return !affectedIds.has(id) })
                root.selectedIds = selecting ? next.concat(affected) : next
            }
            onPressed: mouse => {
                pressIndex = indexAtY(mouse.y, false)
                if (pressIndex < 0) { mouse.accepted = false; return }
                pressY = mouse.y; pointerY = mouse.y
                originalIds = root.selectedIds.slice()
                selecting = originalIds.indexOf(root.history[pressIndex].id) === -1
                rangeActive = false
                lastIndex = -1
            }
            onPositionChanged: mouse => {
                pointerY = mouse.y
                if (pressIndex < 0 || !pressed) return
                if (Math.abs(pointerY - pressY) >= 8) rangeActive = true
                updateRange()
            }
            onPressAndHold: {
                if (pressIndex >= 0) { rangeActive = true; updateRange() }
            }
            onReleased: mouse => {
                pointerY = mouse.y
                if (rangeActive) updateRange()
                if (pressIndex >= 0 && !rangeActive && indexAtY(mouse.y, false) === pressIndex)
                    root.toggleRecord(root.history[pressIndex].id)
                resetGesture()
            }
            onCanceled: resetGesture()
            onWheel: wheel => wheel.accepted = false
            Timer {
                interval: 24; repeat: true
                running: selectionDrag.pressed && selectionDrag.rangeActive && (selectionDrag.pointerY < 28 || selectionDrag.pointerY > selectionDrag.height - 28)
                onTriggered: {
                    let direction = selectionDrag.pointerY < 28 ? -1 : 1
                    let minimum = records.originY
                    let maximum = Math.max(minimum, minimum + records.contentHeight - records.height)
                    records.contentY = Math.max(minimum, Math.min(maximum, records.contentY + direction * 12))
                    selectionDrag.updateRange()
                }
            }
        }
    }
    RowLayout {
        objectName: "historySelectionActions"
        visible: root.selectionMode
        Layout.fillWidth: true; spacing: 2
        ArenaButton {
            objectName: "selectAllHistoryButton"
            text: root.allSelected ? "取消全选" : "全选"
            enabled: !root.busy && root.history.length > 0
            kind: "ghost"; compact: true; foreground: Theme.accent
            implicitHeight: 32; leftPadding: 6; rightPadding: 6
            implicitWidth: contentItem.implicitWidth + leftPadding + rightPadding
            onClicked: root.selectedIds = root.allSelected ? [] : root.history.map(function(record) { return record.id })
        }
        Item { Layout.fillWidth: true }
        ArenaButton {
            objectName: "deleteSelectedHistoryButton"
            text: "删除"
            enabled: !root.busy && root.selectedCount > 0
            kind: "ghost"; compact: true; foreground: Theme.error
            implicitHeight: 32; leftPadding: 6; rightPadding: 6
            implicitWidth: contentItem.implicitWidth + leftPadding + rightPadding
            onClicked: root.bulkDeleteRequested(root.selectedIds.slice())
            Accessible.name: "删除选中的 " + root.selectedCount + " 条翻译记录"
        }
    }
}
