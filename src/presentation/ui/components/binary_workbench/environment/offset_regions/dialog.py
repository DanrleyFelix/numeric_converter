from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QSizePolicy,
    QVBoxLayout,
)

from src.modules.binary_workbench_dtos import BinaryWorkbenchOffsetRegionDTO
from src.presentation.ui.components.binary_workbench.action_controls import (
    configure_binary_workbench_dialog_action,
    configure_binary_workbench_filter,
    configure_binary_workbench_line_edit,
)
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_DIALOG_LAYOUT,
    BINARY_WORKBENCH_LAYOUT,
    BINARY_WORKBENCH_TEXT,
)
from src.presentation.ui.components.binary_workbench.environment.offset_regions.constants import OFFSET_REGIONS_SIZE
from src.presentation.ui.components.binary_workbench.environment.offset_regions.io import OffsetRegionsFileActionsMixin
from src.presentation.ui.components.binary_workbench.environment.offset_regions.rows import OffsetRegionsRowsMixin
from src.presentation.ui.components.binary_workbench.environment.symbols_dialog_widgets import symbol_button, symbol_input
from src.presentation.ui.components.binary_workbench.environment_table.model import (
    EnvironmentFilterProxyModel,
    EnvironmentTableModel,
)
from src.presentation.ui.components.binary_workbench.environment_table.view import (
    EnvironmentCellDelegate,
    EnvironmentTableView,
    configure_environment_table,
)
from src.presentation.ui.components.binary_workbench.input_validators import set_hex_value_validator
from src.presentation.ui.design.icons import Icons


