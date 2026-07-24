"""Filtered debugger log with project-standard context actions."""

from __future__ import annotations

import re

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor, QKeySequence, QSyntaxHighlighter, QTextCharFormat
from PySide6.QtWidgets import QMenu, QPlainTextEdit, QVBoxLayout, QWidget

from src.core.debugger.contracts.base import BWDebugger
from src.presentation.ui.components.binary_workbench.editor.context_menu_icons import (
    use_white_menu_icons,
)
from src.presentation.ui.components.binary_workbench.editor.highlighter_colors import (
    psx_mips_highlight_color,
    psx_mips_required_highlight_color,
)
from src.presentation.ui.design.icons import Icons
from src.presentation.ui.helpers.load_qss import THEME_TOKENS

HEX_VALUE = re.compile(r"0x[0-9A-Fa-f]+")
ACCESS_WORD = re.compile(r"\b(?:Write|Read)\b")
EVENT_WORD = re.compile(r"\b(?:Breakpoint|Ignored|Import)\b", re.IGNORECASE)


class DebuggerLogHighlighter(QSyntaxHighlighter):
    """Color levels, addresses and memory-access operations."""

    LEVEL_COLORS = {
        "Warning": THEME_TOKENS["text-warning"],
        "Error": THEME_TOKENS["text-danger"],
        "Info": THEME_TOKENS["text-success"],
        "Execution": psx_mips_highlight_color("registers", "$t0"),
        "Memory": psx_mips_highlight_color("registers", "$sp"),
    }
    ACCESS_COLORS = {
        "Write": THEME_TOKENS["text-debug-write"],
        "Read": THEME_TOKENS["text-debug-read"],
    }
    EVENT_COLORS = {
        "breakpoint": THEME_TOKENS["text-debug-write"],
        "ignored": THEME_TOKENS["text-warning"],
        "import": psx_mips_highlight_color("registers", "$sp"),
    }

    def highlightBlock(self, text: str) -> None:
        """Highlight every supported token in one log line."""

        level = text.split(":", 1)[0].split(" ", 1)[0]
        self._format(0, len(level), self.LEVEL_COLORS.get(level))
        for match in HEX_VALUE.finditer(text):
            self._format(
                match.start(),
                match.end() - match.start(),
                psx_mips_required_highlight_color("hex"),
            )
        for match in ACCESS_WORD.finditer(text):
            self._format(
                match.start(),
                match.end() - match.start(),
                self.ACCESS_COLORS[match.group()],
            )
        for match in EVENT_WORD.finditer(text):
            self._format(
                match.start(),
                match.end() - match.start(),
                self.EVENT_COLORS[match.group().casefold()],
            )

    def _format(self, start: int, length: int, color: str | None) -> None:
        """Apply one foreground color when its token is available."""

        if color is None:
            return
        style = QTextCharFormat()
        style.setForeground(QColor(color))
        self.setFormat(start, length, style)


class DebuggerLogView(QWidget):
    """Render and filter structured debugger events without extra controls."""

    def __init__(self, debugger: BWDebugger, parent=None) -> None:
        """Create a read-only log with a standard context menu."""

        super().__init__(parent)
        self._debugger = debugger
        self._filter = ""
        self._rendered_count = -1
        self.output = QPlainTextEdit(self)
        self.output.setObjectName("debugger-log")
        self.output.setReadOnly(True)
        self.output.setContextMenuPolicy(Qt.CustomContextMenu)
        self.output.customContextMenuRequested.connect(self._context_menu)
        self._clear_action = QAction(Icons.remove(), "Clear Log", self.output)
        self._clear_action.setShortcut(QKeySequence("Ctrl+L"))
        self._clear_action.setShortcutContext(Qt.WidgetWithChildrenShortcut)
        self._clear_action.setShortcutVisibleInContextMenu(True)
        self._clear_action.triggered.connect(self._clear)
        self.output.addAction(self._clear_action)
        self._highlighter = DebuggerLogHighlighter(self.output.document())
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.output)
        self.refresh()

    def refresh(self) -> None:
        """Rebuild visible lines when events or filter state changes."""

        events = self._debugger.events
        if len(events) == self._rendered_count:
            return
        lines = []
        for event in events:
            show_address = event.address is not None and event.level not in {"Memory", "Info"}
            address = f" [0x{event.address:08X}]" if show_address else ""
            line = f"{event.level}{address}: {event.message}"
            if not self._filter or self._filter in line.casefold():
                lines.append(line)
        self.output.setPlainText("\n".join(lines))
        self._rendered_count = len(events)
        scrollbar = self.output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def set_filter(self, text: str) -> None:
        """Filter log lines case-insensitively by typed characters."""

        self._filter = text.strip().casefold()
        self._rendered_count = -1
        self.refresh()

    def _context_menu(self, position) -> None:
        """Add Clear Log to the standard styled text menu."""

        menu = self.output.createStandardContextMenu()
        menu.setObjectName("binary-workbench-editor-context-menu")
        menu.addAction(self._clear_action)
        use_white_menu_icons(menu)
        menu.exec(self.output.viewport().mapToGlobal(position))

    def _clear(self) -> None:
        """Clear events through the debugger without changing counters."""

        self._debugger.clear_events()
        self._rendered_count = -1
        self.refresh()
