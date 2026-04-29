from __future__ import annotations

import importlib.util
from pathlib import Path

from PySide6.QtGui import QFontDatabase

from src.main.resource_paths import fonts_root
from src.presentation.ui.design.icon_specs import FONT_AWESOME_SOLID_FILENAME

_FONT_FAMILY: str | None = None


def fontawesome_solid_family() -> str:
    global _FONT_FAMILY

    if _FONT_FAMILY is not None:
        return _FONT_FAMILY

    font_path = resolve_fontawesome_solid_path()
    font_id = QFontDatabase.addApplicationFont(str(font_path))
    families = QFontDatabase.applicationFontFamilies(font_id)
    if not families:
        raise RuntimeError(f"Unable to load icon font '{font_path}'.")

    _FONT_FAMILY = families[0]
    return _FONT_FAMILY


def resolve_fontawesome_solid_path() -> Path:
    packaged_path = fonts_root() / FONT_AWESOME_SOLID_FILENAME
    if packaged_path.exists():
        return packaged_path

    package_spec = importlib.util.find_spec("qtawesome")
    if package_spec is None or package_spec.origin is None:
        raise ModuleNotFoundError(
            "Unable to resolve the Font Awesome solid font."
        )

    fallback_path = (
        Path(package_spec.origin).resolve().parent
        / "fonts"
        / FONT_AWESOME_SOLID_FILENAME
    )
    if not fallback_path.exists():
        raise FileNotFoundError(
            f"Unable to locate '{FONT_AWESOME_SOLID_FILENAME}'."
        )
    return fallback_path
