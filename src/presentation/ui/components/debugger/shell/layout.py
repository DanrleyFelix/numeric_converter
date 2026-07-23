from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSplitter, QVBoxLayout, QWidget

from src.core.debugger.session.factory import DebuggerSessionBundle
from src.presentation.ui.components.debugger.actions import DebuggerActionBar, DebuggerActions
from src.presentation.ui.components.debugger.constants.layout import DEBUGGER_LAYOUT
from src.presentation.ui.components.debugger.panels.instructions import (
    DebuggerInstructionPanel,
)
from src.presentation.ui.components.debugger.panels.registers import DebuggerRegisterPanel
from src.presentation.ui.components.debugger.panels.tabs.widget import DebuggerLowerTabs


@dataclass(frozen=True)
class DebuggerWindowPanels:
    """Expose the debugger widgets that require refresh or persistence."""

    instructions: DebuggerInstructionPanel
    registers: DebuggerRegisterPanel
    lower: DebuggerLowerTabs
    horizontal: QSplitter
    vertical: QSplitter


def build_debugger_shell(
    parent,
    bundle: DebuggerSessionBundle,
    actions: DebuggerActions,
) -> tuple[QWidget, DebuggerWindowPanels]:
    """Build the complete resizable debugger layout with established spacing."""

    instructions = DebuggerInstructionPanel(parent)
    registers = DebuggerRegisterPanel(bundle.debugger, parent)
    lower = DebuggerLowerTabs(bundle.debugger, bundle.memory, parent)
    vertical = QSplitter(Qt.Vertical, parent)
    vertical.setObjectName("debugger-vertical-splitter")
    vertical.setHandleWidth(DEBUGGER_LAYOUT.PANEL_GAP)
    vertical.addWidget(instructions)
    vertical.addWidget(lower)
    vertical.setSizes(list(DEBUGGER_LAYOUT.TOP_BOTTOM_SIZES))
    horizontal = QSplitter(Qt.Horizontal, parent)
    horizontal.setObjectName("debugger-horizontal-splitter")
    horizontal.setHandleWidth(DEBUGGER_LAYOUT.PANEL_GAP)
    horizontal.addWidget(vertical)
    horizontal.addWidget(registers)
    horizontal.setSizes(list(DEBUGGER_LAYOUT.INSTRUCTION_REGISTER_SIZES))
    shell = QWidget(parent)
    shell.setObjectName("debugger-shell")
    layout = QVBoxLayout(shell)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)
    layout.addWidget(DebuggerActionBar(actions, shell))
    body = QWidget(shell)
    body_layout = QVBoxLayout(body)
    body_layout.setContentsMargins(*(DEBUGGER_LAYOUT.OUTER_MARGIN,) * 4)
    body_layout.addWidget(horizontal)
    layout.addWidget(body, 1)
    panels = DebuggerWindowPanels(instructions, registers, lower, horizontal, vertical)
    return shell, panels
