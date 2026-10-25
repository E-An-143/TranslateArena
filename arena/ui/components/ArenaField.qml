import QtQuick
import QtQuick.Controls
TextField {
    id: control
    implicitHeight: 44
    font.family: Theme.font; font.weight: Theme.bodyWeight; font.pixelSize: Theme.bodySize
    color: Theme.text; placeholderTextColor: Theme.tertiary
    selectionColor: Theme.accent; selectedTextColor: "white"
    leftPadding: 12; rightPadding: 12
    selectByMouse: true
    background: Rectangle { radius: 10; color: Theme.background; border.width: control.activeFocus ? 1.5 : 0; border.color: Theme.accent }
}
