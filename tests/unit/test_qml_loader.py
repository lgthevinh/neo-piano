from neo_piano.ui.qml_loader import main_qml_path, qml_root


def test_qml_root_is_packaged() -> None:
    assert qml_root().is_dir()


def test_main_qml_exists() -> None:
    path = main_qml_path()
    assert path.is_file()
    assert path.name == "MainWindow.qml"

