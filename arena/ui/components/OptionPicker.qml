import QtQuick
import QtQuick.Controls

ComboBox {
    id: control
    property var options: []
    property string value: ""
    signal chosen(string value)
    model: options
    textRole: "label"
    valueRole: "value"
    currentIndex: {
        for (let i = 0; i < options.length; i++)
            if (options[i].value === value) return i
        return -1
    }
    onActivated: chosen(currentValue)
    implicitWidth: 116; implicitHeight: 34
    leftPadding: 22; rightPadding: 22; topPadding: 0; bottomPadding: 0
    hoverEnabled: true
    font.family: Theme.font; font.pixelSize: Theme.controlSize; font.weight: Theme.bodyWeight
    contentItem: CenteredCaption {
        text: control.displayText; font: control.font; color: Theme.text
    }
    indicator: Icon {
        name: "chevron"; rotation: 90; color: Theme.secondary; width: 12; height: 12
        x: control.width - width - 9; y: (control.height - height) / 2
    }
    background: ButtonBackground {
        radius: 9; baseColor: Theme.background
        hovered: control.enabled && control.hovered
        pressed: control.enabled && control.down
    }
    delegate: ItemDelegate {
        id: option
        required property var modelData
        required property int index
        objectName: control.objectName + "Option" + modelData.value
        width: menu.availableWidth; implicitHeight: 36
        highlighted: control.highlightedIndex === index
        hoverEnabled: true
        font.family: control.font.family; font.pixelSize: control.font.pixelSize
        font.weight: control.value === modelData.value ? Theme.emphasisWeight : Theme.bodyWeight
        leftPadding: 14; rightPadding: 14; topPadding: 0; bottomPadding: 0
        contentItem: CenteredCaption {
            text: modelData.label; font: option.font
            color: control.value === modelData.value ? Theme.accent : Theme.text
        }
        background: ButtonBackground {
            radius: 7; baseColor: Theme.accentSoft
            baseVisible: control.value === option.modelData.value
            hovered: option.enabled && (option.hovered || option.highlighted)
            pressed: option.enabled && option.down
        }
        Accessible.name: modelData.label
        Accessible.description: control.value === modelData.value ? "已选中" : "未选中"
    }
    popup: Popup {
        id: menu
        objectName: control.objectName + "Menu"
        width: Math.max(control.width, 160)
        implicitHeight: Math.min(optionList.contentHeight + 12, Overlay.overlay.height - 24)
        // Open upwards when the card is near the bottom of the window.
        y: control.mapToItem(Overlay.overlay, 0, control.height).y + implicitHeight + 6 > Overlay.overlay.height - 12 ? -height - 6 : control.height + 6
        padding: 6; margins: 12
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutsideParent
        background: Rectangle { color: Theme.card; radius: 12; border.width: 1; border.color: Theme.line }
        contentItem: ListView {
            id: optionList
            clip: true; implicitHeight: contentHeight
            model: control.popup.visible ? control.delegateModel : null
            currentIndex: control.highlightedIndex
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
        }
    }
}
