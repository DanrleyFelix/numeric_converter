from __future__ import annotations

import re

from PySide6.QtCore import QPoint, QStringListModel, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QCursor, QKeyEvent, QSyntaxHighlighter, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QCompleter, QHBoxLayout, QLabel, QPlainTextEdit, QScrollBar, QSizePolicy, QToolTip, QVBoxLayout, QWidget

from src.core.binary_workbench.mips_r3000a import PsxMipsR3000ACodec
from src.modules.dtos import BinaryWorkbenchRowDTO
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_LAYOUT, BINARY_WORKBENCH_TEXT

_BYTE_TOKEN = re.compile(r"[0-9A-Fa-f]{2}")
_HEX_TOKEN = re.compile(r"0x[0-9A-Fa-f]+")
_REGISTER_TOKEN = re.compile(r"\$?[a-zA-Z_][A-Za-z0-9_]*")
_COMPLETION_TOKEN = re.compile(r"[@_]?[A-Za-z_][A-Za-z0-9_]*")
_VARIABLE_TOKEN = re.compile(r"(?<![A-Za-z0-9_])_[A-Za-z_][A-Za-z0-9_]*")
_EQUATE_TOKEN = re.compile(r"(?<![A-Za-z0-9_])@[A-Za-z_][A-Za-z0-9_]*")
_BRANCHES = {"beq", "bne", "bgtz", "blez", "bltz", "bgez", "beqz", "bnez"}
_JUMPS = {"j", "jal", "jr", "jalr"}
_KNOWN_MNEMONICS = {
    *_BRANCHES,
    *_JUMPS,
    "add", "addiu", "addu", "subu", "ori", "lui", "lw", "sw", "lh", "lhu", "sh",
    "lb", "lbu", "sb", "sltiu", "nop", "word", ".word", ".byte", ".half",
}
_ROW_BYTES = 4


