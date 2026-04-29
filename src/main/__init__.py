from __future__ import annotations

from pathlib import Path


def create_main_window(root: Path | None = None):
    from src.main.application import create_main_window as _create_main_window

    return _create_main_window(root)


__all__ = ["create_main_window"]
