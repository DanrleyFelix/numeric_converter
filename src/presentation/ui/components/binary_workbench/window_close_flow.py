from pathlib import Path

from PySide6.QtWidgets import QMessageBox

from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_TAB_KIND,
    BINARY_WORKBENCH_TEXT,
    BINARY_WORKBENCH_TIMING,
)
from src.presentation.ui.components.binary_workbench.native_dialogs import (
    ask_close_tab_with_native_system_dialog,
)


class BinaryWorkbenchWindowCloseMixin:
    def _request_tab_close(self, index: int) -> None:
        if not self.tabs.has_unsaved_changes(index):
            self.tabs.close_tab(index)
            return
        self.tabs.setCurrentIndex(index)
        response = self._native_close_question()
        if response == QMessageBox.StandardButton.Cancel:
            return
        if response == QMessageBox.StandardButton.Save and not self._save_current_tab_for_close():
            return
        self.tabs.close_tab(index)

    def _native_close_question(self) -> QMessageBox.StandardButton:
        return ask_close_tab_with_native_system_dialog(self)

    def _save_current_tab_for_close(self) -> bool:
        current = self.tabs.current_context()
        if current is None:
            return False
        if current.kind == BINARY_WORKBENCH_TAB_KIND.BINARY:
            return self._save_file()
        if current.source_path and self.tabs.save_current_source_file():
            self._show_status(
                BINARY_WORKBENCH_TEXT.STATUS_ASSEMBLY_SAVED_TEMPLATE.format(
                    name=Path(current.source_path).name
                ),
                BINARY_WORKBENCH_TIMING.STATUS_MESSAGE_VISIBLE_MS,
            )
            return True
        return self._save_assembly_code()
