from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import QWidget

from src.core.binary_workbench.selection_limits import (
    DEFAULT_SELECTION_LIMIT_BYTES,
    normalized_selection_limit,
)
from src.modules.contracts import CPUArchCodec
from src.modules.binary_workbench_dtos import BinaryWorkbenchEditRulesDTO, BinaryWorkbenchRowDTO
from src.presentation.ui.components.binary_workbench.editor.grid_commit import GridCommitMixin
from src.presentation.ui.components.binary_workbench.editor.grid_commands import (
    GridCommandsMixin,
)
from src.presentation.ui.components.binary_workbench.editor.grid_edit_rules import (
    GridEditRulesMixin,
)
from src.presentation.ui.components.binary_workbench.editor.grid_editing import GridEditingMixin
from src.presentation.ui.components.binary_workbench.editor.grid_layout import GridLayoutMixin
from src.presentation.ui.components.binary_workbench.editor.grid_label_folding import (
    GridLabelFoldingMixin,
)
from src.presentation.ui.components.binary_workbench.editor.grid_offsets import GridOffsetsMixin
from src.presentation.ui.components.binary_workbench.editor.grid_rendering import GridRenderingMixin
from src.presentation.ui.components.binary_workbench.editor.grid_resizing import GridResizingMixin
from src.presentation.ui.components.binary_workbench.editor.grid_raw_instructions import (
    GridRawInstructionsMixin,
)
from src.presentation.ui.components.binary_workbench.editor.grid_selection import GridSelectionMixin
from src.presentation.ui.components.binary_workbench.editor.grid_selection_ranges import (
    GridSelectionRangesMixin,
)
from src.presentation.ui.components.binary_workbench.editor.grid_virtual_selection import (
    GridVirtualSelectionMixin,
)
from src.presentation.ui.components.binary_workbench.editor.grid_virtual_undo import (
    GridVirtualUndoMixin,
)
from src.presentation.ui.components.binary_workbench.editor.grid_viewport_selection import (
    GridViewportSelectionMixin,
)
from src.presentation.ui.components.binary_workbench.editor.workbench_editor import WorkbenchEditor


ROWS_CHANGED_DEBOUNCE_MS = 180


class BinaryWorkbenchGrid(
    GridLayoutMixin,
    GridLabelFoldingMixin,
    GridResizingMixin,
    GridRenderingMixin,
    GridCommandsMixin,
    GridRawInstructionsMixin,
    GridEditRulesMixin,
    GridCommitMixin,
    GridEditingMixin,
    GridSelectionMixin,
    GridVirtualSelectionMixin,
    GridViewportSelectionMixin,
    GridVirtualUndoMixin,
    GridSelectionRangesMixin,
    GridOffsetsMixin,
    QWidget,
):
    rowsChanged = Signal(list)
    selectionSummaryChanged = Signal(str)
    visibleWindowRequested = Signal(int, int, int)
    selectAllRequested = Signal()
    copySelectionRequested = Signal(str, int, int)
    immediateSymbolRequested = Signal(str, str, int, int)
    symbolEditRequested = Signal(str)
    labelActivated = Signal(int)
    jumpNavigationActivated = Signal(int, int)
    labelOpenTabRequested = Signal(str, int)
    commandsChanged = Signal(dict)
    commandWarningRequested = Signal(str)
    navigationWarningRequested = Signal(str)

    def __init__(self, codec: CPUArchCodec) -> None:
        super().__init__()
        self.setObjectName("binary-workbench-editor-shell")
        self._codec = codec
        self._columns: list[str] = []
        self._rows: list[BinaryWorkbenchRowDTO] = []
        self._all_rows: list[BinaryWorkbenchRowDTO] = []
        self._offset_editors: dict[str, WorkbenchEditor] = {}
        self._updating = False
        self._syncing_editor_change = False
        self._virtual = False
        self._total_size = 0
        self._original_file_size = 0
        self._group_bytes = 1
        self._uppercase_bytes = True
        self._uppercase_instructions = True
        self._reference_offset_bases: dict[str, str] = {}
        self._visible_offset_columns: list[str] = []
        self._jump_reference_offset = ""
        self._decoded_text_values: dict[int, str] = {}
        self._labels: dict[str, str] = {}
        self._label_folding_enabled = False
        self._label_fold_regions = []
        self._collapsed_labels: set[str] = set()
        self._variables: dict[str, str] = {}
        self._equates: dict[str, str] = {}
        self._symbol_offsets: dict[str, list[str]] = {}
        self._last_editor_kind: str | None = None
        self._dirty_editor_kind: str | None = None
        self._edit_origin_kind: str | None = None
        self._edit_rules = BinaryWorkbenchEditRulesDTO()
        self._custom_commands = {}
        self._command_directory: Path | None = None
        self._editor_text_signatures: dict[int, str] = {}
        self._visible_start_offset = 0
        self._last_visible_offset = 0
        self._layout_refresh_scheduled = False
        self._syncing_editor_scrollbars = False
        self._virtual_selection_anchor: int | None = None
        self._virtual_selection_kind: str | None = None
        self._virtual_selection_range: tuple[str, int, int] | None = None
        self._virtual_selection_scrolling = False
        self._viewport_line_selection = None
        self._selection_limit_bytes = DEFAULT_SELECTION_LIMIT_BYTES
        self._reset_virtual_undo_cache()
        self._pending_rows_changed: list[BinaryWorkbenchRowDTO] | None = None
        self._pending_rows_changed_origin: str | None = None
        self._rows_changed_emit_timer = QTimer(self)
        self._rows_changed_emit_timer.setSingleShot(True)
        self._rows_changed_emit_timer.timeout.connect(self.flush_pending_rows_changed)
        self._build_ui()
        self._refresh_command_completions()

    def _emit_rows_changed(self, rows: list[BinaryWorkbenchRowDTO], deferred: bool = False) -> None:
        snapshot = list(rows)
        if not deferred:
            self._pending_rows_changed = None
            self._pending_rows_changed_origin = None
            self._rows_changed_emit_timer.stop()
            self.rowsChanged.emit(snapshot)
            return
        self._pending_rows_changed = snapshot
        self._pending_rows_changed_origin = self._edit_origin_kind
        self._rows_changed_emit_timer.start(ROWS_CHANGED_DEBOUNCE_MS)

    def flush_pending_rows_changed(self) -> None:
        if self._pending_rows_changed is None:
            return
        rows = self._pending_rows_changed
        origin = self._pending_rows_changed_origin
        self._pending_rows_changed = None
        self._pending_rows_changed_origin = None
        self._rows_changed_emit_timer.stop()
        previous_origin = self._edit_origin_kind
        self._edit_origin_kind = origin
        try:
            self.rowsChanged.emit(rows)
        finally:
            self._edit_origin_kind = previous_origin

    def set_editor_popups_suppressed(self, enabled: bool) -> None:
        for editor in self._popup_editors():
            editor.set_completion_popup_suppressed(enabled)

    def hide_editor_popups(self) -> None:
        for editor in self._popup_editors():
            editor.hide_completion_popup()

    def _popup_editors(self):
        return (
            *self._offset_editors.values(),
            self.raw_instructions,
            self.bytes,
            self.decoded_text,
            self.instructions,
        )

    def set_codec(self, codec: CPUArchCodec) -> None:
        self._codec = codec

    def set_selection_limit_bytes(self, value: int) -> None:
        self._selection_limit_bytes = normalized_selection_limit(value)

    def set_decoded_text_values(self, values: dict[int, str]) -> None:
        self._decoded_text_values = dict(values)
