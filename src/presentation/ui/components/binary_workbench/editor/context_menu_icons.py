from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QMenu

from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_LAYOUT,
)
from src.presentation.ui.components.binary_workbench.editor.constants.context_menu import (
    CONTEXT_MENU_ICON_COLOR,
    CONTEXT_MENU_ICON_GLYPHS,
)
from src.presentation.ui.design.icon_font import fontawesome_solid_family


def use_white_menu_icons(menu: QMenu) -> None:
    for action in menu.actions():
        glyph = CONTEXT_MENU_ICON_GLYPHS.get(_clean_text(action.text()))
        if glyph:
            action.setIcon(_glyph_icon(glyph))


def _glyph_icon(glyph: str) -> QIcon:
    size = BINARY_WORKBENCH_LAYOUT.CONTEXT_MENU_ICON_SIZE
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.TextAntialiasing, True)
    painter.setPen(QColor(CONTEXT_MENU_ICON_COLOR))
    font = QFont(fontawesome_solid_family())
    font.setPixelSize(round(size * 0.78))
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignCenter, glyph)
    painter.end()
    icon = QIcon()
    for mode in (QIcon.Normal, QIcon.Disabled, QIcon.Active, QIcon.Selected):
        icon.addPixmap(pixmap, mode)
    return icon


def _clean_text(text: str) -> str:
    return text.replace("&", "").split("\t", 1)[0].strip()
