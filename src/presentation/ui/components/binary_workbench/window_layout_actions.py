from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QWidget

from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_LAYOUT,
    BINARY_WORKBENCH_TEXT,
    BINARY_WORKBENCH_TIMING,
)


class BinaryWorkbenchWindowLayoutMixin:
    def _connect_actions(self) -> None:
        self.toolbar.open_file_action.triggered.connect(self._open_any_file)
        self.toolbar.new_scratch_action.triggered.connect(self.tabs.new_scratch_tab)
        self.toolbar.open_internal_action.triggered.connect(self._open_internal_file)
        self.toolbar.create_version_action.triggered.connect(self._create_version)
        self.toolbar.att_current_version_action.triggered.connect(self._update_version)
        self.toolbar.load_version_action.triggered.connect(self._load_version)
        self.toolbar.save_binary_file_action.triggered.connect(self._save_current_tab)
        self.toolbar.lba_filesystem_action.triggered.connect(self._open_lba_filesystem)
        self.toolbar.symbols_action.triggered.connect(self._open_symbols)
        self.toolbar.labels_action.triggered.connect(self._open_labels)
        self.toolbar.bytes_formatter_action.triggered.connect(self._open_bytes_formatter)
        self.toolbar.reference_offsets_action.triggered.connect(self._open_reference_offsets)
        self.toolbar.go_to_action.triggered.connect(self._open_go_to)
        self.toolbar.find_action.triggered.connect(self._open_find)
        self.toolbar.select_block_action.triggered.connect(self._open_select_block)
        self.toolbar.select_all_action.triggered.connect(self.tabs.select_all_content)
        self.addActions([
            self.toolbar.go_to_action,
            self.toolbar.find_action,
            self.toolbar.select_block_action,
            self.toolbar.select_all_action,
            self.toolbar.open_file_action,
            self.toolbar.new_scratch_action,
            self.toolbar.save_binary_file_action,
        ])
        self.toolbar.advanced_configuration_action.triggered.connect(self._open_advanced_configuration)
        for action in self._placeholder_actions():
            action.triggered.connect(lambda _, name=action.text(): self._show_status(BINARY_WORKBENCH_TEXT.STATUS_PLACEHOLDER_TEMPLATE.format(name=name), BINARY_WORKBENCH_TIMING.STATUS_MESSAGE_VISIBLE_MS))

    def _build_ui(self) -> None:
        shell = QWidget()
        shell.setObjectName("binary-workbench-shell")
        layout = QVBoxLayout(shell)
        layout.setContentsMargins(BINARY_WORKBENCH_LAYOUT.BODY_LEFT, BINARY_WORKBENCH_LAYOUT.BODY_TOP, BINARY_WORKBENCH_LAYOUT.BODY_RIGHT, BINARY_WORKBENCH_LAYOUT.BODY_BOTTOM)
        layout.setSpacing(BINARY_WORKBENCH_LAYOUT.STATUS_TOP_MARGIN)
        layout.addWidget(self.tabs, 1)
        layout.addWidget(self.footer_status, 0, Qt.AlignLeft)
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self.toolbar)
        root.addWidget(shell, 1)
        self.setCentralWidget(central)
