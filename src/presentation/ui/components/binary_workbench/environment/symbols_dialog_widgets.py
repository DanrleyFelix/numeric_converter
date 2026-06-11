from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_LAYOUT
from src.presentation.ui.components.workspace_table.constants.layout import WORKSPACE_TABLE_SIZE
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
    return editor


def symbol_kind_combo(parent: QWidget, value: str, *, expanding: bool = False) -> QComboBox:
    combo = QComboBox(parent)
    combo.setObjectName("binary-workbench-dialog-input")
    combo.addItems(["Variable", "Equate"])
    combo.setCurrentText(value)
    combo.setCursor(Qt.PointingHandCursor)
    size_symbol_input(combo, BINARY_WORKBENCH_LAYOUT.SYMBOL_KIND_WIDTH, expanding=expanding)
    return combo


def size_symbol_input(widget: QWidget, width: int, *, expanding: bool = False) -> None:
    if expanding:
        widget.setMinimumWidth(width)
        widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    else:
        widget.setFixedWidth(width)
    widget.setFixedHeight(BINARY_WORKBENCH_LAYOUT.SYMBOL_INPUT_HEIGHT)


def size_symbol_action(button: QPushButton, width: int, *, expanding: bool = False) -> None:
    if expanding:
        button.setMinimumWidth(0)
        button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    else:
        button.setFixedWidth(width)
    button.setFixedHeight(BINARY_WORKBENCH_LAYOUT.SYMBOL_INPUT_HEIGHT)


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
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(4)
    layout.addWidget(symbol_label(text, "preferences-section-title", field))
    layout.addWidget(widget, 0, Qt.AlignLeft)
    return field


def symbol_button(text: str, object_name: str, parent: QWidget) -> QPushButton:
    button = QPushButton(text, parent)
    button.setObjectName(object_name)
    button.setFocusPolicy(Qt.NoFocus)
    button.setCursor(Qt.PointingHandCursor)
    return button


class SymbolRemoveRowButton(QPushButton):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("workspace-row-remove")
        self.setFocusPolicy(Qt.NoFocus)
        self.setCursor(Qt.PointingHandCursor)
        self.setIcon(Icons.remove())
        self.setIconSize(QSize(WORKSPACE_TABLE_SIZE.REMOVE_ICON_SIZE, WORKSPACE_TABLE_SIZE.REMOVE_ICON_SIZE))

    def enterEvent(self, event) -> None:
        self.setIcon(Icons.remove_hover())
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self.setIcon(Icons.remove())
        super().leaveEvent(event)
