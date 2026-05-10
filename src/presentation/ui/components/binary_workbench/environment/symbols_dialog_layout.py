from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QScrollArea, QVBoxLayout, QWidget

from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_LAYOUT, BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.environment.symbols_dialog_widgets import (
    size_symbol_input,
    symbol_button,
    symbol_field,
    symbol_input,
    symbol_kind_combo,
    symbol_label,
)


class SymbolsDialogLayoutMixin:
    def _build_library_controls(self, parent: QVBoxLayout, default_library_name: str) -> None:
        library = QWidget(self.shell)
        row = QHBoxLayout(library)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)
        self.library_name_input = symbol_input(
            "Library Name",
            library,
            default_library_name,
            BINARY_WORKBENCH_LAYOUT.SYMBOL_LIBRARY_NAME_WIDTH,
        )
        row.addWidget(symbol_field("Library Name", self.library_name_input), 0)
        parent.addWidget(library, 0, Qt.AlignLeft)

    def _build_footer_actions(self, parent: QVBoxLayout) -> None:
        footer = QWidget(self.shell)
        row = QHBoxLayout(footer)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(14)
        row.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        load = symbol_button("Load", "preferences-cancel", footer)
        save = symbol_button("Save", "preferences-ok", footer)
        ok = symbol_button("OK", "preferences-ok", footer)
        for button in (load, save, ok):
            button.setFixedSize(BINARY_WORKBENCH_LAYOUT.SYMBOL_ACTION_WIDTH, BINARY_WORKBENCH_LAYOUT.SYMBOL_INPUT_HEIGHT)
        load.clicked.connect(self._load_library_json_dialog)
        save.clicked.connect(self._save_library_json_dialog)
        ok.clicked.connect(self.accept)
        row.addWidget(load, 0, Qt.AlignLeft | Qt.AlignVCenter)
        row.addWidget(save, 0, Qt.AlignLeft | Qt.AlignVCenter)
        row.addWidget(ok, 0, Qt.AlignLeft | Qt.AlignVCenter)
        parent.addWidget(footer, 0)

    def _build_entry(self, parent: QVBoxLayout) -> None:
        entry = QWidget(self.shell)
        row = QHBoxLayout(entry)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)
        self.kind = symbol_kind_combo(self.shell, "Variable")
        self.name = symbol_input(BINARY_WORKBENCH_TEXT.SYMBOL_NAME, self.shell)
        self.value = symbol_input(BINARY_WORKBENCH_TEXT.SYMBOL_VALUE, self.shell)
        add = symbol_button(BINARY_WORKBENCH_TEXT.SYMBOL_ADD, "preferences-ok", self.shell)
        add.setFixedSize(BINARY_WORKBENCH_LAYOUT.SYMBOL_ACTION_WIDTH, BINARY_WORKBENCH_LAYOUT.SYMBOL_INPUT_HEIGHT)
        add.clicked.connect(self._append_from_entry)
        row.addWidget(symbol_field(BINARY_WORKBENCH_TEXT.SYMBOL_TYPE, self.kind), 0)
        row.addWidget(symbol_field(BINARY_WORKBENCH_TEXT.SYMBOL_NAME, self.name), 0)
        row.addWidget(symbol_field(BINARY_WORKBENCH_TEXT.SYMBOL_VALUE, self.value), 0)
        row.addWidget(add, 0, Qt.AlignBottom)
        parent.addWidget(entry, 0, Qt.AlignLeft)

    def _build_scroll_body(self, parent: QVBoxLayout) -> None:
        self.scroll = QScrollArea(self.shell)
        self.scroll.setObjectName("workspace-table-body-scroll")
        self.scroll.verticalScrollBar().setObjectName("workspace-table-scrollbar")
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

    def _add_header(self, parent: QVBoxLayout) -> None:
        parent.addWidget(symbol_label(BINARY_WORKBENCH_TEXT.SYMBOLS_TITLE, "workspace-table-title", self.shell))
        parent.addWidget(symbol_label(BINARY_WORKBENCH_TEXT.SYMBOLS_SUBTITLE, "help-subtitle", self.shell))
