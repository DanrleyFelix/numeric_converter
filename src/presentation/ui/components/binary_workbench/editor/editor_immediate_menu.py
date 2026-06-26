from __future__ import annotations

from PySide6.QtCore import Qt

from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.editor.context_menu_icons import (
    use_white_menu_icons,
)
from src.presentation.ui.components.binary_workbench.editor.add_command_dialog import (
    ask_command_name,
)
from src.presentation.ui.components.binary_workbench.editor.editor_shortcuts import (
    INSTRUCTIONS_PANEL,
)
from src.presentation.ui.components.binary_workbench.editor.immediate_tokens import (
    immediate_token_at_cursor,
    immediate_token_at_position,
    variable_token_at_cursor,
    variable_token_at_position,
)


class EditorImmediateMenuMixin:
    def set_immediate_symbol_menu_enabled(self, enabled: bool) -> None:
        self._immediate_symbol_menu_enabled = enabled

    def handle_immediate_symbol_shortcut(self, key: int, modifiers: Qt.KeyboardModifiers) -> bool:
        if not self._immediate_symbol_menu_enabled or not modifiers & Qt.AltModifier:
            return False
        if key == Qt.Key_W:
            token = variable_token_at_cursor(self)
            target = BINARY_WORKBENCH_TEXT.VARIABLE_TARGET
        elif key == Qt.Key_E:
            token = _equate_token_at_cursor(self)
            target = BINARY_WORKBENCH_TEXT.EQUATE_TARGET
        elif key == Qt.Key_K:
            selected_code = _selected_code(self)
            if not selected_code:
                return False
            self._request_add_command(selected_code)
            return True
        else:
            return False
        if token is None:
            return False
        self.immediateSymbolRequested.emit(target, token.value, token.start, token.end)
        return True

    def contextMenuEvent(self, event) -> None:
        variable_token = variable_token_at_position(self, event.pos())
        immediate_token = immediate_token_at_position(self, event.pos())
        equate_token = immediate_token if variable_token == immediate_token else None
        label = self._label_at_position(event.pos())
        selected_code = _selected_code(self)
        if (
            not selected_code
            and (not self._immediate_symbol_menu_enabled or variable_token is None)
            and label is None
        ):
            menu = self.createStandardContextMenu()
            menu.setObjectName("binary-workbench-editor-context-menu")
            use_white_menu_icons(menu)
            menu.exec(event.globalPos())
            menu.deleteLater()
            return
        menu = self.createStandardContextMenu()
        menu.setObjectName("binary-workbench-editor-context-menu")
        menu.addSeparator()
        variable = menu.addAction(BINARY_WORKBENCH_TEXT.ADD_VARIABLE_FROM_IMMEDIATE) if variable_token else None
        equate = menu.addAction(BINARY_WORKBENCH_TEXT.ADD_EQUATE_FROM_IMMEDIATE) if equate_token else None
        open_label = menu.addAction(BINARY_WORKBENCH_TEXT.OPEN_LABEL_NEW_TAB) if label else None
        add_command = (
            menu.addAction(BINARY_WORKBENCH_TEXT.ADD_COMMAND)
            if selected_code
            else None
        )
        use_white_menu_icons(menu)
        selected = menu.exec(event.globalPos())
        if selected is variable and variable_token is not None:
            self.immediateSymbolRequested.emit(
                BINARY_WORKBENCH_TEXT.VARIABLE_TARGET,
                variable_token.value,
                variable_token.start,
                variable_token.end,
            )
        elif selected is equate and equate_token is not None:
            self.immediateSymbolRequested.emit(
                BINARY_WORKBENCH_TEXT.EQUATE_TARGET,
                equate_token.value,
                equate_token.start,
                equate_token.end,
            )
        elif selected is open_label and label is not None:
            self.labelOpenTabRequested.emit(*label)
        elif selected is add_command and selected_code:
            self._request_add_command(selected_code)
        menu.deleteLater()

    def _request_add_command(self, selected_code: str) -> None:
        name = ask_command_name(self)
        if name:
            self.addCommandRequested.emit(name, selected_code)


def _equate_token_at_cursor(editor):
    variable_token = variable_token_at_cursor(editor)
    immediate_token = immediate_token_at_cursor(editor)
    return immediate_token if variable_token == immediate_token else None


def _selected_code(editor) -> str:
    if editor.objectName() != INSTRUCTIONS_PANEL:
        return ""
    cursor = editor.textCursor()
    if not cursor.hasSelection():
        return ""
    return cursor.selection().toPlainText()
