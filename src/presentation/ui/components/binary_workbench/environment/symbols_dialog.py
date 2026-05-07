from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QComboBox, QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea, QVBoxLayout, QWidget

from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.workspace_table.constants.layout import WORKSPACE_TABLE_SIZE
from src.presentation.ui.design.icons import Icons


class BinaryWorkbenchSymbolsDialog(QDialog):
    def __init__(
        self,
        variables: dict[str, str],
        equates: dict[str, str],
        labels: dict[str, str],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("workspace-table-dialog")
        self.setWindowTitle(BINARY_WORKBENCH_TEXT.SYMBOLS_TITLE)
        self.setMinimumSize(780, 420)
        self.resize(920, 560)
        self._rows: list[tuple[str, QLineEdit, QLineEdit, QWidget]] = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 30, 20, 20)
        self.shell = QFrame(self)
        self.shell.setObjectName("workspace-table-shell")
        shell_layout = QVBoxLayout(self.shell)
        shell_layout.setContentsMargins(10, 10, 10, 0)
        shell_layout.setSpacing(12)
        shell_layout.addWidget(_label(BINARY_WORKBENCH_TEXT.SYMBOLS_TITLE, "workspace-table-title", self.shell))
        shell_layout.addWidget(_label(BINARY_WORKBENCH_TEXT.SYMBOLS_SUBTITLE, "help-subtitle", self.shell))
        self._build_entry(shell_layout)
        self.scroll = QScrollArea(self.shell)
        self.scroll.setObjectName("workspace-table-body-scroll")
        self.scroll.verticalScrollBar().setObjectName("workspace-table-scrollbar")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.body = QWidget(self.scroll)
        self.body.setObjectName("workspace-table-body")
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(0, 4, 0, 0)
        self.body_layout.setSpacing(10)
        self.body_layout.setAlignment(Qt.AlignTop)
        self.scroll.setWidget(self.body)
        self._load_rows(variables, equates, labels)
        shell_layout.addWidget(self.scroll, 1)
        ok = QPushButton("OK", self.shell)
        ok.setObjectName("preferences-ok")
        ok.clicked.connect(self.accept)
        shell_layout.addWidget(ok, 0, Qt.AlignRight)
        layout.addWidget(self.shell, 1)

    def values(self) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
        targets = {"Variable": {}, "Equate": {}, "Label": {}}
        for kind, name, value, _ in self._rows:
            if name.text().strip() and value.text().strip():
                targets[kind][name.text().strip()] = value.text().strip()
        return targets["Variable"], targets["Equate"], targets["Label"]

    def _build_entry(self, parent: QVBoxLayout) -> None:
        row = QHBoxLayout()
        row.setSpacing(10)
        self.kind = QComboBox(self.shell)
        self.kind.setObjectName("binary-workbench-dialog-input")
        self.kind.addItems(["Variable", "Equate", "Label"])
        self.name = _input(BINARY_WORKBENCH_TEXT.SYMBOL_NAME, self.shell)
        self.value = _input(BINARY_WORKBENCH_TEXT.SYMBOL_VALUE, self.shell)
        add = QPushButton(BINARY_WORKBENCH_TEXT.SYMBOL_ADD, self.shell)
        add.setObjectName("preferences-ok")
        add.clicked.connect(self._append_from_entry)
        row.addWidget(_field(BINARY_WORKBENCH_TEXT.SYMBOL_TYPE, self.kind), 1)
        row.addWidget(_field(BINARY_WORKBENCH_TEXT.SYMBOL_NAME, self.name), 2)
        row.addWidget(_field(BINARY_WORKBENCH_TEXT.SYMBOL_VALUE, self.value), 2)
        row.addWidget(add, 0, Qt.AlignBottom)
        parent.addLayout(row)

    def _load_rows(self, variables: dict[str, str], equates: dict[str, str], labels: dict[str, str]) -> None:
        for kind, items in (("Variable", variables), ("Equate", equates), ("Label", labels)):
            for name, value in items.items():
                self._append_row(kind, str(name), str(value))

    def _append_from_entry(self) -> None:
        self._append_row(self.kind.currentText(), self.name.text(), self.value.text())
        self.name.clear()
        self.value.clear()

    def _append_row(self, kind: str, name: str, value: str) -> None:
        row = QWidget(self.body)
        row.setObjectName("workspace-row")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        name_edit = _input(BINARY_WORKBENCH_TEXT.SYMBOL_NAME, row, name)
        value_edit = _input(BINARY_WORKBENCH_TEXT.SYMBOL_VALUE, row, value)
        remove = QPushButton(row)
        remove.setObjectName("workspace-row-remove")
        remove.setIcon(Icons.remove())
        remove.setIconSize(QSize(WORKSPACE_TABLE_SIZE.REMOVE_ICON_SIZE, WORKSPACE_TABLE_SIZE.REMOVE_ICON_SIZE))
        remove.setFixedSize(WORKSPACE_TABLE_SIZE.REMOVE_BUTTON_WIDTH, WORKSPACE_TABLE_SIZE.REMOVE_BUTTON_HEIGHT)
        remove.clicked.connect(lambda: self._remove_row(row))
        layout.addWidget(_label(kind, "workspace-row-cell", row), 1)
        layout.addWidget(name_edit, 2)
        layout.addWidget(value_edit, 2)
        layout.addWidget(remove, 0, Qt.AlignVCenter)
        self._rows.append((kind, name_edit, value_edit, row))
        self.body_layout.addWidget(row)

    def _remove_row(self, row: QWidget) -> None:
        self._rows = [item for item in self._rows if item[3] is not row]
        row.deleteLater()


def _input(placeholder: str, parent: QWidget, value: str = "") -> QLineEdit:
    editor = QLineEdit(value, parent)
    editor.setObjectName("binary-workbench-dialog-input")
    editor.setPlaceholderText(placeholder)
    return editor


def _label(text: str, object_name: str, parent: QWidget) -> QLabel:
    label = QLabel(text, parent)
    label.setObjectName(object_name)
    return label


def _field(text: str, widget: QWidget) -> QWidget:
    field = QWidget(widget.parentWidget())
    layout = QVBoxLayout(field)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(4)
    layout.addWidget(_label(text, "preferences-section-title", field))
    layout.addWidget(widget)
    return field
