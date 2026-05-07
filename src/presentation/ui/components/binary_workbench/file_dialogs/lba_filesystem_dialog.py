from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea, QVBoxLayout, QWidget

from src.modules.dtos import BinaryWorkbenchInternalFileDTO
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_LAYOUT, BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.file_dialogs.constants import (
    BINARY_WORKBENCH_FILE_DIALOG_TEXT,
)
from src.presentation.ui.components.workspace_table.constants.layout import WORKSPACE_TABLE_SIZE
from src.presentation.ui.design.icons import Icons


class BinaryWorkbenchLbaFilesystemDialog(QDialog):
    def __init__(self, internal_files: list[BinaryWorkbenchInternalFileDTO], parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("workspace-table-dialog")
        self.setWindowTitle(BINARY_WORKBENCH_FILE_DIALOG_TEXT.LBA_TITLE)
        self.setMinimumSize(720, 420)
        self.resize(860, 520)
        self._rows: list[tuple[QLineEdit, QLineEdit, QWidget]] = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 30, 20, 20)
        self.shell = QFrame(self)
        self.shell.setObjectName("workspace-table-shell")
        shell_layout = QVBoxLayout(self.shell)
        shell_layout.setContentsMargins(20, 20, 20, 16)
        shell_layout.setSpacing(12)
        shell_layout.addWidget(_label(BINARY_WORKBENCH_FILE_DIALOG_TEXT.LBA_TITLE, "workspace-table-title", self.shell))
        subtitle = _label(BINARY_WORKBENCH_FILE_DIALOG_TEXT.LBA_SUBTITLE, "help-subtitle", self.shell)
        subtitle.setWordWrap(True)
        shell_layout.addWidget(subtitle)
        self._build_entry(shell_layout)
        self._build_rows(shell_layout, internal_files)
        ok = QPushButton(BINARY_WORKBENCH_FILE_DIALOG_TEXT.OK, self.shell)
        ok.setObjectName("preferences-ok")
        ok.clicked.connect(self.accept)
        shell_layout.addWidget(ok, 0, Qt.AlignRight)
        layout.addWidget(self.shell, 1)

    def mappings(self) -> list[BinaryWorkbenchInternalFileDTO]:
        rows: list[BinaryWorkbenchInternalFileDTO] = []
        for name, lba, _ in self._rows:
            if name.text().strip() and lba.text().strip():
                rows.append(BinaryWorkbenchInternalFileDTO(name=name.text().strip(), start_lba=int(lba.text().strip(), 0)))
        return rows

    def _build_entry(self, parent: QVBoxLayout) -> None:
        entry = QWidget(self.shell)
        row = QHBoxLayout(entry)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)
        self.name = _input(BINARY_WORKBENCH_TEXT.LBA_FILE_NAME, self.shell)
        self.lba = _input(BINARY_WORKBENCH_TEXT.LBA_START, self.shell)
        add = QPushButton(BINARY_WORKBENCH_TEXT.SYMBOL_ADD, self.shell)
        add.setObjectName("preferences-ok")
        add.setFixedSize(BINARY_WORKBENCH_LAYOUT.SYMBOL_ACTION_WIDTH, BINARY_WORKBENCH_LAYOUT.SYMBOL_INPUT_HEIGHT)
        add.clicked.connect(self._append_from_entry)
        row.addWidget(_field(BINARY_WORKBENCH_TEXT.LBA_FILE_NAME, self.name), 0)
        row.addWidget(_field(BINARY_WORKBENCH_TEXT.LBA_START, self.lba), 0)
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

    def _append_from_entry(self) -> None:
        self._append_row(self.name.text(), self.lba.text())
        self.name.clear()
        self.lba.clear()

    def _append_row(self, name: str, lba: str) -> None:
        row = QWidget(self.body)
        row.setObjectName("workspace-row")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        name_edit = _input(BINARY_WORKBENCH_TEXT.LBA_FILE_NAME, row, name)
        lba_edit = _input(BINARY_WORKBENCH_TEXT.LBA_START, row, lba)
        remove = QPushButton(row)
        remove.setObjectName("workspace-row-remove")
        remove.setIcon(Icons.remove())
        remove.setIconSize(QSize(WORKSPACE_TABLE_SIZE.REMOVE_ICON_SIZE, WORKSPACE_TABLE_SIZE.REMOVE_ICON_SIZE))
        remove.setFixedSize(WORKSPACE_TABLE_SIZE.REMOVE_BUTTON_WIDTH, WORKSPACE_TABLE_SIZE.REMOVE_BUTTON_HEIGHT)
        remove.clicked.connect(lambda: self._remove_row(row))
        layout.addWidget(name_edit, 0)
        layout.addWidget(lba_edit, 0)
        layout.addWidget(remove, 0, Qt.AlignVCenter)
        self._rows.append((name_edit, lba_edit, row))
        self.body_layout.addWidget(row, 0, Qt.AlignLeft)

    def _remove_row(self, row: QWidget) -> None:
        self._rows = [item for item in self._rows if item[2] is not row]
        row.deleteLater()


def _input(placeholder: str, parent: QWidget, value: str = "") -> QLineEdit:
    editor = QLineEdit(value, parent)
    editor.setObjectName("binary-workbench-dialog-input")
    editor.setPlaceholderText(placeholder)
    editor.setFixedSize(BINARY_WORKBENCH_LAYOUT.SYMBOL_FIELD_WIDTH, BINARY_WORKBENCH_LAYOUT.SYMBOL_INPUT_HEIGHT)
    return editor


def _label(text: str, object_name: str, parent: QWidget) -> QLabel:
    label = QLabel(text, parent)
    label.setObjectName(object_name)
    return label


def _field(text: str, widget: QWidget) -> QWidget:
    field = QWidget(widget.parentWidget())
    field.setFixedWidth(widget.width())
    layout = QVBoxLayout(field)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(4)
    layout.addWidget(_label(text, "preferences-section-title", field))
    layout.addWidget(widget, 0, Qt.AlignLeft)
    return field
