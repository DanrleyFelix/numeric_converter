"""Register context actions including conditional breakpoint creation."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QApplication, QDialog, QMenu

from src.presentation.ui.components.binary_workbench.editor.context_menu_icons import (
    use_white_menu_icons,
)
from src.presentation.ui.components.debugger.panels.register.breakpoint.dialog import (
    DebuggerRegisterBreakpointDialog,
)
from src.presentation.ui.design.icons import Icons


def create_register_breakpoint_action(panel) -> QAction:
    """Create the reusable Add Breakpoint action with its local shortcut."""

    action = QAction(Icons.expand_circle(), "Add Breakpoint", panel)
    action.setShortcut(QKeySequence("Alt+B"))
    action.setShortcutContext(Qt.WidgetWithChildrenShortcut)
    action.setShortcutVisibleInContextMenu(True)
    action.triggered.connect(lambda: add_register_breakpoint(panel))
    return action


def add_register_breakpoint(panel) -> None:
    """Open the condition-only dialog for the currently selected register."""

    current = panel.currentItem()
    if current is None:
        return
    register = panel.item(current.row(), 0).text()
    dialog = DebuggerRegisterBreakpointDialog(
        panel._debugger,
        register,
        panel,
    )
    if dialog.exec() == QDialog.DialogCode.Accepted:
        panel.breakpointAdded.emit()


def show_register_menu(panel, position) -> None:
    """Show Copy and Add Breakpoint using the established project menu."""

    item = panel.itemAt(position)
    if item is None:
        return
    panel.setCurrentItem(item)
    menu = QMenu(panel)
    menu.setObjectName("binary-workbench-editor-context-menu")
    copy_action = QAction("Copy", menu)
    copy_action.triggered.connect(
        lambda: QApplication.clipboard().setText(item.text())
    )
    menu.addActions((copy_action, panel._add_breakpoint_action))
    use_white_menu_icons(menu)
    menu.exec(panel.viewport().mapToGlobal(position))
