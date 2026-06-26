from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QCompleter


def fit_completer_popup_height(completer: QCompleter) -> None:
    QTimer.singleShot(0, lambda: _fit_visible_popup_height(completer))


def _fit_visible_popup_height(completer: QCompleter) -> None:
    popup = completer.popup()
    if not popup.isVisible():
        return
    visible_rows = min(completer.maxVisibleItems(), popup.model().rowCount())
    rows_height = sum(popup.sizeHintForRow(row) for row in range(visible_rows))
    frame_height = max(0, popup.height() - popup.viewport().height())
    popup.resize(popup.width(), rows_height + frame_height)
