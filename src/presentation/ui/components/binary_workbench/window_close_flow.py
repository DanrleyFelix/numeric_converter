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
from src.presentation.ui.components.binary_workbench.file_dialogs import (
    BinaryWorkbenchVersionNameDialog,
)


class BinaryWorkbenchWindowCloseMixin:
    def _request_tab_close(self, index: int) -> None:
        self.tabs.commit_current_editor_text()
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
            return self._save_binary_workspace_for_close(current)
        if current.source_path and self.tabs.save_current_source_file():
            self._show_status(
                BINARY_WORKBENCH_TEXT.STATUS_ASSEMBLY_SAVED_TEMPLATE.format(
                    name=Path(current.source_path).name
                ),
                BINARY_WORKBENCH_TIMING.STATUS_MESSAGE_VISIBLE_MS,
            )
            self.tabs.save_current_workspace()
            return True
        if self._save_assembly_code():
            self.tabs.save_current_workspace()
            return True
        return False

    def _save_binary_workspace_for_close(self, current) -> bool:
        if (current.byte_overlays or current.instruction_overlays) and not current.active_version_name:
            dialog = BinaryWorkbenchVersionNameDialog(
                BINARY_WORKBENCH_TEXT.CREATE_VERSION,
                parent=self,
            )
            if dialog.exec() != dialog.DialogCode.Accepted or not dialog.version_name():
                return False
            if not self.tabs.create_version(dialog.version_name()):
                return False
        elif current.active_version_name:
            self.tabs.update_current_version(current.active_version_name)
        return self.tabs.save_current_workspace()
