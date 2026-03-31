from __future__ import annotations

import os
import sys

from PySide6.QtCore import QUrl
from PySide6.QtWebEngineCore import QWebEngineProfile
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication


def run_ui() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("MindFlow")

    # Disable disk cache so Vite HMR and fresh builds always reflect immediately.
    profile = QWebEngineProfile.defaultProfile()
    profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.NoCache)

    view = QWebEngineView()
    view.setWindowTitle("MindFlow")
    view.resize(1440, 900)

    frontend_url = os.getenv("MINDFLOW_FRONTEND_URL", "http://127.0.0.1:5173")
    view.setUrl(QUrl(frontend_url))
    view.show()

    raise SystemExit(app.exec())


def run() -> None:
    run_ui()


if __name__ == "__main__":
    run()
