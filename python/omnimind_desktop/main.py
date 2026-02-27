from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from omnimind_desktop.viewmodels import ChatViewModel, MindViewModel


def run() -> None:
    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Fusion")

    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()

    chat_vm = ChatViewModel()
    mind_vm = MindViewModel()

    engine.rootContext().setContextProperty("chatVM", chat_vm)
    engine.rootContext().setContextProperty("mindVM", mind_vm)

    qml_file = Path(__file__).resolve().parent / "qml" / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_file)))

    if not engine.rootObjects():
        raise SystemExit(1)

    raise SystemExit(app.exec())


if __name__ == "__main__":
    run()
