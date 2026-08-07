from __future__ import annotations

from pathlib import Path
import re
from typing import TYPE_CHECKING
from uuid import uuid4

from PySide6.QtCore import Signal
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QVBoxLayout, QWidget

from src.core.binary_workbench.selection_limits import capped_end_offset
from src.core.binary_workbench.row_structure import valid_offset_end
from src.core.binary_workbench.encoding_tables import enabled_encoding_values
from src.modules.binary_workbench_constants import (
    BINARY_WORKBENCH_ROW_BYTES as ROW_BYTES,
    BINARY_WORKBENCH_TAB_KIND,
)
from src.modules.binary_workbench_dtos import (
    BinaryWorkbenchEditRulesDTO,
    BinaryWorkbenchPreferencesDTO,
    BinaryWorkbenchTabContextDTO,
)
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_LAYOUT,
    BINARY_WORKBENCH_TEXT,
)
from src.presentation.ui.components.binary_workbench.editor.page_defaults import default_editor_kind, offset_from_hex
from src.presentation.ui.components.binary_workbench.editor.page_binary_loading import EditorPageBinaryLoadingMixin
from src.presentation.ui.components.binary_workbench.editor.page_byte_replacement import (
    EditorPageByteReplacementMixin,
)
from src.presentation.ui.components.binary_workbench.editor.page_virtual_copy import EditorPageVirtualCopyMixin
from src.presentation.ui.components.binary_workbench.editor.page_context_updates import EditorPageContextMixin
from src.presentation.ui.components.binary_workbench.editor.page_immediate_symbols import EditorPageImmediateSymbolsMixin
from src.presentation.ui.components.binary_workbench.editor.page_search import EditorPageSearchMixin
from src.presentation.ui.components.binary_workbench.editor.page_reader import reader_for_context
from src.presentation.ui.components.binary_workbench.editor.selection_summary import selection_summary_footer
from src.presentation.ui.components.binary_workbench.editor.table import BinaryWorkbenchGrid
from src.core.binary_workbench.codec_registry import binary_workbench_codec_for

JUMP_RETURN_HISTORY_LIMIT = 50

if TYPE_CHECKING:
    from src.core.binary_workbench.block_reader import CachedBinaryReader
    from src.core.binary_workbench.internal_file_reader import InternalFileView


