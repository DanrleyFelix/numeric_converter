from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from src.modules.dtos import BinaryWorkbenchTabContextDTO
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_LAYOUT,
    BINARY_WORKBENCH_TEXT,
)
from src.presentation.ui.components.binary_workbench.editor.page_defaults import (
    default_editor_kind,
    offset_from_hex,
)
from src.presentation.ui.components.binary_workbench.editor.page_binary_loading import (
    EditorPageBinaryLoadingMixin,
)
from src.presentation.ui.components.binary_workbench.editor.page_context_updates import (
    EditorPageContextMixin,
)
from src.presentation.ui.components.binary_workbench.editor.page_search import (
    EditorPageSearchMixin,
)
from src.presentation.ui.components.binary_workbench.editor.table import BinaryWorkbenchGrid
from src.core.binary_workbench.codec_registry import binary_workbench_codec_for

if TYPE_CHECKING:
    from src.core.binary_workbench.block_reader import CachedBinaryReader


class BinaryWorkbenchEditorPage(
    EditorPageBinaryLoadingMixin,
    EditorPageContextMixin,
    EditorPageSearchMixin,
    QWidget,
):
    contextChanged = Signal(object)

    def __init__(self, context: BinaryWorkbenchTabContextDTO) -> None:
        super().__init__()
        self._context = context
        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            0,
            BINARY_WORKBENCH_LAYOUT.PAGE_TOP_MARGIN,
            0,
            BINARY_WORKBENCH_LAYOUT.SUMMARY_BOTTOM_MARGIN,
        )
        layout.setSpacing(0)
        self.grid = BinaryWorkbenchGrid(binary_workbench_codec_for(context.cpu_arch))
        self.grid.rowsChanged.connect(self._on_rows_changed)
        self.grid.selectionSummaryChanged.connect(self._set_summary)
        self.grid.visibleWindowRequested.connect(self._load_visible_rows)
        self.grid.selectAllRequested.connect(self.select_all_content)
        self._reader: CachedBinaryReader | None = None
        self._loading_visible_rows = False
        self._pending_selection: tuple[int, int] | None = None
        self.summary = QLabel(BINARY_WORKBENCH_TEXT.SELECTION_EMPTY, self)
        self.summary.setObjectName("binary-workbench-selection")
        footer = QHBoxLayout()
        footer.setContentsMargins(0, BINARY_WORKBENCH_LAYOUT.SUMMARY_TOP_MARGIN, 0, 0)
        footer.addWidget(self.summary)
        footer.addStretch(1)
        layout.addWidget(self.grid, 1)
        layout.addLayout(footer)
        self.load_context(context)

    def current_context(self) -> BinaryWorkbenchTabContextDTO:
        return self._context

    def load_context(self, context: BinaryWorkbenchTabContextDTO) -> None:
        self._context = context
        self._reader = self._reader_for_context(context)
        self.grid.set_codec(binary_workbench_codec_for(context.cpu_arch))
        self.grid.set_symbols(context.labels, context.variables, context.equates)
        self.grid.set_default_editor_kind(default_editor_kind(context))
        if self._reader is not None:
            self.grid.load_rows(
                self._visible_columns(),
                [],
                context.view_preferences.group_bytes,
                offset_from_hex(context.last_open_offset),
                self._reader.file_size,
                True,
                context.view_preferences.uppercase_bytes,
                context.view_preferences.uppercase_instructions,
            )
            self._load_visible_rows(
                offset_from_hex(context.last_open_offset),
                self.grid.visible_size(),
                1,
            )
        else:
            self.grid.load_rows(
                self._visible_columns(),
                context.rows,
                context.view_preferences.group_bytes,
                uppercase_bytes=context.view_preferences.uppercase_bytes,
                uppercase_instructions=context.view_preferences.uppercase_instructions,
            )
        self.summary.setText(BINARY_WORKBENCH_TEXT.SELECTION_EMPTY)

    def set_cpu_arch(self, value: str) -> None:
        self._update_context({"cpu_arch": value})

    def go_to_offset(self, offset: int) -> None:
        self._pending_selection = (offset, offset)
        self.grid.set_visible_offset(offset)
        if self._reader is None:
            self._select_pending_offset()

    def select_block(self, start_offset: int, end_offset: int) -> None:
        if self._reader is not None:
            size = max(1, end_offset - start_offset + 1)
            self._load_visible_rows(start_offset, size, 1)
        else:
            self.grid.set_visible_offset(start_offset)
        if self.focused_editor_kind() == BINARY_WORKBENCH_TEXT.INSTRUCTION:
            self.grid.select_instruction_offsets(start_offset, end_offset)
            return
        self.grid.select_offsets(start_offset, end_offset)

    def select_all_content(self) -> None:
        if self._reader is not None:
            self._load_visible_rows(
                0,
                min(self._reader.file_size, BINARY_WORKBENCH_LAYOUT.SELECT_ALL_MAX_BYTES),
                1,
            )
        self.grid.select_all_content()

    def assembly_text(self) -> str:
        return self.grid.assembly_text()

    def focused_editor_kind(self) -> str | None:
        return self.grid.focused_editor_kind()

    def _select_pending_offset(self) -> None:
        if self._pending_selection is None:
            return
        start, end = self._pending_selection
        self.grid.select_offsets(start, end)
        self._pending_selection = None
