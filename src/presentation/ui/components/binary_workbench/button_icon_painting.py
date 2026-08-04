from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QIcon, QPalette
from PySide6.QtWidgets import (
    QPushButton,
    QStyle,
    QStyleOptionButton,
    QStylePainter,
)

from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_LAYOUT,
)

ICON_TEXT_SPACING_PROPERTY = "binaryWorkbenchIconTextSpacing"


def configure_binary_workbench_icon_text(button: QPushButton) -> None:
    """Request centered icon/text painting with the symbols-dialog spacing."""

    button.setProperty(
        ICON_TEXT_SPACING_PROPERTY,
        BINARY_WORKBENCH_LAYOUT.SYMBOL_ACTION_ICON_TEXT_SPACING,
    )


class CenteredIconTextButton(QPushButton):
    """Keep icon and text visibly separated and centered as one group."""

    def paintEvent(self, event) -> None:
        """Let QSS paint the button shell, then paint its content explicitly."""

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
        _draw_centered_icon_text(
            option,
            painter,
            BINARY_WORKBENCH_LAYOUT.SYMBOL_ACTION_ICON_TEXT_SPACING,
        )


def _draw_centered_icon_text(option, painter, spacing: int) -> None:
    icon_size = option.iconSize
    text_width = option.fontMetrics.horizontalAdvance(option.text)
    content_width = icon_size.width() + spacing + text_width
    left = option.rect.x() + max(0, (option.rect.width() - content_width) // 2)
    icon_rect = QRect(
        left,
        option.rect.y() + (option.rect.height() - icon_size.height()) // 2,
        icon_size.width(),
        icon_size.height(),
    )
    enabled = bool(option.state & QStyle.StateFlag.State_Enabled)
    mode = QIcon.Mode.Active if option.state & QStyle.StateFlag.State_MouseOver else QIcon.Mode.Normal
    if not enabled:
        mode = QIcon.Mode.Disabled
    state = QIcon.State.On if option.state & QStyle.StateFlag.State_On else QIcon.State.Off
    option.icon.paint(painter, icon_rect, Qt.AlignmentFlag.AlignCenter, mode, state)
    color_group = QPalette.ColorGroup.Active if enabled else QPalette.ColorGroup.Disabled
    painter.setPen(option.palette.color(color_group, QPalette.ColorRole.ButtonText))
    painter.drawText(
        QRect(
            icon_rect.right() + 1 + spacing,
            option.rect.y(),
            text_width,
            option.rect.height(),
        ),
        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
        option.text,
    )