class BinaryWorkbenchOffsetRegionsDialog(OffsetRegionsRowsMixin, OffsetRegionsFileActionsMixin, QDialog):
    """Manage offset regions through a virtualized editable table."""

    directoryChanged = Signal(str)
    goToRequested = Signal(int)

    def __init__(self, regions: list[BinaryWorkbenchOffsetRegionDTO], directory: str, parent=None,
                 details_loader: Callable[[str, int], str] | None = None,
                 details_source_path: Path | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("workspace-table-dialog")
        self.setWindowTitle(BINARY_WORKBENCH_TEXT.OFFSET_REGIONS)
        self.setMinimumSize(OFFSET_REGIONS_SIZE.DIALOG_MIN_WIDTH, OFFSET_REGIONS_SIZE.DIALOG_MIN_HEIGHT)
        self.setMaximumSize(OFFSET_REGIONS_SIZE.DIALOG_MAX_WIDTH, OFFSET_REGIONS_SIZE.DIALOG_MAX_HEIGHT)
        self.resize(OFFSET_REGIONS_SIZE.DIALOG_WIDTH, OFFSET_REGIONS_SIZE.DIALOG_HEIGHT)
        self._directory = directory
        self._saved_path = ""
        self._loaded_path = ""
        self._details_loader = details_loader
        self._details_source_path = details_source_path
        self.regions_model = EnvironmentTableModel((BINARY_WORKBENCH_TEXT.OFFSET_NAME, BINARY_WORKBENCH_TEXT.OFFSET_VALUE), {0, 1}, self)
        self.regions_proxy = EnvironmentFilterProxyModel(self)
        self.regions_proxy.setSourceModel(self.regions_model)
        self._build_dialog(regions)

    def saved_path(self) -> str:
        """Return the latest successfully saved path."""

        return self._saved_path

    def loaded_path(self) -> str:
        """Return the latest successfully loaded path."""

        return self._loaded_path

    def _build_dialog(self, regions: list[BinaryWorkbenchOffsetRegionDTO]) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(*BINARY_WORKBENCH_DIALOG_LAYOUT.DIALOG_MARGINS)
        self.shell = QFrame(self)
        self.shell.setObjectName("workspace-table-shell")
        layout = QVBoxLayout(self.shell)
        layout.setContentsMargins(*BINARY_WORKBENCH_DIALOG_LAYOUT.SYMBOLS_PANEL_MARGINS)
        layout.setSpacing(BINARY_WORKBENCH_DIALOG_LAYOUT.PANEL_SPACING)
        self._build_entry(layout)
        self.table = EnvironmentTableView(self.shell)
        self.table.setModel(self.regions_proxy)
        self.table.setItemDelegate(EnvironmentCellDelegate({1: set_hex_value_validator}, self.table))
        configure_environment_table(
            self.table,
            "binary-workbench-environment-table",
            extended_selection=True,
        )
        self.table.selectionModel().selectionChanged.connect(self._update_action_state)
        self.table.selectionModel().currentChanged.connect(self._update_action_state)
        self.regions_proxy.layoutChanged.connect(self._update_action_state)
        layout.addWidget(self.table, 1)
        self._build_footer(layout)
        self._replace_regions(regions)
        root.addWidget(self.shell, 1)

    def _build_entry(self, parent: QVBoxLayout) -> None:
        entry = QFrame(self.shell)
        row = QHBoxLayout(entry)
        row.setContentsMargins(*BINARY_WORKBENCH_DIALOG_LAYOUT.EMPTY_MARGINS)
        row.setSpacing(BINARY_WORKBENCH_LAYOUT.SYMBOL_ROW_SIDE_MARGIN)
        self.name = symbol_input(BINARY_WORKBENCH_TEXT.OFFSET_NAME, entry, expanding=True)
        self.offset = symbol_input(BINARY_WORKBENCH_TEXT.OFFSET_VALUE, entry, expanding=True)
        set_hex_value_validator(self.offset)
        configure_binary_workbench_line_edit(self.name)
        configure_binary_workbench_line_edit(self.offset)
        add = symbol_button(BINARY_WORKBENCH_TEXT.SYMBOL_ADD, "", entry)
        self.remove_button = symbol_button(
            BINARY_WORKBENCH_TEXT.SYMBOL_REMOVE,
            "",
            entry,
        )
        self.details_button = symbol_button(BINARY_WORKBENCH_TEXT.DETAILS, "", entry)
        add.setIcon(Icons.add())
        self.remove_button.setIcon(Icons.remove())
        self.details_button.setIcon(Icons.show())
        for button in (add, self.remove_button, self.details_button):
            configure_binary_workbench_dialog_action(button)
        add.clicked.connect(self._append_from_entry)
        self.remove_button.clicked.connect(self._remove_selected)
        self.details_button.clicked.connect(self._edit_selected_details)
        self.remove_button.setEnabled(False)
        self.details_button.setEnabled(False)
        row.addWidget(self.name, 1)
        row.addWidget(self.offset, 1)
        row.addWidget(add)
        row.addStretch(1)
        row.addWidget(self.remove_button)
        row.addStretch(1)
        row.addWidget(self.details_button)
        parent.addWidget(entry)

    def _build_footer(self, parent: QVBoxLayout) -> None:
        """Keep Filter elastic so its right edge follows the table."""

        footer = QFrame(self.shell)
        row = QHBoxLayout(footer)
        row.setContentsMargins(*BINARY_WORKBENCH_DIALOG_LAYOUT.EMPTY_MARGINS)
        row.setSpacing(BINARY_WORKBENCH_DIALOG_LAYOUT.ROW_SPACING)
        actions = ((BINARY_WORKBENCH_TEXT.LOAD, Icons.load(), self._load), (BINARY_WORKBENCH_TEXT.SAVE, Icons.save(), self._save), (BINARY_WORKBENCH_TEXT.GO_TO, Icons.offsets(), self._go_to_selected))
        buttons = []
        for text, icon, callback in actions:
            button = symbol_button(text, "", footer)
            button.setIcon(icon)
            configure_binary_workbench_dialog_action(button)
            button.clicked.connect(callback)
            row.addWidget(button)
            buttons.append(button)
        self.go_to_button = buttons[2]
        self.go_to_button.setEnabled(False)
        self.filter_input = symbol_input(BINARY_WORKBENCH_TEXT.FILTER, footer, search_icon=True)
        configure_binary_workbench_filter(self.filter_input)
        configure_binary_workbench_line_edit(self.filter_input)
        self.filter_input.setMinimumWidth(BINARY_WORKBENCH_LAYOUT.SHARED_FILTER_WIDTH)
        self.filter_input.setMaximumWidth(
            BINARY_WORKBENCH_LAYOUT.EXPANDING_CONTROL_MAX_WIDTH
        )
        self.filter_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.filter_input.textChanged.connect(self._apply_filter)
        row.addWidget(self.filter_input, 1)
        row.setStretch(row.indexOf(self.filter_input), 1)
        parent.addWidget(footer)
