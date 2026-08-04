from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_LAYOUT,
    BINARY_WORKBENCH_TEXT,
)
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_DIALOG_LAYOUT as ENVIRONMENT_LAYOUT,
)
from src.presentation.ui.components.binary_workbench.action_controls import (
    configure_binary_workbench_dialog_action,
)
from src.presentation.ui.components.binary_workbench.dialog_context_menu import (
    configure_dialog_text_context_menu,
)
from src.presentation.ui.components.binary_workbench.environment.symbols_dialog_widgets import (
    symbol_button,
)


def command_load_path(parent: QWidget, directory: str) -> str:
    """Request a command library through the unchanged native file dialog."""

    path, _ = QFileDialog.getOpenFileName(
        parent, BINARY_WORKBENCH_TEXT.COMMANDS, directory, BINARY_WORKBENCH_TEXT.FILE_FILTER_COMMANDS
    )
    return path


def command_save_path(parent: QWidget, directory: str) -> str:
    """Request a command destination through the unchanged native file dialog."""

    initial = str(Path(directory) / "commands.json")
    path, _ = QFileDialog.getSaveFileName(
        parent, BINARY_WORKBENCH_TEXT.COMMANDS, initial, BINARY_WORKBENCH_TEXT.FILE_FILTER_COMMANDS
    )
    return path


class CommandsFileActionsMixin:
    """Preserve the native command-library load and save flows."""

    def _request_load(self) -> None:
        path = command_load_path(self, self._default_directory)
        if path:
            self.commandLoadRequested.emit(path)

    def _request_save(self) -> None:
        path = command_save_path(self, self._default_directory)
        if path:
            self.commandSaveRequested.emit(path)


def edit_command_instructions(name: str, instructions: list[str], parent: QWidget) -> list[str] | None:
    dialog = QDialog(parent)
    dialog.setObjectName("workspace-table-dialog")
    dialog.setWindowTitle(f"/{name}")
    dialog.setFixedSize(
        BINARY_WORKBENCH_LAYOUT.COMMANDS_SHOW_DIALOG_WIDTH,
        BINARY_WORKBENCH_LAYOUT.COMMANDS_SHOW_DIALOG_HEIGHT,
    )
    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(*ENVIRONMENT_LAYOUT.DIALOG_MARGINS)
    shell = QFrame(dialog)
    shell.setObjectName("workspace-table-shell")
    shell_layout = QVBoxLayout(shell)
    shell_layout.setContentsMargins(*ENVIRONMENT_LAYOUT.PANEL_MARGINS)
    shell_layout.setSpacing(ENVIRONMENT_LAYOUT.SECTION_SPACING)
    editor = QPlainTextEdit(shell)
    configure_dialog_text_context_menu(editor)
    editor.setObjectName("binary-workbench-command-instructions")
    margin = BINARY_WORKBENCH_LAYOUT.SHARED_CONTROL_CONTENT_MARGIN
    editor.setViewportMargins(margin, margin, margin, margin)
    editor.setPlainText("\n".join(instructions))
    shell_layout.addWidget(editor, 1)
    footer = QHBoxLayout()
    footer.setContentsMargins(*ENVIRONMENT_LAYOUT.EMPTY_MARGINS)
    footer.addStretch(1)
    ok = symbol_button(BINARY_WORKBENCH_TEXT.OK, "", shell)
    configure_binary_workbench_dialog_action(ok)
    ok.clicked.connect(dialog.accept)
    footer.addWidget(ok, 0)
    footer.addStretch(1)
    shell_layout.addLayout(footer)
    layout.addWidget(shell, 1)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None
    return [line.rstrip() for line in editor.toPlainText().splitlines()]
