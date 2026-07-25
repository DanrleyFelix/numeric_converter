"""Project-standard breakpoint table context menu."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QMenu

from src.presentation.ui.components.binary_workbench.editor.context_menu_icons import (
    use_white_menu_icons,
)


def show_breakpoint_menu(view, position) -> None:
    """Open breakpoint actions without narrowing PSX addresses to signed int."""

    item = view.table.itemAt(position)
    if item is None:
        return
    identifier = int(item.data(Qt.UserRole))
    breakpoint = next(
        value
        for value in view._debugger.breakpoints
        if value.identifier == identifier
    )
    menu = QMenu(view)
    menu.setObjectName("binary-workbench-editor-context-menu")
    toggle = QAction("Disable" if breakpoint.enabled else "Enable", menu)
    toggle.triggered.connect(
        lambda _checked=False: _set_enabled(
            view, identifier, not breakpoint.enabled
        )
    )
    remove = QAction("Remove", menu)
    remove.triggered.connect(lambda _checked=False: _remove(view, identifier))
    copy = QAction("Copy WHERE", menu)
    copy.triggered.connect(
        lambda _checked=False: QApplication.clipboard().setText(
            breakpoint.where
        )
    )
    menu.addActions((toggle, remove, copy))
    if breakpoint.address is not None:
        navigate = QAction("Go to Instruction", menu)
        navigate.triggered.connect(
            lambda _checked=False: view.navigateRequested.emit(
                breakpoint.address
            )
        )
        menu.addAction(navigate)
    use_white_menu_icons(menu)
    menu.exec(view.table.viewport().mapToGlobal(position))


def _set_enabled(view, identifier: int, enabled: bool) -> None:
    """Update one breakpoint state and refresh its view."""

    view._debugger.set_breakpoint_enabled(identifier, enabled)
    view.refresh()


def _remove(view, identifier: int) -> None:
    """Remove one breakpoint and refresh its view."""

    view._debugger.remove_breakpoint(identifier)
    view.refresh()
