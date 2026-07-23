"""Debounced contextual filter displayed beside debugger tabs."""

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QLineEdit, QWidget

from src.presentation.ui.components.debugger.constants.layout import DEBUGGER_LAYOUT
from src.presentation.ui.components.debugger.constants.texts import (
    FOLLOW_ACCESS_TEXT,
)
from src.presentation.ui.design.icons import Icons


class DebuggerTabFilter(QWidget):
    """Expose one search field whose meaning follows the active tab."""

    filterApplied = Signal(str)
    followAccessChanged = Signal(bool)

    def __init__(self, parent=None) -> None:
        """Create a two-second debounced search and W/R toggle."""

        super().__init__(parent)
        self.search = QLineEdit(self)
        self.search.setObjectName("debugger-tab-filter")
        self.search.setFixedWidth(DEBUGGER_LAYOUT.FILTER_WIDTH)
        self.search.addAction(
            Icons.search_muted(), QLineEdit.ActionPosition.TrailingPosition
        )
        self.follow = QCheckBox(FOLLOW_ACCESS_TEXT, self)
        self.follow.setCursor(Qt.PointingHandCursor)
        self.follow.setFocusPolicy(Qt.NoFocus)
        self.follow.toggled.connect(self.followAccessChanged.emit)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(DEBUGGER_LAYOUT.FILTER_DEBOUNCE_MS)
        self._timer.timeout.connect(
            lambda: self.filterApplied.emit(self.search.text().strip())
        )
        self.search.textChanged.connect(lambda _text: self._schedule())
        self.search.returnPressed.connect(self._schedule)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(DEBUGGER_LAYOUT.TOOLBAR_SPACING)
        layout.addWidget(self.search)
        layout.addWidget(self.follow)

    def set_mode(self, placeholder: str, follow_visible: bool) -> None:
        """Reset the field and expose controls appropriate for one tab."""

        self._timer.stop()
        self.search.blockSignals(True)
        self.search.clear()
        self.search.setPlaceholderText(placeholder)
        self.search.blockSignals(False)
        self.follow.setVisible(follow_visible)
        self.setVisible(bool(placeholder))

    def _schedule(self) -> None:
        """Restart the shared debounce interval for typing and Enter."""

        self._timer.start()
