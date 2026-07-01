import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QRect
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication, QWidget

from src.presentation.ui.helpers.window_geometry import (
    clamp_rect_to_available_geometry,
    ensure_window_on_available_screen,
)


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_clamp_preserves_geometry_already_inside_available_area():
    available = QRect(-1920, 0, 1920, 1040)
    geometry = QRect(-1600, 120, 900, 700)

    assert clamp_rect_to_available_geometry(geometry, available) == geometry


def test_clamp_anchors_oversized_offscreen_geometry_inside_available_area():
    available = QRect(0, 0, 1280, 720)

    clamped = clamp_rect_to_available_geometry(
        QRect(2400, -900, 1920, 1080),
        available,
    )

    assert clamped == available


def test_window_is_resized_and_moved_into_a_screen_available_geometry():
    app = _app()
    window = QWidget()
    window.setMinimumSize(10_000, 10_000)
    window.resize(100_000, 100_000)
    window.move(100_000, 100_000)
    window.show()
    app.processEvents()

    ensure_window_on_available_screen(window)
    app.processEvents()

    assert any(
        screen.availableGeometry().contains(window.frameGeometry())
        for screen in QGuiApplication.screens()
    )
    window.close()
