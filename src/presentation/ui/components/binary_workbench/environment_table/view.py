from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QMouseEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QLineEdit,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTableView,
)

from src.presentation.ui.components.binary_workbench.action_controls import (
    configure_binary_workbench_line_edit,
)
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_LAYOUT
from src.presentation.ui.helpers.load_qss import THEME_TOKENS

EditorValidator = Callable[[QLineEdit], None]


class EnvironmentTableView(QTableView):
    """Track row hover while retaining cell-specific editing."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._hovered_row = -1
        self.setMouseTracking(True)

    @property
    def hovered_row(self) -> int:
        """Return the proxy row currently under the pointer."""

        return self._hovered_row

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Update the complete hovered row before normal view handling."""

        self._set_hovered_row(self.indexAt(event.position().toPoint()).row())
        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:
        """Clear row hover when the pointer exits the viewport."""

        self._set_hovered_row(-1)
        super().leaveEvent(event)

    def _set_hovered_row(self, row: int) -> None:
        if row != self._hovered_row:
            self._hovered_row = row
            self.viewport().update()


class EnvironmentCellDelegate(QStyledItemDelegate):
    """Create full-cell editors and paint row-wide hover feedback."""

    def __init__(self, validators: dict[int, EditorValidator] | None = None, parent=None) -> None:
        super().__init__(parent)
        self._validators = validators or {}

    def createEditor(self, parent, option, index):
        """Create a centered temporary editor for an editable cell."""

        editor = QLineEdit(parent)
        editor.setObjectName("binary-workbench-environment-cell-editor")
        editor.setAlignment(Qt.AlignmentFlag.AlignCenter)
        configure_binary_workbench_line_edit(editor)
        validator = self._validators.get(index.column())
        if validator is not None:
            validator(editor)
        return editor

    def updateEditorGeometry(self, editor, option, index) -> None:
        """Extend the editor border over the complete table cell."""

        editor.setGeometry(option.rect)

    def paint(self, painter, option, index) -> None:
        """Paint hover across the row while keeping selection stronger."""

        paint_option = QStyleOptionViewItem(option)
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        if getattr(self.parent(), "hovered_row", -1) == index.row() and not selected:
            painter.fillRect(option.rect, QColor(THEME_TOKENS["bg-workspace-row-hover"]))
            paint_option.state &= ~QStyle.StateFlag.State_MouseOver
        super().paint(painter, paint_option, index)


def configure_environment_table(
    table: EnvironmentTableView,
    object_name: str,
    *,
    extended_selection: bool = False,
) -> None:
    """Apply the shared Symbols table behavior to an environment view."""

    table.setObjectName(object_name)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    selection_mode = (
        QAbstractItemView.SelectionMode.ExtendedSelection
        if extended_selection
        else QAbstractItemView.SelectionMode.SingleSelection
    )
    table.setSelectionMode(selection_mode)
    table.setEditTriggers(
        QAbstractItemView.EditTrigger.DoubleClicked
        | QAbstractItemView.EditTrigger.SelectedClicked
        | QAbstractItemView.EditTrigger.EditKeyPressed
    )
    table.setShowGrid(True)
    table.setSortingEnabled(True)
    table.sortByColumn(-1, Qt.SortOrder.AscendingOrder)
    table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
    table.setViewportMargins(0, 0, BINARY_WORKBENCH_LAYOUT.SYMBOL_OFFSETS_SCROLLBAR_MARGIN, 0)
    table.verticalHeader().hide()
    table.verticalHeader().setDefaultSectionSize(BINARY_WORKBENCH_LAYOUT.SHARED_CONTROL_HEIGHT)
    header = table.horizontalHeader()
    header.setObjectName("binary-workbench-environment-header")
    header.setFixedHeight(BINARY_WORKBENCH_LAYOUT.SHARED_CONTROL_HEIGHT)
    header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    header.setHighlightSections(False)
    # The object name is assigned after the application stylesheet is loaded.
    # Re-polish only this child so Qt resolves the dark environment-header QSS
    # without restyling the dialog or any native file dialog.
    header.style().unpolish(header)
    header.style().polish(header)
    scrollbar = table.verticalScrollBar()
    scrollbar.setObjectName("binary-workbench-environment-scrollbar")
