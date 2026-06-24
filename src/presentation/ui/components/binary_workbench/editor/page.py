from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QVBoxLayout, QWidget

from src.core.binary_workbench.selection_limits import capped_end_offset
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
from src.presentation.ui.components.binary_workbench.editor.page_virtual_copy import EditorPageVirtualCopyMixin
from src.presentation.ui.components.binary_workbench.editor.page_context_updates import EditorPageContextMixin
from src.presentation.ui.components.binary_workbench.editor.page_immediate_symbols import EditorPageImmediateSymbolsMixin
from src.presentation.ui.components.binary_workbench.editor.page_search import EditorPageSearchMixin
from src.presentation.ui.components.binary_workbench.editor.selection_summary import selection_summary_footer
from src.presentation.ui.components.binary_workbench.editor.table import BinaryWorkbenchGrid
from src.core.binary_workbench.codec_registry import binary_workbench_codec_for
from src.core.binary_workbench.symbolic_replacements import apply_symbol_offsets

if TYPE_CHECKING:
    from src.core.binary_workbench.block_reader import CachedBinaryReader


class BinaryWorkbenchEditorPage(
    EditorPageBinaryLoadingMixin,
    EditorPageVirtualCopyMixin,
    EditorPageContextMixin,
    EditorPageImmediateSymbolsMixin,
    EditorPageSearchMixin,
    QWidget,
):
    contextChanged = Signal(object)
    openLabelTabRequested = Signal(str, int)
    statusWarningRequested = Signal(str)

    def __init__(
        self,
        context: BinaryWorkbenchTabContextDTO,
        preferences: BinaryWorkbenchPreferencesDTO | None = None,
        command_directory: Path | None = None,
    ) -> None:
        super().__init__()
        self._context = context
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
        self.grid.commandsChanged.connect(self._on_commands_changed)
        self.grid.selectionSummaryChanged.connect(self._set_summary)
        self.grid.visibleWindowRequested.connect(self._load_visible_rows)
        self.grid.copySelectionRequested.connect(self._copy_virtual_selection)
        self.grid.immediateSymbolRequested.connect(self._add_immediate_symbol)
        self.grid.labelActivated.connect(self.go_to_instruction_offset)
        self.grid.labelOpenTabRequested.connect(self.openLabelTabRequested)
        self.grid.selectAllRequested.connect(self.select_all_content)
        self.grid.commandWarningRequested.connect(self.statusWarningRequested.emit)
        self._reader: CachedBinaryReader | None = None
        self._loading_visible_rows = False
        self._pending_selection: tuple[int, int] | None = None
        footer, (
            self.offset_summary,
            self.summary,
            self.length_summary,
            self.cpu_arch_summary,
        ) = selection_summary_footer(self)
        layout.addWidget(self.grid, 1)
        layout.addLayout(footer)
        self.load_context(context)

    def current_context(self) -> BinaryWorkbenchTabContextDTO:
        return self._context

    def replace_context(self, context: BinaryWorkbenchTabContextDTO) -> None:
        self._context = context
        self.grid.set_original_file_size(context.original_file_size)
        self._set_cpu_arch_summary(context.cpu_arch)

    def load_context(self, context: BinaryWorkbenchTabContextDTO) -> None:
        self._reader = self._reader_for_context(context)
        context = self._context_with_original_file_size(context)
        self._context = context
        codec = binary_workbench_codec_for(context.cpu_arch)
        self.grid.set_codec(codec)
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
            )
            self._load_visible_rows(
                offset_from_hex(context.last_open_offset),
                self.grid.visible_size(),
                1,
            )
        else:
            rows = apply_symbol_offsets(context.rows, context.variables, context.equates, context.symbol_offsets, codec)
            self.grid.load_rows(
                self._visible_columns(),
                rows,
                self._preferences.group_bytes,
                uppercase_bytes=self._preferences.uppercase_bytes,
                uppercase_instructions=self._preferences.uppercase_instructions,
            )
        self._set_cpu_arch_summary(context.cpu_arch)

    def load_preferences(self, preferences: BinaryWorkbenchPreferencesDTO) -> None:
        self.set_preferences(preferences)
        self.load_context(self._context)

    def set_preferences(self, preferences: BinaryWorkbenchPreferencesDTO) -> None:
        self._preferences = preferences
        self.grid.set_edit_rules(_edit_rules_for_context(self._context, preferences))
        self.grid.set_selection_limit_bytes(preferences.selection_limit_bytes)

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
        original_file_size = self._reader.file_size if self._reader is not None else len(context.rows) * ROW_BYTES
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
