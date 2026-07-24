from __future__ import annotations

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtWidgets import QTabWidget

from src.core.debugger.contracts.base import BWDebugger
from src.core.debugger.memory.image import DebuggerMemoryImage
from src.presentation.ui.components.debugger.constants.layout import DEBUGGER_LAYOUT
from src.presentation.ui.components.debugger.constants.texts import LOWER_TAB_NAMES
from src.presentation.ui.components.debugger.constants.texts import (
    LOG_FILTER,
)
from src.presentation.ui.components.debugger.panels.log.view import DebuggerLogView
from src.presentation.ui.components.debugger.panels.memory.stack import DebuggerStackView
from src.presentation.ui.components.debugger.panels.memory.view import DebuggerMemoryView
from src.presentation.ui.components.debugger.panels.session.breakpoints import (
    DebuggerBreakpointsView,
)
from src.presentation.ui.components.debugger.panels.tabs.filter_bar import (
    DebuggerTabFilter,
)


class DebuggerLowerTabs(QTabWidget):
    """Group all lower debugger inspection views in persisted tabs."""

    navigateRequested = Signal(object)

    def __init__(self, debugger: BWDebugger, image: DebuggerMemoryImage, parent=None) -> None:
        """Create stack, memory, breakpoint and log tabs with one shared filter."""

        super().__init__(parent)
        self.setObjectName("debugger-lower-tabs")
        self.stack = DebuggerStackView(debugger, image, self)
        self.memory = DebuggerMemoryView(debugger, image, self)
        self.breakpoints = DebuggerBreakpointsView(debugger, self)
        self.log = DebuggerLogView(debugger, self)
        self.breakpoints.navigateRequested.connect(self.navigateRequested.emit)
        for name, widget in zip(
            LOWER_TAB_NAMES,
            (self.stack, self.memory, self.breakpoints, self.log),
        ):
            self.addTab(widget, name)
        self.filter = DebuggerTabFilter(self)
        self.setCornerWidget(self.filter, Qt.TopRightCorner)
        self.filter.filterApplied.connect(self._apply_filter)
        self.filter.followWritesChanged.connect(self.memory.set_follow_writes)
        self.filter.followReadsChanged.connect(self.memory.set_follow_reads)
        self.currentChanged.connect(self._tab_changed)
        self._corner_timer = QTimer(self)
        self._corner_timer.setSingleShot(True)
        self._corner_timer.timeout.connect(self._position_corner)
        self._breakpoint_fit_timer = QTimer(self)
        self._breakpoint_fit_timer.setSingleShot(True)
        self._breakpoint_fit_timer.timeout.connect(self.breakpoints.fit_columns)
        self._tab_changed(self.currentIndex())

    def refresh(self) -> None:
        """Refresh volatile panels after one execution or memory operation."""

        self.stack.refresh()
        self.memory.refresh()
        self.breakpoints.refresh()
        self.log.refresh()

    def resizeEvent(self, event) -> None:
        """Keep the breakpoint entry aligned with the complete tab strip."""

        super().resizeEvent(event)
        self._sync_corner()

    def _sync_corner(self) -> None:
        """Match the contextual corner exactly to the remaining tab-bar area."""

        tabs_width = self.tabBar().sizeHint().width()
        self.breakpoints.set_entry_width(tabs_width)
        self.filter.setFixedHeight(self.tabBar().height())
        self.filter.search.setFixedHeight(self.tabBar().height())
        self._corner_timer.start(0)

    def _position_corner(self) -> None:
        """Remove QTabWidget's extra gap before the contextual controls."""

        tabs_width = self.tabBar().sizeHint().width()
        self.filter.setGeometry(
            tabs_width,
            self.tabBar().geometry().top(),
            max(1, self.width() - tabs_width),
            self.tabBar().height(),
        )

    def _tab_changed(self, _index: int) -> None:
        """Update filter behavior and clear filters from inactive views."""

        self.log.set_filter("")
        current = self.currentWidget()
        if current is self.memory:
            self.filter.set_mode("", True)
        elif current is self.breakpoints:
            self.filter.set_mode("")
            self._breakpoint_fit_timer.start(0)
        elif current is self.log:
            self.filter.search.set_icon_right_margin(
                DEBUGGER_LAYOUT.LOG_FILTER_ICON_MARGIN
            )
            self.filter.set_mode(LOG_FILTER)
        else:
            self.filter.set_mode("")
        self._sync_corner()

    def _apply_filter(self, text: str) -> None:
        """Apply the debounced value according to the active tab."""

        if self.currentWidget() is self.log:
            self.log.set_filter(text)

    def refresh_running(self) -> None:
        """Refresh metadata that is safe while Unicorn owns its engine thread."""

        self.breakpoints.refresh()
        self.log.refresh()
