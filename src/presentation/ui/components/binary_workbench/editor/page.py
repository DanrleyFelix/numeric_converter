from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from src.core.binary_workbench.block_reader import CachedBinaryReader
from src.core.binary_workbench.mips_r3000a import build_rows_from_bytes
from src.core.binary_workbench.mips_r3000a import extract_labels_from_instructions
from src.modules.dtos import BinaryWorkbenchTabContextDTO
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_LAYOUT,
    BINARY_WORKBENCH_TAB_KIND,
    BINARY_WORKBENCH_TEXT,
)
from src.presentation.ui.components.binary_workbench.editor.table import BinaryWorkbenchGrid
from src.presentation.ui.components.binary_workbench.symbols import symbol_offsets


class BinaryWorkbenchEditorPage(QWidget):
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
        self.grid = BinaryWorkbenchGrid()
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
        self.grid.set_symbols(context.labels, context.variables, context.equates)
        self.grid.set_default_editor_kind(_default_editor_kind(context))
        if self._reader is not None:
            self.grid.load_rows(
                self._visible_columns(),
                [],
                context.view_preferences.group_bytes,
                _offset_from_hex(context.last_open_offset),
                self._reader.file_size,
                True,
            )
            self._load_visible_rows(
                _offset_from_hex(context.last_open_offset),
                self.grid.visible_size(),
                1,
            )
        else:
            self.grid.load_rows(self._visible_columns(), context.rows, context.view_preferences.group_bytes)
        self.summary.setText(BINARY_WORKBENCH_TEXT.SELECTION_EMPTY)

    def set_cpu_arch(self, value: str) -> None:
        self._update_context({"cpu_arch": value})

    def _on_rows_changed(self, rows: list) -> None:
        if self._reader is not None:
            self._update_overlay(rows)
            return
        self._update_context(_symbol_updates(self._context, rows))

    def _load_visible_rows(self, offset: int, size: int, direction: int) -> None:
        if self._loading_visible_rows or self._reader is None:
            return
        self._loading_visible_rows = True
        visible_offset = max(0, offset)
        self._reader.prefetch_for_offset(visible_offset, direction)
        data = self._reader.read(
            visible_offset,
            size,
            _overlay_bytes(self._context.byte_overlays),
        )
        rows = build_rows_from_bytes(
            data,
            list(self._context.reference_offsets),
            visible_offset,
            dict(self._context.reference_offset_bases),
        )
        self.grid.render_rows(rows, visible_offset)
        self._select_pending_offset()
        self._loading_visible_rows = False
        self._context = BinaryWorkbenchTabContextDTO(
            **{
                **self._context.__dict__,
                "rows": rows,
                "file_size": self._reader.file_size,
                "last_open_offset": f"0x{visible_offset:08X}",
            }
        )
        self.contextChanged.emit(self._context)

    def _update_overlay(self, rows: list) -> None:
        if self._reader is None:
            return
        overlays = dict(self._context.byte_overlays)
        for row in rows:
            offset = int(row.offsets.get("File", "0x0"), 16)
            current = bytes.fromhex(row.bytes_text.replace(" ", ""))
            original = self._reader.read(offset, len(current), {})
            key = f"0x{offset:08X}"
            if current == original:
                overlays.pop(key, None)
            else:
                overlays[key] = row.bytes_text
        self._context = BinaryWorkbenchTabContextDTO(
            **{
                **self._context.__dict__,
                "byte_overlays": overlays,
                **_symbol_updates(self._context, rows),
            }
        )
        self.contextChanged.emit(self._context)

    def _set_summary(self, text: str) -> None:
        self.summary.setText(text or BINARY_WORKBENCH_TEXT.SELECTION_EMPTY)

    def _visible_columns(self) -> list[str]:
        offsets = [
            name
            for name in self._context.reference_offsets
            if self._context.view_preferences.visible_columns.get(name, True)
        ]
        return [*offsets, BINARY_WORKBENCH_TEXT.BYTES, BINARY_WORKBENCH_TEXT.INSTRUCTION]

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

    def find_text(self, mode: str, query: str) -> bool:
        results = self.find_offsets(mode, query)
        if results:
            self.go_to_offset(results[0])
            return True
        return False

    def find_offsets(self, mode: str, query: str) -> list[int]:
        if mode == BINARY_WORKBENCH_TEXT.FIND_HEX_BYTES:
            return self._find_hex_bytes(query)
        if mode == BINARY_WORKBENCH_TEXT.FIND_ASSEMBLY:
            return self._find_instruction(query)
        return []

    def assembly_text(self) -> str:
        return self.grid.assembly_text()

    def focused_editor_kind(self) -> str | None:
        return self.grid.focused_editor_kind()

    def _update_context(self, updates: dict[str, object]) -> None:
        self._context = BinaryWorkbenchTabContextDTO(**{**self._context.__dict__, **updates})
        self.contextChanged.emit(self._context)

    def _reader_for_context(
        self,
        context: BinaryWorkbenchTabContextDTO,
    ) -> CachedBinaryReader | None:
        if context.kind != BINARY_WORKBENCH_TAB_KIND.BINARY:
            return None
        if context.read_mode == "assembly" or not context.source_path:
            return None
        path = Path(context.source_path)
        if not path.exists():
            return None
        return CachedBinaryReader(path, context.block_size, context.cache_max_blocks)

    def _find_instruction(self, query: str) -> list[int]:
        needle = query.strip().lower()
        if not needle:
            return []
        rows = self.grid.export_rows() or self._context.rows
        return [
            int(row.offsets.get("File", "0x0"), 16)
            for row in rows
            if needle in row.instruction.lower()
        ]

    def _select_pending_offset(self) -> None:
        if self._pending_selection is None:
            return
        start, end = self._pending_selection
        self.grid.select_offsets(start, end)
        self._pending_selection = None

    def _find_hex_bytes(self, query: str) -> list[int]:
        needle = _hex_query_bytes(query)
        if not needle:
            return []
        if self._reader is None:
            return _find_in_rows(self._context.rows, needle, self.go_to_offset)
        offset = 0
        carry = b""
        results: list[int] = []
        overlays = _overlay_bytes(self._context.byte_overlays)
        while offset < self._reader.file_size:
            data = self._reader.read(offset, self._context.block_size, overlays)
            haystack = carry + data
            start = 0
            while (found := haystack.find(needle, start)) >= 0:
                results.append(max(0, offset - len(carry) + found))
                start = found + 1
            carry = haystack[-max(0, len(needle) - 1) :]
            offset += max(1, self._context.block_size)
        return results


