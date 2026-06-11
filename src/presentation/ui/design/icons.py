from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap

from src.presentation.ui.design.icon_font import fontawesome_solid_family
from src.presentation.ui.design.icon_specs import (
    ICON_GLYPHS,
    WINDOW_ICON_NAME,
    WINDOW_ICON_TOKEN,
)
from src.presentation.ui.helpers.load_qss import THEME_TOKENS

ICON_SIZES = (16, 20, 24, 32, 48, 64)
MUTED_ICON_OPACITY = 0.48


class Icons:

    @staticmethod
    def _icon(
        glyph_name: str,
        token_name: str,
        *,
        active_token_name: str | None = None,
        selected_token_name: str | None = None,
        opacity: float = 1.0,
    ) -> QIcon:
        icon = QIcon()
        icon.addPixmap(
            _pixmap(glyph_name, token_name, 64, opacity),
            QIcon.Normal,
            QIcon.Off,
        )
        icon.addPixmap(
            _pixmap(glyph_name, active_token_name or token_name, 64, opacity),
            QIcon.Active,
            QIcon.Off,
        )
        icon.addPixmap(
            _pixmap(glyph_name, selected_token_name or token_name, 64, opacity),
            QIcon.Selected,
            QIcon.Off,
        )
        for size in ICON_SIZES:
            icon.addPixmap(_pixmap(glyph_name, token_name, size, opacity), QIcon.Normal)
            icon.addPixmap(
                _pixmap(glyph_name, active_token_name or token_name, size, opacity),
                QIcon.Active,
            )
            icon.addPixmap(
                _pixmap(glyph_name, selected_token_name or token_name, size, opacity),
                QIcon.Selected,
            )
        return icon

    @staticmethod
    def numeric_workbench():
        return Icons._icon("numeric_workbench", "icon-brand")

    @staticmethod
    def calculator():
        return Icons._icon("calculator", "icon-primary")

    @staticmethod
    def decimal():
        return Icons._icon("decimal", "icon-primary")

    @staticmethod
    def binary():
        return Icons._icon("binary", "icon-primary")

    @staticmethod
    def hexadecimal():
        return Icons._icon(WINDOW_ICON_NAME, WINDOW_ICON_TOKEN)

    @staticmethod
    def command_window():
        return Icons._icon("command_window", "icon-primary")

    @staticmethod
    def file():
        return Icons._icon("file", "icon-toolbar")

    @staticmethod
    def donor():
        return Icons._icon("donor", "icon-toolbar")

    @staticmethod
    def environment():
        return Icons._icon("environment", "icon-toolbar")

    @staticmethod
    def preferences():
        return Icons._icon("preferences", "icon-toolbar")

    @staticmethod
    def tools():
        return Icons._icon("tools", "icon-toolbar")

    @staticmethod
    def help():
        return Icons._icon("help", "icon-toolbar")

    @staticmethod
    def copy():
        return Icons._icon("copy", "icon-toolbar")

    @staticmethod
    def remove():
        return Icons._icon(
            "remove",
            "icon-toolbar",
            active_token_name="icon-danger",
            selected_token_name="icon-danger",
        )

    @staticmethod
    def remove_hover():
        return Icons._icon("remove", "icon-danger")

    @staticmethod
    def search():
        return Icons._icon("search", "icon-toolbar")

    @staticmethod
    def search_muted():
        return Icons._icon("search", "icon-toolbar", opacity=MUTED_ICON_OPACITY)


def _pixmap(glyph_name: str, token_name: str, size: int, opacity: float = 1.0) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setRenderHint(QPainter.TextAntialiasing, True)
    painter.setOpacity(opacity)
    painter.setPen(QColor(THEME_TOKENS[token_name]))

    font = QFont(fontawesome_solid_family())
    font.setPixelSize(round(size * 0.78))
    if glyph_name == "hexadecimal":
        font.setBold(True)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignCenter, ICON_GLYPHS[glyph_name])
    painter.end()

    return pixmap
