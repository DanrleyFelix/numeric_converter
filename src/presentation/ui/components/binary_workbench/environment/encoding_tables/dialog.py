from pathlib import Path

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QDialog, QFileDialog, QPushButton, QVBoxLayout

from src.core.binary_workbench.encoding_tables import (
    encoding_table_conflicts,
    encoding_table_from_payload,
)
from src.modules.binary_workbench_constants import BINARY_WORKBENCH_ANSI_TABLE_NAME
from src.modules.binary_workbench_dtos import BinaryWorkbenchEncodingTableDTO
from src.modules.utils import read_json
from src.presentation.ui.components.binary_workbench.action_controls import (
    configure_binary_workbench_dialog_action,
)
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_DIALOG_LAYOUT,
    BINARY_WORKBENCH_TEXT,
)
from src.presentation.ui.components.binary_workbench.environment.encoding_tables.constants import (
    ENCODING_TABLES_SIZE,
    ENCODING_TABLES_SPACING,
    ENCODING_TABLES_TIMING,
)
from src.presentation.ui.components.binary_workbench.environment.encoding_tables.list_view import EncodingTablesList
from src.presentation.ui.components.binary_workbench.file_dialogs.constants import BINARY_WORKBENCH_FILE_DIALOG_TEXT


class BinaryWorkbenchEncodingTablesDialog(QDialog):
    def __init__(self, tables: list[BinaryWorkbenchEncodingTableDTO], enabled: list[str], directory: str, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("preferences-dialog")
        self.setWindowTitle(BINARY_WORKBENCH_TEXT.ENCODING_TABLES)
        self.setFixedSize(
            ENCODING_TABLES_SIZE.DIALOG_WIDTH,
            ENCODING_TABLES_SIZE.DIALOG_HEIGHT,
        )
        self._tables = {table.name: table for table in tables}
        self._enabled: list[str] = []
        for name in enabled:
            if name != BINARY_WORKBENCH_ANSI_TABLE_NAME and name not in self._tables:
                continue
            if not encoding_table_conflicts(name, self._enabled, list(self._tables.values())):
                self._enabled.append(name)
        self._directory = directory
        self._loaded_paths: list[Path] = []
        self._items = {}
        self._conflict_generation: dict[str, int] = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(*BINARY_WORKBENCH_DIALOG_LAYOUT.CONTENT_MARGINS)
        layout.setSpacing(ENCODING_TABLES_SPACING.CONTROL)
        load = QPushButton(BINARY_WORKBENCH_TEXT.LOAD_TABLE, self)
        configure_binary_workbench_dialog_action(load)
        load.clicked.connect(self._load_table)
        layout.addWidget(load, 0, Qt.AlignHCenter)
        self.tables_list = EncodingTablesList(self)
        self.tables_list.itemClicked.connect(lambda item: self._toggle(item.text()))
        layout.addWidget(self.tables_list, 1)
        self._rebuild_items()

    def tables(self) -> list[BinaryWorkbenchEncodingTableDTO]:
        return list(self._tables.values())

    def enabled_names(self) -> list[str]:
        return list(self._enabled)

    def directory(self) -> str:
        return self._directory

    def loaded_paths(self) -> list[Path]:
        return list(self._loaded_paths)

    def _load_table(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, BINARY_WORKBENCH_TEXT.ENCODING_TABLES, self._directory, BINARY_WORKBENCH_FILE_DIALOG_TEXT.ENCODING_TABLE_JSON_FILTER)
        if not path:
            return
        source = Path(path)
        table = encoding_table_from_payload(read_json(source), source.stem)
        if table is None or table.name == BINARY_WORKBENCH_ANSI_TABLE_NAME:
            return
        self._directory = str(source.parent)
        self._loaded_paths.append(source)
        self._tables[table.name] = table
        self._enabled = [name for name in self._enabled if name != table.name]
        self._rebuild_items()

    def _rebuild_items(self) -> None:
        self.tables_list.clear()
        self._items.clear()
        for name in [BINARY_WORKBENCH_ANSI_TABLE_NAME, *self._tables]:
            self._items[name] = self.tables_list.append_table(name, name in self._enabled)

    def _toggle(self, name: str) -> None:
        if name in self._enabled:
            self._enabled.remove(name)
            self._sync_item(name)
            return
        if encoding_table_conflicts(name, self._enabled, self.tables()):
            self._show_conflict(name)
            return
        self._enabled.append(name)
        self._sync_item(name)

    def _sync_item(self, name: str) -> None:
        self._items[name].setSelected(name in self._enabled)

    def _show_conflict(self, name: str) -> None:
        item = self._items[name]
        generation = self._conflict_generation.get(name, 0) + 1
        self._conflict_generation[name] = generation
        self.tables_list.set_conflict(item, True)
        QTimer.singleShot(
            ENCODING_TABLES_TIMING.CONFLICT_MS,
            lambda: self._clear_conflict(name, generation),
        )

    def _clear_conflict(self, name: str, generation: int) -> None:
        if self._conflict_generation.get(name) != generation or name not in self._items:
            return
        self.tables_list.set_conflict(self._items[name], False)
        self._sync_item(name)
