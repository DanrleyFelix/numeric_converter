from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QFrame, QHBoxLayout, QSizePolicy, QVBoxLayout, QWidget

from src.modules.binary_workbench_constants import (
    BINARY_WORKBENCH_DEFAULT_LBA_SECTOR_SIZE,
    BINARY_WORKBENCH_LBA_SECTOR_SIZE_OPTIONS,
)
from src.modules.binary_workbench_dtos import BinaryWorkbenchInternalFileDTO
from src.presentation.ui.components.binary_workbench.action_controls import (
    configure_binary_workbench_combo,
    configure_binary_workbench_dialog_action,
    configure_binary_workbench_filter,
    configure_binary_workbench_line_edit,
)
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_DIALOG_LAYOUT as ENVIRONMENT_LAYOUT,
    BINARY_WORKBENCH_LAYOUT,
    BINARY_WORKBENCH_TEXT,
)
from src.presentation.ui.components.binary_workbench.environment.symbols_dialog_widgets import (
    symbol_button,
    symbol_input,
)
from src.presentation.ui.components.binary_workbench.environment_table.view import (
    EnvironmentCellDelegate,
    EnvironmentTableView,
    configure_environment_table,
)
from src.presentation.ui.components.binary_workbench.file_dialogs.constants import (
    BINARY_WORKBENCH_FILE_DIALOG_TEXT,
)
from src.presentation.ui.components.binary_workbench.file_dialogs.lba_filesystem_widgets import (
    lba_inline_field,
)
from src.presentation.ui.components.binary_workbench.input_validators import (
    set_decimal_integer_validator,
    set_internal_file_name_validator,
)
from src.presentation.ui.design.icons import Icons


class LbaFilesystemLayoutMixin:
    """Build an LBA editor with fixed controls around a virtualized table."""

    def _build_library_controls(self, parent: QVBoxLayout, _name: str, sector_size: int) -> None:
        """Create the sector-size selector without per-record widgets."""

        row_widget = QWidget(self.shell)
        row = QHBoxLayout(row_widget)
        row.setContentsMargins(*ENVIRONMENT_LAYOUT.EMPTY_MARGINS)
        self.sector_size = QComboBox(row_widget)
        self.sector_size.setObjectName("binary-workbench-dialog-input")
        self.sector_size.addItems([f"{value} bytes" for value in BINARY_WORKBENCH_LBA_SECTOR_SIZE_OPTIONS])
        selected = sector_size if sector_size in BINARY_WORKBENCH_LBA_SECTOR_SIZE_OPTIONS else BINARY_WORKBENCH_DEFAULT_LBA_SECTOR_SIZE
        self.sector_size.setCurrentText(f"{selected} bytes")
        configure_binary_workbench_combo(self.sector_size, BINARY_WORKBENCH_LAYOUT.SHARED_INPUT_WIDTH)
        row.addWidget(lba_inline_field(BINARY_WORKBENCH_FILE_DIALOG_TEXT.LBA_SECTOR_LABEL, self.sector_size))
        row.addStretch(1)
        parent.addWidget(row_widget)

    def _build_entry(self, parent: QVBoxLayout) -> None:
        """Create fixed Name, Start LBA, Add, and Remove controls."""

        entry = QFrame(self.shell)
        row = QHBoxLayout(entry)
        row.setContentsMargins(*ENVIRONMENT_LAYOUT.EMPTY_MARGINS)
        row.setSpacing(BINARY_WORKBENCH_LAYOUT.SYMBOL_ROW_SIDE_MARGIN)
        self.name = symbol_input(BINARY_WORKBENCH_TEXT.LBA_FILE_NAME, entry, expanding=True)
        self.lba = symbol_input(BINARY_WORKBENCH_TEXT.LBA_START, entry, expanding=True)
        configure_binary_workbench_line_edit(self.name)
        configure_binary_workbench_line_edit(self.lba)
        set_internal_file_name_validator(self.name)
        set_decimal_integer_validator(self.lba)
        add = symbol_button(BINARY_WORKBENCH_TEXT.SYMBOL_ADD, "", entry)
        self.remove_button = symbol_button(BINARY_WORKBENCH_TEXT.SYMBOL_REMOVE, "", entry)
        add.setIcon(Icons.add())
        self.remove_button.setIcon(Icons.remove())
        for button in (add, self.remove_button):
            configure_binary_workbench_dialog_action(button)
        self.remove_button.setEnabled(False)
        add.clicked.connect(self._append_from_entry)
        self.remove_button.clicked.connect(self._remove_selected)
        for widget in (self.name, self.lba, add, self.remove_button):
            row.addWidget(widget, 1 if widget in (self.name, self.lba) else 0)
        parent.addWidget(entry)

    def _build_rows(self, parent: QVBoxLayout, files: list[BinaryWorkbenchInternalFileDTO]) -> None:
        """Create the shared Model/View table and load its initial records."""

        self.table = EnvironmentTableView(self.shell)
        self.table.setModel(self.lba_proxy)
        self.table.setItemDelegate(EnvironmentCellDelegate({0: set_internal_file_name_validator, 1: set_decimal_integer_validator}, self.table))
        configure_environment_table(self.table, "binary-workbench-environment-table")
        self.table.selectionModel().selectionChanged.connect(self._update_action_state)
        self.lba_proxy.layoutChanged.connect(self._update_action_state)
        self._replace_rows(files)
        parent.addWidget(self.table, 1)

    def _build_footer_actions(self, parent: QVBoxLayout) -> None:
        """Create fixed Load, Save, Go to, and expanding Filter controls."""

        footer = QFrame(self.shell)
        footer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        row = QHBoxLayout(footer)
        row.setContentsMargins(*ENVIRONMENT_LAYOUT.EMPTY_MARGINS)
        row.setSpacing(ENVIRONMENT_LAYOUT.ROW_SPACING)
        load = symbol_button(BINARY_WORKBENCH_TEXT.LOAD, "", footer)
        save = symbol_button(BINARY_WORKBENCH_TEXT.SAVE, "", footer)
        self.go_to_button = symbol_button(BINARY_WORKBENCH_TEXT.GO_TO, "", footer)
        load.setIcon(Icons.load())
        save.setIcon(Icons.save())
        self.go_to_button.setIcon(Icons.offsets())
        for button in (load, save, self.go_to_button):
            configure_binary_workbench_dialog_action(button)
        self.go_to_button.setEnabled(False)
        load.clicked.connect(self._load_library_json_dialog)
        save.clicked.connect(self._save_library_json_dialog)
        self.go_to_button.clicked.connect(self._go_to_selected)
        self.filter_input = symbol_input(BINARY_WORKBENCH_TEXT.FILTER, footer, search_icon=True)
        configure_binary_workbench_filter(self.filter_input)
        configure_binary_workbench_line_edit(self.filter_input)
        self.filter_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.filter_input.textChanged.connect(self._apply_filter)
        for button in (load, save, self.go_to_button):
            row.addWidget(button)
        row.addWidget(self.filter_input, 1)
        parent.addWidget(footer)
