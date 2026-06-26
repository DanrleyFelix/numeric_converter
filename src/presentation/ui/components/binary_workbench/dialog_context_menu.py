from __future__ import annotations

from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QLineEdit, QPlainTextEdit

from src.presentation.ui.components.binary_workbench.editor.context_menu_icons import (
    use_white_menu_icons,
)

DIALOG_CONTEXT_MENU_CONFIGURED = "binaryWorkbenchContextMenuConfigured"


def configure_dialog_text_context_menu(editor: QLineEdit | QPlainTextEdit) -> None:
    if editor.property(DIALOG_CONTEXT_MENU_CONFIGURED):
        return
    editor.setProperty(DIALOG_CONTEXT_MENU_CONFIGURED, True)
    editor.setContextMenuPolicy(Qt.CustomContextMenu)
    editor.customContextMenuRequested.connect(
        lambda position, target=editor: _show_context_menu(target, position)
    )


def _show_context_menu(editor: QLineEdit | QPlainTextEdit, position: QPoint) -> None:
    menu = editor.createStandardContextMenu()
    menu.setObjectName("binary-workbench-editor-context-menu")
    use_white_menu_icons(menu)
    menu.exec(editor.mapToGlobal(position))
    menu.deleteLater()