class BinaryWorkbenchEditorPage(
    EditorPageBinaryLoadingMixin,
    EditorPageByteReplacementMixin,
    EditorPageVirtualCopyMixin,
    EditorPageContextMixin,
    EditorPageImmediateSymbolsMixin,
    EditorPageSearchMixin,
    QWidget,
):
    contextChanged = Signal(object)
    structuralVersionSaveRequested = Signal()
    openLabelTabRequested = Signal(str, int)
    symbolEditRequested = Signal(str)
    statusRequested = Signal(str)
    statusWarningRequested = Signal(str)
    statusErrorRequested = Signal(str)

    def __init__(
        self,
        context: BinaryWorkbenchTabContextDTO,
        preferences: BinaryWorkbenchPreferencesDTO | None = None,
        command_directory: Path | None = None,
    ) -> None:
        super().__init__()
        self._context = context
        self._consistency_version_ids: dict[str, str] = {}
        self._preferences = preferences or BinaryWorkbenchPreferencesDTO()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            0,
            BINARY_WORKBENCH_LAYOUT.PAGE_TOP_MARGIN,
            0,
            BINARY_WORKBENCH_LAYOUT.SUMMARY_BOTTOM_MARGIN,
        )
        layout.setSpacing(0)
        self.grid = BinaryWorkbenchGrid(binary_workbench_codec_for(context.cpu_arch))
        self.grid.set_command_directory(command_directory)
        self.grid.rowsChanged.connect(self._on_rows_changed)
        self.grid.assemblyTextChanged.connect(
            self.structuralVersionSaveRequested.emit
        )
        self.grid.commandsChanged.connect(self._on_commands_changed)
        self.grid.selectionSummaryChanged.connect(self._set_summary)
        self.grid.visibleWindowRequested.connect(self._load_visible_rows)
        self.grid.copySelectionRequested.connect(self._copy_virtual_selection)
        self.grid.immediateSymbolRequested.connect(self._add_immediate_symbol)
        self.grid.symbolEditRequested.connect(self.symbolEditRequested.emit)
        self.grid.labelActivated.connect(self.go_to_instruction_offset)
        self.grid.jumpNavigationActivated.connect(self.go_to_clicked_instruction_offset)
        self.grid.labelOpenTabRequested.connect(self.openLabelTabRequested)
        self.grid.selectAllRequested.connect(self.select_all_content)
        self.grid.commandStatusRequested.connect(self.statusRequested.emit)
        self.grid.commandWarningRequested.connect(self.statusWarningRequested.emit)
        self.grid.navigationWarningRequested.connect(self.statusErrorRequested.emit)
        self._reader: CachedBinaryReader | InternalFileView | None = None
        self._loading_visible_rows = False
        self._suppress_context_changed = False
        self._pending_selection: tuple[int, int] | None = None
        self._jump_return_history_by_version: dict[str, list[int]] = {}
        footer, (
            self.offset_summary,
            self.summary,
            self.length_summary,
            self.cpu_arch_summary,
            self.internal_file_summary,
        ) = selection_summary_footer(self)
        layout.addWidget(self.grid, 1)
        layout.addLayout(footer)
        self.load_context(context)

    def current_context(self) -> BinaryWorkbenchTabContextDTO:
        self.grid.flush_consistency_changes()
        self.grid.flush_pending_rows_changed()
        labels = self.grid.current_labels()
        if labels != self._context.labels:
            self._context = BinaryWorkbenchTabContextDTO(
                **{
                    **self._context.__dict__,
                    "labels": labels,
                    "symbol_offsets": {name: [offset] for name, offset in labels.items()},
                }
            )
        return self._context

    def has_pending_editor_changes(self) -> bool:
        """Return the page's constant-time dirty signal for close prompting."""

        return self.grid.has_pending_editor_changes()

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt API
        """Cancel this page's private workers before native widgets close.

        Waiting for ``destroyed`` was one event-loop turn too late: a closed
        page could keep a semantic worker busy while the next tab was already
        serving its viewport.  The explicit shutdown preserves the strict
        owner isolation required by the Binary Workbench scheduler.
        """

        self.grid.shutdown_consistency()
        super().closeEvent(event)

    def ensure_consistent(self, reason: str):
        """Return a complete current snapshot for a critical consumer."""

        return self.grid.ensure_consistent(reason)

    def suspend_eventual_consistency(self) -> tuple[bool, bool]:
        """Pause this page's CPU-bound work while a native modal is visible."""

        return self.grid.suspend_eventual_consistency()

    def resume_eventual_consistency(self, suspended: tuple[bool, bool]) -> None:
        """Resume work when a close prompt is cancelled or saving fails."""

        self.grid.resume_eventual_consistency(suspended)

    def rederive_symbol_lines(self, indices: tuple[int, ...]) -> None:
        """Project only source rows affected by changed Symbol definitions."""

        self.grid._consistency_coordinator.rederive_symbol_lines(indices)

    def rederive_all_symbol_lines(self) -> None:
        """Prioritize the viewport after a bulk Symbol catalog replacement."""

        self.grid._consistency_coordinator.rederive_all_symbol_lines()

    def rename_symbol_tokens(
        self,
        old_name: str,
        new_name: str,
        indices: tuple[int, ...],
    ) -> None:
        """Rename known source occurrences as one aggregated text operation."""

        pattern = re.compile(
            rf"(?<![A-Za-z0-9_])([_@]){re.escape(old_name)}(?![A-Za-z0-9_])",
            re.IGNORECASE,
        )
        coordinator = self.grid._consistency_coordinator
        coordinator.begin_edit_operation("rename-symbol")
        try:
            document = self.grid.instructions.document()
            for index in sorted(set(indices), reverse=True):
                block = document.findBlockByNumber(index)
                if not block.isValid():
                    continue
                updated = pattern.sub(
                    lambda match: f"{match.group(1)}{new_name}",
                    block.text(),
                )
                if updated == block.text():
                    continue
                cursor = QTextCursor(block)
                cursor.select(QTextCursor.SelectionType.LineUnderCursor)
                cursor.insertText(updated)
        finally:
            coordinator.end_edit_operation()

    def rename_consistency_version(self, previous: str, current: str) -> None:
        """Preserve one runtime version identity across a rename."""

        if previous in self._consistency_version_ids:
            self._consistency_version_ids[current] = self._consistency_version_ids.pop(previous)

    def create_consistency_version(self, name: str) -> str:
        """Assign a fresh runtime-only identity to a newly created version."""

        previous = self._consistency_version_ids.get(name)
        if previous is not None:
            self.grid.forget_consistency_owner(previous)
        version_id = uuid4().hex
        self._consistency_version_ids[name] = version_id
        return version_id

    def replace_consistency_versions(self, names: list[str]) -> None:
        """Materialize a newly loaded version collection with fresh identities."""

        for version_id in self._consistency_version_ids.values():
            self.grid.forget_consistency_owner(version_id)
        self._consistency_version_ids = {name: uuid4().hex for name in names}

    def delete_consistency_version(self, name: str) -> None:
        """Forget a runtime identity when its owning version is removed."""

        version_id = self._consistency_version_ids.pop(name, None)
        if version_id is not None:
            self.grid.forget_consistency_owner(version_id)

    def activate_consistency_context(self) -> None:
        """Start a fresh activation epoch for the currently materialized version."""

        self._activate_consistency_owner(self._context)

    def go_to_clicked_instruction_offset(self, target_offset: int, source_offset: int) -> None:
        self.grid.expand_label_for_offset(target_offset)
        if self._navigation_offset_is_valid(target_offset) and self._navigation_offset_is_valid(source_offset):
            self._push_jump_return_offset(source_offset)
        self.go_to_instruction_offset(target_offset, typing_cursor=True)

    def return_to_previous_jump_offset(self) -> bool:
        history = self._jump_return_history()
        if not history:
            return False
        self.go_to_instruction_offset(history.pop())
        return True

    def _push_jump_return_offset(self, offset: int) -> None:
        history = self._jump_return_history()
        history.append(offset)
        if len(history) > JUMP_RETURN_HISTORY_LIMIT:
            del history[: len(history) - JUMP_RETURN_HISTORY_LIMIT]

    def _jump_return_history(self) -> list[int]:
        return self._jump_return_history_by_version.setdefault(self._jump_return_history_key(), [])

    def _jump_return_history_key(self) -> str:
        return self._context.active_version_name or ""

    def replace_context(self, context: BinaryWorkbenchTabContextDTO) -> None:
        self._context = context
        self._activate_consistency_owner(context)
        self.grid.set_symbols(context.labels, context.variables, context.equates, context.symbol_offsets)
        self.grid.set_original_file_size(context.original_file_size)
        self._set_cpu_arch_summary(context.cpu_arch)
        self._set_internal_file_summary(context)

    def update_symbol_context(self, context: BinaryWorkbenchTabContextDTO) -> None:
        """Install a catalog revision without resetting this editor owner."""

        self._context = context
        self.grid.set_symbols(
            context.labels,
            context.variables,
            context.equates,
            context.symbol_offsets,
        )

    def replace_persistence_context(
        self,
        context: BinaryWorkbenchTabContextDTO,
    ) -> None:
        """Accept version persistence metadata without rebuilding editor projections."""

        self._context = context
        if not context.version_dirty:
            self.grid.mark_persistence_clean()

    def refresh_shared_context(
        self,
        context: BinaryWorkbenchTabContextDTO,
    ) -> BinaryWorkbenchTabContextDTO:
        self._suppress_context_changed = True
        try:
            self.load_context(context)
        finally:
            self._suppress_context_changed = False
        return self._context

    def release_heavy_resources(self, context: BinaryWorkbenchTabContextDTO) -> None:
        self._reader = None
        self._pending_selection = None
        self._context = context
        self.grid.set_decoded_text_values({})
        self.grid.set_symbols({}, {}, {}, {})
        self.grid.set_custom_commands({})
        self.grid.load_rows(
            [BINARY_WORKBENCH_TEXT.INSTRUCTION],
            [],
            self._preferences.group_bytes,
            uppercase_bytes=self._preferences.uppercase_bytes,
            uppercase_instructions=self._preferences.uppercase_instructions,
            reference_offset_bases=context.reference_offset_bases,
            jump_reference_offset=context.view_preferences.jump_reference_offset,
        )
        self._set_cpu_arch_summary(context.cpu_arch)
        self._set_internal_file_summary(context)

    def load_context(self, context: BinaryWorkbenchTabContextDTO) -> None:
        self._reader = reader_for_context(context, self._preferences)
        context = self._context_with_original_file_size(context)
        self._context = context
        self._activate_consistency_owner(context)
        codec = binary_workbench_codec_for(context.cpu_arch)
        self.grid.set_codec(codec)
        self.grid.set_label_folding_enabled(
            context.kind in {
                BINARY_WORKBENCH_TAB_KIND.ASSEMBLY,
                BINARY_WORKBENCH_TAB_KIND.SCRATCH,
            }
        )
        self.grid.set_decoded_text_values(enabled_encoding_values(
            context.encoding_tables,
            context.view_preferences.decoded_text_tables,
        ))
        self.grid.set_symbols(context.labels, context.variables, context.equates, context.symbol_offsets)
        self.grid.set_custom_commands(context.custom_commands)
        self.grid.set_edit_rules(_edit_rules_for_context(context, self._preferences))
        self.grid.set_selection_limit_bytes(self._preferences.selection_limit_bytes)
        self.grid.set_original_file_size(context.original_file_size)
        self.grid.set_default_editor_kind(default_editor_kind(context))
        if self._reader is not None:
            self.grid.load_rows(
                self._visible_columns(),
                [],
                self._preferences.group_bytes,
                offset_from_hex(context.last_open_offset),
                max(self._reader.file_size, context.file_size),
                True,
                self._preferences.uppercase_bytes,
                self._preferences.uppercase_instructions,
                reference_offset_bases=context.reference_offset_bases,
                jump_reference_offset=context.view_preferences.jump_reference_offset,
            )
            # The empty virtual shell is only a loading projection.  It must
            # never be flushed as a user edit into the newly installed reader.
            self.grid.discard_pending_rows_changed()
            self._load_visible_rows(
                offset_from_hex(context.last_open_offset),
                self.grid.visible_size(),
                1,
            )
        else:
            self.grid.load_rows(
                self._visible_columns(),
                context.rows,
                self._preferences.group_bytes,
                uppercase_bytes=self._preferences.uppercase_bytes,
                uppercase_instructions=self._preferences.uppercase_instructions,
                reference_offset_bases=context.reference_offset_bases,
                jump_reference_offset=context.view_preferences.jump_reference_offset,
            )
        self._set_cpu_arch_summary(context.cpu_arch)
        self._set_internal_file_summary(context)

    def _activate_consistency_owner(self, context: BinaryWorkbenchTabContextDTO) -> None:
        """Bind the grid to an internal version identity for this activation."""

        key = context.active_version_name or "<unversioned>"
        version_id = self._consistency_version_ids.setdefault(key, uuid4().hex)
        self.grid.activate_consistency_owner(context.tab_id, version_id)

    def load_preferences(self, preferences: BinaryWorkbenchPreferencesDTO) -> None:
        self.set_preferences(preferences)
        self.load_context(self._context)

    def set_preferences(self, preferences: BinaryWorkbenchPreferencesDTO) -> None:
        self._preferences = preferences
        self.grid.set_edit_rules(_edit_rules_for_context(self._context, preferences))
        self.grid.set_selection_limit_bytes(preferences.selection_limit_bytes)

    def set_responsive_bytes_hidden(self, hidden: bool) -> None:
        """Apply the Binary Workbench window-width rule to this page's grid."""

        self.grid.set_responsive_bytes_hidden(hidden)

    def set_cpu_arch(self, value: str) -> None:
        self._update_context({"cpu_arch": value})

    def select_block(self, start_offset: int, end_offset: int) -> None:
        first, last = sorted((start_offset, end_offset))
        end_offset = capped_end_offset(first, last, self._preferences.selection_limit_bytes)
        start_offset = first
        if self._reader is not None:
            self._load_visible_rows(start_offset, self.grid.visible_size(), 1)
            kind = self.focused_editor_kind() or BINARY_WORKBENCH_TEXT.BYTES
            if kind not in {
                BINARY_WORKBENCH_TEXT.BYTES,
                BINARY_WORKBENCH_TEXT.RAW_INSTRUCTIONS,
                BINARY_WORKBENCH_TEXT.INSTRUCTION,
            }:
                kind = BINARY_WORKBENCH_TEXT.BYTES
            self.grid.select_virtual_range(kind, start_offset, end_offset)
            return
        else:
            self.grid.set_visible_offset(start_offset)
        if self.focused_editor_kind() == BINARY_WORKBENCH_TEXT.INSTRUCTION:
            self.grid.select_instruction_offsets(start_offset, end_offset)
            return
        self.grid.select_offsets(start_offset, end_offset)

    def select_all_content(self) -> None:
        self.grid.select_all_content()

    def current_cursor_offset(self) -> int:
        return self.grid.current_cursor_offset()

    def assembly_text(self) -> str:
        return self.grid.assembly_text()

    def set_custom_commands(self, commands: dict[str, list[str]]) -> None:
        self.grid.set_custom_commands(commands)
        self._update_context({"custom_commands": commands})

    def set_command_directory(self, path: Path | None) -> None:
        self.grid.set_command_directory(path)

    def replace_custom_command(self, name: str, instructions: list[str]) -> bool:
        return self.grid.replace_custom_command(name, instructions)

    def remove_custom_command(self, name: str) -> bool:
        return self.grid.remove_custom_command(name)

    def focused_editor_kind(self) -> str | None:
        return self.grid.focused_editor_kind()

    def _select_pending_offset(self) -> None:
        if self._pending_selection is None:
            return
        start, end = self._pending_selection
        self.grid.select_offsets(start, end)
        self._pending_selection = None

    def _context_with_original_file_size(
        self,
        context: BinaryWorkbenchTabContextDTO,
    ) -> BinaryWorkbenchTabContextDTO:
        if context.original_file_size > 0:
            return context
        original_file_size = self._reader.file_size if self._reader is not None else valid_offset_end(context.rows)
        return BinaryWorkbenchTabContextDTO(
            **{
                **context.__dict__,
                "file_size": max(context.file_size, original_file_size),
                "original_file_size": original_file_size,
            }
        )


def _edit_rules_for_context(
    context: BinaryWorkbenchTabContextDTO,
    preferences: BinaryWorkbenchPreferencesDTO,
) -> BinaryWorkbenchEditRulesDTO:
    if context.kind in {
        BINARY_WORKBENCH_TAB_KIND.ASSEMBLY,
        BINARY_WORKBENCH_TAB_KIND.SCRATCH,
    }:
        return preferences.assembly_edit_rules
    return preferences.binary_edit_rules