class _WorkbenchEditor(QPlainTextEdit):
    focused = Signal()
    selectAllRequested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._shared_scrollbar: QScrollBar | None = None
        self._completion_model = QStringListModel(self)
        self._completion_items: dict[str, list[str]] = {"label": [], "variable": [], "equate": []}
        self._symbol_tooltips: dict[str, str] = {}
        self._completer = QCompleter(self._completion_model, self)
        self._completer.setWidget(self)
        self._completer.activated.connect(self._insert_completion)
        self._selection_scroll_delta = 0
        self._selection_timer = QTimer(self)
        self._selection_timer.timeout.connect(self._step_selection_scroll)

    def set_shared_scrollbar(self, scrollbar: QScrollBar) -> None:
        self._shared_scrollbar = scrollbar

    def mouseMoveEvent(self, event) -> None:
        super().mouseMoveEvent(event)
        if event.buttons() & Qt.LeftButton:
            self._update_selection_scroll(event.position().toPoint())
            return
        self._show_symbol_tooltip(event)
        self._stop_selection_scroll()

    def mouseReleaseEvent(self, event) -> None:
        self._stop_selection_scroll()
        super().mouseReleaseEvent(event)

    def focusInEvent(self, event) -> None:
        self.focused.emit()
        super().focusInEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key_A and event.modifiers() & Qt.ControlModifier:
            self.selectAllRequested.emit()
            event.accept()
            return
        if event.key() == Qt.Key_Tab:
            self.insertPlainText(" " * BINARY_WORKBENCH_LAYOUT.EDITOR_TAB_SPACES)
            event.accept()
            return
        if self._shared_scrollbar is None:
            super().keyPressEvent(event)
            return
        key = event.key()
        block = self.textCursor().blockNumber()
        last_block = max(0, self.document().blockCount() - 1)
        if key == Qt.Key_Down and block >= last_block:
            self._shared_scrollbar.setValue(self._shared_scrollbar.value() + _ROW_BYTES)
            QTimer.singleShot(0, lambda: self._move_cursor_to_edge(False))
            event.accept()
            return
        if key == Qt.Key_Up and block <= 0:
            self._shared_scrollbar.setValue(self._shared_scrollbar.value() - _ROW_BYTES)
            QTimer.singleShot(0, lambda: self._move_cursor_to_edge(True))
            event.accept()
            return
        super().keyPressEvent(event)
        self._refresh_completions()

    def set_symbol_helpers(
        self,
        labels: dict[str, str],
        variables: dict[str, str],
        equates: dict[str, str],
    ) -> None:
        self._completion_items = {
            "label": sorted(labels),
            "variable": sorted(f"_{name.lstrip('_')}" for name in variables),
            "equate": sorted(f"@{name.lstrip('@')}" for name in equates),
        }
        self._symbol_tooltips = {
            **_tooltip_values(labels),
            **_tooltip_values({f"_{name.lstrip('_')}": value for name, value in variables.items()}),
            **_tooltip_values({f"@{name.lstrip('@')}": value for name, value in equates.items()}),
        }

    def _move_cursor_to_edge(self, top: bool) -> None:
        cursor = self.textCursor()
        block = self.document().firstBlock() if top else self.document().lastBlock()
        cursor.setPosition(block.position())
        self.setTextCursor(cursor)

    def wheelEvent(self, event) -> None:
        if self._shared_scrollbar is None:
            super().wheelEvent(event)
            return
        delta = event.pixelDelta().y()
        if delta == 0:
            delta = (event.angleDelta().y() // BINARY_WORKBENCH_LAYOUT.WHEEL_SCROLL_DIVISOR) * _ROW_BYTES
        self._shared_scrollbar.setValue(self._shared_scrollbar.value() - delta)
        event.accept()

    def leaveEvent(self, event) -> None:
        if not (self.textCursor().hasSelection() and self.hasFocus()):
            self._stop_selection_scroll()
        super().leaveEvent(event)

    def _update_selection_scroll(self, position: QPoint) -> None:
        threshold = 18
        if position.y() < threshold:
            self._selection_scroll_delta = -_ROW_BYTES
        elif position.y() > self.viewport().height() - threshold:
            self._selection_scroll_delta = _ROW_BYTES
        else:
            self._stop_selection_scroll()
            return
        if not self._selection_timer.isActive():
            self._selection_timer.start(20)

    def _stop_selection_scroll(self) -> None:
        self._selection_scroll_delta = 0
        self._selection_timer.stop()

    def _step_selection_scroll(self) -> None:
        if self._shared_scrollbar is None or self._selection_scroll_delta == 0:
            self._stop_selection_scroll()
            return
        self._shared_scrollbar.setValue(self._shared_scrollbar.value() + self._selection_scroll_delta)
        position = self.viewport().mapFromGlobal(QCursor.pos())
        cursor = self.cursorForPosition(QPoint(max(position.x(), 0), max(position.y(), 0)))
        selection = self.textCursor()
        anchor = selection.anchor()
        selection.setPosition(anchor)
        selection.setPosition(cursor.position(), QTextCursor.KeepAnchor)
        self.setTextCursor(selection)

    def _refresh_completions(self) -> None:
        prefix = self._current_completion_prefix()
        candidates = self._candidates_for_prefix(prefix)
        if not prefix or not candidates:
            self._completer.popup().hide()
            return
        self._completion_model.setStringList(candidates)
        self._completer.setCompletionPrefix(prefix)
        self._completer.complete(self.cursorRect())

    def _current_completion_prefix(self) -> str:
        cursor = self.textCursor()
        block = cursor.block().text()
        column = cursor.positionInBlock()
        for match in _COMPLETION_TOKEN.finditer(block):
            if match.start() <= column <= match.end():
                return block[match.start() : column]
        return ""

    def _candidates_for_prefix(self, prefix: str) -> list[str]:
        if prefix.startswith("_"):
            return [item for item in self._completion_items["variable"] if item.startswith(prefix)]
        if prefix.startswith("@"):
            return [item for item in self._completion_items["equate"] if item.startswith(prefix)]
        return [item for item in self._completion_items["label"] if item.startswith(prefix)]

    def _insert_completion(self, completion: str) -> None:
        prefix = self._current_completion_prefix()
        cursor = self.textCursor()
        for _ in prefix:
            cursor.deletePreviousChar()
        cursor.insertText(completion)
        self.setTextCursor(cursor)

    def _show_symbol_tooltip(self, event) -> None:
        text = self._symbol_tooltips.get(self._token_at_position(event.position().toPoint()))
        if text:
            QToolTip.showText(event.globalPosition().toPoint(), text, self)
            return
        QToolTip.hideText()

    def _token_at_position(self, position: QPoint) -> str:
        cursor = self.cursorForPosition(position)
        block = cursor.block().text()
        column = cursor.positionInBlock()
        for match in _COMPLETION_TOKEN.finditer(block):
            if match.start() <= column <= match.end():
                return match.group()
        return ""


class _BytesHighlighter(QSyntaxHighlighter):
    def highlightBlock(self, text: str) -> None:
        even = _format("#EAEAF5")
        odd = _format("#8FA6FF")
        for index, match in enumerate(_BYTE_TOKEN.finditer(text)):
            self.setFormat(match.start(), match.end() - match.start(), even if index % 2 == 0 else odd)


class _InstructionHighlighter(QSyntaxHighlighter):
    def __init__(self, parent) -> None:
        super().__init__(parent)
        self._labels: dict[str, str] = {}
        self._variables: dict[str, str] = {}
        self._equates: dict[str, str] = {}

    def set_symbols(
        self,
        labels: dict[str, str],
        variables: dict[str, str],
        equates: dict[str, str],
    ) -> None:
        self._labels = dict(labels)
        self._variables = {f"_{name.lstrip('_')}": value for name, value in variables.items()}
        self._equates = {f"@{name.lstrip('@')}": value for name, value in equates.items()}
        self.rehighlight()

    def highlightBlock(self, text: str) -> None:
        comment_start = text.find(";")
        raw_code = text if comment_start < 0 else text[:comment_start]
        code_start, code = _code_without_label(raw_code)
        mnemonic = re.search(r"\S+", code)
        if _invalid_instruction(code):
            self.setFormat(0, len(text), _format("#FF8B96"))
            return
        if mnemonic:
            self.setFormat(code_start + mnemonic.start(), mnemonic.end() - mnemonic.start(), _format(_mnemonic_color(mnemonic.group())))
        for match in _REGISTER_TOKEN.finditer(code):
            if mnemonic and mnemonic.start() <= match.start() < mnemonic.end():
                continue
            self.setFormat(code_start + match.start(), match.end() - match.start(), _format(_register_color(match.group())))
        for match in _HEX_TOKEN.finditer(code):
            self.setFormat(code_start + match.start(), match.end() - match.start(), _format("#7FD6A4"))
        self._highlight_symbols(text, code, code_start)
        if comment_start >= 0:
            self.setFormat(comment_start, len(text) - comment_start, _format("#7F879B"))

    def _highlight_symbols(self, original: str, code: str, code_start: int) -> None:
        for match in _VARIABLE_TOKEN.finditer(code):
            if match.group() in self._variables:
                self.setFormat(code_start + match.start(), match.end() - match.start(), _format("#C084FC"))
        for match in _EQUATE_TOKEN.finditer(code):
            if match.group() in self._equates:
                self.setFormat(code_start + match.start(), match.end() - match.start(), _format("#FFB86C"))
        for name in self._labels:
            for match in re.finditer(rf"\b{re.escape(name)}\b", original):
                self.setFormat(match.start(), match.end() - match.start(), _format("#FFD166"))


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
        self._offset_editors: dict[str, QPlainTextEdit] = {}
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
        self._sync_offset_columns([name for name in columns if name not in {BINARY_WORKBENCH_TEXT.BYTES, BINARY_WORKBENCH_TEXT.INSTRUCTION}])
        self._group_bytes = group_bytes if group_bytes in {1, 2, 4} else 1
        self._virtual = virtual
        self._total_size = total_size if virtual else len(rows) * _ROW_BYTES
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
        return self._visible_row_count() * _ROW_BYTES

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
        end = min(end_offset, self._visible_start_offset + (len(self._rows) * _ROW_BYTES) - 1)
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
        start_row = max(0, (start_offset - self._visible_start_offset) // _ROW_BYTES)
        end_row = max(0, (end_offset - self._visible_start_offset) // _ROW_BYTES)
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
        self.bytes_shell, self.bytes = self._panel(BINARY_WORKBENCH_TEXT.BYTES, "binary-workbench-bytes-panel", False, BINARY_WORKBENCH_LAYOUT.EDITOR_BYTES_WIDTH)
        self.instructions_shell, self.instructions = self._panel(BINARY_WORKBENCH_TEXT.INSTRUCTION, "binary-workbench-instructions-panel", False)
        _BytesHighlighter(self.bytes.document())
        self._instruction_highlighter = _InstructionHighlighter(self.instructions.document())
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
        self._set_editor_text(self.bytes, [_group_bytes_text(row.bytes_text, self._group_bytes) for row in self._rows])
        self._set_editor_text(self.instructions, [row.instruction for row in self._rows])
        for name, editor in self._offset_editors.items():
            self._set_editor_text(editor, [row.offsets.get(name, "") for row in self._rows])
        self.selectionSummaryChanged.emit(BINARY_WORKBENCH_TEXT.SELECTION_EMPTY)

    def _render_static_window(self) -> None:
        count = self._visible_row_count()
        start = self._aligned_scroll_offset(self.scrollbar.value()) // _ROW_BYTES
        self._rows = self._all_rows[start : start + count]
        self._visible_start_offset = start * _ROW_BYTES
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
            address = _address_from_row(row)
            assembly = _assembly_for_encoding(
                line,
                address,
                self._labels,
                self._variables,
                self._equates,
            )
            data = _parse_bytes(line) if editing_bytes else self._codec.assemble(assembly, address)
            if data is None:
                return
            updated[index] = BinaryWorkbenchRowDTO(
                offsets=row.offsets,
                instruction=self._codec.disassemble(data, address) if editing_bytes else line.rstrip(),
                bytes_text=self._codec.bytes_text(data),
            )
        self._rows = updated
        if not self._virtual:
            start = self._aligned_scroll_offset(self.scrollbar.value()) // _ROW_BYTES
            self._all_rows[start : start + len(updated)] = updated
            self.rowsChanged.emit(self.export_rows())
        else:
            self.rowsChanged.emit(self._rows)
        target = self.instructions if editing_bytes else self.bytes
        values = [row.instruction for row in self._rows] if editing_bytes else [_group_bytes_text(row.bytes_text, self._group_bytes) for row in self._rows]
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
        first = self._visible_start_offset + (start_block * _ROW_BYTES)
        last = self._visible_start_offset + ((end_block + 1) * _ROW_BYTES) - 1
        self.selectionSummaryChanged.emit(
            f"Selected: 0x{first:08X}..0x{last:08X} | Length: {last - first + 1} bytes"
        )

    def _panel(self, label_text: str, object_name: str, read_only: bool, width: int | None = None) -> tuple[QWidget, QPlainTextEdit]:
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

    def _editor(self, object_name: str, read_only: bool, width: int | None = None) -> QPlainTextEdit:
        editor = _WorkbenchEditor(self)
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
            shell, editor = self._panel(name, "binary-workbench-offsets-panel", True, BINARY_WORKBENCH_LAYOUT.EDITOR_OFFSET_WIDTH)
            self._offset_editors[name] = editor
            self.offsets_layout.addWidget(shell)

    def _configure_scrollbar(self) -> None:
        self._updating = True
        self.scrollbar.setRange(0, max(0, self._total_size - self.visible_size()))
        self.scrollbar.setSingleStep(_ROW_BYTES)
        self.scrollbar.setPageStep(max(_ROW_BYTES, self.visible_size()))
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
            self.visibleWindowRequested.emit(self._aligned_scroll_offset(self.scrollbar.value()), self.visible_size(), 1)
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
            for byte_index, match in enumerate(_BYTE_TOKEN.finditer(block.text())):
                token_start = block.position() + match.start()
                token_end = block.position() + match.end()
                if token_end <= start or token_start >= end:
                    continue
                offsets.append(self._visible_start_offset + (block_number * _ROW_BYTES) + byte_index)
        return offsets

    def _byte_selection_positions(self, start_offset: int, end_offset: int) -> tuple[int, int] | None:
        start_row = (start_offset - self._visible_start_offset) // _ROW_BYTES
        end_row = (end_offset - self._visible_start_offset) // _ROW_BYTES
        start_byte = (start_offset - self._visible_start_offset) % _ROW_BYTES
        end_byte = (end_offset - self._visible_start_offset) % _ROW_BYTES
        document = self.bytes.document()
        start_block = document.findBlockByNumber(start_row)
        end_block = document.findBlockByNumber(end_row)
        if not start_block.isValid() or not end_block.isValid():
            return None
        start_tokens = list(_BYTE_TOKEN.finditer(start_block.text()))
        end_tokens = list(_BYTE_TOKEN.finditer(end_block.text()))
        if start_byte >= len(start_tokens) or end_byte >= len(end_tokens):
            return None
        start = start_block.position() + start_tokens[start_byte].start()
        end = end_block.position() + end_tokens[end_byte].end()
        return start, end

    def _aligned_scroll_offset(self, value: int) -> int:
        return max(0, value - (value % _ROW_BYTES))


def _address_from_row(row: BinaryWorkbenchRowDTO) -> int:
    return 0x80010000 + int(row.offsets.get("File", "0x0"), 16)


def _assembly_for_encoding(
    text: str,
    address: int,
    labels: dict[str, str],
    variables: dict[str, str],
    equates: dict[str, str],
) -> str:
    code = _strip_label(text.split(";", 1)[0]).strip()
    for name, value in variables.items():
        code = code.replace(f"_{name.lstrip('_')}", value)
    for name, value in equates.items():
        code = code.replace(f"@{name.lstrip('@')}", value)
    for name, value in labels.items():
        code = re.sub(
            rf"\b{re.escape(name)}\b",
            f"0x{0x80010000 + _safe_int(value, address):X}",
            code,
        )
    return code


def _safe_int(value: str, fallback: int = 0) -> int:
    try:
        return int(value, 0)
    except ValueError:
        return fallback


def _tooltip_values(values: dict[str, str]) -> dict[str, str]:
    tooltips: dict[str, str] = {}
    for name, value in values.items():
        number = _safe_int(value)
        tooltips[name] = f"{number} | 0x{number:X}"
    return tooltips


def _format(color: str) -> QTextCharFormat:
    style = QTextCharFormat()
    style.setForeground(QColor(color))
    return style


def _mnemonic_color(token: str) -> str:
    mnemonic = token.strip().lower()
    return "#F08080" if mnemonic in _BRANCHES or mnemonic in _JUMPS else "#A0DC45"


def _register_color(token: str) -> str:
    register = token.lstrip("$").lower()
    if register.startswith(("a", "v")):
        return "#D4AF37"
    if register.startswith(("t", "s")) and register != "sp":
        return "#41C1EC"
    return "#00CFFF"


def _strip_label(text: str) -> str:
    _, code = _code_without_label(text)
    return code


def _code_without_label(text: str) -> tuple[int, str]:
    if ":" not in text:
        return 0, text
    left, right = text.split(":", 1)
    if left.strip() and " " not in left.strip():
        stripped = right.lstrip()
        return len(left) + 1 + (len(right) - len(stripped)), stripped
    return 0, text


def _invalid_instruction(text: str) -> bool:
    code = text.strip()
    if not code:
        return False
    mnemonic = code.split()[0].lower()
    return mnemonic not in _KNOWN_MNEMONICS


def _parse_bytes(text: str) -> bytes | None:
    raw = text.replace(" ", "").strip()
    if len(raw) != 8:
        return None
    try:
        return bytes.fromhex(raw)
    except ValueError:
        return None


def _group_bytes_text(text: str, group_size: int) -> str:
    raw = text.replace(" ", "")
    width = group_size * 2
    return " ".join(raw[index : index + width] for index in range(0, len(raw), width))
