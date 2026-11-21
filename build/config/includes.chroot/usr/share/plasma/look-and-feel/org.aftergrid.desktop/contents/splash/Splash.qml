import QtQuick

Rectangle {
    id: root
    color: "#14171a"
    property int stage
    Image {
        id: logo
        anchors.centerIn: parent
        anchors.verticalCenterOffset: -30
        source: "images/aftergrid.png"
        width: 240; fillMode: Image.PreserveAspectFit; smooth: true
        opacity: 0
        OpacityAnimator on opacity { from: 0; to: 1; duration: 600; running: true }
    }
    Rectangle {
        anchors.top: logo.bottom; anchors.topMargin: 36; anchors.horizontalCenter: parent.horizontalCenter
        width: 240; height: 4; color: "#262d33"
        Rectangle { height: parent.height; color: "#f2a33a"; width: parent.width * Math.min(root.stage, 6) / 6
            Behavior on width { NumberAnimation { duration: 400 } } }
    }
}
