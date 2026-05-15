from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QDialog, QFrame, QHBoxLayout, QLineEdit, QScrollArea, QVBoxLayout, QWidget

from src.modules.dtos import BinaryWorkbenchMemoryRegionDTO
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_LAYOUT,
    BINARY_WORKBENCH_TEXT,
)
from src.presentation.ui.components.binary_workbench.file_dialogs.constants import (
    BINARY_WORKBENCH_FILE_DIALOG_TEXT,
)
from src.presentation.ui.components.binary_workbench.file_dialogs.lba_filesystem_widgets import (
    lba_button,
    lba_field,
    lba_input,
    lba_label,
)
from src.presentation.ui.components.binary_workbench.file_dialogs.memory_regions_json import (
    MemoryRegionsJsonMixin,
)
from src.presentation.ui.components.binary_workbench.file_dialogs.memory_regions_rows import (
    MemoryRegionsRowsMixin,
)


class BinaryWorkbenchMemoryRegionsDialog(
    MemoryRegionsJsonMixin,
    MemoryRegionsRowsMixin,
    QDialog,
):
    directoryChanged = Signal(str)

    def __init__(
        self,
        regions: list[BinaryWorkbenchMemoryRegionDTO],
        default_directory: str = "",
        parent=None,
    ) -> None:
        if parent is None and default_directory and not isinstance(default_directory, str):
            parent = default_directory
            default_directory = ""
        super().__init__(parent)
        self.setObjectName("workspace-table-dialog")
        self.setWindowTitle(BINARY_WORKBENCH_FILE_DIALOG_TEXT.MEMORY_REGIONS_TITLE)
        self.setMinimumSize(
            BINARY_WORKBENCH_LAYOUT.LBA_DIALOG_MIN_WIDTH,
            BINARY_WORKBENCH_LAYOUT.FILE_DIALOG_MIN_HEIGHT,
        )
        self.resize(BINARY_WORKBENCH_LAYOUT.LBA_DIALOG_WIDTH, BINARY_WORKBENCH_LAYOUT.FILE_DIALOG_HEIGHT)
        self._directory = default_directory
        self._json_path = ""
        self._rows: list[tuple[QLineEdit, QLineEdit, QLineEdit, QWidget]] = []
        self._build_dialog(regions)

    def json_path(self) -> str:
        return self._json_path

    def _build_dialog(self, regions: list[BinaryWorkbenchMemoryRegionDTO]) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 30, 20, 20)
        self.shell = QFrame(self)
        self.shell.setObjectName("workspace-table-shell")
        shell_layout = QVBoxLayout(self.shell)
        shell_layout.setContentsMargins(20, 20, 20, 16)
        shell_layout.setSpacing(12)
        self._add_header(shell_layout)
        self._build_entry(shell_layout)
        self._build_rows(shell_layout, regions)
        self.status = lba_label("", "help-subtitle", self.shell)
        self.status.setWordWrap(True)
        shell_layout.addWidget(self.status)
        self._build_footer(shell_layout)
        layout.addWidget(self.shell, 1)

    def _add_header(self, parent: QVBoxLayout) -> None:
        title = lba_label(BINARY_WORKBENCH_FILE_DIALOG_TEXT.MEMORY_REGIONS_TITLE, "workspace-table-title", self.shell)
        subtitle = lba_label(BINARY_WORKBENCH_FILE_DIALOG_TEXT.MEMORY_REGIONS_SUBTITLE, "help-subtitle", self.shell)
        subtitle.setWordWrap(True)
        parent.addWidget(title)
        parent.addWidget(subtitle)

    def _build_entry(self, parent: QVBoxLayout) -> None:
        entry = QWidget(self.shell)
        row = QHBoxLayout(entry)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)
        self.name = lba_input(BINARY_WORKBENCH_FILE_DIALOG_TEXT.MEMORY_REGION_NAME_LABEL, self.shell)
        self.start = lba_input(BINARY_WORKBENCH_FILE_DIALOG_TEXT.MEMORY_REGION_START_LABEL, self.shell)
        self.end = lba_input(BINARY_WORKBENCH_FILE_DIALOG_TEXT.MEMORY_REGION_END_LABEL, self.shell)
        add = lba_button(BINARY_WORKBENCH_TEXT.SYMBOL_ADD, "preferences-ok", self.shell)
        add.setFixedSize(BINARY_WORKBENCH_LAYOUT.SYMBOL_ADD_ACTION_WIDTH, BINARY_WORKBENCH_LAYOUT.SYMBOL_INPUT_HEIGHT)
        add.clicked.connect(self._append_from_entry)
        row.addWidget(lba_field(BINARY_WORKBENCH_FILE_DIALOG_TEXT.MEMORY_REGION_NAME_LABEL, self.name), 0)
        row.addWidget(lba_field(BINARY_WORKBENCH_FILE_DIALOG_TEXT.MEMORY_REGION_START_LABEL, self.start), 0)
        row.addWidget(lba_field(BINARY_WORKBENCH_FILE_DIALOG_TEXT.MEMORY_REGION_END_LABEL, self.end), 0)
        row.addWidget(add, 0, Qt.AlignBottom)
        parent.addWidget(entry, 0, Qt.AlignLeft)

    def _build_rows(self, parent: QVBoxLayout, regions: list[BinaryWorkbenchMemoryRegionDTO]) -> None:
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
        for region in regions:
            self._append_row(region.name, str(region.start_offset), str(region.end_offset))
        parent.addWidget(self.scroll, 1)

    def _build_footer(self, parent: QVBoxLayout) -> None:
        footer = QWidget(self.shell)
        row = QHBoxLayout(footer)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(14)
        for text, callback, object_name in (
            (BINARY_WORKBENCH_FILE_DIALOG_TEXT.LOAD, self._load_dialog, "preferences-cancel"),
            (BINARY_WORKBENCH_FILE_DIALOG_TEXT.SAVE, self._save_dialog, "preferences-ok"),
            (BINARY_WORKBENCH_FILE_DIALOG_TEXT.OK, self.accept, "preferences-ok"),
        ):
            button = lba_button(text, object_name, footer)
            button.setFixedSize(
                BINARY_WORKBENCH_LAYOUT.SYMBOL_ACTION_WIDTH,
                BINARY_WORKBENCH_LAYOUT.SYMBOL_INPUT_HEIGHT,
            )
            button.clicked.connect(callback)
            row.addWidget(button, 0, Qt.AlignLeft | Qt.AlignVCenter)
        parent.addWidget(footer, 0)
