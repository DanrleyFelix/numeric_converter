from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent, QKeySequence
from PySide6.QtWidgets import QApplication, QAbstractItemView, QTableWidget, QTableWidgetItem

from src.modules.contracts import CPUArchCodec
from src.modules.dtos import BinaryWorkbenchRowDTO
from src.core.binary_workbench.mips_r3000a import PsxMipsR3000ACodec


class BinaryWorkbenchGrid(QTableWidget):
    rowsChanged = Signal(list)
    selectionSummaryChanged = Signal(str)

    def __init__(self) -> None:
        super().__init__(0, 0)
        self.setObjectName("binary-workbench-grid")
        self.setShowGrid(False)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed)
        self.horizontalHeader().sectionClicked.connect(self.selectColumn)
        self.itemSelectionChanged.connect(self._emit_selection_summary)
        self.itemChanged.connect(self._on_item_changed)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setStretchLastSection(True)
        self.verticalScrollBar().setObjectName("workspace-table-scrollbar")
        self._codec: CPUArchCodec = PsxMipsR3000ACodec()
        self._columns: list[str] = []
        self._rows: list[BinaryWorkbenchRowDTO] = []
        self._updating = False

    def load_rows(self, columns: list[str], rows: list[BinaryWorkbenchRowDTO]) -> None:
        self._updating = True
        self._columns = columns
        self._rows = list(rows)
        self.setColumnCount(len(columns))
        self.setHorizontalHeaderLabels(columns)
        self.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            for column_index, name in enumerate(columns):
                value = row.instruction if name == "Instruction" else row.bytes_text if name == "Bytes" else row.offsets.get(name, "")
                item = QTableWidgetItem(value)
                flags = Qt.ItemIsSelectable | Qt.ItemIsEnabled
                if name in {"Instruction", "Bytes"}:
                    flags |= Qt.ItemIsEditable
                item.setFlags(flags)
                self.setItem(row_index, column_index, item)
        self._updating = False
        self._emit_selection_summary()

    def export_rows(self) -> list[BinaryWorkbenchRowDTO]:
        return list(self._rows)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.matches(QKeySequence.Copy):
            self._copy_selection()
            return
        super().keyPressEvent(event)

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if self._updating:
            return
        row = self._rows[item.row()]
        if self._columns[item.column()] == "Instruction":
            encoded = self._codec.assemble(item.text(), _address(item.row()))
            if encoded is None:
                return self._reload()
            self._rows[item.row()] = BinaryWorkbenchRowDTO(row.offsets, self._codec.disassemble(encoded, _address(item.row())), self._codec.bytes_text(encoded))
        elif self._columns[item.column()] == "Bytes":
            data = _parse_bytes(item.text())
            if data is None:
                return self._reload()
            self._rows[item.row()] = BinaryWorkbenchRowDTO(row.offsets, self._codec.disassemble(data, _address(item.row())), self._codec.bytes_text(data))
        self.rowsChanged.emit(self.export_rows())
        self._reload()

    def _reload(self) -> None:
        self.load_rows(self._columns, self._rows)

    def _copy_selection(self) -> None:
        indexes = sorted(self.selectedIndexes(), key=lambda idx: (idx.row(), idx.column()))
        if not indexes:
            return
        lines: list[str] = []
        for row in sorted({index.row() for index in indexes}):
            values = [index.data() for index in indexes if index.row() == row]
            lines.append("\t".join(values))
        QApplication.clipboard().setText("\n".join(lines))

    def _emit_selection_summary(self) -> None:
        indexes = self.selectedIndexes()
        if not indexes or not self._rows:
            return self.selectionSummaryChanged.emit("Selected: none | Length: 0 bytes")
        rows = sorted({index.row() for index in indexes})
        start = self._rows[rows[0]].offsets.get("File", "0x00000000")
        end_offset = int(self._rows[rows[-1]].offsets.get("File", "0x00000000"), 16) + 3
        self.selectionSummaryChanged.emit(f"Selected: {start}..0x{end_offset:08X} | Length: {len(rows) * 4} bytes")


def _address(row_index: int) -> int:
    return 0x80010000 + (row_index * 4)


def _parse_bytes(text: str) -> bytes | None:
    raw = text.replace(" ", "").strip()
    if len(raw) != 8:
        return None
    try:
        return bytes.fromhex(raw)
    except ValueError:
        return None
