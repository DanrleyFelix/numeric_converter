from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, QSize, Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QFrame, QHBoxLayout, QToolButton

from src.presentation.ui.components.debugger.constants.layout import DEBUGGER_LAYOUT
from src.presentation.ui.components.debugger.constants.texts import DEBUGGER_ACTIONS
from src.presentation.ui.components.toolbar_constants import TOOLBAR_SIZE


class DebuggerActions(QObject):
    """Own the QActions shared by Binary Workbench and debugger windows."""

    def __init__(self, parent: QObject) -> None:
        """Create debugger actions with window-local function-key shortcuts."""

        super().__init__(parent)
        self._actions: list[QAction] = []
        for name, text, shortcut in DEBUGGER_ACTIONS:
            action = QAction(f"{text} ({shortcut})", self)
            action.setObjectName(f"debugger-{name}-action")
            action.setShortcut(QKeySequence(shortcut))
            action.setShortcutContext(Qt.WindowShortcut)
            action.setShortcutVisibleInContextMenu(True)
            action.setToolTip("")
            action.setStatusTip("")
            setattr(self, name, action)
            self._actions.append(action)

    def all(self) -> tuple[QAction, ...]:
        """Return actions in toolbar display order."""

        return tuple(self._actions)


class DebuggerActionButton(QToolButton):
    """Suppress redundant hover tooltips while preserving QAction behavior."""

    def event(self, event) -> bool:
        """Consume tooltip requests and delegate every other event."""

        if event.type() == QEvent.ToolTip:
            event.ignore()
            return True
        return super().event(event)


class DebuggerActionBar(QFrame):
    """Render shared debugger QActions with the existing toolbar language."""

    def __init__(self, actions: DebuggerActions, parent=None) -> None:
        """Create one pointer-driven button for every shared action."""

        super().__init__(parent)
        self.setObjectName("toolbar")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(DEBUGGER_LAYOUT.TOOLBAR_SPACING)
        for action in actions.all():
            button = DebuggerActionButton(self)
            button.setDefaultAction(action)
            button.setToolTip("")
            button.setToolButtonStyle(Qt.ToolButtonTextOnly)
            button.setIconSize(QSize(TOOLBAR_SIZE.ICON_SIZE, TOOLBAR_SIZE.ICON_SIZE))
            button.setMinimumWidth(DEBUGGER_LAYOUT.TOOLBAR_BUTTON_MIN_WIDTH)
            button.setFixedHeight(DEBUGGER_LAYOUT.TOOLBAR_BUTTON_HEIGHT)
            button.setCursor(Qt.PointingHandCursor)
            button.setFocusPolicy(Qt.NoFocus)
            layout.addWidget(button)
        layout.addStretch(1)
