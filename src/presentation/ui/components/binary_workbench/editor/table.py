from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget

from src.modules.contracts import CPUArchCodec
from src.modules.dtos import BinaryWorkbenchRowDTO
from src.presentation.ui.components.binary_workbench.editor.grid_commit import GridCommitMixin
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
from src.presentation.ui.components.binary_workbench.editor.workbench_editor import WorkbenchEditor


class BinaryWorkbenchGrid(
    GridLayoutMixin,
    GridResizingMixin,
    GridRenderingMixin,
    GridRawInstructionsMixin,
    GridCommitMixin,
    GridEditingMixin,
    GridSelectionMixin,
    GridSelectionRangesMixin,
    GridOffsetsMixin,
    QWidget,
):
    rowsChanged = Signal(list)
    selectionSummaryChanged = Signal(str)
    visibleWindowRequested = Signal(int, int, int)
    selectAllRequested = Signal()
    immediateSymbolRequested = Signal(str, str)
    labelActivated = Signal(int)
    labelOpenTabRequested = Signal(str, int)

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
        self._group_bytes = 1
        self._uppercase_bytes = True
        self._uppercase_instructions = True
        self._labels: dict[str, str] = {}
        self._variables: dict[str, str] = {}
        self._equates: dict[str, str] = {}
        self._last_editor_kind: str | None = None
        self._dirty_editor_kind: str | None = None
        self._edit_origin_kind: str | None = None
        self._editor_text_signatures: dict[int, str] = {}
        self._visible_start_offset = 0
        self._last_visible_offset = 0
        self._layout_refresh_scheduled = False
        self._build_ui()

    def set_codec(self, codec: CPUArchCodec) -> None:
        self._codec = codec
