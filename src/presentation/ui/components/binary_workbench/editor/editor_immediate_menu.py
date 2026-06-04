from __future__ import annotations

from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.editor.context_menu_icons import (
    use_white_menu_icons,
)
from src.presentation.ui.components.binary_workbench.editor.immediate_tokens import (
    immediate_token_at_position,
    variable_token_at_position,
)


class EditorImmediateMenuMixin:
    def set_immediate_symbol_menu_enabled(self, enabled: bool) -> None:
        self._immediate_symbol_menu_enabled = enabled

    def contextMenuEvent(self, event) -> None:
        variable_token = variable_token_at_position(self, event.pos())
        immediate_token = immediate_token_at_position(self, event.pos())
        equate_token = immediate_token if variable_token == immediate_token else None
        label = self._label_at_position(event.pos())
        if (not self._immediate_symbol_menu_enabled or variable_token is None) and label is None:
            super().contextMenuEvent(event)
            return
        menu = self.createStandardContextMenu()
        menu.setObjectName("binary-workbench-editor-context-menu")
        menu.addSeparator()
        variable = menu.addAction(BINARY_WORKBENCH_TEXT.ADD_VARIABLE_FROM_IMMEDIATE) if variable_token else None
        equate = menu.addAction(BINARY_WORKBENCH_TEXT.ADD_EQUATE_FROM_IMMEDIATE) if equate_token else None
        open_label = menu.addAction(BINARY_WORKBENCH_TEXT.OPEN_LABEL_NEW_TAB) if label else None
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
        menu.deleteLater()
