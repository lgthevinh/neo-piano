from pathlib import Path


def qml_root() -> Path:
    """Return the installed QML directory."""
    return Path(__file__).parent / "qml"


def main_qml_path() -> Path:
    """Return the QML application entry point."""
    return qml_root() / "MainWindow.qml"

