from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QFrame, QHBoxLayout, QScrollArea, QSizePolicy, QVBoxLayout, QWidget

from src.modules.binary_workbench_constants import (
    BINARY_WORKBENCH_DEFAULT_LBA_SECTOR_SIZE,
    BINARY_WORKBENCH_LBA_SECTOR_SIZE_OPTIONS,
)
from src.modules.binary_workbench_dtos import BinaryWorkbenchInternalFileDTO
from src.presentation.ui.components.binary_workbench.action_controls import (
    configure_binary_workbench_combo,
    configure_binary_workbench_dialog_action,
    configure_binary_workbench_line_edit,
)
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_LAYOUT, BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_DIALOG_LAYOUT as ENVIRONMENT_LAYOUT,
)
from src.presentation.ui.components.binary_workbench.file_dialogs.constants import (
    BINARY_WORKBENCH_FILE_DIALOG_TEXT,
)
from src.presentation.ui.components.binary_workbench.file_dialogs.lba_filesystem_widgets import (
    lba_button,
    lba_inline_field,
    lba_input,
)
from src.presentation.ui.components.binary_workbench.input_validators import (
    set_decimal_integer_validator,
    set_internal_file_name_validator,
)
from src.presentation.ui.components.workspace_table.constants.layout import WORKSPACE_TABLE_SIZE


class LbaFilesystemLayoutMixin:
    def _build_footer_actions(self, parent: QVBoxLayout) -> None:
        footer = QWidget(self.shell)
        footer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        row = QHBoxLayout(footer)
        row.setContentsMargins(
            ENVIRONMENT_LAYOUT.ZERO,
            ENVIRONMENT_LAYOUT.ZERO,
            _delete_gutter_width(),
            ENVIRONMENT_LAYOUT.ZERO,
        )
        row.setSpacing(ENVIRONMENT_LAYOUT.ZERO)
        load = lba_button(BINARY_WORKBENCH_FILE_DIALOG_TEXT.LOAD, "binary-workbench-lba-action", footer)
        save = lba_button(BINARY_WORKBENCH_FILE_DIALOG_TEXT.SAVE, "binary-workbench-lba-action", footer)
        ok = lba_button(BINARY_WORKBENCH_FILE_DIALOG_TEXT.OK, "binary-workbench-lba-action", footer)
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

    def _build_library_controls(
        self,
        parent: QVBoxLayout,
        _default_library_name: str,
        lba_sector_size: int,
    ) -> None:
        library = QWidget(self.shell)
        row = QHBoxLayout(library)
        row.setContentsMargins(*ENVIRONMENT_LAYOUT.EMPTY_MARGINS)
        row.setSpacing(BINARY_WORKBENCH_LAYOUT.LBA_FILESYSTEM_FIELD_SPACING)
        self.sector_size = QComboBox(library)
        self.sector_size.setObjectName("binary-workbench-dialog-input")
        self.sector_size.addItems(
            [f"{value} bytes" for value in BINARY_WORKBENCH_LBA_SECTOR_SIZE_OPTIONS]
        )
        selected_sector_size = (
            lba_sector_size
            if lba_sector_size in BINARY_WORKBENCH_LBA_SECTOR_SIZE_OPTIONS
            else BINARY_WORKBENCH_DEFAULT_LBA_SECTOR_SIZE
        )
        self.sector_size.setCurrentText(f"{selected_sector_size} bytes")
        configure_binary_workbench_combo(
            self.sector_size,
            BINARY_WORKBENCH_LAYOUT.SHARED_INPUT_WIDTH,
        )
        row.addWidget(lba_inline_field(BINARY_WORKBENCH_FILE_DIALOG_TEXT.LBA_SECTOR_LABEL, self.sector_size), 0)
        parent.addWidget(library, 0, Qt.AlignLeft)

    def _build_entry(self, parent: QVBoxLayout) -> None:
        entry = QWidget(self.shell)
        entry.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        row = QHBoxLayout(entry)
        row.setContentsMargins(
            ENVIRONMENT_LAYOUT.ZERO,
            ENVIRONMENT_LAYOUT.ZERO,
            _delete_gutter_width(),
            ENVIRONMENT_LAYOUT.ZERO,
        )
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
        configure_binary_workbench_line_edit(self.name)
        configure_binary_workbench_line_edit(self.lba)
        set_internal_file_name_validator(self.name)
        set_decimal_integer_validator(self.lba)
        add = lba_button(BINARY_WORKBENCH_TEXT.SYMBOL_ADD, "binary-workbench-lba-action", self.shell)
        configure_binary_workbench_dialog_action(add)
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
            ENVIRONMENT_LAYOUT.ZERO,
            ENVIRONMENT_LAYOUT.SCROLL_VERTICAL_MARGIN,
            BINARY_WORKBENCH_LAYOUT.ROW_DELETE_SCROLLBAR_MARGIN,
            ENVIRONMENT_LAYOUT.SCROLL_VERTICAL_MARGIN,
        )
        scroll_layout.setSpacing(BINARY_WORKBENCH_LAYOUT.ROW_DELETE_COLUMN_SPACING)
        self.body = QFrame(self.scroll_body)
        self.body.setObjectName("workspace-table-body")
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(*ENVIRONMENT_LAYOUT.EMPTY_MARGINS)
        self.body_layout.setSpacing(ENVIRONMENT_LAYOUT.ROW_SPACING)
        self.body_layout.setAlignment(Qt.AlignTop)
        self.remove_body = QFrame(self.scroll_body)
        self.remove_body.setObjectName("workspace-table-body")
        self.remove_layout = QVBoxLayout(self.remove_body)
        self.remove_layout.setContentsMargins(*ENVIRONMENT_LAYOUT.EMPTY_MARGINS)
        self.remove_layout.setSpacing(ENVIRONMENT_LAYOUT.ROW_SPACING)
        self.remove_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        scroll_layout.addWidget(self.body, 1)
        scroll_layout.addWidget(self.remove_body, 0)
        self.scroll.setWidget(self.scroll_body)
        for item in internal_files:
            self._append_row(item.name, str(item.start_lba))
        parent.addWidget(self.scroll, 1)


def _delete_gutter_width() -> int:
    return (
        WORKSPACE_TABLE_SIZE.REMOVE_GUTTER_WIDTH
        + BINARY_WORKBENCH_LAYOUT.ROW_DELETE_COLUMN_SPACING
        + BINARY_WORKBENCH_LAYOUT.ROW_DELETE_SCROLLBAR_MARGIN
        + BINARY_WORKBENCH_LAYOUT.ROW_SCROLLBAR_RESERVED_WIDTH
    )
