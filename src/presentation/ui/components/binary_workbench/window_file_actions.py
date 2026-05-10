from pathlib import Path

from PySide6.QtWidgets import QFileDialog

from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_STATE,
    BINARY_WORKBENCH_TAB_KIND,
    BINARY_WORKBENCH_TEXT,
    BINARY_WORKBENCH_TIMING,
)


class BinaryWorkbenchWindowFileActionsMixin:
    def _open_file(self, action_key: str, file_filter: str, callback) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            BINARY_WORKBENCH_TEXT.TITLE,
            self.tabs.directory_for(action_key),
            file_filter,
        )
        if path:
            callback(Path(path))

    def _open_any_file(self) -> None:
        self._open_file(BINARY_WORKBENCH_STATE.OPEN_FILE_DIRECTORY, BINARY_WORKBENCH_TEXT.FILE_FILTER_ANY, self.tabs.open_file_path)

    def _save_file(self) -> bool:
        default_directory = self._default_save_directory(BINARY_WORKBENCH_STATE.SAVE_FILE_DIRECTORY)
        path, _ = QFileDialog.getSaveFileName(self, BINARY_WORKBENCH_TEXT.SAVE_BINARY_FILE, default_directory, BINARY_WORKBENCH_TEXT.FILE_FILTER_OUTPUT)
        if not path:
            return False
        if self.tabs.save_current_binary_copy(Path(path)):
            self._show_status(BINARY_WORKBENCH_TEXT.STATUS_FILE_SAVED_TEMPLATE.format(name=Path(path).name), BINARY_WORKBENCH_TIMING.STATUS_MESSAGE_VISIBLE_MS)
            return True
        self._show_status(BINARY_WORKBENCH_TEXT.STATUS_VERSION_REQUIRED, BINARY_WORKBENCH_TIMING.STATUS_MESSAGE_VISIBLE_MS)
        return False

    def _save_assembly_code(self) -> bool:
        default_directory = self._default_save_directory(BINARY_WORKBENCH_STATE.SAVE_ASSEMBLY_DIRECTORY)
        path, _ = QFileDialog.getSaveFileName(self, BINARY_WORKBENCH_TEXT.SAVE_ASSEMBLY_CODE, default_directory, BINARY_WORKBENCH_TEXT.FILE_FILTER_ASSEMBLY)
        if not path:
            return False
        if self.tabs.save_current_assembly_copy(Path(path)):
            self._show_status(BINARY_WORKBENCH_TEXT.STATUS_ASSEMBLY_SAVED_TEMPLATE.format(name=Path(path).name), BINARY_WORKBENCH_TIMING.STATUS_MESSAGE_VISIBLE_MS)
            return True
        return False

    def _save_current_tab(self) -> None:
        current = self.tabs.current_context()
        if current is None:
            return
        if current.kind != BINARY_WORKBENCH_TAB_KIND.BINARY and current.source_path and self.tabs.save_current_source_file():
            self._show_status(BINARY_WORKBENCH_TEXT.STATUS_ASSEMBLY_SAVED_TEMPLATE.format(name=Path(current.source_path).name), BINARY_WORKBENCH_TIMING.STATUS_MESSAGE_VISIBLE_MS)
            return
        focused = self.tabs.focused_editor_kind()
        if focused == BINARY_WORKBENCH_TEXT.BYTES:
            self._save_file()
            return
        if focused != BINARY_WORKBENCH_TEXT.INSTRUCTION:
            self._show_status(BINARY_WORKBENCH_TEXT.STATUS_NO_FOCUSED_EDITOR, BINARY_WORKBENCH_TIMING.STATUS_MESSAGE_VISIBLE_MS)
            return
        self._save_assembly_code()

    def _default_save_directory(self, action_key: str) -> str:
        default_directory = self.tabs.directory_for(action_key)
        current = self.tabs.current_context()
        if not default_directory and current is not None and current.source_path:
            return str(Path(current.source_path).parent)
        return default_directory
