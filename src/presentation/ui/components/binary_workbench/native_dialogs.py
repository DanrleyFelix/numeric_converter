import ctypes
import sys

from PySide6.QtWidgets import QMessageBox, QWidget

from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT


_IDYES = 6
_IDNO = 7
_IDCANCEL = 2

_MB_YESNOCANCEL = 0x00000003
_MB_ICONQUESTION = 0x00000020
_MB_TASKMODAL = 0x00002000
_MB_SETFOREGROUND = 0x00010000


def ask_close_tab_with_native_system_dialog(parent: QWidget) -> QMessageBox.StandardButton:
    if sys.platform == "win32":
        return _ask_windows_close_tab(parent)
    return _ask_qt_fallback(parent)


def _ask_windows_close_tab(parent: QWidget) -> QMessageBox.StandardButton:
    result = ctypes.windll.user32.MessageBoxW(
        _owner_window(parent),
        BINARY_WORKBENCH_TEXT.SAVE_BEFORE_CLOSE,
        BINARY_WORKBENCH_TEXT.TITLE,
        _MB_YESNOCANCEL | _MB_ICONQUESTION | _MB_TASKMODAL | _MB_SETFOREGROUND,
    )
    return _map_windows_response(result)


def _owner_window(parent: QWidget) -> int:
    try:
        return int(parent.winId())
    except RuntimeError:
        return 0


def _map_windows_response(response: int) -> QMessageBox.StandardButton:
    if response == _IDYES:
        return QMessageBox.StandardButton.Save
    if response == _IDNO:
        return QMessageBox.StandardButton.Discard
    if response == _IDCANCEL:
        return QMessageBox.StandardButton.Cancel
    return QMessageBox.StandardButton.Cancel


def _ask_qt_fallback(parent: QWidget) -> QMessageBox.StandardButton:
    return QMessageBox.question(
        parent,
        BINARY_WORKBENCH_TEXT.TITLE,
        BINARY_WORKBENCH_TEXT.SAVE_BEFORE_CLOSE,
        QMessageBox.StandardButton.Save
        | QMessageBox.StandardButton.Discard
        | QMessageBox.StandardButton.Cancel,
    )
