from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPlainTextEdit, QScrollBar, QSizePolicy, QVBoxLayout, QWidget

from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_LAYOUT, BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.editor.highlighters import BytesHighlighter, InstructionHighlighter
from src.presentation.ui.components.binary_workbench.editor.syntax_tokens import ROW_BYTES
from src.presentation.ui.components.binary_workbench.editor.workbench_editor import WorkbenchEditor


class GridLayoutMixin:
    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(BINARY_WORKBENCH_LAYOUT.EDITOR_SPACING)
        self.canvas = QFrame(self)
        self.canvas.setObjectName("binary-workbench-editor-canvas")
        self.canvas_layout = QHBoxLayout(self.canvas)
        self.canvas_layout.setContentsMargins(0, 0, 0, 0)
        self.canvas_layout.setSpacing(BINARY_WORKBENCH_LAYOUT.EDITOR_SPACING)
        self.offsets_host = QFrame(self.canvas)
        self.offsets_layout = QHBoxLayout(self.offsets_host)
        self.offsets_layout.setContentsMargins(0, 0, 0, 0)
        self.offsets_layout.setSpacing(BINARY_WORKBENCH_LAYOUT.EDITOR_SPACING)
        self.scrollbar = QScrollBar(Qt.Vertical, self)
        self.scrollbar.setObjectName("binary-workbench-editor-scrollbar")
        self.scrollbar.valueChanged.connect(self._on_scrollbar_changed)
        self.raw_shell, self.raw_instructions = self._panel(BINARY_WORKBENCH_TEXT.RAW_INSTRUCTIONS, "binary-workbench-raw-instructions-panel", True, BINARY_WORKBENCH_LAYOUT.EDITOR_RAW_INSTRUCTION_WIDTH)
        self.bytes_shell, self.bytes = self._panel(BINARY_WORKBENCH_TEXT.BYTES, "binary-workbench-bytes-panel", False, BINARY_WORKBENCH_LAYOUT.EDITOR_BYTES_WIDTH)
        self.instructions_shell, self.instructions = self._panel(BINARY_WORKBENCH_TEXT.INSTRUCTION, "binary-workbench-instructions-panel", False)
        self._bytes_highlighter = BytesHighlighter(self.bytes.document())
        self._raw_instruction_highlighter = InstructionHighlighter(self.raw_instructions.document())
        self._instruction_highlighter = InstructionHighlighter(self.instructions.document())
        self._connect_editors()
        self.canvas_layout.addWidget(self.offsets_host, 0)
        self.canvas_layout.addWidget(self.raw_shell, 0)
        self.canvas_layout.addWidget(self.bytes_shell, 0)
        self.canvas_layout.addWidget(self.instructions_shell, 1)
        layout.addWidget(self.canvas, 1)
        layout.addWidget(self.scrollbar, 0)

    def _connect_editors(self) -> None:
        self.bytes.textChanged.connect(self._on_bytes_changed)
        self.instructions.textChanged.connect(self._on_instructions_changed)
        self.instructions.set_immediate_symbol_menu_enabled(True)
        self.instructions.immediateSymbolRequested.connect(self.immediateSymbolRequested)
        self.instructions.addCommandRequested.connect(self._add_custom_command_from_selection)
        self.instructions.labelActivated.connect(self.labelActivated)
        self.instructions.labelOpenTabRequested.connect(self.labelOpenTabRequested)
        self.raw_instructions.focused.connect(lambda: self._set_last_editor(BINARY_WORKBENCH_TEXT.RAW_INSTRUCTIONS))
        self.bytes.focused.connect(lambda: self._set_last_editor(BINARY_WORKBENCH_TEXT.BYTES))
        self.instructions.focused.connect(lambda: self._set_last_editor(BINARY_WORKBENCH_TEXT.INSTRUCTION))
        self.raw_instructions.cursorPositionChanged.connect(self._emit_selection_summary)
        self.bytes.cursorPositionChanged.connect(self._emit_selection_summary)
        self.instructions.cursorPositionChanged.connect(self._emit_selection_summary)
        for editor in (self.raw_instructions, self.bytes, self.instructions):
            editor.copyRequested.connect(self._copy_editor_selection)
            editor.selectionStarted.connect(self._clear_virtual_selection)
            editor.selectionAutoScrollAboutToStep.connect(self._capture_virtual_selection_anchor)
            editor.selectionAutoScrolled.connect(self._restore_virtual_selection)
            editor.verticalScrollBar().valueChanged.connect(self._on_editor_scrollbar_changed)
            editor.returnKeyPressed.connect(self._handle_editor_return_key)
            editor.protectedEditKeyPressed.connect(self._handle_editor_protected_edit_key)

    def _panel(self, label_text: str, object_name: str, read_only: bool, width: int | None = None) -> tuple[QFrame, WorkbenchEditor]:
        shell = QFrame(self)
        shell.setObjectName("binary-workbench-column-shell")
        shell.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        layout = QVBoxLayout(shell)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(BINARY_WORKBENCH_LAYOUT.PANEL_LABEL_SPACING)
        label = QLabel(label_text, shell)
        label.setObjectName("binary-workbench-column-label")
        editor = self._editor(object_name, read_only, width)
        layout.addWidget(label, 0)
        layout.addWidget(editor, 1)
        return shell, editor

    def _editor(self, object_name: str, read_only: bool, width: int | None = None) -> WorkbenchEditor:
        editor = WorkbenchEditor(self)
        editor.setObjectName(object_name)
        editor.setReadOnly(read_only)
        editor.setLineWrapMode(QPlainTextEdit.NoWrap)
        editor.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        editor.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        editor.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        editor.document().setDocumentMargin(BINARY_WORKBENCH_LAYOUT.EDITOR_DOCUMENT_MARGIN)
        editor.set_shared_scrollbar(self.scrollbar)
        editor.selectAllRequested.connect(
            editor.selectAll if read_only and object_name != "binary-workbench-raw-instructions-panel" else self.selectAllRequested.emit
        )
        if width is not None:
            editor.setFixedWidth(width)
        return editor

    def _configure_scrollbar(self) -> None:
        was_updating = self._updating
        self._updating = True
        try:
            maximum = max(0, self._total_size - self.visible_size())
            target = min(max(0, self._aligned_scroll_offset(self._visible_start_offset)), maximum)
            self._visible_start_offset = target
            self.scrollbar.setRange(0, maximum)
            self.scrollbar.setSingleStep(ROW_BYTES)
            self.scrollbar.setPageStep(max(ROW_BYTES, self.visible_size()))
            self.scrollbar.setValue(target)
            if not self._virtual:
                self._scroll_static_document(target)
        finally:
            self._updating = was_updating

    def _on_editor_scrollbar_changed(self, value: int) -> None:
        if self._virtual or self._updating or self._syncing_editor_scrollbars:
            return
        self.scrollbar.setValue(value * ROW_BYTES)
