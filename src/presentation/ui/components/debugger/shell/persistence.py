from __future__ import annotations

from PySide6.QtCore import Qt

from src.presentation.repository.debugger_window.repository import (
    DebuggerWindowStateRepository,
)
from src.presentation.repository.debugger_window.state import DebuggerWindowState
from src.presentation.ui.components.debugger.constants.layout import DEBUGGER_LAYOUT


def restore_debugger_window(window, repository, workspace_key: str) -> None:
    """Restore geometry and splitters while tolerating incomplete state."""

    state = repository.load(workspace_key)
    width = state.width or DEBUGGER_LAYOUT.WINDOW_WIDTH
    height = state.height or DEBUGGER_LAYOUT.WINDOW_HEIGHT
    window.resize(width, height)
    if state.x is not None and state.y is not None:
        window.move(state.x, state.y)
    if state.horizontal_sizes:
        window.panels.horizontal.setSizes(list(state.horizontal_sizes))
    if state.vertical_sizes:
        window.panels.vertical.setSizes(list(state.vertical_sizes))
    last_tab = max(0, window.panels.lower.count() - 1)
    window.panels.lower.setCurrentIndex(min(state.bottom_tab, last_tab))
    if state.maximized:
        window.setWindowState(window.windowState() | Qt.WindowMaximized)


def save_debugger_window(
    window,
    repository: DebuggerWindowStateRepository,
    workspace_key: str,
) -> None:
    """Persist independent workspace geometry without touching its manifest."""

    geometry = window.normalGeometry() if window.isMaximized() else window.geometry()
    state = DebuggerWindowState(
        geometry.x(),
        geometry.y(),
        geometry.width(),
        geometry.height(),
        window.isMaximized(),
        tuple(window.panels.horizontal.sizes()),
        tuple(window.panels.vertical.sizes()),
        window.panels.lower.currentIndex(),
    )
    repository.save(workspace_key, state)
