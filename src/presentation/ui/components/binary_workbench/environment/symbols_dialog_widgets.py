from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_LAYOUT,
    BINARY_WORKBENCH_DIALOG_LAYOUT as ENVIRONMENT_LAYOUT,
)
from src.presentation.ui.components.binary_workbench.action_controls import (
    configure_binary_workbench_line_edit,
)
from src.presentation.ui.components.binary_workbench.button_icon_painting import (
    CenteredIconTextButton,
    configure_binary_workbench_icon_text,
)
from src.presentation.ui.components.binary_workbench.input_validators import (
    set_python_identifier_validator,
)
from src.presentation.ui.design.icons import Icons


def symbol_input(
    placeholder: str,
    parent: QWidget,
    value: str = "",
    width: int = BINARY_WORKBENCH_LAYOUT.SYMBOL_FIELD_WIDTH,
    *,
    expanding: bool = False,
    search_icon: bool = False,
) -> QLineEdit:
    editor = QLineEdit(value, parent)
    editor.setObjectName("binary-workbench-dialog-input")
    editor.setPlaceholderText(placeholder)
    if search_icon:
        editor.addAction(Icons.search_muted(), QLineEdit.ActionPosition.TrailingPosition)
    size_symbol_input(editor, width, expanding=expanding)
    editor.setFixedHeight(BINARY_WORKBENCH_LAYOUT.SHARED_CONTROL_HEIGHT)
    editor.setFixedWidth(width)
    return editor


def size_symbol_input(widget: QWidget, width: int, *, expanding: bool = False) -> None:
    if expanding:
        widget.setMinimumWidth(width)
        widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    else:
        widget.setFixedWidth(width)
    widget.setFixedHeight(BINARY_WORKBENCH_LAYOUT.SHARED_CONTROL_HEIGHT)


def size_symbol_action(button: QPushButton, width: int, *, expanding: bool = False) -> None:
    if expanding:
        button.setMinimumWidth(0)
        button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    else:
        button.setFixedWidth(width)
    button.setFixedHeight(BINARY_WORKBENCH_LAYOUT.SHARED_CONTROL_HEIGHT)


def symbol_label(text: str, object_name: str, parent: QWidget) -> QLabel:
    label = QLabel(text, parent)
    label.setObjectName(object_name)
    return label


def symbol_field(text: str, widget: QWidget, *, expanding: bool = False) -> QWidget:
    field = QWidget(widget.parentWidget())
    if expanding:
        field.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    else:
        field.setFixedWidth(widget.width())
    layout = QVBoxLayout(field)
    layout.setContentsMargins(*ENVIRONMENT_LAYOUT.EMPTY_MARGINS)
    layout.setSpacing(ENVIRONMENT_LAYOUT.FIELD_LABEL_SPACING)
    layout.addWidget(symbol_label(text, "preferences-section-title", field))
    layout.addWidget(widget, 0, Qt.AlignLeft)
    return field


def symbol_button(text: str, object_name: str, parent: QWidget) -> QPushButton:
    button = CenteredIconTextButton(text, parent)
    button.setObjectName(object_name)
    button.setFocusPolicy(Qt.NoFocus)
    button.setCursor(Qt.PointingHandCursor)
    button.setFixedHeight(BINARY_WORKBENCH_LAYOUT.SHARED_CONTROL_HEIGHT)
    button.setFixedWidth(BINARY_WORKBENCH_LAYOUT.SHARED_ACTION_WIDTH)
    configure_binary_workbench_icon_text(button)
    return button
