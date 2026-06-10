from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QScrollArea, QSizePolicy, QVBoxLayout, QWidget

from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_LAYOUT, BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.environment.symbols_dialog_widgets import (
    symbol_button,
    symbol_input,
    symbol_kind_combo,
)


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
        )
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
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(BINARY_WORKBENCH_LAYOUT.SYMBOL_FOOTER_ACTION_SPACING)
        load = symbol_button("Load", "preferences-cancel", footer)
        save = symbol_button("Save", "preferences-ok", footer)
        ok = symbol_button("OK", "preferences-ok", footer)
        for button in (load, save, ok):
            button.setFixedSize(BINARY_WORKBENCH_LAYOUT.SYMBOL_ACTION_WIDTH, BINARY_WORKBENCH_LAYOUT.SYMBOL_INPUT_HEIGHT)
        load.clicked.connect(self._load_library_json_dialog)
        save.clicked.connect(self._save_library_json_dialog)
        ok.clicked.connect(self.accept)
        row.addWidget(load, 0, Qt.AlignVCenter)
        row.addWidget(save, 0, Qt.AlignVCenter)
        row.addWidget(ok, 0, Qt.AlignVCenter)
        row.addStretch(1)
        parent.addWidget(footer, 0)

    def _build_entry(self, parent: QVBoxLayout) -> None:
        entry = QFrame(self.shell)
        entry.setObjectName("binary-workbench-symbol-entry-row")
        entry.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        row = QHBoxLayout(entry)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(BINARY_WORKBENCH_LAYOUT.SYMBOL_ROW_SIDE_MARGIN)
        self.kind = symbol_kind_combo(entry, "Variable")
        self.name = symbol_input(BINARY_WORKBENCH_TEXT.SYMBOL_NAME, entry)
        self.value = symbol_input(BINARY_WORKBENCH_TEXT.SYMBOL_VALUE, entry)
        add = symbol_button(BINARY_WORKBENCH_TEXT.SYMBOL_ADD, "preferences-ok", entry)
        add.setFixedSize(BINARY_WORKBENCH_LAYOUT.SYMBOL_ADD_ACTION_WIDTH, BINARY_WORKBENCH_LAYOUT.SYMBOL_INPUT_HEIGHT)
        add.clicked.connect(self._append_from_entry)
        row.addWidget(self.kind, 0)
        row.addWidget(self.name, 0)
        row.addWidget(self.value, 0)
        row.addWidget(add, 0, Qt.AlignVCenter)
        row.addStretch(1)
        parent.addWidget(entry, 0)

    def _build_scroll_body(self, parent: QVBoxLayout) -> None:
        self.scroll = QScrollArea(self.shell)
        self.scroll.setObjectName("workspace-table-body-scroll")
        self.scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.scroll.verticalScrollBar().setObjectName("workspace-table-scrollbar")
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.body = QWidget(self.scroll)
        self.body.setObjectName("workspace-table-body")
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(0, 10, 0, 10)
        self.body_layout.setSpacing(10)
        self.body_layout.setAlignment(Qt.AlignTop)
        self.scroll.setWidget(self.body)
        parent.addWidget(self.scroll, 1)
