from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QWidget

from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.environment.symbols_dialog_widgets import (
    SymbolRemoveRowButton,
    symbol_input,
    symbol_kind_combo,
)
from src.presentation.ui.components.workspace_table.constants.layout import WORKSPACE_TABLE_SIZE


class SymbolsDialogRowsMixin:
    def values(self) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
        targets = {"Variable": {}, "Equate": {}, "Label": {}}
        for kind, name, value, _ in self._rows:
            if name.text().strip() and value.text().strip():
                targets[kind.currentText()][name.text().strip()] = value.text().strip()
        return targets["Variable"], targets["Equate"], targets["Label"]

    def _load_rows(self, variables: dict[str, str], equates: dict[str, str], labels: dict[str, str]) -> None:
        for kind, items in (("Variable", variables), ("Equate", equates), ("Label", labels)):
            for name, value in items.items():
                self._append_row(kind, str(name), str(value))

    def _append_from_entry(self) -> None:
        self._append_row(self.kind.currentText(), self.name.text(), self.value.text())
        self.name.clear()
        self.value.clear()

    def _clear_rows(self) -> None:
        for _, _, _, row in self._rows:
            row.deleteLater()
        self._rows.clear()

    def _append_row(self, kind: str, name: str, value: str) -> None:
        row = QWidget(self.body)
        row.setObjectName("workspace-row")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        kind_combo = symbol_kind_combo(row, kind)
        name_edit = symbol_input(BINARY_WORKBENCH_TEXT.SYMBOL_NAME, row, name)
        value_edit = symbol_input(BINARY_WORKBENCH_TEXT.SYMBOL_VALUE, row, value)
        remove = SymbolRemoveRowButton(row)
        remove.setFixedSize(WORKSPACE_TABLE_SIZE.REMOVE_BUTTON_WIDTH, WORKSPACE_TABLE_SIZE.REMOVE_BUTTON_HEIGHT)
        remove.clicked.connect(lambda: self._remove_row(row))
        layout.addWidget(kind_combo, 0)
        layout.addWidget(name_edit, 0)
        layout.addWidget(value_edit, 0)
        layout.addWidget(remove, 0, Qt.AlignVCenter)
        self._rows.append((kind_combo, name_edit, value_edit, row))
        self.body_layout.addWidget(row, 0, Qt.AlignLeft)

    def _remove_row(self, row: QWidget) -> None:
        self._rows = [item for item in self._rows if item[3] is not row]
        row.deleteLater()
