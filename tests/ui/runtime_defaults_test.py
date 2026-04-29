from pathlib import Path

from src.main import resource_paths
from src.main import runtime_defaults
from src.main.runtime_defaults import (
    LINUX_FONT_CANDIDATES,
    MACOS_FONT_CANDIDATES,
    WINDOWS_FONT_CANDIDATES,
    _platform_font_candidates,
)


def test_resource_path_uses_resource_root(monkeypatch):
    fake_root = Path("C:/numeric-workbench")
    monkeypatch.setattr(resource_paths, "resolve_resource_root", lambda: fake_root)

    resolved = resource_paths.resource_path("data", "contexts")

    assert resolved == fake_root / "data" / "contexts"


def test_platform_font_candidates_for_windows(monkeypatch):
    monkeypatch.setattr(runtime_defaults.sys, "platform", "win32")

    assert _platform_font_candidates() == WINDOWS_FONT_CANDIDATES


def test_platform_font_candidates_for_macos(monkeypatch):
    monkeypatch.setattr(runtime_defaults.sys, "platform", "darwin")

    assert _platform_font_candidates() == MACOS_FONT_CANDIDATES


def test_platform_font_candidates_for_linux(monkeypatch):
    monkeypatch.setattr(runtime_defaults.sys, "platform", "linux")

    assert _platform_font_candidates() == LINUX_FONT_CANDIDATES
