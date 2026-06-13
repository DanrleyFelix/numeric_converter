from pathlib import Path

from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_STATE,
    BINARY_WORKBENCH_TEXT,
    BINARY_WORKBENCH_TIMING,
)
from src.presentation.ui.components.binary_workbench.environment import (
    BinaryWorkbenchLabelsDialog,
    BinaryWorkbenchSymbolsDialog,
)
from src.presentation.ui.components.binary_workbench.file_dialogs import (
    BinaryWorkbenchInternalFileDialog,
    BinaryWorkbenchLbaFilesystemDialog,
)
from src.presentation.ui.components.binary_workbench.preferences import (
    BinaryWorkbenchAdvancedConfigDialog,
    BinaryWorkbenchBytesFormatterDialog,
    BinaryWorkbenchReferenceOffsetsDialog,
    BinaryWorkbenchRulesDialog,
)
from src.presentation.repository.binary_workbench_workspace.constants import (
    LBA_FILESYSTEM,
    SYMBOLS,
)


class BinaryWorkbenchWindowEnvironmentMixin:
    def _open_advanced_configuration(self) -> None:
        current = self.tabs.current_context()
        preferences = self.tabs.preferences()
        dialog = BinaryWorkbenchAdvancedConfigDialog(
            current.cpu_arch if current else "",
            current.read_mode if current else BINARY_WORKBENCH_TEXT.AUTO_READ_MODE,
            preferences.block_size,
            preferences.cache_max_blocks,
            preferences.selection_limit_bytes,
            self,
        )
        if dialog.exec() == dialog.DialogCode.Accepted:
            self.tabs.set_current_advanced_config(
                dialog.selected_arch(),
                dialog.selected_read_mode(),
                dialog.selected_block_size(),
                dialog.selected_cache_max_blocks(),
                dialog.selected_selection_limit_bytes(),
            )

    def _open_lba_filesystem(self) -> None:
        current = self.tabs.current_context()
        if current is None or not current.source_path:
            self._show_status(BINARY_WORKBENCH_TEXT.STATUS_INTERNAL_SOURCE_REQUIRED, BINARY_WORKBENCH_TIMING.STATUS_MESSAGE_VISIBLE_MS)
            return
        dialog = BinaryWorkbenchLbaFilesystemDialog(current.internal_files, current.lba_sector_size, [], current.display_name, self.tabs.directory_for(BINARY_WORKBENCH_STATE.LBA_FILESYSTEM_DIRECTORY), self)
        dialog.directoryChanged.connect(lambda value: self.tabs.set_directory(BINARY_WORKBENCH_STATE.LBA_FILESYSTEM_DIRECTORY, Path(value)))
        dialog.goToRequested.connect(self.tabs.go_to_offset)
        if dialog.exec() == dialog.DialogCode.Accepted:
            self.tabs.set_current_internal_files(dialog.mappings(), dialog.selected_lba_sector_size())
            module_path = dialog.saved_library_path() or dialog.loaded_library_path()
            if module_path:
                self.tabs.set_current_module_path(LBA_FILESYSTEM, Path(module_path))
            if dialog.should_save_library() or dialog.loaded_library_name():
                self.tabs.save_current_lba_filesystem(dialog.library_name() or dialog.saved_library_name() or dialog.loaded_library_name())
            self.tabs.save_current_workspace()

    def _open_symbols(self) -> None:
        current = self.tabs.current_context()
        if current is None:
            return
        dialog = BinaryWorkbenchSymbolsDialog(
            current.variables,
            current.equates,
            current.labels,
            [],
            current.display_name,
            self.tabs.directory_for(BINARY_WORKBENCH_STATE.SYMBOLS_DIRECTORY),
            self,
            symbol_offsets=current.symbol_offsets,
        )
        dialog.directoryChanged.connect(lambda value: self.tabs.set_directory(BINARY_WORKBENCH_STATE.SYMBOLS_DIRECTORY, Path(value)))
        dialog.goToRequested.connect(self.tabs.go_to_offset)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        variables, equates, _ = dialog.values()
        self.tabs.set_current_symbols(variables, equates, current.labels)
        module_path = dialog.saved_library_path() or dialog.loaded_library_path()
        if module_path:
            self.tabs.set_current_module_path(SYMBOLS, Path(module_path))
        if dialog.should_save_library() or dialog.loaded_library_name():
            self.tabs.save_current_symbols(dialog.library_name() or dialog.saved_library_name() or dialog.loaded_library_name())
        self.tabs.save_current_workspace()

    def _open_labels(self) -> None:
        self.tabs.commit_current_editor_text()
        current = self.tabs.current_context()
        if current is None:
            return
        dialog = BinaryWorkbenchLabelsDialog(current.labels, self)
        dialog.goToRequested.connect(self.tabs.go_to_instruction_offset)
        dialog.exec()

    def _open_bytes_formatter(self) -> None:
        current = self.tabs.current_context()
        if current is None:
            return
        preferences = self.tabs.preferences()
        dialog = BinaryWorkbenchBytesFormatterDialog(preferences.group_bytes, preferences.uppercase_bytes, preferences.uppercase_instructions, self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            self.tabs.set_current_bytes_formatter(dialog.selected_group_bytes(), dialog.selected_uppercase_bytes(), dialog.selected_uppercase_instructions())

    def _open_reference_offsets(self) -> None:
        current = self.tabs.current_context()
        if current is None:
            return
        dialog = BinaryWorkbenchReferenceOffsetsDialog(current.reference_offsets, current.reference_offset_bases, current.view_preferences.visible_columns, self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            offsets, bases, visible = dialog.values()
            self.tabs.set_current_reference_offsets(offsets, bases, visible)

    def _open_rules(self) -> None:
        current = self.tabs.current_context()
        if current is None:
            return
        dialog = BinaryWorkbenchRulesDialog(self.tabs.edit_rules_for_current_context(), self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            self.tabs.set_current_edit_rules(dialog.selected_rules())

    def _open_internal_file(self) -> None:
        current = self.tabs.current_context()
        if current is None or not current.source_path:
            self._show_status(BINARY_WORKBENCH_TEXT.STATUS_INTERNAL_SOURCE_REQUIRED, BINARY_WORKBENCH_TIMING.STATUS_MESSAGE_VISIBLE_MS)
            return
        if not current.internal_files:
            self._show_status(BINARY_WORKBENCH_TEXT.STATUS_INTERNAL_FILES_REQUIRED, BINARY_WORKBENCH_TIMING.STATUS_MESSAGE_VISIBLE_MS)
            return
        dialog = BinaryWorkbenchInternalFileDialog(current.internal_files, self)
        if dialog.exec() == dialog.DialogCode.Accepted and dialog.selected_name() is not None:
            self.tabs.open_internal_tab(dialog.selected_name())
