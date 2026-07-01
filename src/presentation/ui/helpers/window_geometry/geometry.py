from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QGuiApplication, QScreen
from PySide6.QtWidgets import QWidget

_ORIGINAL_MINIMUM_SIZE_PROPERTY = "_window_geometry_original_minimum_size"


def clamp_rect_to_available_geometry(rect: QRect, available: QRect) -> QRect:
    width = min(rect.width(), available.width())
    height = min(rect.height(), available.height())
    maximum_x = available.right() - width + 1
    maximum_y = available.bottom() - height + 1
    x = min(max(rect.x(), available.left()), maximum_x)
    y = min(max(rect.y(), available.top()), maximum_y)
    return QRect(x, y, width, height)


def ensure_window_on_available_screen(
    window: QWidget,
    anchor: QWidget | None = None,
) -> None:
    screens = QGuiApplication.screens()
    if not screens:
        return

    frame = window.frameGeometry()
    screen = _target_screen(window, frame, screens, anchor)
    available = screen.availableGeometry()
    client = window.geometry()
    horizontal_frame = max(0, frame.width() - client.width())
    vertical_frame = max(0, frame.height() - client.height())
    maximum_width = max(1, available.width() - horizontal_frame)
    maximum_height = max(1, available.height() - vertical_frame)
    original_minimum = window.property(_ORIGINAL_MINIMUM_SIZE_PROPERTY)
    if not isinstance(original_minimum, QSize):
        original_minimum = window.minimumSize()
        window.setProperty(_ORIGINAL_MINIMUM_SIZE_PROPERTY, original_minimum)
    window.setMinimumSize(
        min(original_minimum.width(), maximum_width),
        min(original_minimum.height(), maximum_height),
    )
    if available.contains(frame):
        return

    window.resize(
        min(client.width(), maximum_width),
        min(client.height(), maximum_height),
    )

    frame = window.frameGeometry()
    clamped = clamp_rect_to_available_geometry(frame, available)
    window.move(clamped.topLeft())


def _target_screen(
    window: QWidget,
    frame: QRect,
    screens: Sequence[QScreen],
    anchor: QWidget | None,
) -> QScreen:
    if anchor is not None and not window.testAttribute(Qt.WA_WState_Created):
        anchor_screen = anchor.screen()
        if anchor_screen in screens:
            return anchor_screen

    overlaps = [
        (
            frame.intersected(screen.availableGeometry()).width()
            * frame.intersected(screen.availableGeometry()).height(),
            screen,
        )
        for screen in screens
    ]
    overlap_area, overlap_screen = max(overlaps, key=lambda item: item[0])
    if overlap_area > 0:
        return overlap_screen

    if anchor is not None:
        anchor_screen = anchor.screen()
        if anchor_screen in screens:
            return anchor_screen
    return QGuiApplication.primaryScreen() or screens[0]
