from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QFrame, QHBoxLayout, QScrollArea, QSizePolicy, QVBoxLayout, QWidget

from src.modules.dtos import BinaryWorkbenchInternalFileDTO
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_LAYOUT, BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.file_dialogs.constants import (
    BINARY_WORKBENCH_FILE_DIALOG_TEXT,
)
from src.presentation.ui.components.binary_workbench.file_dialogs.lba_filesystem_widgets import (
    lba_button,
    lba_inline_field,
    lba_input,
    size_lba_action,
    size_lba_input,
)
from src.presentation.ui.components.binary_workbench.input_validators import (
    set_decimal_integer_validator,
    set_python_identifier_validator,
)
from src.presentation.ui.components.workspace_table.constants.layout import WORKSPACE_TABLE_SIZE


class LbaFilesystemLayoutMixin:
    def _build_footer_actions(self, parent: QVBoxLayout) -> None:
        footer = QWidget(self.shell)
        footer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        row = QHBoxLayout(footer)
        row.setContentsMargins(0, 0, _delete_gutter_width(), 0)
        row.setSpacing(BINARY_WORKBENCH_LAYOUT.LBA_FILESYSTEM_FIELD_SPACING)
        load = lba_button(BINARY_WORKBENCH_FILE_DIALOG_TEXT.LOAD, "binary-workbench-lba-action", footer)
        save = lba_button(BINARY_WORKBENCH_FILE_DIALOG_TEXT.SAVE, "binary-workbench-lba-action", footer)
        ok = lba_button(BINARY_WORKBENCH_FILE_DIALOG_TEXT.OK, "binary-workbench-lba-action", footer)
        for button in (load, save, ok):
            size_lba_action(button, BINARY_WORKBENCH_LAYOUT.LBA_FILESYSTEM_ACTION_WIDTH, expanding=True)
        load.clicked.connect(self._load_library_json_dialog)
        save.clicked.connect(self._save_library_json_dialog)
        ok.clicked.connect(self.accept)
        row.addWidget(load, 1)
        row.addWidget(ok, 1)
        row.addWidget(save, 1)
        parent.addWidget(footer, 0)

    def _build_library_controls(
        self,
        parent: QVBoxLayout,
        _default_library_name: str,
        lba_sector_size: int,
    ) -> None:
        library = QWidget(self.shell)
        row = QHBoxLayout(library)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(BINARY_WORKBENCH_LAYOUT.LBA_FILESYSTEM_FIELD_SPACING)
        self.sector_size = QComboBox(library)
        self.sector_size.setObjectName("binary-workbench-dialog-input")
        self.sector_size.addItems(["2048 bytes", "2334 bytes", "2352 bytes"])
        self.sector_size.setCurrentText(f"{lba_sector_size if lba_sector_size in {2048, 2334, 2352} else 2352} bytes")
        size_lba_input(self.sector_size)
        row.addWidget(lba_inline_field(BINARY_WORKBENCH_FILE_DIALOG_TEXT.LBA_SECTOR_LABEL, self.sector_size), 0)
        parent.addWidget(library, 0, Qt.AlignLeft)

    def _build_entry(self, parent: QVBoxLayout) -> None:
        entry = QWidget(self.shell)
        entry.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        row = QHBoxLayout(entry)
        row.setContentsMargins(0, 0, _delete_gutter_width(), 0)
        row.setSpacing(BINARY_WORKBENCH_LAYOUT.LBA_FILESYSTEM_FIELD_SPACING)
        self.name = lba_input(
            BINARY_WORKBENCH_TEXT.LBA_FILE_NAME,
            self.shell,
            width=BINARY_WORKBENCH_LAYOUT.LBA_FILESYSTEM_NAME_WIDTH,
            expanding=True,
        )
        self.lba = lba_input(
            BINARY_WORKBENCH_TEXT.LBA_START,
            self.shell,
            width=BINARY_WORKBENCH_LAYOUT.LBA_FILESYSTEM_START_WIDTH,
            expanding=True,
        )
        set_python_identifier_validator(self.name)
        set_decimal_integer_validator(self.lba)
        add = lba_button(BINARY_WORKBENCH_TEXT.SYMBOL_ADD, "binary-workbench-lba-action", self.shell)
        size_lba_action(add, BINARY_WORKBENCH_LAYOUT.LBA_FILESYSTEM_ACTION_WIDTH, expanding=True)
        add.clicked.connect(self._append_from_entry)
        row.addWidget(self.name, 1)
        row.addWidget(self.lba, 1)
        row.addWidget(add, 1, Qt.AlignVCenter)
        parent.addWidget(entry, 0)

    def _build_rows(self, parent: QVBoxLayout, internal_files: list[BinaryWorkbenchInternalFileDTO]) -> None:
        self.scroll = QScrollArea(self.shell)
        self.scroll.setObjectName("workspace-table-body-scroll")
        self.scroll.verticalScrollBar().setObjectName("workspace-table-scrollbar")
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
        for item in internal_files:
            self._append_row(item.name, str(item.start_lba))
        parent.addWidget(self.scroll, 1)


def _delete_gutter_width() -> int:
    return (
        WORKSPACE_TABLE_SIZE.REMOVE_BUTTON_WIDTH
        + BINARY_WORKBENCH_LAYOUT.ROW_DELETE_COLUMN_SPACING
        + BINARY_WORKBENCH_LAYOUT.ROW_DELETE_SCROLLBAR_MARGIN
        + BINARY_WORKBENCH_LAYOUT.ROW_SCROLLBAR_RESERVED_WIDTH
    )
