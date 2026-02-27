from __future__ import annotations

import json
from typing import Any

from PySide6.QtCore import QObject, Signal, Slot

from omnimind_desktop.api.client import OmniMindApiClient


class MindViewModel(QObject):
    allowlistLoaded = Signal(str)
    projectsLoaded = Signal(str)
    sessionsLoaded = Signal(str)
    linksLoaded = Signal(str)
    jobUpdated = Signal(str)
    sandboxResult = Signal(str)
    errorOccurred = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._api = OmniMindApiClient()

    @Slot()
    def loadAllowlist(self) -> None:
        try:
            data = self._api.get("/v1/agent/mind/allowlist")
            self.allowlistLoaded.emit(json.dumps(data))
        except Exception as exc:
            self.errorOccurred.emit(str(exc))

    @Slot()
    def loadProjects(self) -> None:
        try:
            data = self._api.get("/v1/agent/mind/projects")
            self.projectsLoaded.emit(json.dumps(data))
        except Exception as exc:
            self.errorOccurred.emit(str(exc))

    @Slot(str, str, str)
    def createProject(self, folder_path: str, title: str = "", topic_about: str = "") -> None:
        try:
            payload = {
                "folderPath": folder_path,
                "title": title or None,
                "topicAbout": topic_about or None,
            }
            self._api.post("/v1/agent/mind/projects", payload)
            self.loadProjects()
        except Exception as exc:
            self.errorOccurred.emit(str(exc))

    @Slot(str)
    def loadSessions(self, folder_path: str) -> None:
        try:
            data = self._api.get("/v1/agent/mind/sessions", params={"folderPath": folder_path})
            self.sessionsLoaded.emit(json.dumps(data))
        except Exception as exc:
            self.errorOccurred.emit(str(exc))

    @Slot(str)
    def loadLinks(self, folder_path: str) -> None:
        try:
            data = self._api.get("/v1/agent/mind/links", params={"folderPath": folder_path})
            self.linksLoaded.emit(json.dumps(data))
        except Exception as exc:
            self.errorOccurred.emit(str(exc))

    @Slot(str, str, str, str)
    def createLink(self, folder_path: str, source_session_id: str, target_session_id: str, label: str = "") -> None:
        try:
            payload = {
                "folderPath": folder_path,
                "sourceSessionId": source_session_id,
                "targetSessionId": target_session_id,
                "label": label or None,
            }
            data = self._api.post("/v1/agent/mind/links", payload)
            self.jobUpdated.emit(json.dumps({"type": "link_created", "data": data}))
            self.loadLinks(folder_path)
        except Exception as exc:
            self.errorOccurred.emit(str(exc))

    @Slot(str, str, str, str)
    def createJob(self, folder_path: str, session_ids_json: str, query: str = "", source_session_id: str = "") -> None:
        try:
            session_ids = json.loads(session_ids_json)
            payload = {
                "folderPath": folder_path,
                "sessionIds": session_ids,
                "query": query or None,
                "sourceSessionId": source_session_id or None,
            }
            data = self._api.post("/v1/agent/mind/jobs", payload)
            self.jobUpdated.emit(json.dumps(data))
        except Exception as exc:
            self.errorOccurred.emit(str(exc))

    @Slot(str)
    def pollJob(self, job_id: str) -> None:
        try:
            data = self._api.get(f"/v1/agent/mind/jobs/{job_id}")
            self.jobUpdated.emit(json.dumps(data))
        except Exception as exc:
            self.errorOccurred.emit(str(exc))

    @Slot(str, str, str, str, str)
    def sandboxQuery(
        self,
        folder_path: str,
        session_ids_json: str,
        query: str = "",
        tools_json: str = "[]",
        snippets_json: str = "[]",
    ) -> None:
        try:
            payload: dict[str, Any] = {
                "folderPath": folder_path or None,
                "sessionIds": json.loads(session_ids_json),
                "query": query or None,
                "tools": json.loads(tools_json) if tools_json else [],
                "selectedSnippets": json.loads(snippets_json) if snippets_json else [],
            }
            data = self._api.post("/v1/agent/mind/sandbox/query", payload)
            self.sandboxResult.emit(json.dumps(data))
        except Exception as exc:
            self.errorOccurred.emit(str(exc))
