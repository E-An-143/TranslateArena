import QtQuick

Item {
    id: root
    property color baseColor: Theme.card
    property color hoverColor: Theme.hover
    property color pressedColor: Theme.line
    property bool baseVisible: true
    property bool hovered: false
    property bool pressed: false
    property real radius: 10
    property int duration: 110

    // Fade opaque layers only; interpolating transparent black causes dark flashes.
    // Focus remains available to keyboard users without adding a button outline.
    Rectangle {
        anchors.fill: parent; radius: root.radius; color: root.baseColor
        opacity: root.baseVisible ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: root.duration } }
    }
    Rectangle {
        anchors.fill: parent; radius: root.radius; color: root.hoverColor
        opacity: root.hovered ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: root.duration } }
    }
    Rectangle {
        anchors.fill: parent; radius: root.radius; color: root.pressedColor
        opacity: root.pressed ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: root.duration } }
    }
}
