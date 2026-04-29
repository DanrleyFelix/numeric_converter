import main as app_main
from src.main.runtime_root import resolve_application_root


class _FakeApplication:
    instances: list["_FakeApplication"] = []

    def __init__(self, argv):
        self.argv = argv
        self.exec_called = False
        _FakeApplication.instances.append(self)

    def exec(self) -> int:
        self.exec_called = True
        return 73


class _FakeWindow:
    def __init__(self):
        self.shown = False

    def show(self) -> None:
        self.shown = True


def test_main_entrypoint_shows_main_window(monkeypatch):
    window = _FakeWindow()

    monkeypatch.setattr(app_main, "QApplication", _FakeApplication)
    monkeypatch.setattr(app_main, "create_main_window", lambda: window)

    exit_code = app_main.main()

    assert exit_code == 73
    assert window.shown is True
    assert _FakeApplication.instances[-1].exec_called is True


def test_runtime_root_resolves_to_project_root():
    assert resolve_application_root().name == "numeric_converter"
