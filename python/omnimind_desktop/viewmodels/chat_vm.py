from __future__ import annotations

from typing import Any

import httpx
from PySide6.QtCore import QObject, QThread, Signal, Slot

from omnimind_desktop.api.client import OmniMindApiClient


class ChatStreamWorker(QThread):
    eventReceived = Signal(str)
    streamError = Signal(str)
    streamFinished = Signal()

    def __init__(self, *, url: str, payload: dict[str, Any]) -> None:
        super().__init__()
        self._url = url
        self._payload = payload

    def run(self) -> None:  # noqa: D401
        try:
            with (
                httpx.Client(timeout=None) as client,
                client.stream("POST", self._url, json=self._payload) as response,
            ):
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line:
                        continue
                    if line.startswith("data: "):
                        self.eventReceived.emit(line[6:])
        except Exception as exc:  # pragma: no cover - runtime path
            self.streamError.emit(str(exc))
        finally:
            self.streamFinished.emit()


class ChatViewModel(QObject):
    streamEvent = Signal(str)
    streamStateChanged = Signal(bool)
    errorOccurred = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._api = OmniMindApiClient()
        self._worker: ChatStreamWorker | None = None

    @Slot(str)
    def sendMessage(self, message: str) -> None:
        if not message.strip():
            return
        if self._worker is not None and self._worker.isRunning():
            self.errorOccurred.emit("A stream is already running.")
            return

        payload: dict[str, Any] = {"message": message}

        worker = ChatStreamWorker(
            url=f"{self._api.base_url}/v1/agent/chat/stream",
            payload=payload,
        )
        worker.eventReceived.connect(self._handle_stream_event)
        worker.streamError.connect(self.errorOccurred.emit)
        worker.streamFinished.connect(self._on_stream_finished)
        self._worker = worker

        self.streamStateChanged.emit(True)
        worker.start()

    def _handle_stream_event(self, raw: str) -> None:
        self.streamEvent.emit(raw)

    def _on_stream_finished(self) -> None:
        self.streamStateChanged.emit(False)
        self._worker = None
