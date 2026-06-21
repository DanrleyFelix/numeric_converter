from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QScrollArea, QSizePolicy, QVBoxLayout, QWidget

from src.presentation.ui.components.binary_workbench.action_controls import (
    configure_binary_workbench_dialog_action,
    configure_binary_workbench_combo,
    configure_binary_workbench_filter,
    configure_binary_workbench_line_edit,
)
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_LAYOUT, BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.environment.symbols_dialog_widgets import (
    symbol_button,
    symbol_input,
    symbol_kind_combo,
)
from src.presentation.ui.components.binary_workbench.input_validators import set_python_identifier_validator
from src.presentation.ui.components.workspace_table.constants.layout import WORKSPACE_TABLE_SIZE


class SymbolsDialogLayoutMixin:
    def _build_library_controls(self, parent: QVBoxLayout, _default_library_name: str) -> None:
        filters = QFrame(self.shell)
        filters.setObjectName("binary-workbench-symbol-filter-row")
        filters.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        row = QHBoxLayout(filters)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)
        self.filter_input = symbol_input(
            BINARY_WORKBENCH_TEXT.FILTER,
            filters,
            "",
            BINARY_WORKBENCH_LAYOUT.SYMBOL_FILTER_WIDTH,
            search_icon=True,
        )
        configure_binary_workbench_filter(self.filter_input)
        configure_binary_workbench_line_edit(self.filter_input)
        self.filter_input.textChanged.connect(self._apply_filter)
        row.addWidget(self.filter_input, 0, Qt.AlignLeft | Qt.AlignVCenter)
        row.addStretch(1)
        parent.addWidget(filters, 0)
        parent.addSpacing(20)

    def _build_footer_actions(self, parent: QVBoxLayout) -> None:
        footer = QFrame(self.shell)
        footer.setObjectName("binary-workbench-symbol-footer")
        footer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        row = QHBoxLayout(footer)
        row.setContentsMargins(0, 0, _delete_gutter_width(), 0)
        row.setSpacing(0)
        load = symbol_button("Load", "", footer)
        save = symbol_button("Save", "", footer)
        ok = symbol_button("OK", "", footer)
        for button in (load, save, ok):
            configure_binary_workbench_dialog_action(button)
        load.clicked.connect(self._load_library_json_dialog)
        save.clicked.connect(self._save_library_json_dialog)
        ok.clicked.connect(self.accept)
        row.addWidget(load, 0, Qt.AlignLeft)
        row.addStretch(1)
        row.addWidget(ok, 0, Qt.AlignHCenter)
        row.addStretch(1)
        row.addWidget(save, 0, Qt.AlignRight)
        parent.addWidget(footer, 0)

    def _build_entry(self, parent: QVBoxLayout) -> None:
        entry = QFrame(self.shell)
        entry.setObjectName("binary-workbench-symbol-entry-row")
        entry.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        row = QHBoxLayout(entry)
        row.setContentsMargins(0, 0, _delete_gutter_width(), 0)
        row.setSpacing(BINARY_WORKBENCH_LAYOUT.SYMBOL_ROW_SIDE_MARGIN)
        self.kind = symbol_kind_combo(entry, "Variable", expanding=True)
        self.name = symbol_input(BINARY_WORKBENCH_TEXT.SYMBOL_NAME, entry, expanding=True)
        self.value = symbol_input(BINARY_WORKBENCH_TEXT.SYMBOL_VALUE, entry, expanding=True)
        configure_binary_workbench_combo(self.kind)
        configure_binary_workbench_line_edit(self.name)
        configure_binary_workbench_line_edit(self.value)
        set_python_identifier_validator(self.name)
        add = symbol_button(BINARY_WORKBENCH_TEXT.SYMBOL_ADD, "", entry)
        configure_binary_workbench_dialog_action(add)
        add.clicked.connect(self._append_from_entry)
        row.addWidget(self.kind, 1)
        row.addWidget(self.name, 1)
        row.addWidget(self.value, 1)
        row.addWidget(add, 1, Qt.AlignVCenter)
        parent.addWidget(entry, 0)

    def _build_scroll_body(self, parent: QVBoxLayout) -> None:
        self.scroll = QScrollArea(self.shell)
        self.scroll.setObjectName("workspace-table-body-scroll")
        self.scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.scroll.verticalScrollBar().setObjectName("workspace-table-scrollbar")
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll_body = QWidget(self.scroll)
        self.scroll_body.setObjectName("workspace-table-body")
        scroll_layout = QHBoxLayout(self.scroll_body)
        scroll_layout.setContentsMargins(
            0,
            10,
            BINARY_WORKBENCH_LAYOUT.ROW_DELETE_SCROLLBAR_MARGIN,
            10,
        )
        scroll_layout.setSpacing(BINARY_WORKBENCH_LAYOUT.ROW_DELETE_COLUMN_SPACING)
        self.body = QFrame(self.scroll_body)
        self.body.setObjectName("workspace-table-body")
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setSpacing(10)
        self.body_layout.setAlignment(Qt.AlignTop)
        self.remove_body = QFrame(self.scroll_body)
        self.remove_body.setObjectName("workspace-table-body")
        self.remove_layout = QVBoxLayout(self.remove_body)
        self.remove_layout.setContentsMargins(0, 0, 0, 0)
        self.remove_layout.setSpacing(10)
        self.remove_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        scroll_layout.addWidget(self.body, 1)
        scroll_layout.addWidget(self.remove_body, 0)
        self.scroll.setWidget(self.scroll_body)
        parent.addWidget(self.scroll, 1)


def _delete_gutter_width() -> int:
    return (
        WORKSPACE_TABLE_SIZE.REMOVE_BUTTON_WIDTH
        + BINARY_WORKBENCH_LAYOUT.ROW_DELETE_COLUMN_SPACING
        + BINARY_WORKBENCH_LAYOUT.ROW_DELETE_SCROLLBAR_MARGIN
        + BINARY_WORKBENCH_LAYOUT.ROW_SCROLLBAR_RESERVED_WIDTH
    )
