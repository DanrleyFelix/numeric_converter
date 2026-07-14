from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import QPoint, QRect, QSize, Qt
from PySide6.QtGui import QCursor, QGuiApplication, QScreen
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


def recover_window_on_available_screen(
    window: QWidget,
    anchor: QWidget | None = None,
    *,
    alternate_screen: bool = False,
) -> None:
    screens = QGuiApplication.screens()
    if not screens:
        return
    frame = window.frameGeometry()
    screen = _target_screen(window, frame, screens, anchor)
    if alternate_screen and len(screens) > 1:
        screen = screens[(screens.index(screen) + 1) % len(screens)]
        target = _centered_top_left(frame, screen.availableGeometry())
    else:
        target = _clamped_top_left(frame, screen.availableGeometry())
    window.move(target)


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

    center_screen = _screen_containing(frame.center(), screens)
    if center_screen is not None:
        return center_screen

    if anchor is not None:
        anchor_screen = _screen_containing(anchor.frameGeometry().center(), screens)
        if anchor_screen is not None:
            return anchor_screen
        anchor_screen = anchor.screen()
        if anchor_screen in screens:
            return anchor_screen
    mouse_screen = _screen_containing(QCursor.pos(), screens)
    if mouse_screen is not None:
        return mouse_screen
    return QGuiApplication.primaryScreen() or screens[0]


def _screen_containing(point: QPoint, screens: Sequence[QScreen]) -> QScreen | None:
    return next(
        (screen for screen in screens if screen.availableGeometry().contains(point)),
        None,
    )


def _clamped_top_left(frame: QRect, available: QRect) -> QPoint:
    maximum_x = available.right() - frame.width() + 1
    maximum_y = available.bottom() - frame.height() + 1
    x = available.left() if maximum_x < available.left() else min(max(frame.x(), available.left()), maximum_x)
    y = available.top() if maximum_y < available.top() else min(max(frame.y(), available.top()), maximum_y)
    return QPoint(x, y)


def _centered_top_left(frame: QRect, available: QRect) -> QPoint:
    centered = QPoint(
        available.left() + max(0, (available.width() - frame.width()) // 2),
        available.top() + max(0, (available.height() - frame.height()) // 2),
    )
    return _clamped_top_left(QRect(centered, frame.size()), available)
