from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import QWidget

from src.core.binary_workbench.selection_limits import (
    DEFAULT_SELECTION_LIMIT_BYTES,
    normalized_selection_limit,
)
from src.core.binary_workbench.mips_r3000a.symbol_resolver import MipsSymbolResolver
from src.modules.contracts import CPUArchCodec
from src.modules.binary_workbench_dtos import BinaryWorkbenchEditRulesDTO, BinaryWorkbenchRowDTO
from src.presentation.ui.components.binary_workbench.editor.grid_commit import GridCommitMixin
from src.presentation.ui.components.binary_workbench.editor.grid_byte_replacement import (
    GridByteReplacementMixin,
)
from src.presentation.ui.components.binary_workbench.editor.grid_bytes_structural_editing import (
    GridBytesStructuralEditingMixin,
)
from src.presentation.ui.components.binary_workbench.editor.grid_commands import (
    GridCommandsMixin,
)
from src.presentation.ui.components.binary_workbench.editor.grid_edit_rules import (
    GridEditRulesMixin,
)
from src.presentation.ui.components.binary_workbench.editor.grid_editing import GridEditingMixin
from src.presentation.ui.components.binary_workbench.editor.grid_derived_display import (
    GridDerivedDisplayMixin,
)
from src.presentation.ui.components.binary_workbench.editor.grid_incremental_editing import (
    GridIncrementalEditingMixin,
)
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
from src.presentation.ui.components.binary_workbench.editor.grid_refresh_window import (
    GridRefreshWindowMixin,
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
from src.presentation.ui.components.binary_workbench.editor.consistency import (
    EditorConsistencyCoordinator,
)
from src.presentation.ui.components.binary_workbench.constant_groups.timing import (
    BINARY_WORKBENCH_TIMING,
)


ROWS_CHANGED_DEBOUNCE_MS = 180


class BinaryWorkbenchGrid(
    GridLayoutMixin,
    GridLabelFoldingMixin,
    GridResizingMixin,
    GridDerivedDisplayMixin,
    GridRenderingMixin,
    GridCommandsMixin,
    GridRawInstructionsMixin,
    GridEditRulesMixin,
    GridCommitMixin,
    GridByteReplacementMixin,
    GridBytesStructuralEditingMixin,
    GridIncrementalEditingMixin,
    GridRefreshWindowMixin,
    GridEditingMixin,
    GridSelectionMixin,
    GridVirtualSelectionMixin,
    GridViewportSelectionMixin,
    GridVirtualUndoMixin,
    GridSelectionRangesMixin,
    GridOffsetsMixin,
    QWidget,
):
    """Coordinate one source editor and a bounded set of derived text columns."""

    rowsChanged = Signal(list)
    assemblyTextChanged = Signal()
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
        self._configured_columns: list[str] = []
        self._rows: list[BinaryWorkbenchRowDTO] = []
        self._all_rows: list[BinaryWorkbenchRowDTO] = []
        self._offset_editors: dict[str, WorkbenchEditor] = {}
        self._updating = False
        self._syncing_editor_change = False
        self._bytes_staged_incomplete = False
        self._bytes_staged_block: int | None = None
        self._bytes_edit_block_hint: int | None = None
        self._bytes_edit_alignment_hint: int | None = None
        self._active_bytes_alignment_hint: int | None = None
        self._byte_transition_validated = False
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
        self._label_fold_regions_by_row = {}
        self._collapsed_labels: set[str] = set()
        self._directive_fold_region = None
        self._directives_collapsed = False
        self._last_fold_hidden_rows: set[int] = set()
        self._variables: dict[str, str] = {}
        self._equates: dict[str, str] = {}
        self._symbol_resolver = MipsSymbolResolver()
        self._symbol_offsets: dict[str, list[str]] = {}
        self._last_editor_kind: str | None = None
        self._dirty_editor_kind: str | None = None
        self._edit_origin_kind: str | None = None
        self._edit_rules = BinaryWorkbenchEditRulesDTO()
        self._custom_commands = {}
        self._command_directory: Path | None = None
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
        self._pending_current_rows_changed = False
        self._pending_rows_changed_origin: str | None = None
        self._rows_changed_emit_timer = QTimer(self)
        self._rows_changed_emit_timer.setSingleShot(True)
        self._rows_changed_emit_timer.timeout.connect(self.flush_pending_rows_changed)
        self._viewport_projection_timer = QTimer(self)
        self._viewport_projection_timer.setSingleShot(True)
        self._viewport_projection_timer.setInterval(
            BINARY_WORKBENCH_TIMING.CONSISTENCY_SCROLL_FRAME_MS
        )
        self._viewport_projection_timer.timeout.connect(
            self._refresh_visible_highlighter_projection
        )
        self._setup_incremental_editing()
        self._setup_bytes_structural_editing()
        self._setup_refresh_window()
        self._build_ui()
        self._consistency_coordinator = EditorConsistencyCoordinator(self)
        self.destroyed.connect(lambda: self._consistency_coordinator.shutdown())
        self._refresh_command_completions()

    def activate_consistency_owner(self, tab_id: str, version_id: str) -> None:
        """Bind editor derivations to one runtime tab/version identity."""

        self._consistency_coordinator.activate_owner(tab_id, version_id)

    def forget_consistency_owner(self, version_id: str) -> None:
        """Remove the runtime state of a version that no longer exists."""

        self._consistency_coordinator.forget_owner(version_id)

    def shutdown_consistency(self) -> None:
        """Stop this grid's private timers and cooperative worker pool."""

        self._consistency_coordinator.shutdown()

    def ensure_consistent(self, reason: str):
        """Run a synchronous source-to-derived barrier for a critical action."""

        return self._consistency_coordinator.ensure_consistent(reason)

    def flush_consistency_changes(self) -> None:
        """Classify document changes already delivered by Qt."""

        self._consistency_coordinator.flush_collected_changes()

    def _emit_rows_changed(
        self,
        rows: list[BinaryWorkbenchRowDTO] | None = None,
        deferred: bool = False,
    ) -> None:
        """Publish rows, deferring the full snapshot allocation when possible."""

        if not deferred:
            self._pending_rows_changed = None
            self._pending_current_rows_changed = False
            self._pending_rows_changed_origin = None
            self._rows_changed_emit_timer.stop()
            self.rowsChanged.emit(list(self.export_rows() if rows is None else rows))
            return
        self._pending_rows_changed = rows
        self._pending_current_rows_changed = rows is None
        self._pending_rows_changed_origin = self._edit_origin_kind
        self._rows_changed_emit_timer.start(ROWS_CHANGED_DEBOUNCE_MS)

    def flush_pending_rows_changed(self) -> None:
        if self._pending_rows_changed is None and not self._pending_current_rows_changed:
            return
        rows = (
            self.export_rows()
            if self._pending_current_rows_changed
            else self._pending_rows_changed
        )
        origin = self._pending_rows_changed_origin
        self._pending_rows_changed = None
        self._pending_current_rows_changed = False
        self._pending_rows_changed_origin = None
        self._rows_changed_emit_timer.stop()
        previous_origin = self._edit_origin_kind
        self._edit_origin_kind = origin
        try:
            self.rowsChanged.emit(list(rows or ()))
        finally:
            self._edit_origin_kind = previous_origin

    def discard_pending_rows_changed(self) -> None:
        """Discard a deferred edit superseded by an authoritative context load."""

        self._pending_rows_changed = None
        self._pending_current_rows_changed = False
        self._pending_rows_changed_origin = None
        self._rows_changed_emit_timer.stop()

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
