"""Register-condition breakpoint dialog matching Debugger Config geometry."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QLineEdit, QPushButton, QVBoxLayout

from src.core.debugger.contracts.base import BWDebugger
from src.core.debugger.models.session import DebuggerError
from src.presentation.ui.components.binary_workbench.action_controls import (
    configure_binary_workbench_dialog_action,
    configure_binary_workbench_line_edit,
)
from src.presentation.ui.components.debugger.constants.layout import DEBUGGER_LAYOUT
from src.presentation.ui.components.debugger.constants.texts import (
    CONFIG_CONFIRM,
    REGISTER_BREAKPOINT_PLACEHOLDER,
    REGISTER_BREAKPOINT_TITLE,
)


class DebuggerRegisterBreakpointDialog(QDialog):
    """Collect and create one condition for a selected register."""

    def __init__(
        self,
        debugger: BWDebugger,
        register: str,
        parent=None,
    ) -> None:
        """Create the condition-only fixed-size debugger dialog."""

        super().__init__(parent)
        self._debugger = debugger
        self.setObjectName("preferences-dialog")
        self.setWindowTitle(REGISTER_BREAKPOINT_TITLE)
        self.setFixedSize(
            DEBUGGER_LAYOUT.CONFIG_DIALOG_WIDTH,
            DEBUGGER_LAYOUT.CONFIG_DIALOG_HEIGHT,
        )
        self.condition = QLineEdit(self)
        self.condition.setObjectName("binary-workbench-dialog-input")
        self.condition.setPlaceholderText(
            REGISTER_BREAKPOINT_PLACEHOLDER.format(register=register)
        )
        configure_binary_workbench_line_edit(
            self.condition,
            DEBUGGER_LAYOUT.CONFIG_FIELD_WIDTH,
        )
        confirm = QPushButton(CONFIG_CONFIRM, self)
        configure_binary_workbench_dialog_action(confirm)
        confirm.setFixedWidth(DEBUGGER_LAYOUT.CONFIG_CONFIRM_WIDTH)
        confirm.clicked.connect(self._accept_condition)
        self.condition.returnPressed.connect(self._accept_condition)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(*(DEBUGGER_LAYOUT.OUTER_MARGIN,) * 4)
        layout.setSpacing(DEBUGGER_LAYOUT.CONFIG_VERTICAL_SPACING)
        layout.addWidget(self.condition, 0, Qt.AlignCenter)
        layout.addWidget(confirm, 0, Qt.AlignCenter)

    def _accept_condition(self) -> None:
        """Create the breakpoint only when the core accepts its condition."""

        condition = self.condition.text().strip()
        if not condition:
            return
        try:
            self._debugger.add_register_breakpoint(condition)
        except (DebuggerError, ValueError):
            return
        self.accept()