def _overlay_bytes(values: dict[str, str]) -> dict[int, bytes]:
    return {
        int(offset, 16): bytes.fromhex(bytes_text.replace(" ", ""))
        for offset, bytes_text in values.items()
    }


def _offset_from_hex(value: str) -> int:
    try:
        return int(value, 16)
    except ValueError:
        return 0


def _hex_query_bytes(value: str) -> bytes:
    try:
        return bytes.fromhex(value.replace(" ", ""))
    except ValueError:
        return b""


def _find_in_rows(rows: list, needle: bytes, go_to) -> list[int]:
    results: list[int] = []
    for row in rows:
        if needle.hex(" ").upper() in row.bytes_text:
            results.append(int(row.offsets.get("File", "0x0"), 16))
    return results


def _symbol_updates(context: BinaryWorkbenchTabContextDTO, rows: list) -> dict[str, object]:
    labels = {
        **context.labels,
        **extract_labels_from_instructions([row.instruction for row in rows]),
    }
    return {
        "rows": rows,
        "labels": labels,
        "symbol_offsets": symbol_offsets(rows, context.variables, context.equates, labels),
    }


def _default_editor_kind(context: BinaryWorkbenchTabContextDTO) -> str:
    if context.kind in {BINARY_WORKBENCH_TAB_KIND.ASSEMBLY, BINARY_WORKBENCH_TAB_KIND.SCRATCH}:
        return BINARY_WORKBENCH_TEXT.INSTRUCTION
    return BINARY_WORKBENCH_TEXT.BYTES
