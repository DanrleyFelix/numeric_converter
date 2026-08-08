from pathlib import Path

from contextlib import contextmanager

from src.modules.binary_workbench_constants import (
    BINARY_WORKBENCH_STATE,
    BINARY_WORKBENCH_TAB_KIND,
)
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_TEXT,
    BINARY_WORKBENCH_TIMING,
)
from src.presentation.ui.components.binary_workbench.environment import (
    BinaryWorkbenchCommandsDialog,
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
    @contextmanager
    def _environment_dialog_session(self):
        """Suspend editor CPU work before constructing a modal dialog."""

        page = self.tabs.currentWidget()
        suspended = None
        if hasattr(page, "suspend_eventual_consistency"):
            suspended = page.suspend_eventual_consistency()
        try:
            yield
        finally:
            if suspended is not None and hasattr(page, "resume_eventual_consistency"):
                page.resume_eventual_consistency(suspended)

    def _exec_environment_dialog(self, dialog):
        """Pause this tab's eventual CPU work for a modal UI interaction."""

        with self._environment_dialog_session():
            return dialog.exec()

    def _open_advanced_configuration(self) -> None:
        current = self.tabs.current_metadata_context()
        preferences = self.tabs.preferences()
        dialog = BinaryWorkbenchAdvancedConfigDialog(
            current.cpu_arch if current else "",
            current.read_mode if current else BINARY_WORKBENCH_TEXT.AUTO_READ_MODE,
            preferences.block_size,
            preferences.cache_max_blocks,
            preferences.selection_limit_bytes,
            self,
        )
        if self._exec_environment_dialog(dialog) == dialog.DialogCode.Accepted:
            self.tabs.set_current_advanced_config(
                dialog.selected_arch(),
                dialog.selected_read_mode(),
                dialog.selected_block_size(),
                dialog.selected_cache_max_blocks(),
                dialog.selected_selection_limit_bytes(),
            )

    def _open_lba_filesystem(self) -> None:
        current = self.tabs.current_metadata_context()
        if current is None or not current.source_path:
            self._show_status(BINARY_WORKBENCH_TEXT.STATUS_INTERNAL_SOURCE_REQUIRED, BINARY_WORKBENCH_TIMING.STATUS_MESSAGE_VISIBLE_MS)
            return
        with self._environment_dialog_session():
            dialog = BinaryWorkbenchLbaFilesystemDialog(current.internal_files, current.lba_sector_size, [], current.display_name, self.tabs.directory_for(BINARY_WORKBENCH_STATE.LBA_FILESYSTEM_DIRECTORY), self)
            dialog.directoryChanged.connect(lambda value: self.tabs.set_directory(BINARY_WORKBENCH_STATE.LBA_FILESYSTEM_DIRECTORY, Path(value)))
            dialog.goToRequested.connect(self.tabs.go_to_offset)
            dialog.exec()
        mappings = dialog.mappings()
        sector_size = dialog.selected_lba_sector_size()
        content_changed = (
            mappings != current.internal_files
            or sector_size != current.lba_sector_size
        )
        if content_changed:
            self.tabs.set_current_internal_files(mappings, sector_size)
        module_path = dialog.saved_library_path() or dialog.loaded_library_path()
        if module_path:
            self.tabs.set_current_module_path(LBA_FILESYSTEM, Path(module_path))
        library_changed = bool(
            dialog.should_save_library() or dialog.loaded_library_name()
        )
        if library_changed:
            self.tabs.save_current_lba_filesystem(dialog.library_name() or dialog.saved_library_name() or dialog.loaded_library_name())
        if content_changed or module_path or library_changed:
            self.tabs.save_current_workspace()

    def _open_symbols(self) -> None:
        self._open_local_symbols()

    def _open_local_symbols(self) -> None:
        current = self.tabs.current_metadata_context()
        if current is None:
            return
        if self.tabs.scratch_initial_version_required(current):
            self._show_warning_status(BINARY_WORKBENCH_TEXT.STATUS_SYMBOLS_VERSION_REQUIRED)
            return
        dialog = BinaryWorkbenchSymbolsDialog(
            self.tabs.local_symbols(current),
            {},
            current.labels,
            [],
            current.display_name,
            self.tabs.directory_for(BINARY_WORKBENCH_STATE.SYMBOLS_DIRECTORY),
            self,
            symbol_offsets=current.symbol_offsets,
            offsets_provider=lambda name: (
                current.tab_id,
                self.tabs.symbol_offsets_for(current.tab_id, name),
            ),
        )
        dialog.setWindowTitle(BINARY_WORKBENCH_TEXT.LOCAL_SYMBOLS)
        dialog.directoryChanged.connect(lambda value: self.tabs.set_directory(BINARY_WORKBENCH_STATE.SYMBOLS_DIRECTORY, Path(value)))
        dialog.goToRequested.connect(self.tabs.go_to_offset)
        self._exec_environment_dialog(dialog)
        symbols, _, _ = dialog.values()
        symbols_changed = symbols != self.tabs.local_symbols(current)
        if symbols_changed:
            self.tabs.set_current_symbols(
                symbols,
                {},
                current.labels,
                apply_existing=False,
            )
        module_path = dialog.saved_library_path() or dialog.loaded_library_path()
        if module_path:
            self.tabs.set_current_module_path(SYMBOLS, Path(module_path))
        if dialog.should_save_library() or dialog.loaded_library_name():
            self.tabs.save_current_symbols(dialog.library_name() or dialog.saved_library_name() or dialog.loaded_library_name())
        if symbols_changed or module_path or dialog.should_save_library() or dialog.loaded_library_name():
            self.tabs.save_current_workspace()

    def _open_global_symbols(self) -> None:
        """Open Global Symbols with offsets resolved from the active tab on demand."""

        current = self.tabs.current_metadata_context()
        if current is None:
            return
        dialog = BinaryWorkbenchSymbolsDialog(
            self.tabs.global_symbols(),
            {},
            current.labels,
            [],
            BINARY_WORKBENCH_TEXT.GLOBAL_SYMBOLS,
            self.tabs.directory_for(BINARY_WORKBENCH_STATE.SYMBOLS_DIRECTORY),
            self,
            symbol_offsets=current.symbol_offsets,
            offsets_provider=self._global_symbol_offsets,
        )
        dialog.setWindowTitle(BINARY_WORKBENCH_TEXT.GLOBAL_SYMBOLS)
        dialog.goToRequested.connect(self.tabs.go_to_offset)
        dialog.symbolsChanged.connect(
            lambda values: self.tabs.set_global_symbols(
                values,
                apply_existing=False,
            )
        )
        self.tabs.currentChanged.connect(dialog.invalidate_offsets_context)
        try:
            self._exec_environment_dialog(dialog)
        finally:
            self.tabs.currentChanged.disconnect(dialog.invalidate_offsets_context)
        symbols, _, _ = dialog.values()
        if symbols != self.tabs.global_symbols():
            self.tabs.set_global_symbols(symbols, apply_existing=False)

    def _global_symbol_offsets(self, name: str) -> tuple[str | None, list[str]]:
        """Read one Global Symbol's offsets from the tab active at click time."""

        current = self.tabs.current_metadata_context()
        if current is None:
            return None, []
        return current.tab_id, self.tabs.symbol_offsets_for(current.tab_id, name)

    def _open_labels(self) -> None:
        """Open the cached label index without a global consistency barrier."""

        current = self.tabs.current_metadata_context()
        if current is None:
            return
        with self._environment_dialog_session():
            page = self.tabs.currentWidget()
            grid = getattr(page, "grid", None)
            labels = grid.current_labels() if grid is not None else current.labels
            dialog = BinaryWorkbenchLabelsDialog(labels, self)
            dialog.goToRequested.connect(self.tabs.go_to_instruction_offset)
            dialog.exec()

    def _open_commands(self) -> None:
        current = self.tabs.current_metadata_context()
        if current is None:
            return
        with self._environment_dialog_session():
            dialog = BinaryWorkbenchCommandsDialog(
                self.tabs.custom_commands_for_current_context(),
                self.tabs.directory_for(BINARY_WORKBENCH_STATE.COMMANDS_DIRECTORY),
                self,
            )
            dialog.commandLoadRequested.connect(lambda path: self._load_command(dialog, Path(path)))
            dialog.commandSaveRequested.connect(lambda path: self._save_commands(dialog, Path(path)))
            dialog.commandRemoveRequested.connect(lambda name: self._remove_command(dialog, name))
            dialog.commandInstructionsChangeRequested.connect(
                lambda name, instructions: self._replace_command_instructions(dialog, name, instructions)
            )
            dialog.exec()

    def _load_command(self, dialog: BinaryWorkbenchCommandsDialog, path: Path) -> None:
        if not self.tabs.load_custom_commands_from_path(path):
            self._show_status(
                BINARY_WORKBENCH_TEXT.STATUS_COMMAND_INVALID_INSTRUCTIONS,
                BINARY_WORKBENCH_TIMING.STATUS_MESSAGE_VISIBLE_MS,
                error=True,
            )
            return
        self.tabs.set_directory(BINARY_WORKBENCH_STATE.COMMANDS_DIRECTORY, path.parent)
        dialog.set_default_directory(str(path.parent))
        dialog.set_commands(self.tabs.custom_commands_for_current_context())

    def _save_commands(self, dialog: BinaryWorkbenchCommandsDialog, path: Path) -> None:
        target = self.tabs.save_custom_commands_to_path(path)
        if target is None:
            return
        self.tabs.set_directory(BINARY_WORKBENCH_STATE.COMMANDS_DIRECTORY, target.parent)
        dialog.set_default_directory(str(target.parent))
        dialog.set_commands(self.tabs.custom_commands_for_current_context())

    def _remove_command(self, dialog: BinaryWorkbenchCommandsDialog, name: str) -> None:
        if not self.tabs.remove_custom_command(name):
            return
        dialog.set_commands(self.tabs.custom_commands_for_current_context())

    def _replace_command_instructions(
        self,
        dialog: BinaryWorkbenchCommandsDialog,
        name: str,
        instructions: list[str],
    ) -> None:
        if not self.tabs.replace_custom_command(name, instructions):
            self._show_status(
                BINARY_WORKBENCH_TEXT.STATUS_COMMAND_INVALID_INSTRUCTIONS,
                BINARY_WORKBENCH_TIMING.STATUS_MESSAGE_VISIBLE_MS,
                error=True,
            )
            return
        dialog.set_commands(self.tabs.custom_commands_for_current_context())

    def _open_bytes_formatter(self) -> None:
        current = self.tabs.current_metadata_context()
        if current is None:
            return
        preferences = self.tabs.preferences()
        dialog = BinaryWorkbenchBytesFormatterDialog(preferences.group_bytes, preferences.uppercase_bytes, preferences.uppercase_instructions, self)
        if self._exec_environment_dialog(dialog) == dialog.DialogCode.Accepted:
            self.tabs.set_current_bytes_formatter(dialog.selected_group_bytes(), dialog.selected_uppercase_bytes(), dialog.selected_uppercase_instructions())

    def _open_reference_offsets(self) -> None:
        current = self.tabs.current_metadata_context()
        if current is None:
            return
        dialog = BinaryWorkbenchReferenceOffsetsDialog(
            current.reference_offsets,
            current.reference_offset_bases,
            current.view_preferences.visible_columns,
            current.view_preferences.jump_reference_offset,
            self,
        )
        if self._exec_environment_dialog(dialog) == dialog.DialogCode.Accepted:
            offsets, bases, visible, jump_reference_offset = dialog.values()
            self.tabs.set_current_reference_offsets(offsets, bases, visible, jump_reference_offset)

    def _open_rules(self) -> None:
        current = self.tabs.current_context()
        if current is None:
            return
        dialog = BinaryWorkbenchRulesDialog(self.tabs.edit_rules_for_current_context(), self)
        if self._exec_environment_dialog(dialog) == dialog.DialogCode.Accepted:
            self.tabs.set_current_edit_rules(dialog.selected_rules())

    def _open_internal_file(self) -> None:
        current = self.tabs.current_metadata_context()
        if (
            current is None
            or current.kind != BINARY_WORKBENCH_TAB_KIND.BINARY
            or not current.source_path
            or not current.internal_files
        ):
            self._show_warning_status(BINARY_WORKBENCH_TEXT.STATUS_INTERNAL_REQUIREMENTS)
            return
        dialog = BinaryWorkbenchInternalFileDialog(current.internal_files, self)
        if (
            self._exec_environment_dialog(dialog) == dialog.DialogCode.Accepted
            and dialog.selected_name() is not None
        ):
            self.tabs.open_internal_tab(dialog.selected_name())
