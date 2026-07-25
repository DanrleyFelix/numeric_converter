"""Memory header painting with HxD-style colored byte offsets."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QHeaderView, QStyle, QStyleOptionHeader

from src.presentation.ui.helpers.load_qss import THEME_TOKENS


class DebuggerMemoryHeader(QHeaderView):
    """Keep the address label white and byte-offset labels golden."""

    def __init__(self, parent=None) -> None:
        """Create the horizontal header owned by the memory table."""

        super().__init__(Qt.Horizontal, parent)

    def paintSection(self, painter: QPainter, rect, logical_index: int) -> None:
        """Paint themed section chrome before drawing its explicit text color."""

        if not rect.isValid():
            return
        option = QStyleOptionHeader()
        self.initStyleOptionForIndex(option, logical_index)
        text = option.text
        option.text = ""
        self.style().drawControl(QStyle.CE_Header, option, painter, self)
        painter.save()
        painter.setFont(self.font())
        painter.setPen(self.section_text_color(logical_index))
        painter.drawText(rect, option.textAlignment, text)
        painter.restore()

    @staticmethod
    def section_text_color(logical_index: int) -> QColor:
        """Return white for Address and golden yellow for byte offsets."""

        token = "text-main" if logical_index == 0 else "text-warning"
        return QColor(THEME_TOKENS[token])
