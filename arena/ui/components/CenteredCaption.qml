import QtQuick

Item {
    id: root
    property string text: ""
    property font font: Qt.font({family: Theme.font, pixelSize: Theme.bodySize, weight: Theme.bodyWeight})
    property alias color: glyphs.color
    property int elide: Text.ElideRight
    readonly property string displayText: elide === Text.ElideNone ? text : metrics.elidedText(text, elide, Math.max(0, width))
    readonly property rect inkRect: metrics.tightBoundingRect(displayText)
    readonly property real contentWidth: inkRect.width
    readonly property real contentHeight: inkRect.height
    implicitWidth: Math.ceil(metrics.advanceWidth(text))
    implicitHeight: Math.ceil(metrics.height)
    FontMetrics { id: metrics; font: root.font }
    Text {
        id: glyphs
        // Center the visible glyph bounds, including font bearings and baseline.
        x: (root.width - root.inkRect.width) / 2 - root.inkRect.x
        y: (root.height - root.inkRect.height) / 2 - baselineOffset - root.inkRect.y
        text: root.displayText; textFormat: Text.PlainText; wrapMode: Text.NoWrap
        font: root.font; color: Theme.text
        verticalAlignment: Text.AlignTop
    }
}
