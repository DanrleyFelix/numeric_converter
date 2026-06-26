from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QStyle, QStyledItemDelegate, QStyleOptionViewItem

from src.presentation.ui.components.preferences_dialog.constants import (
    PREFERENCES_DIALOG_SIZE,
)


class PreferencesComboItemDelegate(QStyledItemDelegate):
    def sizeHint(self, option: QStyleOptionViewItem, index) -> QSize:
        size = super().sizeHint(option, index)
        return QSize(size.width(), PREFERENCES_DIALOG_SIZE.GROUP_SIZE_ITEM_HEIGHT)

    def paint(self, painter, option: QStyleOptionViewItem, index) -> None:
        painter.save()
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        painter.fillRect(
            option.rect,
            option.palette.highlight() if selected else option.palette.base(),
        )
        painter.setPen(
            option.palette.highlightedText().color()
            if selected
            else option.palette.text().color()
        )
        padding = PREFERENCES_DIALOG_SIZE.LIST_TEXT_PADDING
        text_rect = option.rect.adjusted(padding, 0, -padding, 0)
        painter.drawText(
            text_rect,
            Qt.AlignLeft | Qt.AlignVCenter,
            str(index.data() or ""),
        )
        painter.restore()
