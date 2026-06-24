from pathlib import Path

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QDialog, QFileDialog, QFrame, QPushButton, QScrollArea, QVBoxLayout, QWidget

from src.core.binary_workbench.encoding_tables import (
    encoding_table_conflicts,
    encoding_table_from_payload,
)
from src.modules.binary_workbench_constants import BINARY_WORKBENCH_ANSI_TABLE_NAME
from src.modules.binary_workbench_dtos import BinaryWorkbenchEncodingTableDTO
from src.modules.utils import read_json
from src.presentation.ui.components.binary_workbench.action_controls import (
    configure_binary_workbench_dialog_action,
    configure_binary_workbench_dialog_button,
)
from src.presentation.ui.components.binary_workbench.constant_groups.layout import BINARY_WORKBENCH_LAYOUT
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_DIALOG_LAYOUT,
    BINARY_WORKBENCH_TEXT,
)
from src.presentation.ui.components.binary_workbench.environment.encoding_tables.constants import (
    ENCODING_TABLES_SIZE,
    ENCODING_TABLES_SPACING,
    ENCODING_TABLES_TIMING,
)
from src.presentation.ui.components.binary_workbench.environment.encoding_tables.constants.layout import BODY_MARGINS
from src.presentation.ui.components.binary_workbench.file_dialogs.constants import BINARY_WORKBENCH_FILE_DIALOG_TEXT
from src.presentation.ui.helpers.load_qss import THEME_TOKENS


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
        self._buttons: dict[str, QPushButton] = {}
        self._conflict_generation: dict[str, int] = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(*BINARY_WORKBENCH_DIALOG_LAYOUT.CONTENT_MARGINS)
        layout.setSpacing(ENCODING_TABLES_SPACING.CONTROL)
        load = QPushButton(BINARY_WORKBENCH_TEXT.LOAD_TABLE, self)
        configure_binary_workbench_dialog_action(load)
        load.clicked.connect(self._load_table)
        layout.addWidget(load, 0, Qt.AlignHCenter)
        scroll = QScrollArea(self)
        scroll.setObjectName("binary-workbench-version-scroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        self._body = QWidget(scroll)
        self._body.setObjectName("binary-workbench-version-list")
        self._body.setContentsMargins(BODY_MARGINS.LEFT, BODY_MARGINS.TOP, BODY_MARGINS.RIGHT, BODY_MARGINS.BOTTOM)
        self._body_layout = QVBoxLayout(self._body)
        self._body_layout.setContentsMargins(*BINARY_WORKBENCH_DIALOG_LAYOUT.EMPTY_MARGINS)
        self._body_layout.setSpacing(ENCODING_TABLES_SPACING.CONTROL)
        self._body_layout.setAlignment(Qt.AlignTop)
        scroll.setWidget(self._body)
        layout.addWidget(scroll, 1)
        self._rebuild_buttons()

    def tables(self) -> list[BinaryWorkbenchEncodingTableDTO]:
        return list(self._tables.values())

    def enabled_names(self) -> list[str]:
        return list(self._enabled)

    def directory(self) -> str:
        return self._directory

    def _load_table(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, BINARY_WORKBENCH_TEXT.ENCODING_TABLES, self._directory, BINARY_WORKBENCH_FILE_DIALOG_TEXT.ENCODING_TABLE_JSON_FILTER)
        if not path:
            return
        source = Path(path)
        table = encoding_table_from_payload(read_json(source), source.stem)
        if table is None or table.name == BINARY_WORKBENCH_ANSI_TABLE_NAME:
            return
        self._directory = str(source.parent)
        self._tables[table.name] = table
        self._enabled = [name for name in self._enabled if name != table.name]
        self._rebuild_buttons()

    def _rebuild_buttons(self) -> None:
        while self._body_layout.count():
            item = self._body_layout.takeAt(0)
            if widget := item.widget():
                widget.deleteLater()
        self._buttons.clear()
        for name in [BINARY_WORKBENCH_ANSI_TABLE_NAME, *self._tables]:
            button = QPushButton(name, self._body)
            button.setCursor(Qt.PointingHandCursor)
            button.setFocusPolicy(Qt.NoFocus)
            button.setFixedHeight(BINARY_WORKBENCH_LAYOUT.SHARED_CONTROL_HEIGHT)
            configure_binary_workbench_dialog_button(button)
            button.clicked.connect(lambda _, table_name=name: self._toggle(table_name))
            self._buttons[name] = button
            self._sync_button(name)
            self._body_layout.addWidget(button)

    def _toggle(self, name: str) -> None:
        if name in self._enabled:
            self._enabled.remove(name)
            self._sync_button(name)
            return
        if encoding_table_conflicts(name, self._enabled, self.tables()):
            self._show_conflict(name)
            return
        self._enabled.append(name)
        self._sync_button(name)

    def _sync_button(self, name: str) -> None:
        button = self._buttons[name]
        button.setObjectName("binary-workbench-version-active" if name in self._enabled else "binary-workbench-version-item")
        button.style().unpolish(button)
        button.style().polish(button)

    def _show_conflict(self, name: str) -> None:
        button = self._buttons[name]
        generation = self._conflict_generation.get(name, 0) + 1
        self._conflict_generation[name] = generation
        button.setStyleSheet(f"border: 1px solid {THEME_TOKENS['border-danger']};")
        QTimer.singleShot(
            ENCODING_TABLES_TIMING.CONFLICT_MS,
            lambda: self._clear_conflict(name, generation),
        )

    def _clear_conflict(self, name: str, generation: int) -> None:
        if self._conflict_generation.get(name) != generation or name not in self._buttons:
            return
        self._buttons[name].setStyleSheet("")
        self._sync_button(name)
