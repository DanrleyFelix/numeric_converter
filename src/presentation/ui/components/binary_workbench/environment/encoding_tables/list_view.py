from PySide6.QtCore import QModelIndex, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QAbstractItemView,
    QListWidget,
    QListWidgetItem,
    QStyledItemDelegate,
    QStyleOptionViewItem,
)

from src.presentation.ui.helpers.load_qss import THEME_TOKENS


CONFLICT_ROLE = int(Qt.ItemDataRole.UserRole) + 1


class EncodingTableItemDelegate(QStyledItemDelegate):
    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        super().paint(painter, option, index)
        if not index.data(CONFLICT_ROLE):
            return
        painter.save()
        painter.setPen(QPen(QColor(THEME_TOKENS["border-danger"]), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(option.rect.adjusted(0, 0, -1, -1))
        painter.restore()


class EncodingTablesList(QListWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("binary-workbench-encoding-tables")
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)
        self.setSpacing(0)
        self.setUniformItemSizes(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.setItemDelegate(EncodingTableItemDelegate(self))

    def append_table(self, name: str, selected: bool) -> QListWidgetItem:
        item = QListWidgetItem(name)
        item.setSizeHint(QSize(0, self.fontMetrics().height() * 2))
        self.addItem(item)
        item.setSelected(selected)
        return item

    def set_conflict(self, item: QListWidgetItem, conflict: bool) -> None:
        item.setData(CONFLICT_ROLE, conflict or None)
        self.viewport().update(self.visualItemRect(item))
