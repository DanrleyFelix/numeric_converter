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
    address = int(item.data(Qt.UserRole))
    breakpoint = next(
        value for value in view._debugger.breakpoints if value.address == address
    )
    menu = QMenu(view)
    menu.setObjectName("binary-workbench-editor-context-menu")
    toggle = QAction("Disable" if breakpoint.enabled else "Enable", menu)
    toggle.triggered.connect(
        lambda _checked=False: _set_enabled(
            view, address, not breakpoint.enabled
        )
    )
    remove = QAction("Remove", menu)
    remove.triggered.connect(lambda _checked=False: _remove(view, address))
    copy = QAction("Copy Address", menu)
    copy.triggered.connect(
        lambda _checked=False: QApplication.clipboard().setText(
            f"0x{address:08X}"
        )
    )
    navigate = QAction("Go to Instruction", menu)
    navigate.triggered.connect(
        lambda _checked=False: view.navigateRequested.emit(address)
    )
    menu.addActions((toggle, remove, copy, navigate))
    use_white_menu_icons(menu)
    menu.exec(view.table.viewport().mapToGlobal(position))


def _set_enabled(view, address: int, enabled: bool) -> None:
    """Update one breakpoint state and refresh its view."""

    view._debugger.set_breakpoint_enabled(address, enabled)
    view.refresh()


def _remove(view, address: int) -> None:
    """Remove one breakpoint and refresh its view."""

    view._debugger.remove_breakpoint(address)
    view.refresh()
