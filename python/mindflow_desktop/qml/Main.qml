import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

ApplicationWindow {
    id: root
    width: 1280
    height: 860
    visible: true
    title: "OmniMind"
    color: "#080b10"

    property bool technicalMode: false
    property string activeRunId: ""

    ListModel { id: chatEventsModel }

    function parseJsonSafe(raw) {
        try {
            return JSON.parse(raw)
        } catch (e) {
            return null
        }
    }

    function eventColor(kind, category) {
        if (kind === "thought") return "#4d6bb2"
        if (kind === "tool_call") return "#a87c2c"
        if (kind === "tool_result") return "#317a5a"
        if (kind === "error") return "#a33b4e"
        if (kind === "agent_step") return "#37566e"
        if (kind === "run_separator") return "#3b4553"
        if (kind === "response") {
            if (category === "decision") return "#58658e"
            if (category === "summary") return "#365c69"
            if (category === "code_result") return "#5d4f2b"
            if (category === "explanation") return "#4b525e"
            return "#4b525e"
        }
        return "#4b525e"
    }

    function appendStreamEvent(evt) {
        const meta = evt.meta || {}
        if (meta.runId && meta.runId !== root.activeRunId) {
            root.activeRunId = meta.runId
            chatEventsModel.append({
                kind: "run_separator",
                title: "Run " + meta.runId,
                body: "",
                color: eventColor("run_separator", ""),
                runId: meta.runId,
                userVisible: true,
                expanded: false
            })
        }

        if (evt.type === "agent_step" && !root.technicalMode && meta.userVisible === false)
            return

        let title = evt.type
        if (evt.type === "agent_step") {
            const stepPayload = parseJsonSafe(evt.data)
            if (stepPayload && stepPayload.stepName)
                title = stepPayload.stepName
        }

        chatEventsModel.append({
            kind: evt.type,
            title: title,
            body: evt.data || "",
            color: eventColor(evt.type, meta.category || ""),
            category: meta.category || "",
            runId: meta.runId || "",
            userVisible: meta.userVisible === undefined ? true : meta.userVisible,
            node: meta.node || "",
            nodeCategory: meta.nodeCategory || "",
            expanded: false
        })
        chatListView.positionViewAtEnd()
    }

    Connections {
        target: chatVM

        function onStreamEvent(raw) {
            const evt = parseJsonSafe(raw)
            if (!evt)
                return
            appendStreamEvent(evt)
        }

        function onErrorOccurred(message) {
            chatEventsModel.append({
                kind: "error",
                title: "error",
                body: message,
                color: eventColor("error", ""),
                runId: root.activeRunId,
                userVisible: true,
                expanded: true
            })
            chatListView.positionViewAtEnd()
        }
    }

    header: Rectangle {
        height: 56
        color: "#0d121a"
        border.color: "#1e2834"

        RowLayout {
            anchors.fill: parent
            anchors.margins: 10

            Label {
                text: "OmniMind"
                color: "#eef4ff"
                font.pixelSize: 18
                font.bold: true
            }

            Item { Layout.fillWidth: true }

            CheckBox {
                id: technicalToggle
                text: "Technical Steps"
                checked: root.technicalMode
                onToggled: root.technicalMode = checked

                indicator: Rectangle {
                    implicitWidth: 18
                    implicitHeight: 18
                    radius: 4
                    color: technicalToggle.checked ? "#3f6ec5" : "#1f2b3a"
                    border.color: "#4f6378"
                }

                contentItem: Text {
                    text: technicalToggle.text
                    color: "#aab6c7"
                    verticalAlignment: Text.AlignVCenter
                    leftPadding: 24
                }
            }
        }
    }

    Rectangle {
        anchors.fill: parent
        anchors.topMargin: header.height
        color: "#0a0f14"
        border.color: "#1b2632"

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 12
            spacing: 10

            Label {
                text: "Chat"
                color: "#eef5ff"
                font.pixelSize: 18
                font.bold: true
            }

            ListView {
                id: chatListView
                Layout.fillWidth: true
                Layout.fillHeight: true
                model: chatEventsModel
                spacing: 8
                clip: true

                delegate: Item {
                    width: chatListView.width
                    height: contentRect.implicitHeight

                    property bool expanded: model.expanded || false
                    property bool isThought: model.kind === "thought"
                    property bool isTechHidden: model.kind === "agent_step" && !root.technicalMode && model.userVisible === false

                    visible: !isTechHidden

                    Rectangle {
                        id: contentRect
                        width: parent.width
                        implicitHeight: contentCol.implicitHeight + 14
                        radius: model.kind === "run_separator" ? 8 : 10
                        color: model.kind === "run_separator" ? "#131b26" : model.color
                        border.color: model.kind === "run_separator" ? "#324257" : Qt.darker(model.color, 1.3)

                        Column {
                            id: contentCol
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.margins: 8
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 6

                            Row {
                                spacing: 8

                                Text {
                                    text: model.kind
                                    color: "#eff4ff"
                                    font.bold: true
                                    font.pixelSize: 12
                                }

                                Text {
                                    text: model.node ? (model.node + (model.nodeCategory ? " • " + model.nodeCategory : "")) : ""
                                    color: "#b8c5d8"
                                    font.pixelSize: 11
                                }

                                Text {
                                    text: model.category ? ("[" + model.category + "]") : ""
                                    color: "#d0dcf2"
                                    font.pixelSize: 11
                                }
                            }

                            Item {
                                visible: model.kind !== "run_separator"
                                width: parent.width
                                height: bodyText.implicitHeight + (toggleBtn.visible ? toggleBtn.height + 6 : 0)

                                Column {
                                    width: parent.width
                                    spacing: 6

                                    Button {
                                        id: toggleBtn
                                        visible: isThought
                                        text: expanded ? "Collapse thinking" : "Expand thinking"
                                        onClicked: expanded = !expanded
                                    }

                                    Text {
                                        id: bodyText
                                        width: parent.width
                                        text: {
                                            if (isThought && !expanded)
                                                return model.body.length > 160 ? model.body.substring(0, 160) + "..." : model.body
                                            return model.body
                                        }
                                        color: "#f2f7ff"
                                        wrapMode: Text.Wrap
                                        font.pixelSize: model.kind === "run_separator" ? 12 : 13
                                    }
                                }
                            }
                        }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true

                TextArea {
                    id: chatInput
                    Layout.fillWidth: true
                    Layout.preferredHeight: 90
                    placeholderText: "Send a message to the agent..."
                    color: "#dce8fa"
                    placeholderTextColor: "#6d829c"
                    wrapMode: TextEdit.Wrap
                    background: Rectangle {
                        radius: 10
                        color: "#141d29"
                        border.color: "#2a3f56"
                    }
                }

                ColumnLayout {
                    Layout.preferredWidth: 130

                    Label {
                        text: "Modelo: Gemini 3 Flash Preview"
                        color: "#8ea5c0"
                        wrapMode: Text.Wrap
                        font.pixelSize: 11
                    }

                    Button {
                        text: "Send"
                        onClicked: {
                            chatVM.sendMessage(chatInput.text)
                            chatInput.text = ""
                        }
                    }
                }
            }
        }
    }
}
