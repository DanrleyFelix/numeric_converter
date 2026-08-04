from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QLineEdit,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
)

from src.presentation.ui.components.binary_workbench.action_controls import (
    configure_binary_workbench_line_edit,
)
from src.presentation.ui.components.binary_workbench.input_validators import (
    set_python_identifier_validator,
)
from src.presentation.ui.helpers.load_qss import THEME_TOKENS


class SymbolCellDelegate(QStyledItemDelegate):
    """Style temporary editors and paint row-wide hover feedback."""

    def __init__(self, name_column: int, parent=None) -> None:
        super().__init__(parent)
        self._name_column = name_column

    def createEditor(self, parent, option, index):
        """Create a transient line editor with the established validation."""

        editor = QLineEdit(parent)
        editor.setObjectName("binary-workbench-symbol-cell-editor")
        editor.setAlignment(Qt.AlignmentFlag.AlignCenter)
        configure_binary_workbench_line_edit(editor)
        if index.column() == self._name_column:
            set_python_identifier_validator(editor)
        return editor

    def updateEditorGeometry(self, editor, option, index) -> None:
        """Extend the editor border over the complete table cell."""

        editor.setGeometry(option.rect)

    def paint(self, painter, option, index) -> None:
        """Paint hover across both cells while preserving row selection."""

        view = self.parent()
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        paint_option = QStyleOptionViewItem(option)
        if getattr(view, "hovered_row", -1) == index.row() and not selected:
            painter.fillRect(
                paint_option.rect,
                QColor(THEME_TOKENS["bg-workspace-row-hover"]),
            )
            paint_option.state &= ~QStyle.StateFlag.State_MouseOver
        super().paint(painter, paint_option, index)
