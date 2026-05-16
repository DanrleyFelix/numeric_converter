from __future__ import annotations

from pathlib import Path

from src.main.runtime_root import resolve_resource_root

DATA_DIRECTORY = Path("data")
ASSETS_DIRECTORY = Path("assets")
FONTS_DIRECTORY = ASSETS_DIRECTORY / "fonts"
ICONS_DIRECTORY = ASSETS_DIRECTORY / "icons"
STYLE_DIRECTORY = Path("src") / "presentation" / "ui" / "design" / "style"


def resource_path(*parts: str | Path) -> Path:
    root = resolve_resource_root()
    normalized = [
        str(part).replace("\\", "/")
        for part in parts
    ]
    return root.joinpath(*normalized)


def fonts_root() -> Path:
    return resource_path(FONTS_DIRECTORY)


def icons_root() -> Path:
    return resource_path(ICONS_DIRECTORY)


def style_root() -> Path:
    return resource_path(STYLE_DIRECTORY)
