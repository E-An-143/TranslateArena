pragma Singleton
import QtQuick
QtObject {
    property bool dark: false
    readonly property color background: dark ? "#18181b" : "#f5f5f7"
    readonly property color sidebar: dark ? "#202023" : "#ededf0"
    readonly property color card: dark ? "#252529" : "#ffffff"
    readonly property color raised: dark ? "#303035" : "#fafafb"
    readonly property color text: dark ? "#f0f0f2" : "#1d1d1f"
    readonly property color secondary: dark ? "#a6a6af" : "#777780"
    readonly property color tertiary: dark ? "#787882" : "#a0a0a8"
    readonly property color line: dark ? "#38383e" : "#e7e7eb"
    readonly property color hover: dark ? "#35353c" : "#e5e5ea"
    readonly property color accent: dark ? "#6aa1ff" : "#3478f6"
    readonly property color accentSoft: dark ? "#293750" : "#edf3ff"
    readonly property color success: dark ? "#75bc9b" : "#398566"
    readonly property color error: dark ? "#e2928c" : "#b65550"
    readonly property color overlay: "#65000000"
    readonly property string font: "MiSans"
    // Use the bundled typeface's original Regular / Medium weight values.
    readonly property int bodyWeight: 330
    readonly property int emphasisWeight: 380
    // Logical pixel sizes; each text role has one explicit size across the UI.
    readonly property int tinySize: 12
    readonly property int captionSize: 13
    readonly property int controlSize: 14
    readonly property int bodySize: 15
    readonly property int cardTitleSize: 16
    readonly property int sectionTitleSize: 18
    readonly property int scoreSize: 19
    readonly property int dialogTitleSize: 24
    readonly property int pageTitleSize: 30
    readonly property int previewSize: bodySize
    readonly property int sourceSize: 17
    readonly property int judgeSize: 17
    readonly property int translationSize: 17
    readonly property int readingSize: 17
    readonly property int finalReadingSize: 19
    readonly property real readingLineHeight: 1.3
    readonly property int radius: 16
    function identity(i) { return ["#738ca7", "#829480", "#a58b79"][i] }
}
