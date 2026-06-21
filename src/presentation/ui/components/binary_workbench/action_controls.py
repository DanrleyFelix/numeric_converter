from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QLineEdit, QPushButton, QWidget

from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_LAYOUT

BINARY_WORKBENCH_ACTION_OBJECT_NAME = "binary-workbench-action"
BINARY_WORKBENCH_INPUT_OBJECT_NAME = "binary-workbench-input"


def configure_binary_workbench_action(button: QPushButton) -> None:
    button.setObjectName(BINARY_WORKBENCH_ACTION_OBJECT_NAME)
    configure_binary_workbench_dialog_button(
        button,
        BINARY_WORKBENCH_LAYOUT.SHARED_ACTION_WIDTH,
    )


def configure_binary_workbench_dialog_button(
    button: QPushButton,
    width: int | None = None,
) -> None:
    configure_binary_workbench_control_height(button)
    if width is not None:
        button.setFixedWidth(width)
    button.setCursor(Qt.PointingHandCursor)
    button.setFocusPolicy(Qt.NoFocus)


def configure_binary_workbench_filter(editor: QLineEdit) -> None:
    configure_binary_workbench_input(editor, BINARY_WORKBENCH_LAYOUT.SHARED_FILTER_WIDTH)


def configure_binary_workbench_control_height(widget: QWidget) -> None:
    widget.setFixedHeight(BINARY_WORKBENCH_LAYOUT.SHARED_CONTROL_HEIGHT)
    margin = BINARY_WORKBENCH_LAYOUT.SHARED_CONTROL_CONTENT_MARGIN
    widget.setContentsMargins(margin, margin, margin, margin)


def configure_binary_workbench_line_edit(
    editor: QLineEdit,
    width: int | None = None,
) -> None:
    editor.setFixedHeight(BINARY_WORKBENCH_LAYOUT.SHARED_CONTROL_HEIGHT)
    if width is not None:
        editor.setFixedWidth(width)
    margin = BINARY_WORKBENCH_LAYOUT.SHARED_CONTROL_CONTENT_MARGIN
    editor.setTextMargins(margin, margin, margin, margin)


def configure_binary_workbench_combo(
    combo: QComboBox,
    width: int | None = None,
) -> None:
    configure_binary_workbench_control_height(combo)
    if width is not None:
        combo.setFixedWidth(width)
    combo.setCursor(Qt.PointingHandCursor)


def configure_binary_workbench_input(editor: QLineEdit, width: int) -> None:
    editor.setObjectName(BINARY_WORKBENCH_INPUT_OBJECT_NAME)
    configure_binary_workbench_line_edit(editor, width)
