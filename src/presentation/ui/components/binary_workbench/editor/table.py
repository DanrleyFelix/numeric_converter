from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
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
from src.presentation.ui.components.binary_workbench.editor.workbench_editor import WorkbenchEditor


class BinaryWorkbenchGrid(
    GridLayoutMixin,
    GridResizingMixin,
    GridRenderingMixin,
    GridCommandsMixin,
    GridRawInstructionsMixin,
    GridEditRulesMixin,
    GridCommitMixin,
    GridEditingMixin,
    GridSelectionMixin,
    GridVirtualSelectionMixin,
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
    labelActivated = Signal(int)
    labelOpenTabRequested = Signal(str, int)
    commandsChanged = Signal(dict)
    commandWarningRequested = Signal(str)

    def __init__(self, codec: CPUArchCodec) -> None:
        super().__init__()
        self.setObjectName("binary-workbench-editor-shell")
        self._codec = codec
        self._columns: list[str] = []
        self._rows: list[BinaryWorkbenchRowDTO] = []
        self._all_rows: list[BinaryWorkbenchRowDTO] = []
        self._offset_editors: dict[str, WorkbenchEditor] = {}
        self._updating = False
        self._virtual = False
        self._total_size = 0
        self._original_file_size = 0
        self._group_bytes = 1
        self._uppercase_bytes = True
        self._uppercase_instructions = True
        self._decoded_text_values: dict[int, str] = {}
        self._labels: dict[str, str] = {}
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
        self._selection_limit_bytes = DEFAULT_SELECTION_LIMIT_BYTES
        self._build_ui()
        self._refresh_command_completions()

    def set_codec(self, codec: CPUArchCodec) -> None:
        self._codec = codec

    def set_selection_limit_bytes(self, value: int) -> None:
        self._selection_limit_bytes = normalized_selection_limit(value)

    def set_decoded_text_values(self, values: dict[int, str]) -> None:
        self._decoded_text_values = dict(values)
