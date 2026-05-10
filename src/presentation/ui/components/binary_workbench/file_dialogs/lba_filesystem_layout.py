from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QFrame, QHBoxLayout, QScrollArea, QVBoxLayout, QWidget

from src.modules.dtos import BinaryWorkbenchInternalFileDTO
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_LAYOUT, BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.file_dialogs.constants import (
    BINARY_WORKBENCH_FILE_DIALOG_TEXT,
)
from src.presentation.ui.components.binary_workbench.file_dialogs.lba_filesystem_widgets import (
    lba_button,
    lba_field,
    lba_input,
    size_lba_input,
)


class LbaFilesystemLayoutMixin:
    def _build_footer_actions(self, parent: QVBoxLayout) -> None:
        footer = QWidget(self.shell)
        row = QHBoxLayout(footer)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(14)
        row.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        load = lba_button(BINARY_WORKBENCH_FILE_DIALOG_TEXT.LOAD, "preferences-cancel", footer)
        save = lba_button(BINARY_WORKBENCH_FILE_DIALOG_TEXT.SAVE, "preferences-ok", footer)
        ok = lba_button(BINARY_WORKBENCH_FILE_DIALOG_TEXT.OK, "preferences-ok", footer)
        for button in (load, save, ok):
            button.setFixedSize(BINARY_WORKBENCH_LAYOUT.SYMBOL_ACTION_WIDTH, BINARY_WORKBENCH_LAYOUT.SYMBOL_INPUT_HEIGHT)
        load.clicked.connect(self._load_library_json_dialog)
        save.clicked.connect(self._save_library_json_dialog)
        ok.clicked.connect(self.accept)
        row.addWidget(load, 0, Qt.AlignLeft | Qt.AlignVCenter)
        row.addWidget(save, 0, Qt.AlignLeft | Qt.AlignVCenter)
        row.addWidget(ok, 0, Qt.AlignLeft | Qt.AlignVCenter)
        parent.addWidget(footer, 0)

    def _build_library_controls(
        self,
        parent: QVBoxLayout,
        default_library_name: str,
        lba_sector_size: int,
    ) -> None:
        library = QWidget(self.shell)
        row = QHBoxLayout(library)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)
        self.library_name_input = lba_input(
            BINARY_WORKBENCH_FILE_DIALOG_TEXT.LBA_LIBRARY_NAME_LABEL,
            library,
            default_library_name,
            BINARY_WORKBENCH_LAYOUT.LBA_LIBRARY_NAME_WIDTH,
        )
        self.sector_size = QComboBox(library)
        self.sector_size.setObjectName("binary-workbench-dialog-input")
        self.sector_size.addItems(["2048 bytes", "2334 bytes", "2352 bytes"])
        self.sector_size.setCurrentText(f"{lba_sector_size if lba_sector_size in {2048, 2334, 2352} else 2352} bytes")
        size_lba_input(self.sector_size)
        row.addWidget(lba_field(BINARY_WORKBENCH_FILE_DIALOG_TEXT.LBA_LIBRARY_NAME_LABEL, self.library_name_input), 0)
        row.addWidget(lba_field(BINARY_WORKBENCH_FILE_DIALOG_TEXT.LBA_SECTOR_LABEL, self.sector_size), 0)
        parent.addWidget(library, 0, Qt.AlignLeft)

    def _build_entry(self, parent: QVBoxLayout) -> None:
        entry = QWidget(self.shell)
        row = QHBoxLayout(entry)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)
        self.name = lba_input(BINARY_WORKBENCH_TEXT.LBA_FILE_NAME, self.shell)
        self.lba = lba_input(BINARY_WORKBENCH_TEXT.LBA_START, self.shell)
        add = lba_button(BINARY_WORKBENCH_TEXT.SYMBOL_ADD, "preferences-ok", self.shell)
        add.setFixedSize(BINARY_WORKBENCH_LAYOUT.SYMBOL_ACTION_WIDTH, BINARY_WORKBENCH_LAYOUT.SYMBOL_INPUT_HEIGHT)
        add.clicked.connect(self._append_from_entry)
        row.addWidget(lba_field(BINARY_WORKBENCH_TEXT.LBA_FILE_NAME, self.name), 0)
        row.addWidget(lba_field(BINARY_WORKBENCH_TEXT.LBA_START, self.lba), 0)
        row.addWidget(add, 0, Qt.AlignBottom)
        parent.addWidget(entry, 0, Qt.AlignLeft)

    def _build_rows(self, parent: QVBoxLayout, internal_files: list[BinaryWorkbenchInternalFileDTO]) -> None:
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
        for item in internal_files:
            self._append_row(item.name, str(item.start_lba))
        parent.addWidget(self.scroll, 1)
