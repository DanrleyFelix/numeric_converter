from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QTabWidget

from src.core.debugger.contracts.base import BWDebugger
from src.core.debugger.memory.image import DebuggerMemoryImage
from src.presentation.ui.components.debugger.constants.texts import LOWER_TAB_NAMES
from src.presentation.ui.components.debugger.constants.texts import (
    LOG_FILTER,
    MEMORY_ADDRESS_FILTER,
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
        self.filter.followAccessChanged.connect(self.memory.set_follow_access)
        self.currentChanged.connect(self._tab_changed)
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
        self.breakpoints.set_entry_width(self.tabBar().sizeHint().width())

    def _tab_changed(self, _index: int) -> None:
        """Update filter behavior and clear filters from inactive views."""

        self.breakpoints.set_filter("")
        self.log.set_filter("")
        current = self.currentWidget()
        if current is self.memory:
            self.filter.set_mode(MEMORY_ADDRESS_FILTER, True)
        elif current is self.breakpoints:
            self.filter.set_mode(MEMORY_ADDRESS_FILTER, False)
        elif current is self.log:
            self.filter.set_mode(LOG_FILTER, False)
        else:
            self.filter.set_mode("", False)

    def _apply_filter(self, text: str) -> None:
        """Apply the debounced value according to the active tab."""

        current = self.currentWidget()
        if current is self.memory and text:
            self.memory.navigate(text)
        elif current is self.breakpoints:
            self.breakpoints.set_filter(text)
        elif current is self.log:
            self.log.set_filter(text)

    def refresh_running(self) -> None:
        """Refresh metadata that is safe while Unicorn owns its engine thread."""

        self.breakpoints.refresh()
        self.log.refresh()
