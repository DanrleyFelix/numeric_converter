from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPlainTextEdit, QScrollBar, QSizePolicy, QVBoxLayout, QWidget

from src.core.binary_workbench.mips_r3000a import PsxMipsR3000ACodec
from src.modules.dtos import BinaryWorkbenchRowDTO
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_LAYOUT, BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.editor.highlighters import BytesHighlighter, InstructionHighlighter
from src.presentation.ui.components.binary_workbench.editor.syntax_tokens import (
    BYTE_TOKEN,
    ROW_BYTES,
    address_from_row,
    assembly_for_encoding,
    group_bytes_text,
    parse_bytes,
)
from src.presentation.ui.components.binary_workbench.editor.workbench_editor import WorkbenchEditor


class BinaryWorkbenchGrid(QWidget):
    rowsChanged = Signal(list)
    selectionSummaryChanged = Signal(str)
    visibleWindowRequested = Signal(int, int, int)
    selectAllRequested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("binary-workbench-editor-shell")
        self._codec = PsxMipsR3000ACodec()
        self._columns: list[str] = []
        self._rows: list[BinaryWorkbenchRowDTO] = []
        self._all_rows: list[BinaryWorkbenchRowDTO] = []
        self._offset_editors: dict[str, WorkbenchEditor] = {}
        self._updating = False
        self._virtual = False
        self._total_size = 0
        self._group_bytes = 1
        self._labels: dict[str, str] = {}
        self._variables: dict[str, str] = {}
        self._equates: dict[str, str] = {}
        self._last_editor_kind: str | None = None
        self._visible_start_offset = 0
        self._last_visible_offset = 0
        self._build_ui()

    def load_rows(
        self,
        columns: list[str],
        rows: list[BinaryWorkbenchRowDTO],
        group_bytes: int = 1,
        start_offset: int = 0,
        total_size: int = 0,
        virtual: bool = False,
    ) -> None:
        self._sync_offset_columns(
            [
                name
                for name in columns
                if name not in {BINARY_WORKBENCH_TEXT.BYTES, BINARY_WORKBENCH_TEXT.INSTRUCTION}
            ]
        )
        self._group_bytes = group_bytes if group_bytes in {1, 2, 4} else 1
        self._virtual = virtual
        self._total_size = total_size if virtual else len(rows) * ROW_BYTES
        self._all_rows = [] if virtual else list(rows)
        self._visible_start_offset = start_offset
        self._last_visible_offset = start_offset
        self._configure_scrollbar()
        self.render_rows(rows, start_offset) if virtual else self._render_static_window()

    def render_rows(self, rows: list[BinaryWorkbenchRowDTO], start_offset: int) -> None:
        self._rows = list(rows)
        self._visible_start_offset = start_offset
        self._render()

    def set_symbols(
        self,
        labels: dict[str, str],
        variables: dict[str, str],
        equates: dict[str, str],
    ) -> None:
        self._labels = dict(labels)
        self._variables = dict(variables)
        self._equates = dict(equates)
        self._instruction_highlighter.set_symbols(labels, variables, equates)
        self.instructions.set_symbol_helpers(labels, variables, equates)

    def visible_size(self) -> int:
        return self._visible_row_count() * ROW_BYTES

    def export_rows(self) -> list[BinaryWorkbenchRowDTO]:
        return list(self._all_rows if not self._virtual else self._rows)

    def set_visible_offset(self, offset: int) -> None:
        target = min(max(0, offset), self.scrollbar.maximum())
        if self.scrollbar.value() == target:
            self._on_scrollbar_changed(target)
            return
        self.scrollbar.setValue(target)

    def select_offsets(self, start_offset: int, end_offset: int) -> None:
        if end_offset < self._visible_start_offset:
            return
        start = max(start_offset, self._visible_start_offset)
        end = min(end_offset, self._visible_start_offset + (len(self._rows) * ROW_BYTES) - 1)
        positions = self._byte_selection_positions(start, end)
        if positions is None:
            return
        cursor = self.bytes.textCursor()
        cursor.setPosition(positions[0])
        cursor.setPosition(positions[1], QTextCursor.KeepAnchor)
        self.bytes.setTextCursor(cursor)
        self.bytes.setFocus()
        self._emit_selection_summary()

    def select_instruction_offsets(self, start_offset: int, end_offset: int) -> None:
        if end_offset < self._visible_start_offset:
            return
        start_row = max(0, (start_offset - self._visible_start_offset) // ROW_BYTES)
        end_row = max(0, (end_offset - self._visible_start_offset) // ROW_BYTES)
        document = self.instructions.document()
        start_block = document.findBlockByNumber(start_row)
        end_block = document.findBlockByNumber(end_row)
        if not start_block.isValid() or not end_block.isValid():
            return
        cursor = self.instructions.textCursor()
        cursor.setPosition(start_block.position())
        cursor.setPosition(end_block.position() + len(end_block.text()), QTextCursor.KeepAnchor)
        self.instructions.setTextCursor(cursor)
        self.instructions.setFocus()
        self._emit_selection_summary()

    def select_all_content(self) -> None:
        if self._virtual:
            self._select_all_focused_editor()
            return
        self._rows = list(self._all_rows)
        self._visible_start_offset = 0
        self._render()
        self._select_all_focused_editor()

    def assembly_text(self) -> str:
        return self.instructions.toPlainText()

    def focused_editor_kind(self) -> str | None:
        if self.bytes.hasFocus():
            return BINARY_WORKBENCH_TEXT.BYTES
        if self.instructions.hasFocus():
            return BINARY_WORKBENCH_TEXT.INSTRUCTION
        return self._last_editor_kind

    def _set_last_editor(self, kind: str) -> None:
        self._last_editor_kind = kind

    def set_default_editor_kind(self, kind: str) -> None:
        if self._last_editor_kind is None:
            self._last_editor_kind = kind

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(BINARY_WORKBENCH_LAYOUT.EDITOR_SPACING)
        self.canvas = QWidget(self)
        self.canvas.setObjectName("binary-workbench-editor-canvas")
        self.canvas_layout = QHBoxLayout(self.canvas)
        self.canvas_layout.setContentsMargins(0, 0, 0, 0)
        self.canvas_layout.setSpacing(BINARY_WORKBENCH_LAYOUT.EDITOR_SPACING)
        self.canvas_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.offsets_host = QWidget(self.canvas)
        self.offsets_layout = QHBoxLayout(self.offsets_host)
        self.offsets_layout.setContentsMargins(0, 0, 0, 0)
        self.offsets_layout.setSpacing(BINARY_WORKBENCH_LAYOUT.EDITOR_SPACING)
        self.scrollbar = QScrollBar(Qt.Vertical, self)
        self.scrollbar.setObjectName("binary-workbench-editor-scrollbar")
        self.scrollbar.valueChanged.connect(self._on_scrollbar_changed)
        self.bytes_shell, self.bytes = self._panel(
            BINARY_WORKBENCH_TEXT.BYTES,
            "binary-workbench-bytes-panel",
            False,
            BINARY_WORKBENCH_LAYOUT.EDITOR_BYTES_WIDTH,
        )
        self.instructions_shell, self.instructions = self._panel(
            BINARY_WORKBENCH_TEXT.INSTRUCTION,
            "binary-workbench-instructions-panel",
            False,
        )
        BytesHighlighter(self.bytes.document())
        self._instruction_highlighter = InstructionHighlighter(self.instructions.document())
        self.bytes.textChanged.connect(self._on_bytes_changed)
        self.instructions.textChanged.connect(self._on_instructions_changed)
        self.bytes.focused.connect(lambda: self._set_last_editor(BINARY_WORKBENCH_TEXT.BYTES))
        self.instructions.focused.connect(lambda: self._set_last_editor(BINARY_WORKBENCH_TEXT.INSTRUCTION))
        self.bytes.cursorPositionChanged.connect(self._emit_selection_summary)
        self.instructions.cursorPositionChanged.connect(self._emit_selection_summary)
        self.canvas_layout.addWidget(self.offsets_host, 0)
        self.canvas_layout.addWidget(self.bytes_shell, 0)
        self.canvas_layout.addWidget(self.instructions_shell, 1)
        layout.addWidget(self.canvas, 1)
        layout.addWidget(self.scrollbar, 0)

    def _render(self) -> None:
        self._resize_editors()
        self._set_editor_text(self.bytes, [group_bytes_text(row.bytes_text, self._group_bytes) for row in self._rows])
        self._set_editor_text(self.instructions, [row.instruction for row in self._rows])
        for name, editor in self._offset_editors.items():
            self._set_editor_text(editor, [row.offsets.get(name, "") for row in self._rows])
        self.selectionSummaryChanged.emit(BINARY_WORKBENCH_TEXT.SELECTION_EMPTY)

    def _render_static_window(self) -> None:
        count = self._visible_row_count()
        start = self._aligned_scroll_offset(self.scrollbar.value()) // ROW_BYTES
        self._rows = self._all_rows[start : start + count]
        self._visible_start_offset = start * ROW_BYTES
        self._render()

    def _on_scrollbar_changed(self, value: int) -> None:
        if self._updating:
            return
        if not self._virtual:
            self._render_static_window()
            return
        offset = self._aligned_scroll_offset(value)
        direction = 1 if offset >= self._last_visible_offset else -1
        self._last_visible_offset = offset
        self.visibleWindowRequested.emit(offset, self.visible_size(), direction)

    def _on_bytes_changed(self) -> None:
        self._sync_rows(self.bytes.toPlainText().splitlines(), True)

    def _on_instructions_changed(self) -> None:
        self._sync_rows(self.instructions.toPlainText().splitlines(), False)

    def _sync_rows(self, lines: list[str], editing_bytes: bool) -> None:
        if self._updating:
            return
        updated = list(self._rows)
        for index, line in enumerate(lines[: len(updated)]):
            row = updated[index]
            address = address_from_row(row)
            assembly = assembly_for_encoding(
                line,
                address,
                self._labels,
                self._variables,
                self._equates,
            )
            data = parse_bytes(line) if editing_bytes else self._codec.assemble(assembly, address)
            if data is None:
                return
            updated[index] = BinaryWorkbenchRowDTO(
                offsets=row.offsets,
                instruction=self._codec.disassemble(data, address) if editing_bytes else line.rstrip(),
                bytes_text=self._codec.bytes_text(data),
            )
        self._rows = updated
        if not self._virtual:
            start = self._aligned_scroll_offset(self.scrollbar.value()) // ROW_BYTES
            self._all_rows[start : start + len(updated)] = updated
            self.rowsChanged.emit(self.export_rows())
        else:
            self.rowsChanged.emit(self._rows)
        target = self.instructions if editing_bytes else self.bytes
        values = (
            [row.instruction for row in self._rows]
            if editing_bytes
            else [group_bytes_text(row.bytes_text, self._group_bytes) for row in self._rows]
        )
        self._set_editor_text(target, values)
        self._emit_selection_summary()

    def _emit_selection_summary(self) -> None:
        if self.bytes.textCursor().hasSelection():
            editor = self.bytes
        elif self.instructions.textCursor().hasSelection():
            editor = self.instructions
        else:
            editor = self.bytes if self.bytes.hasFocus() else self.instructions
        cursor = editor.textCursor()
        if not cursor.hasSelection():
            self.selectionSummaryChanged.emit(BINARY_WORKBENCH_TEXT.SELECTION_EMPTY)
            return
        if editor is self.bytes:
            selected = self._selected_byte_offsets(cursor)
            if not selected:
                self.selectionSummaryChanged.emit(BINARY_WORKBENCH_TEXT.SELECTION_EMPTY)
                return
            first, last = min(selected), max(selected)
            self.selectionSummaryChanged.emit(
                f"Selected: 0x{first:08X}..0x{last:08X} | Length: {len(selected)} bytes"
            )
            return
        start_block = editor.document().findBlock(cursor.selectionStart()).blockNumber()
        end_position = max(cursor.selectionEnd() - 1, cursor.selectionStart())
        end_block = editor.document().findBlock(end_position).blockNumber()
        first = self._visible_start_offset + (start_block * ROW_BYTES)
        last = self._visible_start_offset + ((end_block + 1) * ROW_BYTES) - 1
        self.selectionSummaryChanged.emit(
            f"Selected: 0x{first:08X}..0x{last:08X} | Length: {last - first + 1} bytes"
        )

    def _panel(
        self,
        label_text: str,
        object_name: str,
        read_only: bool,
        width: int | None = None,
    ) -> tuple[QWidget, WorkbenchEditor]:
        shell = QWidget(self)
        shell.setObjectName("binary-workbench-column-shell")
        layout = QVBoxLayout(shell)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(BINARY_WORKBENCH_LAYOUT.PANEL_LABEL_SPACING)
        layout.setAlignment(Qt.AlignTop)
        label = QLabel(label_text, shell)
        label.setObjectName("binary-workbench-column-label")
        editor = self._editor(object_name, read_only, width)
        layout.addWidget(label, 0)
        layout.addWidget(editor, 0)
        return shell, editor

    def _editor(
        self,
        object_name: str,
        read_only: bool,
        width: int | None = None,
    ) -> WorkbenchEditor:
        editor = WorkbenchEditor(self)
        editor.setObjectName(object_name)
        editor.setReadOnly(read_only)
        editor.setLineWrapMode(QPlainTextEdit.NoWrap)
        editor.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        editor.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        editor.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        editor.document().setDocumentMargin(BINARY_WORKBENCH_LAYOUT.EDITOR_DOCUMENT_MARGIN)
        editor.set_shared_scrollbar(self.scrollbar)
        editor.selectAllRequested.connect(self.selectAllRequested.emit)
        if width is not None:
            editor.setFixedWidth(width)
        return editor

    def _select_all_focused_editor(self) -> None:
        editor = self.bytes if self.focused_editor_kind() == BINARY_WORKBENCH_TEXT.BYTES else self.instructions
        editor.selectAll()
        editor.setFocus()
        self._emit_selection_summary()

    def _set_editor_text(self, editor: QPlainTextEdit, lines: list[str]) -> None:
        self._updating = True
        editor.setPlainText("\n".join(lines))
        self._updating = False

    def _sync_offset_columns(self, names: list[str]) -> None:
        if names == self._columns:
            return
        self._columns = names
        self._offset_editors.clear()
        while self.offsets_layout.count():
            item = self.offsets_layout.takeAt(0)
            if widget := item.widget():
                widget.setParent(None)
                widget.deleteLater()
        for name in names:
            shell, editor = self._panel(
                name,
                "binary-workbench-offsets-panel",
                True,
                BINARY_WORKBENCH_LAYOUT.EDITOR_OFFSET_WIDTH,
            )
            self._offset_editors[name] = editor
            self.offsets_layout.addWidget(shell)

    def _configure_scrollbar(self) -> None:
        self._updating = True
        self.scrollbar.setRange(0, max(0, self._total_size - self.visible_size()))
        self.scrollbar.setSingleStep(ROW_BYTES)
        self.scrollbar.setPageStep(max(ROW_BYTES, self.visible_size()))
        self.scrollbar.setValue(max(0, self._visible_start_offset))
        self._updating = False

    def _resize_editors(self) -> None:
        editors = [*self._offset_editors.values(), self.bytes, self.instructions]
        height = self._editor_viewport_height()
        for editor in editors:
            editor.setFixedHeight(height)

    def _visible_row_count(self) -> int:
        line_height = max(1, self.instructions.fontMetrics().lineSpacing())
        available = self._usable_editor_height(self.instructions)
        rows = max(
            1,
            (available // line_height) - BINARY_WORKBENCH_LAYOUT.EDITOR_VISIBLE_ROW_SAFETY,
        )
        return min(BINARY_WORKBENCH_LAYOUT.EDITOR_MAX_VISIBLE_ROWS, rows)

    def _editor_viewport_height(self) -> int:
        return max(
            BINARY_WORKBENCH_LAYOUT.EDITOR_MIN_HEIGHT,
            self.height() - BINARY_WORKBENCH_LAYOUT.EDITOR_PANEL_HEADER_HEIGHT,
        )

    def _usable_editor_height(self, editor: QPlainTextEdit) -> int:
        viewport_height = editor.viewport().height()
        if viewport_height <= 0:
            frame = editor.frameWidth() * 2
            viewport_height = max(0, self._editor_viewport_height() - frame)
        return max(
            1,
            viewport_height - (BINARY_WORKBENCH_LAYOUT.EDITOR_DOCUMENT_MARGIN * 2),
        )

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._resize_editors()
        self._configure_scrollbar()
        if self._virtual:
            self.visibleWindowRequested.emit(
                self._aligned_scroll_offset(self.scrollbar.value()),
                self.visible_size(),
                1,
            )
        else:
            self._render_static_window()

    def _selected_byte_offsets(self, cursor: QTextCursor) -> list[int]:
        start = cursor.selectionStart()
        end = cursor.selectionEnd()
        offsets: list[int] = []
        document = self.bytes.document()
        for block_number in range(document.blockCount()):
            block = document.findBlockByNumber(block_number)
            if not block.isValid():
                continue
            for byte_index, match in enumerate(BYTE_TOKEN.finditer(block.text())):
                token_start = block.position() + match.start()
                token_end = block.position() + match.end()
                if token_end <= start or token_start >= end:
                    continue
                offsets.append(
                    self._visible_start_offset + (block_number * ROW_BYTES) + byte_index
                )
        return offsets

    def _byte_selection_positions(self, start_offset: int, end_offset: int) -> tuple[int, int] | None:
        start_row = (start_offset - self._visible_start_offset) // ROW_BYTES
        end_row = (end_offset - self._visible_start_offset) // ROW_BYTES
        start_byte = (start_offset - self._visible_start_offset) % ROW_BYTES
        end_byte = (end_offset - self._visible_start_offset) % ROW_BYTES
        document = self.bytes.document()
        start_block = document.findBlockByNumber(start_row)
        end_block = document.findBlockByNumber(end_row)
        if not start_block.isValid() or not end_block.isValid():
            return None
        start_tokens = list(BYTE_TOKEN.finditer(start_block.text()))
        end_tokens = list(BYTE_TOKEN.finditer(end_block.text()))
        if start_byte >= len(start_tokens) or end_byte >= len(end_tokens):
            return None
        start = start_block.position() + start_tokens[start_byte].start()
        end = end_block.position() + end_tokens[end_byte].end()
        return start, end

    def _aligned_scroll_offset(self, value: int) -> int:
        return max(0, value - (value % ROW_BYTES))
