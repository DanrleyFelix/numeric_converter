from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_LAYOUT,
    BINARY_WORKBENCH_TEXT,
)
from src.presentation.ui.components.binary_workbench.action_controls import (
    configure_binary_workbench_dialog_action,
    configure_binary_workbench_filter,
    configure_binary_workbench_line_edit,
)
from src.presentation.ui.components.binary_workbench.environment.symbols_dialog_widgets import (
    SymbolRemoveRowButton,
    symbol_button,
    symbol_input,
)
from src.presentation.ui.components.binary_workbench.environment.commands.dialog_helpers import (
    edit_command_instructions,
    header_cell,
)
from src.presentation.ui.components.workspace_table.constants.layout import WORKSPACE_TABLE_SIZE


class BinaryWorkbenchCommandsDialog(QDialog):
    commandLoadRequested = Signal(str)
    commandSaveRequested = Signal(str)
    commandRemoveRequested = Signal(str)
    commandInstructionsChangeRequested = Signal(str, list)

    def __init__(
        self,
        commands: dict[str, list[str]],
        default_directory: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("workspace-table-dialog")
        self.setWindowTitle(BINARY_WORKBENCH_TEXT.COMMANDS)
        self.setFixedWidth(BINARY_WORKBENCH_LAYOUT.COMMANDS_DIALOG_WIDTH)
        self.setMinimumHeight(BINARY_WORKBENCH_LAYOUT.COMMANDS_DIALOG_MIN_HEIGHT)
        self.setMaximumHeight(BINARY_WORKBENCH_LAYOUT.COMMANDS_DIALOG_MAX_HEIGHT)
        self.resize(
            BINARY_WORKBENCH_LAYOUT.COMMANDS_DIALOG_WIDTH,
            BINARY_WORKBENCH_LAYOUT.COMMANDS_DIALOG_MIN_HEIGHT,
        )
        self._commands = dict(commands)
        self._default_directory = default_directory
        self._rows: list[tuple[QWidget, QWidget, str, list[str]]] = []
        self._build_dialog()

    def set_commands(self, commands: dict[str, list[str]]) -> None:
        self._commands = dict(commands)
        self._refresh_rows()

    def set_default_directory(self, path: str) -> None:
        self._default_directory = path

    def _build_dialog(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 30, 20, 20)
        layout.setSpacing(BINARY_WORKBENCH_LAYOUT.COMMANDS_DIALOG_GAP)
        self._build_filter(layout)
        self.shell = QFrame(self)
        self.shell.setObjectName("workspace-table-shell")
        shell_layout = QVBoxLayout(self.shell)
        shell_layout.setContentsMargins(20, 20, 20, 16)
        shell_layout.setSpacing(12)
        self._build_header(shell_layout)
        self._build_body(shell_layout)
        layout.addWidget(self.shell, 1)
        self._build_footer(layout)
        self._refresh_rows()

    def _build_filter(self, parent: QVBoxLayout) -> None:
        self.filter_input = symbol_input(
            BINARY_WORKBENCH_TEXT.FILTER,
            self,
            "",
            BINARY_WORKBENCH_LAYOUT.SHARED_FILTER_WIDTH,
            search_icon=True,
        )
        configure_binary_workbench_filter(self.filter_input)
        configure_binary_workbench_line_edit(self.filter_input)
        self.filter_input.textChanged.connect(self._apply_filter)
        parent.addWidget(self.filter_input, 0, Qt.AlignLeft)

    def _build_header(self, parent: QVBoxLayout) -> None:
        header = QFrame(self.shell)
        header.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        row = QHBoxLayout(header)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        commands = header_cell(BINARY_WORKBENCH_TEXT.COMMANDS, header)
        commands.setFixedWidth(BINARY_WORKBENCH_LAYOUT.COMMANDS_LEFT_COLUMN_WIDTH)
        row.addWidget(commands, 0)
        row.addSpacing(BINARY_WORKBENCH_LAYOUT.COMMANDS_COLUMN_GAP)
        instructions = header_cell(BINARY_WORKBENCH_TEXT.COMMAND_INSTRUCTION_HEADER, header, Qt.AlignLeft)
        instructions.setFixedWidth(BINARY_WORKBENCH_LAYOUT.SHARED_ACTION_WIDTH)
        row.addWidget(instructions, 0)
        row.addStretch(1)
        parent.addWidget(header, 0)

    def _build_body(self, parent: QVBoxLayout) -> None:
        self.scroll = QScrollArea(self.shell)
        self.scroll.setObjectName("workspace-table-body-scroll")
        self.scroll.verticalScrollBar().setObjectName("workspace-table-scrollbar")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_body = QWidget(self.scroll)
        self.scroll_body.setObjectName("workspace-table-body")
        scroll_layout = QHBoxLayout(self.scroll_body)
        scroll_layout.setContentsMargins(
            0,
            10,
            BINARY_WORKBENCH_LAYOUT.ROW_DELETE_SCROLLBAR_MARGIN
            + BINARY_WORKBENCH_LAYOUT.ROW_SCROLLBAR_RESERVED_WIDTH
            + BINARY_WORKBENCH_LAYOUT.COMMANDS_ACTION_RIGHT_INSET,
            10,
        )
        scroll_layout.setSpacing(BINARY_WORKBENCH_LAYOUT.ROW_DELETE_COLUMN_SPACING)
        self.body = QFrame(self.scroll_body)
        self.body.setObjectName("workspace-table-body")
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setSpacing(BINARY_WORKBENCH_LAYOUT.COMMANDS_DIALOG_GAP)
        self.body_layout.setAlignment(Qt.AlignTop)
        self.remove_body = QFrame(self.scroll_body)
        self.remove_body.setObjectName("workspace-table-body")
        self.remove_layout = QVBoxLayout(self.remove_body)
        self.remove_layout.setContentsMargins(0, 0, 0, 0)
        self.remove_layout.setSpacing(BINARY_WORKBENCH_LAYOUT.COMMANDS_DIALOG_GAP)
        self.remove_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        scroll_layout.addWidget(self.body, 1)
        scroll_layout.addWidget(self.remove_body, 0)
        self.scroll.setWidget(self.scroll_body)
        parent.addWidget(self.scroll, 1)

    def _build_footer(self, parent: QVBoxLayout) -> None:
        footer_frame = QFrame(self)
        footer_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        footer = QHBoxLayout(footer_frame)
        footer.setContentsMargins(0, 0, 0, 0)
        footer.setSpacing(0)
        load = symbol_button(BINARY_WORKBENCH_TEXT.LOAD, "", footer_frame)
        save = symbol_button(BINARY_WORKBENCH_TEXT.SAVE, "", footer_frame)
        for button in (load, save):
            configure_binary_workbench_dialog_action(button)
        load.clicked.connect(self._request_load)
        save.clicked.connect(self._request_save)
        footer.addWidget(load, 0, Qt.AlignLeft)
        footer.addStretch(1)
        footer.addWidget(save, 0, Qt.AlignRight)
        parent.addWidget(footer_frame, 0)

    def _refresh_rows(self) -> None:
        self._rows.clear()
        _clear_layout(self.body_layout)
        _clear_layout(self.remove_layout)
        for name, instructions in sorted(self._commands.items()):
            self._append_row(name, instructions)
        self.body_layout.addStretch(1)
        self._apply_filter()

    def _append_row(self, name: str, instructions: list[str]) -> None:
        row_widget = QWidget(self.body)
        row_widget.setObjectName("workspace-row")
        row = QHBoxLayout(row_widget)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        label = QLabel(f"/{name}", row_widget)
        label.setObjectName("binary-workbench-command-name")
        label.setFixedWidth(BINARY_WORKBENCH_LAYOUT.COMMANDS_LEFT_COLUMN_WIDTH)
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        show = symbol_button(BINARY_WORKBENCH_TEXT.SHOW, "", row_widget)
        configure_binary_workbench_dialog_action(show)
        show.clicked.connect(lambda: self._edit_instructions(name, instructions))
        remove_slot = _remove_slot(self.remove_body)
        remove = SymbolRemoveRowButton(remove_slot)
        remove.setFixedSize(WORKSPACE_TABLE_SIZE.REMOVE_BUTTON_WIDTH, WORKSPACE_TABLE_SIZE.REMOVE_BUTTON_HEIGHT)
        remove.clicked.connect(lambda: self.commandRemoveRequested.emit(name))
        row.addWidget(label, 0)
        row.addSpacing(BINARY_WORKBENCH_LAYOUT.COMMANDS_COLUMN_GAP)
        row.addWidget(show, 0, Qt.AlignRight | Qt.AlignVCenter)
        row.addStretch(1)
        remove_slot.layout().addWidget(remove, 0, Qt.AlignCenter)
        self._rows.append((row_widget, remove_slot, name, instructions))
        self.body_layout.addWidget(row_widget, 0)
        self.remove_layout.addWidget(remove_slot, 0)

    def _edit_instructions(self, name: str, instructions: list[str]) -> None:
        updated = edit_command_instructions(name, instructions, self)
        if updated is not None:
            self.commandInstructionsChangeRequested.emit(name, updated)

    def _apply_filter(self) -> None:
        query = self.filter_input.text().strip().lower()
        for row, remove_slot, name, instructions in self._rows:
            haystack = f"{name} {' '.join(instructions)}".lower()
            visible = not query or query in haystack
            row.setVisible(visible)
            remove_slot.setVisible(visible)

    def _request_load(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            BINARY_WORKBENCH_TEXT.COMMANDS,
            self._default_directory,
            BINARY_WORKBENCH_TEXT.FILE_FILTER_COMMANDS,
        )
        if path:
            self.commandLoadRequested.emit(path)

    def _request_save(self) -> None:
        initial = str(Path(self._default_directory) / "commands.json")
        path, _ = QFileDialog.getSaveFileName(
            self,
            BINARY_WORKBENCH_TEXT.COMMANDS,
            initial,
            BINARY_WORKBENCH_TEXT.FILE_FILTER_COMMANDS,
        )
        if path:
            self.commandSaveRequested.emit(path)


def _remove_slot(parent: QWidget) -> QWidget:
    slot = QWidget(parent)
    slot.setFixedHeight(BINARY_WORKBENCH_LAYOUT.SHARED_CONTROL_HEIGHT)
    layout = QVBoxLayout(slot)
    layout.setContentsMargins(0, 0, 0, 0)
    return slot


def _clear_layout(layout: QVBoxLayout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        if item.widget() is not None:
            item.widget().deleteLater()
