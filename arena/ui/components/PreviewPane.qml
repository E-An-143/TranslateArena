import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: pane
    property string heading: ""
    property string text: ""
    property bool showsResult: false
    property int textSize: Theme.previewSize
    property bool muted: false
    property bool streaming: false
    property bool compact: false
    property int contentMargin: compact ? 8 : 10
    property string errorText: ""
    property string errorObjectName: ""
    property bool followTail: true
    property int viewRevision: 0
    color: Theme.background
    radius: 10
    onHeadingChanged: {
        pane.followTail = true
        pane.resetScroll()
    }
    onShowsResultChanged: {
        pane.viewRevision += 1
        pane.followTail = true
        pane.resetScroll()
    }

    function resetScroll() {
        Qt.callLater(function() { scroll.contentItem.contentY = 0 })
    }

    function followStream() {
        let revision = pane.viewRevision
        Qt.callLater(function() {
            // A callback queued for the thought stream must not scroll the result.
            if (revision !== pane.viewRevision || !pane.streaming || !pane.followTail) return
            let flick = scroll.contentItem
            flick.contentY = Math.max(0, flick.contentHeight - flick.height)
        })
    }

    component PreviewText: TextArea {
        objectName: pane.objectName + "Text"
        text: pane.text
        readOnly: true; selectByMouse: true; wrapMode: TextEdit.Wrap
        textFormat: TextEdit.PlainText
        font.family: Theme.font; font.weight: Theme.bodyWeight; font.pixelSize: pane.textSize
        color: pane.muted ? Theme.secondary : Theme.text
        selectionColor: Theme.accent; selectedTextColor: "white"
        padding: 0; leftPadding: 0; rightPadding: 4; topPadding: 0; bottomPadding: 0
        background: Item {}
        Accessible.name: pane.heading
        onTextChanged: {
            if (!text) pane.followTail = true
            if (pane.streaming && pane.followTail) pane.followStream()
        }
    }
    Component { id: thoughtText; PreviewText {} }
    Component { id: resultText; PreviewText {} }

    function atEnd() {
        let flick = scroll.contentItem
        return flick.contentHeight - flick.height - flick.contentY <= 24
    }
    ColumnLayout {
        anchors.fill: parent; anchors.margins: pane.contentMargin; spacing: pane.compact ? 4 : 8
        Text {
            objectName: pane.objectName + "Heading"
            visible: !!pane.heading
            text: pane.heading; color: Theme.secondary; font.family: Theme.font
            font.pixelSize: Theme.bodySize; font.weight: Theme.emphasisWeight
        }
        ScrollView {
            id: scroll
            objectName: pane.objectName + "Scroll"
            Layout.fillWidth: true; Layout.fillHeight: true
            clip: true; contentWidth: availableWidth
            leftPadding: 0; rightPadding: previewScrollBar.width + 4
            topPadding: 0; bottomPadding: 0
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
            ScrollBar.vertical: ScrollBar {
                id: previewScrollBar
                objectName: pane.objectName + "ScrollBar"
                parent: scroll
                x: scroll.width - width; y: scroll.topPadding
                height: scroll.availableHeight
                policy: ScrollBar.AsNeeded
                onPressedChanged: if (!pressed) pane.followTail = pane.atEnd()
            }
            Loader {
                id: bodyLoader
                width: scroll.availableWidth
                // Use a fresh text item when thoughts become a committed result.
                sourceComponent: pane.showsResult ? resultText : thoughtText
                onLoaded: {
                    item.cursorPosition = 0
                    pane.resetScroll()
                }
            }
            Connections {
                target: scroll.contentItem
                function onMovementEnded() { pane.followTail = pane.atEnd() }
            }
        }
        Text {
            objectName: pane.errorObjectName
            visible: !!pane.errorText
            text: pane.errorText; color: Theme.error
            font.family: Theme.font; font.weight: Theme.bodyWeight; font.pixelSize: Theme.captionSize
            Layout.fillWidth: true
            maximumLineCount: 1; elide: Text.ElideRight
        }
    }
}
