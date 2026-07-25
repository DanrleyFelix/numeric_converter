"""Context actions for one debugger instruction row."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QMenu

from src.presentation.ui.components.binary_workbench.editor.context_menu_icons import (
    use_white_menu_icons,
)
from src.presentation.ui.design.icons import Icons


def show_instruction_menu(panel, position) -> None:
    """Offer breakpoint, ignored-state and address actions for one row."""

    item = panel.itemAt(position)
    if item is None:
        return
    address = int(item.data(Qt.UserRole), 0)
    menu = QMenu(panel)
    menu.setObjectName("binary-workbench-editor-context-menu")
    toggle = QAction(Icons.expand_circle(), "Toggle Breakpoint", menu)
    toggle.triggered.connect(lambda: panel.breakpointToggled.emit(address))
    remove = QAction("Remove Breakpoint", menu)
    remove.triggered.connect(lambda: panel.breakpointRemoved.emit(address))
    copy = QAction("Copy Address", menu)
    copy.triggered.connect(
        lambda: QApplication.clipboard().setText(f"0x{address:08X}")
    )
    ignore = QAction("Toggle IGNORED", menu)
    ignore.triggered.connect(lambda: panel.ignoredToggled.emit(address))
    menu.addActions((toggle, remove, copy, ignore))
    use_white_menu_icons(menu)
    menu.exec(panel.viewport().mapToGlobal(position))
