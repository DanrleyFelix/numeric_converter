"""Debugger Log category controls used by the F11 configuration."""

from collections.abc import Iterable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QGridLayout, QWidget

from src.presentation.ui.components.debugger.constants.layout import DEBUGGER_LAYOUT
from src.presentation.ui.components.debugger.constants.texts import (
    CONFIG_LOG_LEVELS,
)


class DebuggerLogOptions(QWidget):
    """Expose all supported Debug Log categories as checked options."""

    def __init__(
        self,
        enabled_levels: Iterable[str] | None = None,
        parent=None,
    ) -> None:
        """Build a compact grid initialized from the current log selection."""

        super().__init__(parent)
        selected = (
            set(CONFIG_LOG_LEVELS)
            if enabled_levels is None
            else set(enabled_levels)
        )
        self.boxes: dict[str, QCheckBox] = {}
        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(DEBUGGER_LAYOUT.CONFIG_LOG_OPTION_SPACING)
        layout.setVerticalSpacing(DEBUGGER_LAYOUT.CONFIG_LOG_OPTION_SPACING)
        for index, level in enumerate(CONFIG_LOG_LEVELS):
            checkbox = QCheckBox(level, self)
            checkbox.setCursor(Qt.PointingHandCursor)
            checkbox.setChecked(level in selected)
            self.boxes[level] = checkbox
            layout.addWidget(
                checkbox,
                index // DEBUGGER_LAYOUT.CONFIG_LOG_COLUMNS,
                index % DEBUGGER_LAYOUT.CONFIG_LOG_COLUMNS,
            )

    def selected_levels(self) -> frozenset[str]:
        """Return the category names currently enabled by the user."""

        return frozenset(
            level
            for level, checkbox in self.boxes.items()
            if checkbox.isChecked()
        )
