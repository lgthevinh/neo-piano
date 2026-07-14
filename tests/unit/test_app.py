from pathlib import Path

from neo_piano import __version__
from neo_piano import app as app_module
from neo_piano.__main__ import main
from neo_piano.app import run


def test_application_exports_entrypoints() -> None:
    assert __version__ == "0.2.0"
    assert callable(main)
    assert callable(run)


class _FakeApplication:
    def __init__(self, arguments: list[str]) -> None:
        self.arguments = arguments
        self.metadata: dict[str, str] = {}
        self.aboutToQuit = _FakeSignal()

    def setApplicationName(self, value: str) -> None:  # noqa: N802
        self.metadata["name"] = value

    def setApplicationDisplayName(self, value: str) -> None:  # noqa: N802
        self.metadata["display_name"] = value

    def setOrganizationName(self, value: str) -> None:  # noqa: N802
        self.metadata["organization"] = value

    def exec(self) -> int:
        return 7


class _FakeEngine:
    roots: list[object] = [object()]

    def __init__(self) -> None:
        self.import_paths: list[str] = []
        self.loaded_url: object | None = None
        self.context = _FakeContext()

    def addImportPath(self, path: str) -> None:  # noqa: N802
        self.import_paths.append(path)

    def load(self, url: object) -> None:
        self.loaded_url = url

    def rootContext(self) -> "_FakeContext":  # noqa: N802
        return self.context

    def rootObjects(self) -> list[object]:  # noqa: N802
        return self.roots


class _FakeSignal:
    def __init__(self) -> None:
        self.callback = None

    def connect(self, callback) -> None:
        self.callback = callback


class _FakeContext:
    def __init__(self) -> None:
        self.properties: dict[str, object] = {}

    def setContextProperty(self, name: str, value: object) -> None:  # noqa: N802
        self.properties[name] = value


class _FakeAudioEngine:
    instances: list["_FakeAudioEngine"] = []

    def __init__(self) -> None:
        self.started = False
        self.closed = False
        self.instances.append(self)

    def start(self) -> bool:
        self.started = True
        return True

    def close(self) -> None:
        self.closed = True


def test_run_loads_qml_and_enters_event_loop(monkeypatch) -> None:
    _FakeAudioEngine.instances.clear()
    monkeypatch.setattr(app_module, "QGuiApplication", _FakeApplication)
    monkeypatch.setattr(app_module, "QQmlApplicationEngine", _FakeEngine)
    monkeypatch.setattr(app_module, "AudioEngine", _FakeAudioEngine)
    monkeypatch.setattr(app_module, "qml_root", lambda: Path("/qml"))
    monkeypatch.setattr(app_module, "main_qml_path", lambda: Path("/qml/MainWindow.qml"))

    assert run() == 7
    assert _FakeAudioEngine.instances[0].started


def test_run_fails_when_qml_has_no_root_object(monkeypatch) -> None:
    class EmptyEngine(_FakeEngine):
        roots = []

    monkeypatch.setattr(app_module, "QGuiApplication", _FakeApplication)
    monkeypatch.setattr(app_module, "QQmlApplicationEngine", EmptyEngine)
    monkeypatch.setattr(app_module, "AudioEngine", _FakeAudioEngine)

    assert run() == 1
    assert _FakeAudioEngine.instances[-1].closed
