import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

ApplicationWindow {
    id: root
    width: 1024
    height: 600
    minimumWidth: 720
    minimumHeight: 480
    visible: true
    title: "NEO Piano"
    color: white

    readonly property color white: "#FFFFFF"
    readonly property color canvas: "#F5F8F6"
    readonly property color ink: "#17201B"
    readonly property color muted: "#5A6760"
    readonly property color border: "#DDE6E1"
    readonly property color primary: "#02D962"
    readonly property color secondary: "#2E77E7"
    readonly property color danger: "#FE2151"

    property bool controlsExpanded: true
    property int keyCount: 5
    property var activeNotes: ({})
    property var keyDefinitions: [
        { "note": 60, "label": "←", "key": Qt.Key_Left },
        { "note": 62, "label": "↑", "key": Qt.Key_Up },
        { "note": 64, "label": "→", "key": Qt.Key_Right },
        { "note": 65, "label": "↓", "key": Qt.Key_Down },
        { "note": 67, "label": "SPACE", "key": Qt.Key_Space },
        { "note": 69, "label": "A", "key": Qt.Key_A },
        { "note": 71, "label": "S", "key": Qt.Key_S },
        { "note": 72, "label": "D", "key": Qt.Key_D },
        { "note": 74, "label": "F", "key": Qt.Key_F },
        { "note": 76, "label": "G", "key": Qt.Key_G },
        { "note": 77, "label": "H", "key": Qt.Key_H },
        { "note": 79, "label": "J", "key": Qt.Key_J }
    ]
    property var blackKeyDefinitions: [
        { "after": 0, "note": 61 },
        { "after": 1, "note": 63 },
        { "after": 3, "note": 66 },
        { "after": 4, "note": 68 },
        { "after": 5, "note": 70 },
        { "after": 7, "note": 73 },
        { "after": 8, "note": 75 },
        { "after": 10, "note": 78 }
    ]
    property var visibleKeys: keyDefinitions.slice(0, keyCount)

    function noteForKey(key) {
        for (let index = 0; index < visibleKeys.length; index++) {
            if (visibleKeys[index].key === key)
                return visibleKeys[index].note
        }
        return -1
    }

    function pressNote(note) {
        if (note < 0 || activeNotes[note] || !audioEngine || !audioEngine.ready)
            return
        let next = Object.assign({}, activeNotes)
        next[note] = true
        activeNotes = next
        audioEngine.noteOn(note, 100)
    }

    function releaseNote(note) {
        if (note < 0 || !activeNotes[note])
            return
        let next = Object.assign({}, activeNotes)
        delete next[note]
        activeNotes = next
        if (audioEngine)
            audioEngine.noteOff(note)
    }

    function releaseAllNotes() {
        activeNotes = ({})
        if (audioEngine)
            audioEngine.allNotesOff()
    }

    onActiveChanged: {
        if (!active)
            releaseAllNotes()
    }

    header: ToolBar {
        implicitHeight: 64
        background: Rectangle { color: root.ink }

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 24
            anchors.rightMargin: 24
            spacing: 16

            Label {
                text: "NEO Piano"
                color: root.white
                font.family: "Noto Sans"
                font.pixelSize: 22
                font.weight: Font.DemiBold
                Layout.fillWidth: true
            }

            Label {
                text: audioEngine ? audioEngine.statusMessage : "Audio stopped"
                color: "#CAD4CF"
                font.family: "Noto Sans"
                font.pixelSize: 14
            }

            Rectangle {
                Layout.preferredWidth: 10
                Layout.preferredHeight: 10
                radius: 5
                color: audioEngine && audioEngine.ready ? root.primary : root.danger
            }
        }
    }

    Item {
        id: keyHandler
        anchors.fill: parent
        focus: true

        Keys.onPressed: function(event) {
            if (event.isAutoRepeat)
                return
            if (event.key === Qt.Key_Escape) {
                root.releaseAllNotes()
                event.accepted = true
                return
            }
            const note = root.noteForKey(event.key)
            if (note >= 0) {
                root.pressNote(note)
                event.accepted = true
            }
        }

        Keys.onReleased: function(event) {
            if (event.isAutoRepeat)
                return
            const note = root.noteForKey(event.key)
            if (note >= 0) {
                root.releaseNote(note)
                event.accepted = true
            }
        }

        RowLayout {
            anchors.fill: parent
            spacing: 0

            Item {
                id: mainView
                Layout.fillWidth: true
                Layout.fillHeight: true

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 32
                    spacing: 24

                    Item {
                        Layout.fillWidth: true
                        Layout.fillHeight: true

                        Item {
                            id: keyboard
                            anchors.centerIn: parent
                            width: Math.min(parent.width, root.keyCount * 112)
                            height: Math.min(parent.height, 280)

                            Repeater {
                                model: root.visibleKeys

                                Rectangle {
                                    required property int index
                                    property int midiNote: root.visibleKeys[index].note
                                    property string keyLabel: root.visibleKeys[index].label
                                    x: index * keyboard.width / root.visibleKeys.length
                                    width: keyboard.width / root.visibleKeys.length + (index === root.visibleKeys.length - 1 ? 0 : 1)
                                    height: keyboard.height
                                    color: root.activeNotes[midiNote] ? "#CBF7DD" : root.white
                                    border.color: root.activeNotes[midiNote] ? root.primary : root.ink
                                    border.width: root.activeNotes[midiNote] ? 3 : 2
                                    radius: 4

                                    Rectangle {
                                        anchors.left: parent.left
                                        anchors.right: parent.right
                                        anchors.bottom: parent.bottom
                                        height: root.activeNotes[parent.midiNote] ? 8 : 4
                                        color: root.activeNotes[parent.midiNote] ? root.primary : root.border
                                        radius: 2
                                    }

                                    Label {
                                        anchors.horizontalCenter: parent.horizontalCenter
                                        anchors.bottom: parent.bottom
                                        anchors.bottomMargin: 36
                                        text: parent.keyLabel
                                        color: root.activeNotes[parent.midiNote] ? "#075C2E" : root.ink
                                        font.family: "Noto Sans"
                                        font.pixelSize: parent.keyLabel === "SPACE" ? Math.min(18, parent.width * 0.28) : 36
                                        font.weight: Font.Bold
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        onPressed: {
                                            keyHandler.forceActiveFocus()
                                            root.pressNote(parent.midiNote)
                                        }
                                        onReleased: root.releaseNote(parent.midiNote)
                                        onCanceled: root.releaseNote(parent.midiNote)
                                    }
                                }
                            }

                            Repeater {
                                model: root.blackKeyDefinitions

                                Rectangle {
                                    required property int index
                                    property int whiteKeyIndex: root.blackKeyDefinitions[index].after
                                    property int midiNote: root.blackKeyDefinitions[index].note
                                    visible: whiteKeyIndex < root.keyCount - 1
                                    x: (whiteKeyIndex + 1) * keyboard.width / root.visibleKeys.length - width / 2
                                    width: keyboard.width / root.visibleKeys.length * 0.56
                                    height: keyboard.height * 0.58
                                    color: root.activeNotes[midiNote] ? "#075C2E" : root.ink
                                    border.color: root.activeNotes[midiNote] ? root.primary : "#0C120F"
                                    border.width: 2
                                    radius: 4
                                    z: 2

                                    Rectangle {
                                        anchors.left: parent.left
                                        anchors.right: parent.right
                                        anchors.bottom: parent.bottom
                                        height: 4
                                        color: root.activeNotes[parent.midiNote] ? root.primary : "#2D3932"
                                        radius: 2
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        onPressed: {
                                            keyHandler.forceActiveFocus()
                                            root.pressNote(parent.midiNote)
                                        }
                                        onReleased: root.releaseNote(parent.midiNote)
                                        onCanceled: root.releaseNote(parent.midiNote)
                                    }
                                }
                            }
                        }
                    }
                }
            }

            Rectangle {
                Layout.preferredWidth: root.controlsExpanded ? 240 : 56
                Layout.fillHeight: true
                color: root.canvas

                Rectangle {
                    anchors.left: parent.left
                    width: 1
                    height: parent.height
                    color: root.border
                }

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 24

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        Label {
                            visible: root.controlsExpanded
                            text: "Controls"
                            color: root.ink
                            font.family: "Noto Sans"
                            font.pixelSize: 20
                            font.weight: Font.DemiBold
                            Layout.fillWidth: true
                        }

                        ToolButton {
                            id: collapseButton
                            Layout.preferredWidth: 24
                            Layout.preferredHeight: 32
                            text: root.controlsExpanded ? "›" : "‹"
                            font.pixelSize: 24
                            onClicked: {
                                root.controlsExpanded = !root.controlsExpanded
                                keyHandler.forceActiveFocus()
                            }

                            background: Rectangle {
                                radius: 4
                                color: collapseButton.hovered ? "#E6ECE8" : "transparent"
                            }

                            ToolTip.visible: hovered
                            ToolTip.text: root.controlsExpanded ? "Collapse controls" : "Expand controls"
                        }
                    }

                    ColumnLayout {
                        visible: root.controlsExpanded
                        Layout.fillWidth: true
                        spacing: 8

                        Label {
                            text: "White keys"
                            color: root.muted
                            font.family: "Noto Sans"
                            font.pixelSize: 13
                        }

                        ComboBox {
                            id: keyCountSelect
                            Layout.fillWidth: true
                            model: ["5 keys", "8 keys", "12 keys"]
                            currentIndex: root.keyCount === 5 ? 0 : (root.keyCount === 8 ? 1 : 2)
                            onActivated: {
                                root.releaseAllNotes()
                                root.keyCount = [5, 8, 12][currentIndex]
                                keyHandler.forceActiveFocus()
                            }

                            background: Rectangle {
                                implicitHeight: 44
                                color: root.white
                                border.color: keyCountSelect.activeFocus ? root.secondary : root.border
                                border.width: keyCountSelect.activeFocus ? 2 : 1
                                radius: 8
                            }
                        }
                    }

                    ColumnLayout {
                        visible: root.controlsExpanded
                        Layout.fillWidth: true
                        spacing: 8

                        Label {
                            text: "Audio output"
                            color: root.muted
                            font.family: "Noto Sans"
                            font.pixelSize: 13
                        }

                        ComboBox {
                            id: outputSelect
                            Layout.fillWidth: true
                            model: audioEngine ? audioEngine.outputDevices : []
                            textRole: "description"
                            valueRole: "name"
                            enabled: audioEngine && !audioEngine.outputSwitching

                            function selectCurrentOutput() {
                                if (!audioEngine)
                                    return
                                for (let index = 0; index < count; index++) {
                                    if (valueAt(index) === audioEngine.selectedOutputDevice) {
                                        currentIndex = index
                                        return
                                    }
                                }
                                currentIndex = 0
                            }

                            onModelChanged: selectCurrentOutput()
                            onActivated: {
                                if (audioEngine)
                                    audioEngine.setOutputDevice(currentValue)
                                keyHandler.forceActiveFocus()
                            }

                            Connections {
                                target: audioEngine
                                function onSelectedOutputDeviceChanged() {
                                    outputSelect.selectCurrentOutput()
                                }
                            }

                            background: Rectangle {
                                implicitHeight: 44
                                color: root.white
                                border.color: outputSelect.activeFocus ? root.secondary : root.border
                                border.width: outputSelect.activeFocus ? 2 : 1
                                radius: 8
                            }
                        }
                    }

                    Item { Layout.fillHeight: true }
                }
            }
        }
    }

    Component.onCompleted: {
        keyHandler.forceActiveFocus()
        if (audioEngine)
            audioEngine.refreshOutputDevices()
    }
}
