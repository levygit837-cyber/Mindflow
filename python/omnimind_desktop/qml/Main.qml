import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

ApplicationWindow {
    id: root
    width: 1480
    height: 920
    visible: true
    title: "OmniMind"
    color: "#080b10"

    property bool technicalMode: false
    property string activeSessionId: ""
    property string activeRunId: ""
    property string activeFolderPath: ""
    property string selectedSourceSessionId: ""
    property string selectedTargetSessionId: ""

    ListModel { id: chatSessionsModel }
    ListModel { id: chatEventsModel }

    ListModel { id: allowlistModel }
    ListModel { id: projectsModel }
    ListModel { id: projectSessionsModel }
    ListModel { id: linksModel }

    function parseJsonSafe(raw) {
        try { return JSON.parse(raw) } catch (e) { return null }
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

        if (evt.type === "agent_step" && !root.technicalMode && meta.userVisible === false) {
            return
        }

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

    Component.onCompleted: {
        chatVM.loadSessions()
        mindVM.loadAllowlist()
        mindVM.loadProjects()
    }

    Connections {
        target: chatVM
        function onSessionsLoaded(raw) {
            const data = parseJsonSafe(raw) || []
            chatSessionsModel.clear()
            for (let i = 0; i < data.length; i++) {
                chatSessionsModel.append(data[i])
            }
            if (data.length > 0 && !root.activeSessionId) {
                root.activeSessionId = data[0].id
                chatVM.loadSessionMessages(root.activeSessionId, "")
            }
        }

        function onMessagesLoaded(raw) {
            const data = parseJsonSafe(raw) || []
            chatEventsModel.clear()
            root.activeRunId = ""
            for (let i = 0; i < data.length; i++) {
                const msg = data[i]
                const runId = msg.runId || ""
                if (runId && runId !== root.activeRunId) {
                    root.activeRunId = runId
                    chatEventsModel.append({
                        kind: "run_separator",
                        title: "Run " + runId,
                        body: "",
                        color: eventColor("run_separator", ""),
                        runId: runId,
                        userVisible: true,
                        expanded: false
                    })
                }
                chatEventsModel.append({
                    kind: msg.role === "user" ? "user" : "response",
                    title: msg.role,
                    body: msg.content,
                    color: msg.role === "user" ? "#2d3d58" : eventColor("response", "response"),
                    category: "response",
                    runId: runId,
                    userVisible: true,
                    expanded: false
                })
                if (msg.thoughts) {
                    chatEventsModel.append({
                        kind: "thought",
                        title: "thinking",
                        body: msg.thoughts,
                        color: eventColor("thought", ""),
                        category: "",
                        runId: runId,
                        userVisible: true,
                        expanded: false
                    })
                }
            }
            chatListView.positionViewAtEnd()
        }

        function onStreamEvent(raw) {
            const evt = parseJsonSafe(raw)
            if (!evt)
                return
            if (evt.type === "session_created") {
                chatVM.refreshSessions()
                return
            }
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
        }
    }

    Connections {
        target: mindVM

        function onAllowlistLoaded(raw) {
            const data = parseJsonSafe(raw) || []
            allowlistModel.clear()
            for (let i = 0; i < data.length; i++)
                allowlistModel.append(data[i])
        }

        function onProjectsLoaded(raw) {
            const data = parseJsonSafe(raw) || []
            projectsModel.clear()
            for (let i = 0; i < data.length; i++)
                projectsModel.append(data[i])
        }

        function onSessionsLoaded(raw) {
            const data = parseJsonSafe(raw) || []
            projectSessionsModel.clear()
            for (let i = 0; i < data.length; i++)
                projectSessionsModel.append(data[i])
        }

        function onLinksLoaded(raw) {
            const data = parseJsonSafe(raw) || []
            linksModel.clear()
            for (let i = 0; i < data.length; i++)
                linksModel.append(data[i])
        }

        function onJobUpdated(raw) {
            const data = parseJsonSafe(raw)
            if (!data)
                return
            mindOutputArea.text = JSON.stringify(data, null, 2)
        }

        function onSandboxResult(raw) {
            const data = parseJsonSafe(raw)
            if (!data)
                return
            mindOutputArea.text = data.output + (data.neuralFilePath ? "\n\nNeural file: " + data.neuralFilePath : "")
        }

        function onErrorOccurred(message) {
            mindOutputArea.text = "Error: " + message
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

    TabBar {
        id: tabBar
        width: parent.width
        background: Rectangle { color: "#0b0f15"; border.color: "#1a2430" }
        TabButton { text: "Chat" }
        TabButton { text: "Mind" }
    }

    StackLayout {
        anchors {
            top: tabBar.bottom
            left: parent.left
            right: parent.right
            bottom: parent.bottom
        }
        currentIndex: tabBar.currentIndex

        Item {
            anchors.fill: parent
            RowLayout {
                anchors.fill: parent
                spacing: 0

                Rectangle {
                    Layout.preferredWidth: 320
                    Layout.fillHeight: true
                    color: "#0d1218"
                    border.color: "#1b2632"

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 8

                        Label { text: "Sessions"; color: "#e9f0ff"; font.bold: true }

                        RowLayout {
                            TextField {
                                id: newSessionTitle
                                Layout.fillWidth: true
                                placeholderText: "New session title"
                                color: "#d6e0ef"
                                placeholderTextColor: "#6f8198"
                                background: Rectangle { color: "#141d28"; radius: 8; border.color: "#2a3b50" }
                            }
                            Button {
                                text: "+"
                                onClicked: {
                                    chatVM.createStandaloneSession(newSessionTitle.text, "")
                                    newSessionTitle.text = ""
                                }
                            }
                        }

                        ListView {
                            id: sessionsList
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            model: chatSessionsModel
                            spacing: 6
                            clip: true
                            delegate: Rectangle {
                                width: sessionsList.width
                                height: 66
                                radius: 10
                                color: model.id === root.activeSessionId ? "#21344f" : "#121a24"
                                border.color: model.id === root.activeSessionId ? "#3b6da5" : "#263547"
                                Behavior on color { ColorAnimation { duration: 180 } }

                                MouseArea {
                                    anchors.fill: parent
                                    onClicked: {
                                        root.activeSessionId = model.id
                                        root.activeRunId = ""
                                        chatVM.loadSessionMessages(model.id, "")
                                    }
                                }

                                Column {
                                    anchors.fill: parent
                                    anchors.margins: 8
                                    spacing: 2
                                    Text {
                                        text: model.title
                                        color: "#e9f1ff"
                                        font.bold: true
                                        elide: Text.ElideRight
                                        width: parent.width
                                    }
                                    Text {
                                        text: (model.topic_type || "standalone") + (model.folder_path ? " • " + model.folder_path : "")
                                        color: "#8ea1b7"
                                        font.pixelSize: 11
                                        elide: Text.ElideRight
                                        width: parent.width
                                    }
                                }
                            }
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    color: "#0a0f14"
                    border.color: "#1b2632"

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 10

                        Label {
                            text: root.activeSessionId ? "Chat • Session " + root.activeSessionId : "Chat"
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
                                Layout.preferredHeight: 84
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
                                Layout.preferredWidth: 180
                                TextField {
                                    id: providerInput
                                    placeholderText: "provider (optional)"
                                    color: "#dce8fa"
                                    placeholderTextColor: "#6d829c"
                                    background: Rectangle { radius: 8; color: "#141d29"; border.color: "#2a3f56" }
                                }
                                TextField {
                                    id: modelInput
                                    placeholderText: "model (optional)"
                                    color: "#dce8fa"
                                    placeholderTextColor: "#6d829c"
                                    background: Rectangle { radius: 8; color: "#141d29"; border.color: "#2a3f56" }
                                }
                                Button {
                                    text: "Send"
                                    onClicked: {
                                        chatVM.sendMessage(chatInput.text, root.activeSessionId, providerInput.text, modelInput.text)
                                        chatInput.text = ""
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        Item {
            anchors.fill: parent

            RowLayout {
                anchors.fill: parent
                spacing: 0

                Rectangle {
                    Layout.preferredWidth: 320
                    Layout.fillHeight: true
                    color: "#0d1218"
                    border.color: "#1b2632"
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 8

                        Label { text: "Allowed Paths"; color: "#e8efff"; font.bold: true }
                        ListView {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 100
                            model: allowlistModel
                            delegate: Text {
                                text: model.path
                                width: parent.width
                                color: "#97abc4"
                                wrapMode: Text.Wrap
                            }
                        }

                        Label { text: "Projects"; color: "#e8efff"; font.bold: true }
                        TextField {
                            id: projectPathInput
                            placeholderText: "Absolute folder path"
                            color: "#dce8fa"
                            placeholderTextColor: "#6d829c"
                            background: Rectangle { radius: 8; color: "#141d29"; border.color: "#2a3f56" }
                        }
                        TextField {
                            id: projectTitleInput
                            placeholderText: "Project title"
                            color: "#dce8fa"
                            placeholderTextColor: "#6d829c"
                            background: Rectangle { radius: 8; color: "#141d29"; border.color: "#2a3f56" }
                        }
                        Button {
                            text: "Add Project"
                            onClicked: {
                                mindVM.createProject(projectPathInput.text, projectTitleInput.text, "")
                                projectPathInput.text = ""
                                projectTitleInput.text = ""
                            }
                        }

                        ListView {
                            id: projectList
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            model: projectsModel
                            spacing: 6
                            clip: true
                            delegate: Rectangle {
                                width: projectList.width
                                height: 82
                                radius: 10
                                color: model.folderPath === root.activeFolderPath ? "#20334f" : "#121a24"
                                border.color: model.folderPath === root.activeFolderPath ? "#3b6da5" : "#263547"
                                Behavior on color { ColorAnimation { duration: 180 } }

                                MouseArea {
                                    anchors.fill: parent
                                    onClicked: {
                                        root.activeFolderPath = model.folderPath
                                        mindVM.loadSessions(model.folderPath)
                                        mindVM.loadLinks(model.folderPath)
                                    }
                                }

                                Column {
                                    anchors.fill: parent
                                    anchors.margins: 8
                                    spacing: 2
                                    Text { text: model.title; color: "#ebf2ff"; font.bold: true; elide: Text.ElideRight; width: parent.width }
                                    Text { text: model.folderPath; color: "#8ea1b7"; font.pixelSize: 11; elide: Text.ElideRight; width: parent.width }
                                    Text { text: "sessions: " + model.sessionsCount; color: "#7f93aa"; font.pixelSize: 11 }
                                }
                            }
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    color: "#0a0f14"
                    border.color: "#1b2632"

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 8

                        Label { text: "Mind"; color: "#edf4ff"; font.bold: true; font.pixelSize: 18 }

                        RowLayout {
                            Layout.fillWidth: true
                            Layout.fillHeight: true

                            Rectangle {
                                Layout.preferredWidth: 420
                                Layout.fillHeight: true
                                color: "#0f1721"
                                radius: 10
                                border.color: "#2c3f56"

                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    spacing: 8

                                    Label { text: "Project Sessions"; color: "#dce8fb"; font.bold: true }
                                    ListView {
                                        id: projectSessionsList
                                        Layout.fillWidth: true
                                        Layout.fillHeight: true
                                        model: projectSessionsModel
                                        spacing: 6
                                        clip: true
                                        delegate: Rectangle {
                                            width: projectSessionsList.width
                                            height: 78
                                            radius: 8
                                            color: {
                                                if (model.id === root.selectedSourceSessionId || model.id === root.selectedTargetSessionId)
                                                    return "#26466c"
                                                return "#162332"
                                            }
                                            border.color: "#37506b"
                                            MouseArea {
                                                anchors.fill: parent
                                                onClicked: {
                                                    if (!root.selectedSourceSessionId) {
                                                        root.selectedSourceSessionId = model.id
                                                    } else if (!root.selectedTargetSessionId) {
                                                        root.selectedTargetSessionId = model.id
                                                    } else {
                                                        root.selectedSourceSessionId = model.id
                                                        root.selectedTargetSessionId = ""
                                                    }
                                                }
                                            }
                                            Column {
                                                anchors.fill: parent
                                                anchors.margins: 8
                                                spacing: 2
                                                Text { text: model.title; color: "#edf5ff"; font.bold: true; elide: Text.ElideRight; width: parent.width }
                                                Text { text: model.topic_type + (model.folder_path ? " • " + model.folder_path : ""); color: "#95a9c0"; font.pixelSize: 11; elide: Text.ElideRight; width: parent.width }
                                                Text { text: model.topic_about || ""; color: "#7f93aa"; font.pixelSize: 11; elide: Text.ElideRight; width: parent.width }
                                            }
                                        }
                                    }

                                    RowLayout {
                                        Layout.fillWidth: true
                                        TextField {
                                            id: linkLabelInput
                                            Layout.fillWidth: true
                                            placeholderText: "Link label"
                                            color: "#dce8fa"
                                            placeholderTextColor: "#6d829c"
                                            background: Rectangle { radius: 8; color: "#141d29"; border.color: "#2a3f56" }
                                        }
                                        Button {
                                            text: "Connect"
                                            enabled: root.selectedSourceSessionId !== "" && root.selectedTargetSessionId !== "" && root.activeFolderPath !== ""
                                            onClicked: {
                                                mindVM.createLink(root.activeFolderPath, root.selectedSourceSessionId, root.selectedTargetSessionId, linkLabelInput.text)
                                                linkLabelInput.text = ""
                                                root.selectedSourceSessionId = ""
                                                root.selectedTargetSessionId = ""
                                            }
                                        }
                                    }
                                }
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                color: "#0f1721"
                                radius: 10
                                border.color: "#2c3f56"

                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    spacing: 8

                                    Label { text: "Session Canvas"; color: "#dce8fb"; font.bold: true }
                                    Rectangle {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 180
                                        radius: 8
                                        color: "#101a27"
                                        border.color: "#2f4158"

                                        Repeater {
                                            model: projectSessionsModel
                                            delegate: Rectangle {
                                                width: 120
                                                height: 40
                                                radius: 8
                                                color: "#1e2d41"
                                                border.color: "#446083"
                                                x: 14 + (index % 3) * 132
                                                y: 14 + Math.floor(index / 3) * 54
                                                Text {
                                                    anchors.centerIn: parent
                                                    text: model.id.slice(0, 8)
                                                    color: "#dce8fb"
                                                    font.pixelSize: 11
                                                }
                                            }
                                        }
                                    }

                                    Label { text: "Links"; color: "#dce8fb"; font.bold: true }
                                    ListView {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 110
                                        model: linksModel
                                        clip: true
                                        delegate: Text {
                                            width: parent.width
                                            text: model.sourceSessionId + " -> " + model.targetSessionId + (model.label ? " (" + model.label + ")" : "")
                                            color: "#9cb0c8"
                                            wrapMode: Text.Wrap
                                        }
                                    }

                                    TextArea {
                                        id: mindQueryInput
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 86
                                        placeholderText: "Optional query for session supervisor or sandbox"
                                        color: "#dce8fa"
                                        placeholderTextColor: "#6d829c"
                                        wrapMode: TextEdit.Wrap
                                        background: Rectangle { radius: 8; color: "#141d29"; border.color: "#2a3f56" }
                                    }

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 8
                                        Button {
                                            text: "Analyze (Job)"
                                            enabled: root.activeFolderPath !== "" && projectSessionsModel.count > 0
                                            onClicked: {
                                                const ids = []
                                                for (let i = 0; i < projectSessionsModel.count; i++)
                                                    ids.push(projectSessionsModel.get(i).id)
                                                mindVM.createJob(root.activeFolderPath, JSON.stringify(ids), mindQueryInput.text, ids.length > 0 ? ids[0] : "")
                                            }
                                        }
                                        Button {
                                            text: "Sandbox Query"
                                            enabled: projectSessionsModel.count > 0
                                            onClicked: {
                                                const ids = []
                                                for (let i = 0; i < projectSessionsModel.count; i++)
                                                    ids.push(projectSessionsModel.get(i).id)
                                                const tools = ["Read", "Search_Function", "Search_code", "context_analysis", "context_tree", "callSupervisor", "call_analyst", "create_neural"]
                                                mindVM.sandboxQuery(root.activeFolderPath, JSON.stringify(ids), mindQueryInput.text, JSON.stringify(tools), "[]")
                                            }
                                        }
                                    }

                                    TextArea {
                                        id: mindOutputArea
                                        Layout.fillWidth: true
                                        Layout.fillHeight: true
                                        readOnly: true
                                        color: "#dce8fa"
                                        wrapMode: TextEdit.Wrap
                                        background: Rectangle { radius: 8; color: "#121a25"; border.color: "#2a3f56" }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
