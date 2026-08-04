from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QSizePolicy,
    QVBoxLayout,
)

from src.presentation.ui.components.binary_workbench.action_controls import (
    configure_binary_workbench_dialog_action,
    configure_binary_workbench_filter,
    configure_binary_workbench_line_edit,
)
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_LAYOUT,
    BINARY_WORKBENCH_TEXT,
)
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_DIALOG_LAYOUT as ENVIRONMENT_LAYOUT,
)
from src.presentation.ui.components.binary_workbench.environment.symbols_dialog_delegate import (
    SymbolCellDelegate,
)
from src.presentation.ui.components.binary_workbench.environment.symbols_dialog_widgets import (
    symbol_button,
    symbol_input,
)
from src.presentation.ui.components.binary_workbench.environment.symbols_table_view import (
    SymbolsTableView,
)
from src.presentation.ui.components.binary_workbench.input_validators import (
    set_python_identifier_validator,
)
from src.presentation.ui.design.icons import Icons


class SymbolsDialogLayoutMixin:
    """Build the fixed controls and virtualized symbols table."""

    def _build_footer_actions(self, parent: QVBoxLayout) -> None:
        """Create one fixed set of actions outside the scrolling table."""

        footer = QFrame(self.shell)
        footer.setObjectName("binary-workbench-symbol-footer")
        footer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        row = QHBoxLayout(footer)
        row.setContentsMargins(*ENVIRONMENT_LAYOUT.EMPTY_MARGINS)
        row.setSpacing(ENVIRONMENT_LAYOUT.ROW_SPACING)
        load = symbol_button(BINARY_WORKBENCH_TEXT.LOAD, "", footer)
        save = symbol_button(BINARY_WORKBENCH_TEXT.SAVE, "", footer)
        self.offsets_button = symbol_button(BINARY_WORKBENCH_TEXT.SYMBOL_OFFSETS, "", footer)
        load.setIcon(Icons.load())
        save.setIcon(Icons.save())
        self.offsets_button.setIcon(Icons.offsets())
        for button in (load, save, self.offsets_button):
            configure_binary_workbench_dialog_action(button)
        self.offsets_button.setEnabled(False)
        load.clicked.connect(self._load_library_json_dialog)
        save.clicked.connect(self._save_library_json_dialog)
        self.offsets_button.clicked.connect(self._open_selected_symbol_offsets)
        self.filter_input = symbol_input(
            BINARY_WORKBENCH_TEXT.FILTER,
            footer,
            "",
            BINARY_WORKBENCH_LAYOUT.SYMBOL_FILTER_WIDTH,
            search_icon=True,
        )
        configure_binary_workbench_filter(self.filter_input)
        configure_binary_workbench_line_edit(self.filter_input)
        self.filter_input.setMaximumWidth(BINARY_WORKBENCH_LAYOUT.SYMBOLS_DIALOG_MAX_WIDTH)
        self.filter_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.filter_input.textChanged.connect(self._apply_filter)
        row.addWidget(load)
        row.addWidget(save)
        row.addWidget(self.offsets_button)
        row.addWidget(self.filter_input, 1)
        parent.addWidget(footer, 0)

    def _build_entry(self, parent: QVBoxLayout) -> None:
        """Create the fixed controls used to append or merge one symbol."""

        entry = QFrame(self.shell)
        entry.setObjectName("binary-workbench-symbol-entry-row")
        entry.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        row = QHBoxLayout(entry)
        row.setContentsMargins(*ENVIRONMENT_LAYOUT.EMPTY_MARGINS)
        row.setSpacing(BINARY_WORKBENCH_LAYOUT.SYMBOL_ROW_SIDE_MARGIN)
        self.name = symbol_input(BINARY_WORKBENCH_TEXT.SYMBOL_NAME, entry, expanding=True)
        self.value = symbol_input(BINARY_WORKBENCH_TEXT.SYMBOL_VALUE, entry, expanding=True)
        configure_binary_workbench_line_edit(self.name)
        configure_binary_workbench_line_edit(self.value)
        set_python_identifier_validator(self.name)
        add = symbol_button(BINARY_WORKBENCH_TEXT.SYMBOL_ADD, "", entry)
        self.remove_button = symbol_button(BINARY_WORKBENCH_TEXT.SYMBOL_REMOVE, "", entry)
        add.setIcon(Icons.add())
        self.remove_button.setIcon(Icons.remove())
        configure_binary_workbench_dialog_action(add)
        configure_binary_workbench_dialog_action(self.remove_button)
        self.remove_button.setEnabled(False)
        add.clicked.connect(self._append_from_entry)
        self.remove_button.clicked.connect(self._remove_selected_symbol)
        row.addWidget(self.name, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(self.value, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(add, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(self.remove_button, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        row.addStretch(1)
        parent.addWidget(entry, 0)

    def _build_table(self, parent: QVBoxLayout) -> None:
        """Create the model/view table without permanent cell editors."""

        self.table = SymbolsTableView(self.shell)
        self.table.setObjectName("binary-workbench-symbols-table")
        self.table.setModel(self.symbols_proxy)
        self.table.setItemDelegate(SymbolCellDelegate(self.symbols_model.NAME_COLUMN, self.table))
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.SelectedClicked
            | QAbstractItemView.EditTrigger.EditKeyPressed
        )
        self.table.setAlternatingRowColors(False)
        self.table.setShowGrid(True)
        self.table.setSortingEnabled(True)
        self.table.sortByColumn(-1, Qt.SortOrder.AscendingOrder)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        scrollbar = self.table.verticalScrollBar()
        scrollbar.setObjectName("binary-workbench-symbols-scrollbar")
        scrollbar.style().unpolish(scrollbar)
        scrollbar.style().polish(scrollbar)
        self.table.setViewportMargins(
            ENVIRONMENT_LAYOUT.ZERO,
            ENVIRONMENT_LAYOUT.ZERO,
            BINARY_WORKBENCH_LAYOUT.SYMBOL_OFFSETS_SCROLLBAR_MARGIN,
            ENVIRONMENT_LAYOUT.ZERO,
        )
        self.table.verticalHeader().hide()
        self.table.verticalHeader().setDefaultSectionSize(BINARY_WORKBENCH_LAYOUT.SHARED_CONTROL_HEIGHT)
        header = self.table.horizontalHeader()
        header.setFixedHeight(BINARY_WORKBENCH_LAYOUT.SHARED_CONTROL_HEIGHT)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setHighlightSections(False)
        self.table.selectionModel().selectionChanged.connect(self._update_action_state)
        self.symbols_proxy.rowsRemoved.connect(self._update_action_state)
        self.symbols_proxy.layoutChanged.connect(self._update_action_state)
        parent.addWidget(self.table, 1)
