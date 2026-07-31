import QtQuick 2.10
import QtQuick.Controls 2.3
import QtQuick.Layouts 1.3
import UM 1.5 as UM

Component
{
    Item
    {
        id: base
        anchors.fill: parent

        ScrollView
        {
            id: monitorScroll
            anchors.fill: parent
            clip: true

            ColumnLayout
            {
                width: Math.max(420, monitorScroll.availableWidth)
                spacing: UM.Theme.getSize("default_margin").height

                Item { Layout.preferredHeight: UM.Theme.getSize("default_margin").height }

                UM.Label
                {
                    text: "QIDI Legacy Network"
                    font: UM.Theme.getFont("large")
                    Layout.leftMargin: UM.Theme.getSize("default_margin").width
                }

                UM.Label
                {
                    text: OutputDevice.addressText
                    color: UM.Theme.getColor("text_inactive")
                    Layout.leftMargin: UM.Theme.getSize("default_margin").width
                }

                GridLayout
                {
                    columns: 2
                    columnSpacing: UM.Theme.getSize("default_margin").width
                    rowSpacing: UM.Theme.getSize("narrow_margin").height
                    Layout.fillWidth: true
                    Layout.leftMargin: UM.Theme.getSize("default_margin").width
                    Layout.rightMargin: UM.Theme.getSize("default_margin").width

                    UM.Label { text: "Cura communication" }
                    UM.Label
                    {
                        text: OutputDevice.communicationStateText
                        font: UM.Theme.getFont("medium")
                    }

                    UM.Label { text: "Connection" }
                    UM.Label { text: OutputDevice.connectionStatusText; font: UM.Theme.getFont("medium") }

                    UM.Label { text: "Printer state" }
                    UM.Label { text: OutputDevice.printerStateText; font: UM.Theme.getFont("medium") }

                    UM.Label { text: "File" }
                    UM.Label { text: OutputDevice.filenameText; elide: Text.ElideMiddle; Layout.fillWidth: true }

                    UM.Label { text: "Bed" }
                    UM.Label { text: OutputDevice.bedTemperatureText }

                    UM.Label { text: "Extruder E1" }
                    UM.Label { text: OutputDevice.extruder1TemperatureText }

                    UM.Label { text: "Extruder E2" }
                    UM.Label { text: OutputDevice.extruder2TemperatureText }

                    UM.Label { text: "Position" }
                    UM.Label { text: OutputDevice.positionText }

                    UM.Label { text: "Elapsed" }
                    UM.Label { text: OutputDevice.elapsedText }

                    UM.Label { text: "Last update" }
                    UM.Label { text: OutputDevice.lastUpdateText }
                }

                UM.Label
                {
                    text: OutputDevice.communicationNoticeText
                    wrapMode: Text.WordWrap
                    color: OutputDevice.communicationPaused
                        ? UM.Theme.getColor("error")
                        : UM.Theme.getColor("text_inactive")
                    Layout.fillWidth: true
                    Layout.leftMargin: UM.Theme.getSize("default_margin").width
                    Layout.rightMargin: UM.Theme.getSize("default_margin").width
                }

                ColumnLayout
                {
                    visible: OutputDevice.hasProgress
                    Layout.fillWidth: true
                    Layout.leftMargin: UM.Theme.getSize("default_margin").width
                    Layout.rightMargin: UM.Theme.getSize("default_margin").width

                    UM.Label { text: OutputDevice.progressText }
                    ProgressBar
                    {
                        from: 0
                        to: 100
                        value: OutputDevice.progressPercent
                        Layout.fillWidth: true
                    }
                }

                UM.Label
                {
                    visible: OutputDevice.monitorErrorText.length > 0
                    text: OutputDevice.monitorErrorText
                    wrapMode: Text.WordWrap
                    color: UM.Theme.getColor("error")
                    Layout.fillWidth: true
                    Layout.leftMargin: UM.Theme.getSize("default_margin").width
                    Layout.rightMargin: UM.Theme.getSize("default_margin").width
                }

                UM.Label
                {
                    text: "Read-only status monitoring. Network uploads remain content-unverified; use removable USB media for important prints."
                    wrapMode: Text.WordWrap
                    color: UM.Theme.getColor("text_inactive")
                    Layout.fillWidth: true
                    Layout.leftMargin: UM.Theme.getSize("default_margin").width
                    Layout.rightMargin: UM.Theme.getSize("default_margin").width
                }

                Item { Layout.fillHeight: true }
            }
        }
    }
}
