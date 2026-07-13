import logging
import sys

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtQml import QQmlApplicationEngine

from neo_piano.audio import AudioEngine
from neo_piano.ui.qml_loader import main_qml_path, qml_root

logger = logging.getLogger(__name__)


def run() -> int:
    """Start the Qt application and return its exit code."""
    app = QGuiApplication(sys.argv)
    app.setApplicationName("NEO Piano")
    app.setApplicationDisplayName("NEO Piano")
    app.setOrganizationName("MakerViet")

    audio = AudioEngine()
    audio.start()
    app.aboutToQuit.connect(audio.close)

    engine = QQmlApplicationEngine()
    engine.addImportPath(str(qml_root()))
    context = engine.rootContext()
    if context is None:
        logger.error("Failed to create the QML context")
        audio.close()
        return 1
    context.setContextProperty("audioEngine", audio)
    engine.load(QUrl.fromLocalFile(str(main_qml_path())))

    if not engine.rootObjects():
        logger.error("Failed to load the NEO Piano QML interface")
        audio.close()
        return 1

    return app.exec()
