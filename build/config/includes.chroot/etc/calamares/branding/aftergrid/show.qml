import QtQuick 2.0;
import calamares.slideshow 1.0;

Presentation {
    id: presentation
    function nextSlide() { presentation.goToNextSlide(); }
    Timer { id: advanceTimer; interval: 9000; running: presentation.activatedInCalamares; repeat: true; onTriggered: nextSlide() }
    Slide { Rectangle { anchors.fill: parent; color: "#14171a"
        Image { id: l; source: "welcome.png"; width: 420; fillMode: Image.PreserveAspectFit; anchors.centerIn: parent; anchors.verticalCenterOffset: -40 }
        Text { anchors.top: l.bottom; anchors.topMargin: 24; anchors.horizontalCenter: parent.horizontalCenter; color: "#9aa4ad"; font.pixelSize: 16
               text: "Installing Aftergrid. The offline library is copied to the disk too." } } }
    Slide { Rectangle { anchors.fill: parent; color: "#14171a"
        Text { anchors.centerIn: parent; width: parent.width * 0.8; wrapMode: Text.WordWrap; horizontalAlignment: Text.AlignHCenter; color: "#e9ecef"; font.pixelSize: 18
               text: "Field Mode works with no internet: medical, water, food, shelter, maps and comms.\nOpen it from the desktop, or share it to phones with the hotspot." } } }
    Slide { Rectangle { anchors.fill: parent; color: "#14171a"
        Text { anchors.centerIn: parent; width: parent.width * 0.8; wrapMode: Text.WordWrap; horizontalAlignment: Text.AlignHCenter; color: "#e9ecef"; font.pixelSize: 18
               text: "Next time you start this computer, a menu lets you pick Aftergrid or your other systems." } } }
    function onActivate() { }
    function onLeave() { }
}
