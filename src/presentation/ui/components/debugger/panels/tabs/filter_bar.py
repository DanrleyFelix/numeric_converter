"""Debounced contextual filter displayed beside debugger tabs."""

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QLabel, QLineEdit, QWidget

from src.presentation.ui.components.debugger.constants.layout import DEBUGGER_LAYOUT
from src.presentation.ui.components.debugger.constants.texts import (
    FOLLOW_LABEL,
    FOLLOW_READ_LABEL,
    FOLLOW_WRITE_LABEL,
)
from src.presentation.ui.design.icons import Icons


class DebouncedSearchEdit(QLineEdit):
    """Emit trimmed search text after the shared debugger debounce."""

    filterApplied = Signal(str)

    def __init__(self, placeholder: str, parent=None) -> None:
        """Create a search field with icon and two-second debounce."""

        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self._icon_right_margin = DEBUGGER_LAYOUT.FILTER_ICON_DEFAULT_MARGIN
        self._search_icon = QLabel(self)
        self._search_icon.setAttribute(Qt.WA_TransparentForMouseEvents)
        icon_size = DEBUGGER_LAYOUT.FILTER_ICON_SIZE
        self._search_icon.setFixedSize(icon_size, icon_size)
        self._search_icon.setPixmap(Icons.search_muted().pixmap(icon_size, icon_size))
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(DEBUGGER_LAYOUT.FILTER_DEBOUNCE_MS)
        self._timer.timeout.connect(
            lambda: self.filterApplied.emit(self.text().strip())
        )
        self.textChanged.connect(lambda _text: self._schedule())
        self.returnPressed.connect(self._schedule)

    def set_icon_right_margin(self, margin: int) -> None:
        """Position the passive search icon at an exact right-side distance."""

        self._icon_right_margin = margin
        self._position_icon()

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Keep the icon fixed and reserve text space before it."""

        super().resizeEvent(event)
        self._position_icon()

    def _schedule(self) -> None:
        """Restart the debounce interval for typing and Enter."""

        self._timer.start()

    def _position_icon(self) -> None:
        """Apply the configured icon margin and a non-overlapping text area."""

        icon_size = DEBUGGER_LAYOUT.FILTER_ICON_SIZE
        self._search_icon.move(
            self.width() - self._icon_right_margin - icon_size,
            (self.height() - icon_size) // 2,
        )
        text_margin = (
            self._icon_right_margin
            + icon_size
            + DEBUGGER_LAYOUT.FILTER_ICON_TEXT_GAP
        )
        self.setTextMargins(0, 0, text_margin, 0)


class DebuggerTabFilter(QWidget):
    """Expose one search field whose meaning follows the active tab."""

    filterApplied = Signal(str)
    followWritesChanged = Signal(bool)
    followReadsChanged = Signal(bool)

    def __init__(self, parent=None) -> None:
        """Create the contextual search shown beside supported tabs."""

        super().__init__(parent)
        self.setObjectName("debugger-tab-filter-container")
        self.search = DebouncedSearchEdit("", self)
        self.search.setObjectName("debugger-tab-filter")
        self.search.setFixedWidth(DEBUGGER_LAYOUT.FILTER_WIDTH)
        self.search.filterApplied.connect(self.filterApplied.emit)
        self.follow = QWidget(self)
        self.follow.setObjectName("debugger-memory-follow")
        follow_layout = QHBoxLayout(self.follow)
        follow_layout.setContentsMargins(
            0,
            DEBUGGER_LAYOUT.MEMORY_FOLLOW_TOP_MARGIN,
            DEBUGGER_LAYOUT.MEMORY_FOLLOW_RIGHT_MARGIN,
            DEBUGGER_LAYOUT.MEMORY_FOLLOW_BOTTOM_MARGIN,
        )
        follow_layout.setAlignment(Qt.AlignBottom)
        follow_layout.setSpacing(DEBUGGER_LAYOUT.TOOLBAR_SPACING)
        follow_layout.addStretch()
        follow_layout.addWidget(QLabel(FOLLOW_LABEL, self.follow))
        follow_layout.addWidget(QLabel(FOLLOW_WRITE_LABEL, self.follow))
        self.follow_write = self._follow_checkbox(self.followWritesChanged.emit)
        follow_layout.addWidget(self.follow_write)
        follow_layout.addWidget(QLabel(FOLLOW_READ_LABEL, self.follow))
        self.follow_read = self._follow_checkbox(self.followReadsChanged.emit)
        follow_layout.addWidget(self.follow_read)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.search)
        layout.addWidget(self.follow, 1)
        layout.setAlignment(self.search, Qt.AlignRight | Qt.AlignVCenter)

    def set_mode(self, placeholder: str, follow_visible: bool = False) -> None:
        """Reset the field and expose controls appropriate for one tab."""

        self.search._timer.stop()
        self.search.blockSignals(True)
        self.search.clear()
        self.search.setPlaceholderText(placeholder)
        self.search.blockSignals(False)
        self.search.setVisible(bool(placeholder))
        self.follow.setVisible(follow_visible)
        self.setVisible(bool(placeholder) or follow_visible)
        self.layout().invalidate()
        self.layout().activate()

    def _follow_checkbox(self, callback) -> QCheckBox:
        """Create one pointer-only W/R checkbox with its compact label."""

        checkbox = QCheckBox(self.follow)
        checkbox.setCursor(Qt.PointingHandCursor)
        checkbox.setFocusPolicy(Qt.NoFocus)
        checkbox.toggled.connect(callback)
        return checkbox
