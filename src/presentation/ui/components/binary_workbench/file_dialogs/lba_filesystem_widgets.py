from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_LAYOUT
from src.presentation.ui.components.workspace_table.constants.layout import WORKSPACE_TABLE_SIZE
from src.presentation.ui.design.icons import Icons


def lba_input(
    placeholder: str,
    parent: QWidget,
    value: str = "",
    width: int = BINARY_WORKBENCH_LAYOUT.LBA_FIELD_WIDTH,
) -> QLineEdit:
    editor = QLineEdit(value, parent)
    editor.setObjectName("binary-workbench-dialog-input")
    editor.setPlaceholderText(placeholder)
    editor.setFixedSize(width, BINARY_WORKBENCH_LAYOUT.SYMBOL_INPUT_HEIGHT)
    return editor


def size_lba_input(widget: QWidget) -> None:
    widget.setFixedSize(
        BINARY_WORKBENCH_LAYOUT.LBA_FIELD_WIDTH,
        BINARY_WORKBENCH_LAYOUT.SYMBOL_INPUT_HEIGHT,
    )


def lba_label(text: str, object_name: str, parent: QWidget) -> QLabel:
    label = QLabel(text, parent)
    label.setObjectName(object_name)
    return label


def lba_field(text: str, widget: QWidget) -> QWidget:
    field = QWidget(widget.parentWidget())
    field.setFixedWidth(widget.width())
    layout = QVBoxLayout(field)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(4)
    layout.addWidget(lba_label(text, "preferences-section-title", field))
    layout.addWidget(widget, 0, Qt.AlignLeft)
    return field


def lba_button(text: str, object_name: str, parent: QWidget) -> QPushButton:
    button = QPushButton(text, parent)
    button.setObjectName(object_name)
    button.setFocusPolicy(Qt.NoFocus)
    button.setCursor(Qt.PointingHandCursor)
    return button


class LbaRemoveRowButton(QPushButton):
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
