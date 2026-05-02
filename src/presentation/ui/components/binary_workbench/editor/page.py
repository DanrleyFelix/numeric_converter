from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from src.modules.dtos import BinaryWorkbenchRowDTO, BinaryWorkbenchTabContextDTO
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_LAYOUT,
    BINARY_WORKBENCH_TEXT,
)
from src.presentation.ui.components.binary_workbench.editor.table import BinaryWorkbenchGrid


class BinaryWorkbenchEditorPage(QWidget):
    contextChanged = Signal(object)

    def __init__(self, context: BinaryWorkbenchTabContextDTO) -> None:
        super().__init__()
        self._context = context
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(BINARY_WORKBENCH_LAYOUT.TAB_SPACING)
        self.offsets = QFrame(self)
        self.offsets.setObjectName("binary-workbench-offsets")
        self.offsets_layout = QHBoxLayout(self.offsets)
        self.offsets_layout.setContentsMargins(
            BINARY_WORKBENCH_LAYOUT.OFFSET_BAR_LEFT,
            BINARY_WORKBENCH_LAYOUT.OFFSET_BAR_TOP,
            BINARY_WORKBENCH_LAYOUT.OFFSET_BAR_RIGHT,
            BINARY_WORKBENCH_LAYOUT.OFFSET_BAR_BOTTOM,
        )
        self.offsets_layout.setSpacing(BINARY_WORKBENCH_LAYOUT.TAB_SPACING)
        self.grid = BinaryWorkbenchGrid()
        self.grid.rowsChanged.connect(self._on_rows_changed)
        self.grid.selectionSummaryChanged.connect(self._set_summary)
        self.summary = QLabel(self)
        self.summary.setObjectName("binary-workbench-selection")
        layout.addWidget(self.offsets)
        layout.addWidget(self.grid, 1)
        layout.addWidget(self.summary)
        self.load_context(context)

    def current_context(self) -> BinaryWorkbenchTabContextDTO:
        return self._context

    def load_context(self, context: BinaryWorkbenchTabContextDTO) -> None:
        self._context = context
        self._rebuild_offsets()
        self.grid.load_rows(self._visible_columns(), context.rows)

    def set_cpu_arch(self, value: str) -> None:
        self._context = BinaryWorkbenchTabContextDTO(**{**self._context.__dict__, "cpu_arch": value})
        self.contextChanged.emit(self._context)

    def _rebuild_offsets(self) -> None:
        while self.offsets_layout.count():
            item = self.offsets_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        label = QLabel(BINARY_WORKBENCH_TEXT.OFFSET_REFS, self.offsets)
        label.setObjectName("binary-workbench-offset-label")
        self.offsets_layout.addWidget(label)
        for name in self._context.reference_offsets:
            button = QPushButton(name, self.offsets)
            button.setObjectName("binary-workbench-offset")
            button.setCheckable(True)
            button.setChecked(self._context.view_preferences.visible_columns.get(name, True))
            button.clicked.connect(lambda checked, key=name: self._toggle_offset(key, checked))
            self.offsets_layout.addWidget(button)
        self.offsets_layout.addWidget(self._control("+", self._add_offset))
        self.offsets_layout.addWidget(self._control("-", self._remove_offset))
        self.offsets_layout.addStretch(1)

    def _control(self, text: str, callback) -> QPushButton:
        button = QPushButton(text, self.offsets)
        button.setObjectName("binary-workbench-offset-control")
        button.clicked.connect(callback)
        return button

    def _toggle_offset(self, name: str, checked: bool) -> None:
        visible = dict(self._context.view_preferences.visible_columns)
        visible[name] = checked
        self._update_context({"view_preferences": self._context.view_preferences.__class__(visible, list(self._context.view_preferences.decoded_text_tables))})

    def _add_offset(self) -> None:
        next_name = f"Reference Offset {len([name for name in self._context.reference_offsets if name.startswith('Reference Offset')]) + 1}"
        rows = [BinaryWorkbenchRowDTO({**row.offsets, next_name: row.offsets.get("RAM", "0x00000000")}, row.instruction, row.bytes_text) for row in self._context.rows]
        visible = dict(self._context.view_preferences.visible_columns)
        visible[next_name] = True
        self._update_context({"reference_offsets": [*self._context.reference_offsets, next_name], "rows": rows, "view_preferences": self._context.view_preferences.__class__(visible, list(self._context.view_preferences.decoded_text_tables))})

    def _remove_offset(self) -> None:
        custom = [name for name in self._context.reference_offsets if name.startswith("Reference Offset")]
        if not custom:
            return
        remove_name = custom[-1]
        rows = [BinaryWorkbenchRowDTO({key: value for key, value in row.offsets.items() if key != remove_name}, row.instruction, row.bytes_text) for row in self._context.rows]
        visible = {key: value for key, value in self._context.view_preferences.visible_columns.items() if key != remove_name}
        refs = [name for name in self._context.reference_offsets if name != remove_name]
        self._update_context({"reference_offsets": refs, "rows": rows, "view_preferences": self._context.view_preferences.__class__(visible, list(self._context.view_preferences.decoded_text_tables))})

    def _on_rows_changed(self, rows: list) -> None:
        self._update_context({"rows": rows})

    def _set_summary(self, text: str) -> None:
        self.summary.setText(text or BINARY_WORKBENCH_TEXT.SELECTION_EMPTY)

    def _visible_columns(self) -> list[str]:
        offsets = [name for name in self._context.reference_offsets if self._context.view_preferences.visible_columns.get(name, True)]
        return [*offsets, "Instruction", "Bytes"]

    def _update_context(self, updates: dict[str, object]) -> None:
        self._context = BinaryWorkbenchTabContextDTO(**{**self._context.__dict__, **updates})
        self._rebuild_offsets()
        self.grid.load_rows(self._visible_columns(), self._context.rows)
        self.contextChanged.emit(self._context)
