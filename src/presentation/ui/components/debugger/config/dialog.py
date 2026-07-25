"""Fixed debugger execution-interval configuration dialog."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QIntValidator, QValidator
from PySide6.QtWidgets import QDialog, QLabel, QLineEdit, QPushButton, QVBoxLayout

from src.core.debugger.execution.constants import (
    MAX_EXECUTION_INTERVAL_MS,
    MIN_EXECUTION_INTERVAL_MS,
)
from src.presentation.ui.components.binary_workbench.action_controls import (
    configure_binary_workbench_dialog_action,
    configure_binary_workbench_line_edit,
)
from src.presentation.ui.components.debugger.constants.layout import DEBUGGER_LAYOUT
from src.presentation.ui.components.debugger.constants.texts import (
    CONFIG_CONFIRM,
    CONFIG_INTERVAL_PLACEHOLDER,
    CONFIG_LOG_LABEL,
    CONFIG_LOG_LEVELS,
    CONFIG_TITLE,
)
from src.presentation.ui.components.debugger.config.log_options import (
    DebuggerLogOptions,
)


class DebuggerConfigDialog(QDialog):
    """Collect one automatic-instruction interval in milliseconds."""

    def __init__(
        self,
        parent=None,
        enabled_log_levels: frozenset[str] | None = None,
    ) -> None:
        """Create a fixed-size dialog aligned with project controls."""

        super().__init__(parent)
        self.setObjectName("preferences-dialog")
        self.setWindowTitle(CONFIG_TITLE)
        self.setFixedSize(
            DEBUGGER_LAYOUT.CONFIG_DIALOG_WIDTH,
            DEBUGGER_LAYOUT.CONFIG_LOG_DIALOG_HEIGHT,
        )
        log_label = QLabel(CONFIG_LOG_LABEL, self)
        self.log_options = DebuggerLogOptions(enabled_log_levels, self)
        self.interval = QLineEdit(self)
        self.interval.setObjectName("binary-workbench-dialog-input")
        self.interval.setPlaceholderText(CONFIG_INTERVAL_PLACEHOLDER)
        self.interval.setValidator(
            QIntValidator(
                MIN_EXECUTION_INTERVAL_MS,
                MAX_EXECUTION_INTERVAL_MS,
                self.interval,
            )
        )
        configure_binary_workbench_line_edit(
            self.interval, DEBUGGER_LAYOUT.CONFIG_FIELD_WIDTH
        )
        confirm = QPushButton(CONFIG_CONFIRM, self)
        configure_binary_workbench_dialog_action(confirm)
        confirm.setFixedWidth(DEBUGGER_LAYOUT.CONFIG_CONFIRM_WIDTH)
        confirm.clicked.connect(self._accept_valid)
        self.interval.returnPressed.connect(self._accept_valid)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(*(DEBUGGER_LAYOUT.OUTER_MARGIN,) * 4)
        layout.setSpacing(DEBUGGER_LAYOUT.CONFIG_VERTICAL_SPACING)
        layout.addWidget(log_label, 0, Qt.AlignLeft)
        layout.addWidget(self.log_options, 0, Qt.AlignCenter)
        layout.addWidget(self.interval, 0, Qt.AlignCenter)
        layout.addWidget(confirm, 0, Qt.AlignCenter)

    def interval_ms(self) -> int | None:
        """Return the entered interval or no value for an empty field."""

        text = self.interval.text().strip()
        return int(text) if text else None

    def enabled_log_levels(self) -> frozenset[str]:
        """Return the Debug Log categories selected for display."""

        return self.log_options.selected_levels()

    def _accept_valid(self) -> None:
        """Accept only a complete interval inside the supported range."""

        text = self.interval.text().strip()
        state, _text, _position = self.interval.validator().validate(
            text, len(text)
        )
        if state == QValidator.Acceptable:
            self.accept()


def ask_debugger_config(
    parent=None,
    enabled_log_levels: frozenset[str] | None = None,
) -> tuple[int, frozenset[str]] | None:
    """Return the accepted interval and visible Debug Log categories."""

    dialog = DebuggerConfigDialog(parent, enabled_log_levels)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None
    interval = dialog.interval_ms()
    if interval is None:
        return None
    return interval, dialog.enabled_log_levels()


def ask_execution_interval(parent=None) -> int | None:
    """Preserve the interval-only helper used by existing integrations."""

    config = ask_debugger_config(parent, frozenset(CONFIG_LOG_LEVELS))
    return config[0] if config is not None else None
