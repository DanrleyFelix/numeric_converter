from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QMainWindow, QVBoxLayout, QWidget

from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_LAYOUT,
    BINARY_WORKBENCH_TEXT,
)
from src.presentation.ui.components.binary_workbench.toolbar import BinaryWorkbenchToolbar


class BinaryWorkbenchWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setObjectName("binary-workbench-window")
        self.setWindowTitle(BINARY_WORKBENCH_TEXT.TITLE)
        self.resize(
            BINARY_WORKBENCH_LAYOUT.WINDOW_WIDTH,
            BINARY_WORKBENCH_LAYOUT.WINDOW_HEIGHT,
        )

        self.toolbar = BinaryWorkbenchToolbar()
        self.toolbar.help_action.triggered.connect(
            lambda: self._set_status(BINARY_WORKBENCH_TEXT.HELP)
        )
        self._connect_placeholder_actions()

        self.status = QLabel(BINARY_WORKBENCH_TEXT.STATUS_IDLE)
        self.status.setObjectName("binary-workbench-subtitle")
        self.status.setWordWrap(True)

        title = QLabel(BINARY_WORKBENCH_TEXT.TITLE)
        title.setObjectName("binary-workbench-title")
        subtitle = QLabel(BINARY_WORKBENCH_TEXT.SUBTITLE)
        subtitle.setObjectName("binary-workbench-subtitle")
        subtitle.setWordWrap(True)

        shell = QWidget()
        shell.setObjectName("binary-workbench-shell")
        layout = QVBoxLayout(shell)
        layout.setContentsMargins(
            BINARY_WORKBENCH_LAYOUT.BODY_LEFT,
            BINARY_WORKBENCH_LAYOUT.BODY_TOP,
            BINARY_WORKBENCH_LAYOUT.BODY_RIGHT,
            BINARY_WORKBENCH_LAYOUT.BODY_BOTTOM,
        )
        layout.setSpacing(BINARY_WORKBENCH_LAYOUT.BODY_SPACING)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self.status)
        layout.addStretch(1)

        central = QWidget()
        layout_root = QVBoxLayout(central)
        layout_root.setContentsMargins(
            BINARY_WORKBENCH_LAYOUT.ROOT_LEFT,
            BINARY_WORKBENCH_LAYOUT.ROOT_TOP,
            BINARY_WORKBENCH_LAYOUT.ROOT_RIGHT,
            BINARY_WORKBENCH_LAYOUT.ROOT_BOTTOM,
        )
        layout_root.setSpacing(0)
        layout_root.addWidget(self.toolbar)
        layout_root.addWidget(shell, 1)
        self.setCentralWidget(central)

    def _connect_placeholder_actions(self) -> None:
        for action in (
            self.toolbar.open_binary_action,
            self.toolbar.open_assembly_action,
            self.toolbar.new_scratch_action,
            self.toolbar.open_internal_action,
            self.toolbar.symbols_action,
            self.toolbar.regions_action,
            self.toolbar.lba_filesystem_action,
            self.toolbar.labels_action,
            self.toolbar.encoding_tables_action,
            self.toolbar.bytes_formatter_action,
            self.toolbar.reference_offsets_action,
            self.toolbar.visible_columns_action,
            self.toolbar.hex_view_action,
            self.toolbar.go_to_action,
            self.toolbar.find_action,
            self.toolbar.replace_action,
            self.toolbar.select_block_action,
            self.toolbar.select_all_action,
        ):
            action.triggered.connect(lambda _, name=action.text(): self._set_status(name))

    def _set_status(self, action_name: str) -> None:
        self.status.setText(
            BINARY_WORKBENCH_TEXT.STATUS_PLACEHOLDER_TEMPLATE.format(name=action_name)
        )
