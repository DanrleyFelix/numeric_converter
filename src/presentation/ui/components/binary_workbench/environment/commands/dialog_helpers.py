from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_LAYOUT,
    BINARY_WORKBENCH_TEXT,
)
from src.presentation.ui.components.binary_workbench.action_controls import (
    configure_binary_workbench_dialog_action,
)
from src.presentation.ui.components.binary_workbench.environment.symbols_dialog_widgets import (
    symbol_button,
)


def edit_command_instructions(name: str, instructions: list[str], parent: QWidget) -> list[str] | None:
    dialog = QDialog(parent)
    dialog.setObjectName("workspace-table-dialog")
    dialog.setWindowTitle(f"/{name}")
    dialog.setFixedSize(
        BINARY_WORKBENCH_LAYOUT.COMMANDS_SHOW_DIALOG_WIDTH,
        BINARY_WORKBENCH_LAYOUT.COMMANDS_SHOW_DIALOG_HEIGHT,
    )
    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(20, 30, 20, 20)
    shell = QFrame(dialog)
    shell.setObjectName("workspace-table-shell")
    shell_layout = QVBoxLayout(shell)
    shell_layout.setContentsMargins(20, 20, 20, 16)
    shell_layout.setSpacing(20)
    editor = QPlainTextEdit(shell)
    editor.setObjectName("binary-workbench-command-instructions")
    margin = BINARY_WORKBENCH_LAYOUT.SHARED_CONTROL_CONTENT_MARGIN
    editor.setViewportMargins(margin, margin, margin, margin)
    editor.setPlainText("\n".join(instructions))
    shell_layout.addWidget(editor, 1)
    footer = QHBoxLayout()
    footer.setContentsMargins(0, 0, 0, 0)
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


def header_cell(text: str, parent: QWidget, alignment: Qt.AlignmentFlag = Qt.AlignLeft) -> QFrame:
    frame = QFrame(parent)
    layout = QHBoxLayout(frame)
    layout.setContentsMargins(0, 0, 0, 0)
    label = QLabel(text, frame)
    label.setObjectName("workspace-table-header-cell")
    layout.addWidget(label, 1, alignment)
    return frame
