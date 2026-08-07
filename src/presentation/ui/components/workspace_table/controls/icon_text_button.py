from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QIcon, QPalette
from PySide6.QtWidgets import QPushButton, QStyle, QStyleOptionButton, QStylePainter


class CenteredIconTextButton(QPushButton):
    """Paint an icon and label as one centered group with an explicit gutter."""

    def __init__(self, text: str, spacing: int, parent=None) -> None:
        """Create a button whose icon-to-text spacing follows the dialog style."""

        super().__init__(text, parent)
        self._icon_text_spacing = spacing

    def paintEvent(self, event) -> None:
        """Paint the QSS shell before centering the icon and text together."""

        if self.icon().isNull() or not self.text():
            super().paintEvent(event)
            return
        option = QStyleOptionButton()
        self.initStyleOption(option)
        shell = QStyleOptionButton(option)
        shell.icon = QIcon()
        shell.text = ""
        painter = QStylePainter(self)
        painter.drawControl(QStyle.ControlElement.CE_PushButton, shell)
        self._draw_content(option, painter)

    def _draw_content(self, option: QStyleOptionButton, painter: QStylePainter) -> None:
        """Draw the icon/text pair using the configured visual gutter."""

        icon_size = option.iconSize
        text_width = option.fontMetrics.horizontalAdvance(option.text)
        width = icon_size.width() + self._icon_text_spacing + text_width
        left = option.rect.x() + max(0, (option.rect.width() - width) // 2)
        icon_rect = QRect(
            left,
            option.rect.y() + (option.rect.height() - icon_size.height()) // 2,
            icon_size.width(),
            icon_size.height(),
        )
        enabled = bool(option.state & QStyle.StateFlag.State_Enabled)
        mode = (
            QIcon.Mode.Active
            if option.state & QStyle.StateFlag.State_MouseOver
            else QIcon.Mode.Normal
        )
        if not enabled:
            mode = QIcon.Mode.Disabled
        option.icon.paint(painter, icon_rect, Qt.AlignmentFlag.AlignCenter, mode)
        group = QPalette.ColorGroup.Active if enabled else QPalette.ColorGroup.Disabled
        painter.setPen(option.palette.color(group, QPalette.ColorRole.ButtonText))
        painter.drawText(
            QRect(
                icon_rect.right() + 1 + self._icon_text_spacing,
                option.rect.y(),
                text_width,
                option.rect.height(),
            ),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            option.text,
        )
