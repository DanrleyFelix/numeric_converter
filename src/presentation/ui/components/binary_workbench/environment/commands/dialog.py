from PySide6.QtCore import Signal
from PySide6.QtWidgets import QDialog, QFrame, QHBoxLayout, QSizePolicy, QVBoxLayout

from src.presentation.ui.components.binary_workbench.action_controls import (
    configure_binary_workbench_dialog_action,
    configure_binary_workbench_filter,
    configure_binary_workbench_line_edit,
)
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_DIALOG_LAYOUT as ENVIRONMENT_LAYOUT,
    BINARY_WORKBENCH_LAYOUT,
    BINARY_WORKBENCH_TEXT,
)
from src.presentation.ui.components.binary_workbench.environment.commands.dialog_helpers import (
    CommandsFileActionsMixin,
    edit_command_instructions,
)
from src.presentation.ui.components.binary_workbench.environment.symbols_dialog_widgets import (
    symbol_button,
    symbol_input,
)
from src.presentation.ui.components.binary_workbench.environment_table.model import (
    EnvironmentFilterProxyModel,
    EnvironmentTableModel,
)
from src.presentation.ui.components.binary_workbench.environment_table.view import (
    EnvironmentCellDelegate,
    EnvironmentTableView,
    configure_environment_table,
)
from src.presentation.ui.design.icons import Icons


class BinaryWorkbenchCommandsDialog(CommandsFileActionsMixin, QDialog):
    """Manage commands through a virtualized, filterable table."""

    commandLoadRequested = Signal(str)
    commandSaveRequested = Signal(str)
    commandRemoveRequested = Signal(str)
    commandInstructionsChangeRequested = Signal(str, list)

    def __init__(self, commands: dict[str, list[str]], default_directory: str, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("workspace-table-dialog")
        self.setWindowTitle(BINARY_WORKBENCH_TEXT.COMMANDS)
        self.setFixedWidth(BINARY_WORKBENCH_LAYOUT.SYMBOLS_DIALOG_WIDTH)
        self.setMinimumHeight(BINARY_WORKBENCH_LAYOUT.COMMANDS_DIALOG_MIN_HEIGHT)
        self.setMaximumHeight(BINARY_WORKBENCH_LAYOUT.COMMANDS_DIALOG_MAX_HEIGHT)
        self.resize(BINARY_WORKBENCH_LAYOUT.SYMBOLS_DIALOG_WIDTH, BINARY_WORKBENCH_LAYOUT.COMMANDS_DIALOG_MIN_HEIGHT)
        self._default_directory = default_directory
        self.commands_model = EnvironmentTableModel(
            (BINARY_WORKBENCH_TEXT.COMMANDS, BINARY_WORKBENCH_TEXT.COMMAND_INSTRUCTION_HEADER),
            set(),
            self,
        )
        self.commands_proxy = EnvironmentFilterProxyModel(self)
        self.commands_proxy.setSourceModel(self.commands_model)
        self._build_dialog()
        self.set_commands(commands)

    def set_commands(self, commands: dict[str, list[str]]) -> None:
        """Replace commands with one model reset and no row widgets."""

        rows = []
        for name, instructions in sorted(commands.items()):
            payload = (name, list(instructions))
            rows.append(([f"/{name}", " | ".join(instructions)], payload, " ".join(instructions)))
        self.commands_model.replace(rows)
        self._update_action_state()

    def set_default_directory(self, path: str) -> None:
        """Update the directory used by native load/save dialogs."""

        self._default_directory = path

    def _build_dialog(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(*ENVIRONMENT_LAYOUT.DIALOG_MARGINS)
        self.shell = QFrame(self)
        self.shell.setObjectName("workspace-table-shell")
        layout = QVBoxLayout(self.shell)
        layout.setContentsMargins(*ENVIRONMENT_LAYOUT.SYMBOLS_PANEL_MARGINS)
        layout.setSpacing(ENVIRONMENT_LAYOUT.PANEL_SPACING)
        self.table = EnvironmentTableView(self.shell)
        self.table.setModel(self.commands_proxy)
        self.table.setItemDelegate(EnvironmentCellDelegate(parent=self.table))
        configure_environment_table(self.table, "binary-workbench-environment-table")
        self.table.selectionModel().selectionChanged.connect(self._update_action_state)
        self.table.doubleClicked.connect(lambda _index: self._edit_selected())
        layout.addWidget(self.table, 1)
        self._build_footer(layout)
        root.addWidget(self.shell, 1)

    def _build_footer(self, parent: QVBoxLayout) -> None:
        footer = QFrame(self.shell)
        row = QHBoxLayout(footer)
        row.setContentsMargins(*ENVIRONMENT_LAYOUT.EMPTY_MARGINS)
        row.setSpacing(ENVIRONMENT_LAYOUT.ROW_SPACING)
        load = symbol_button(BINARY_WORKBENCH_TEXT.LOAD, "", footer)
        save = symbol_button(BINARY_WORKBENCH_TEXT.SAVE, "", footer)
        self.show_button = symbol_button(BINARY_WORKBENCH_TEXT.SHOW, "", footer)
        self.remove_button = symbol_button(BINARY_WORKBENCH_TEXT.SYMBOL_REMOVE, "", footer)
        load.setIcon(Icons.load())
        save.setIcon(Icons.save())
        self.show_button.setIcon(Icons.show())
        self.remove_button.setIcon(Icons.remove())
        for button in (load, save, self.show_button, self.remove_button):
            configure_binary_workbench_dialog_action(button)
        load.clicked.connect(self._request_load)
        save.clicked.connect(self._request_save)
        self.show_button.clicked.connect(self._edit_selected)
        self.remove_button.clicked.connect(self._remove_selected)
        self.show_button.setEnabled(False)
        self.remove_button.setEnabled(False)
        self.filter_input = symbol_input(BINARY_WORKBENCH_TEXT.FILTER, footer, search_icon=True)
        configure_binary_workbench_filter(self.filter_input)
        configure_binary_workbench_line_edit(self.filter_input)
        self.filter_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.filter_input.textChanged.connect(self.commands_proxy.set_query)
        row.addWidget(load)
        row.addWidget(save)
        row.addWidget(self.show_button)
        row.addWidget(self.remove_button)
        row.addWidget(self.filter_input, 1)
        parent.addWidget(footer)

    def _selected_payload(self) -> tuple[str, list[str]] | None:
        index = self.table.currentIndex()
        if not index.isValid():
            return None
        record = self.commands_model.record_at(self.commands_proxy.mapToSource(index).row())
        return record.payload if record is not None else None

    def _update_action_state(self, *args) -> None:
        enabled = self._selected_payload() is not None
        self.show_button.setEnabled(enabled)
        self.remove_button.setEnabled(enabled)

    def _edit_selected(self) -> None:
        payload = self._selected_payload()
        if payload is None:
            return
        name, instructions = payload
        updated = edit_command_instructions(name, instructions, self)
        if updated is not None:
            self.commandInstructionsChangeRequested.emit(name, updated)

    def _remove_selected(self) -> None:
        payload = self._selected_payload()
        if payload is not None:
            self.commandRemoveRequested.emit(payload[0])
