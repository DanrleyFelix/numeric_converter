from __future__ import annotations

import sys

from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

from src.main.resource_paths import fonts_root

WINDOWS_FONT_CANDIDATES = ("Segoe UI", "Arial", "Tahoma")
MACOS_FONT_CANDIDATES = (
    ".AppleSystemUIFont",
    "SF Pro Text",
    "Helvetica Neue",
)
LINUX_FONT_CANDIDATES = (
    "Noto Sans",
    "DejaVu Sans",
    "Ubuntu",
    "Liberation Sans",
)


def configure_application_defaults(app: QApplication) -> None:
    _load_packaged_fonts()
    font = _resolve_default_font()
    if font is not None:
        app.setFont(font)


def _load_packaged_fonts() -> None:
    directory = fonts_root()
    if not directory.exists():
        return

    for font_path in directory.iterdir():
        if font_path.suffix.lower() not in {".ttf", ".otf"}:
            continue
        QFontDatabase.addApplicationFont(str(font_path))


def _resolve_default_font() -> QFont | None:
    available_families = set(QFontDatabase.families())
    for family in _platform_font_candidates():
        if family in available_families:
            return QFont(family)
    return None


def _platform_font_candidates() -> tuple[str, ...]:
    if sys.platform == "win32":
        return WINDOWS_FONT_CANDIDATES
    if sys.platform == "darwin":
        return MACOS_FONT_CANDIDATES
    return LINUX_FONT_CANDIDATES
