from pathlib import Path

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QDialog, QFileDialog, QFrame, QHBoxLayout, QScrollArea, QSizePolicy, QVBoxLayout, QWidget

from src.modules.binary_workbench_dtos import BinaryWorkbenchOffsetRegionDTO
from src.modules.utils import read_json, write_json
from src.presentation.repository.binary_workbench_workspace.payloads import offset_regions_from_payload, offset_regions_payload
from src.presentation.ui.components.binary_workbench.action_controls import (
    configure_binary_workbench_action,
    configure_binary_workbench_filter,
    configure_binary_workbench_input,
)
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_LAYOUT, BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.environment.offset_regions.rows import OffsetRegionsRowsMixin
from src.presentation.ui.components.binary_workbench.environment.symbols_dialog_widgets import symbol_input
from src.presentation.ui.components.binary_workbench.file_dialogs.lba_filesystem_widgets import lba_button, lba_input
from src.presentation.ui.components.binary_workbench.file_dialogs.constants import BINARY_WORKBENCH_FILE_DIALOG_TEXT
from src.presentation.ui.components.binary_workbench.input_validators import set_hex_value_validator
from src.presentation.ui.components.workspace_table.constants.layout import WORKSPACE_TABLE_SIZE


class BinaryWorkbenchOffsetRegionsDialog(OffsetRegionsRowsMixin, QDialog):
    directoryChanged = Signal(str)
    goToRequested = Signal(int)

    def __init__(self, regions: list[BinaryWorkbenchOffsetRegionDTO], directory: str, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("workspace-table-dialog")
        self.setWindowTitle(BINARY_WORKBENCH_TEXT.OFFSET_REGIONS)
        self.setFixedSize(BINARY_WORKBENCH_LAYOUT.OFFSET_REGIONS_DIALOG_WIDTH, BINARY_WORKBENCH_LAYOUT.OFFSET_REGIONS_DIALOG_HEIGHT)
        self._directory = directory
        self._saved_path = ""
        self._loaded_path = ""
        self._rows = []
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 30, 20, 20)
        root.setSpacing(BINARY_WORKBENCH_LAYOUT.LBA_FILESYSTEM_ACTION_SPACING)
        self._build_filter(root)
        self.shell = QFrame(self)
        self.shell.setObjectName("workspace-table-shell")
        layout = QVBoxLayout(self.shell)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(12)
        self._build_entry(layout)
        self._build_rows(layout, regions)
        root.addWidget(self.shell, 1)
        self._build_footer(root)

    def saved_path(self) -> str:
        return self._saved_path
    def loaded_path(self) -> str:
        return self._loaded_path
    def _build_filter(self, parent: QVBoxLayout) -> None:
        self.filter_input = symbol_input(
            BINARY_WORKBENCH_TEXT.FILTER,
            self,
            width=BINARY_WORKBENCH_LAYOUT.SHARED_FILTER_WIDTH,
            search_icon=True,
        )
        configure_binary_workbench_filter(self.filter_input)
        self.filter_input.textChanged.connect(self._apply_filter)
        parent.addWidget(self.filter_input, 0, Qt.AlignLeft)
    def _build_entry(self, parent: QVBoxLayout) -> None:
        entry = QWidget(self.shell)
        entry.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        row = QHBoxLayout(entry)
        row.setContentsMargins(0, 0, _delete_gutter_width(), 0)
        row.setSpacing(BINARY_WORKBENCH_LAYOUT.LBA_FILESYSTEM_FIELD_SPACING)
        self.name = lba_input(BINARY_WORKBENCH_TEXT.OFFSET_NAME, entry, width=BINARY_WORKBENCH_LAYOUT.OFFSET_REGIONS_FIELD_WIDTH)
        self.offset = lba_input(BINARY_WORKBENCH_TEXT.OFFSET_VALUE, entry, width=BINARY_WORKBENCH_LAYOUT.OFFSET_REGIONS_FIELD_WIDTH)
        set_hex_value_validator(self.offset)
        configure_binary_workbench_input(self.name, BINARY_WORKBENCH_LAYOUT.OFFSET_REGIONS_FIELD_WIDTH)
        configure_binary_workbench_input(self.offset, BINARY_WORKBENCH_LAYOUT.OFFSET_REGIONS_FIELD_WIDTH)
        add = lba_button(BINARY_WORKBENCH_TEXT.SYMBOL_ADD, "", entry)
        configure_binary_workbench_action(add)
        go_to_space = QWidget(entry)
        go_to_space.setFixedSize(
            BINARY_WORKBENCH_LAYOUT.SHARED_ACTION_WIDTH,
            BINARY_WORKBENCH_LAYOUT.SHARED_CONTROL_HEIGHT,
        )
        add.clicked.connect(self._append_from_entry)
        row.addWidget(self.name)
        row.addWidget(self.offset)
        row.addWidget(add)
        row.addWidget(go_to_space)
        parent.addWidget(entry)
    def _build_rows(self, parent: QVBoxLayout, regions: list[BinaryWorkbenchOffsetRegionDTO]) -> None:
        scroll = QScrollArea(self.shell)
        scroll.setObjectName("workspace-table-body-scroll")
        scroll.verticalScrollBar().setObjectName("workspace-table-scrollbar")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll_body = QWidget(scroll)
        scroll_body.setObjectName("workspace-table-body")
        scroll_layout = QHBoxLayout(scroll_body)
        scroll_layout.setContentsMargins(0, 10, BINARY_WORKBENCH_LAYOUT.ROW_DELETE_SCROLLBAR_MARGIN, 10)
        scroll_layout.setSpacing(BINARY_WORKBENCH_LAYOUT.ROW_DELETE_COLUMN_SPACING)
        self.body = QFrame(scroll_body)
        self.body.setObjectName("workspace-table-body")
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setSpacing(10)
        self.body_layout.setAlignment(Qt.AlignTop)
        self.remove_body = QFrame(scroll_body)
        self.remove_body.setObjectName("workspace-table-body")
        self.remove_layout = QVBoxLayout(self.remove_body)
        self.remove_layout.setContentsMargins(0, 0, 0, 0)
        self.remove_layout.setSpacing(10)
        self.remove_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        scroll_layout.addWidget(self.body, 1)
        scroll_layout.addWidget(self.remove_body, 0)
        scroll.setWidget(scroll_body)
        for region in regions:
            self._append_row(region.name, f"{region.offset:X}", region.details)
        parent.addWidget(scroll, 1)
    def _build_footer(self, parent: QVBoxLayout) -> None:
        footer = QWidget(self)
        row = QHBoxLayout(footer)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(BINARY_WORKBENCH_LAYOUT.LBA_FILESYSTEM_FIELD_SPACING)
        buttons = []
        for text, callback in ((BINARY_WORKBENCH_TEXT.LOAD, self._load), (BINARY_WORKBENCH_TEXT.OK, self.accept), (BINARY_WORKBENCH_TEXT.SAVE, self._save)):
            button = lba_button(text, "", footer)
            configure_binary_workbench_action(button)
            button.clicked.connect(callback)
            buttons.append(button)
        row.addWidget(buttons[0], 0, Qt.AlignLeft)
        row.addStretch(1)
        row.addWidget(buttons[1], 0, Qt.AlignCenter)
        row.addStretch(1)
        row.addWidget(buttons[2], 0, Qt.AlignRight)
        parent.addWidget(footer)

    def _load(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, BINARY_WORKBENCH_TEXT.OFFSET_REGIONS, self._directory, BINARY_WORKBENCH_FILE_DIALOG_TEXT.OFFSET_REGIONS_JSON_FILTER)
        if not path:
            return
        payload = read_json(Path(path))
        if not isinstance(payload, dict) or not isinstance(payload.get("regions"), list):
            return
        regions = offset_regions_from_payload(payload)
        self._clear_rows()
        for region in regions:
            self._append_row(region.name, f"{region.offset:X}", region.details)
        self._apply_filter()
        self._loaded_path = path
        self._remember_directory(Path(path))

    def _save(self) -> None:
        initial = str(Path(self._directory) / BINARY_WORKBENCH_FILE_DIALOG_TEXT.OFFSET_REGIONS_DEFAULT_FILENAME)
        path, _ = QFileDialog.getSaveFileName(self, BINARY_WORKBENCH_TEXT.OFFSET_REGIONS, initial, BINARY_WORKBENCH_FILE_DIALOG_TEXT.OFFSET_REGIONS_JSON_FILTER)
        if not path:
            return
        target = Path(path) if Path(path).suffix.lower() == ".json" else Path(path).with_suffix(".json")
        write_json(target, offset_regions_payload(target.stem, self.mappings()))
        self._saved_path = str(target)
        self._remember_directory(target)

    def _remember_directory(self, path: Path) -> None:
        self._directory = str(path.parent)
        self.directoryChanged.emit(self._directory)


def _delete_gutter_width() -> int:
    return (
        WORKSPACE_TABLE_SIZE.REMOVE_BUTTON_WIDTH
        + BINARY_WORKBENCH_LAYOUT.ROW_DELETE_COLUMN_SPACING
        + BINARY_WORKBENCH_LAYOUT.ROW_DELETE_SCROLLBAR_MARGIN
        + BINARY_WORKBENCH_LAYOUT.ROW_SCROLLBAR_RESERVED_WIDTH
    )
