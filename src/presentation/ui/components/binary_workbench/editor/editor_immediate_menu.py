from __future__ import annotations

from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.editor.context_menu_icons import (
    use_white_menu_icons,
)
from src.presentation.ui.components.binary_workbench.editor.immediate_tokens import (
    immediate_at_position,
)


class EditorImmediateMenuMixin:
    def set_immediate_symbol_menu_enabled(self, enabled: bool) -> None:
        self._immediate_symbol_menu_enabled = enabled

    def contextMenuEvent(self, event) -> None:
        value = immediate_at_position(self, event.pos())
        label = self._label_at_position(event.pos())
        if (not self._immediate_symbol_menu_enabled or not value) and label is None:
            super().contextMenuEvent(event)
            return
        menu = self.createStandardContextMenu()
        use_white_menu_icons(menu)
        menu.addSeparator()
        variable = menu.addAction(BINARY_WORKBENCH_TEXT.ADD_VARIABLE_FROM_IMMEDIATE) if value else None
        equate = menu.addAction(BINARY_WORKBENCH_TEXT.ADD_EQUATE_FROM_IMMEDIATE) if value else None
        open_label = menu.addAction(BINARY_WORKBENCH_TEXT.OPEN_LABEL_NEW_TAB) if label else None
        selected = menu.exec(event.globalPos())
        if selected is variable:
            self.immediateSymbolRequested.emit(BINARY_WORKBENCH_TEXT.VARIABLE_TARGET, value)
        elif selected is equate:
            self.immediateSymbolRequested.emit(BINARY_WORKBENCH_TEXT.EQUATE_TARGET, value)
        elif selected is open_label and label is not None:
            self.labelOpenTabRequested.emit(*label)
        menu.deleteLater()
